"""
core.py - Förderverein Grundschule: Abrechnungs-Kernlogik
Plattformunabhängig für Windows, Web (NiceGUI/FastAPI) und Mobile.
"""

__app_name__ = "Förderverein Grundschule – Abrechnungs-Manager"
__version__ = "0.2.0"

import os
import re
import sys
import json
import urllib.request
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional, Any

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pypdf import PdfWriter, PdfReader


# ==============================================================================
# 0. PFAD- UND VERZEICHNIS-INITIALISIERUNG
# ==============================================================================
def get_base_dir() -> str:
    """Ermittelt den echten Basispfad (auch bei gepackter PyInstaller .exe)."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.path.dirname(sys.executable))
    return os.path.abspath(os.path.dirname(__file__))


BASE_DIR = get_base_dir()
CACHE_DIR = os.path.join(BASE_DIR, "cache")
EXPORT_DIR = os.path.join(BASE_DIR, "Exportierte Rechnungen")
UPLOADS_DIR = os.path.join(CACHE_DIR, "uploads")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

FILE_STAMM = os.path.join(CACHE_DIR, "stammdaten.json")
FILE_ENTWURF = os.path.join(CACHE_DIR, "aktueller_entwurf.json")


# ==============================================================================
# 1. FERIEN-MANAGEMENT FÜR BADEN-WÜRTTEMBERG
# ==============================================================================
class FerienManagerBW:
    """Verwaltet BW-Schulferien mit Online-API, JSON-Cache und Offline-Fallback."""
    CACHE_FILE = os.path.join(CACHE_DIR, "ferien_cache_bw.json")
    API_URL = "https://openholidaysapi.org/SchoolHolidays?countryIsoCode=DE&subdivisionCode=DE-BW"

    def __init__(self):
        self.ferien_liste: List[Dict[str, Any]] = []
        self._ferien_laden()

    def _ferien_laden(self) -> None:
        # 1. Online-Abruf
        try:
            req = urllib.request.Request(
                self.API_URL,
                headers={"User-Agent": f"FoerdervereinAbrechnung/{__version__}"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    daten = json.loads(resp.read().decode("utf-8"))
                    self._parse_api_daten(daten)
                    with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(daten, f, ensure_ascii=False, indent=2)
                    return
        except Exception:
            pass

        # 2. Lokaler Cache
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    self._parse_api_daten(daten)
                    return
            except Exception:
                pass

        # 3. Offline-Fallback
        self._lade_fallback_daten()

    def _parse_api_daten(self, raw_daten: List[Dict[str, Any]]) -> None:
        self.ferien_liste = []
        for item in raw_daten:
            try:
                start = datetime.strptime(item.get("startDate", ""), "%Y-%m-%d").date()
                end = datetime.strptime(item.get("endDate", ""), "%Y-%m-%d").date()
                name_list = item.get("name", [])
                name = name_list[0].get("text", "Ferien") if name_list else "Schulferien"
                self.ferien_liste.append({"name": name, "start": start, "end": end})
            except Exception:
                continue
        self.ferien_liste.sort(key=lambda x: x["start"])

    def _lade_fallback_daten(self) -> None:
        fallback_eintraege = [
            ("Sommerferien 2026", "2026-07-30", "2026-09-12"),
            ("Herbstferien 2026", "2026-10-26", "2026-10-31"),
            ("Weihnachtsferien 2026/27", "2026-12-23", "2027-01-09"),
            ("Osterferien 2027", "2027-03-25", "2027-04-03"),
            ("Pfingstferien 2027", "2027-05-18", "2027-05-29"),
            ("Sommerferien 2027", "2027-07-29", "2027-09-11"),
        ]
        self.ferien_liste = []
        for name, s, e in fallback_eintraege:
            self.ferien_liste.append({
                "name": name,
                "start": datetime.strptime(s, "%Y-%m-%d").date(),
                "end": datetime.strptime(e, "%Y-%m-%d").date()
            })
        self.ferien_liste.sort(key=lambda x: x["start"])

    def pruefe_in_ferien(self, pruef_datum: date) -> Optional[str]:
        """Prüft, ob das gegebene Datum in den Ferien liegt. Gibt den Namen der Ferien zurück."""
        for f in self.ferien_liste:
            if f["start"] <= pruef_datum <= f["end"]:
                return f["name"]
        return None

    def ermittle_abrechnungszeitraum(self, kurs_datum: date) -> Tuple[Optional[date], Optional[date], str]:
        """
        Ermittelt das Fenster 'Ferienende vorherige Ferien' bis 'Ferienende Folgeferien'.
        Rückgabe: (start_datum, end_datum, bezeichnung_string)
        """
        if not self.ferien_liste:
            return None, None, "Abrechnungszeitraum flexibel"

        vor_ferien = None
        folge_ferien = None

        for f in self.ferien_liste:
            if f["end"] < kurs_datum:
                vor_ferien = f
            elif f["end"] >= kurs_datum and folge_ferien is None:
                folge_ferien = f

        if vor_ferien and folge_ferien:
            p_start = vor_ferien["end"] + timedelta(days=1)
            p_ende = folge_ferien["end"]
            return p_start, p_ende, f"Ende {vor_ferien['name']} bis Ende {folge_ferien['name']}"
        elif folge_ferien:
            return folge_ferien["start"] - timedelta(days=60), folge_ferien["end"], f"Bis Ende {folge_ferien['name']}"
        elif vor_ferien:
            return vor_ferien["end"] + timedelta(days=1), vor_ferien["end"] + timedelta(days=70), f"Ab Ende {vor_ferien['name']}"

        return None, None, "Zeitraum nicht eindeutig"


ferien_mgr = FerienManagerBW()


# ==============================================================================
# 2. VALIDIERUNG & DATEN-HILFSFUNKTIONEN
# ==============================================================================
def parse_datum(datum_str: str, feldname: str = "Datum") -> Tuple[Optional[date], Optional[str]]:
    """
    Parst deutsche Formate (TT.MM.JJJJ, TT.MM.JJ) oder ISO (JJJJ-MM-TT).
    Verhindert Datumsangaben in der Zukunft.
    """
    s = datum_str.strip()
    if not s:
        return None, f"Bitte ein {feldname} angeben."

    parsed = None
    for fmt in ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]:
        try:
            parsed = datetime.strptime(s, fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        return None, f"Ungültiges Format für {feldname} ('{s}'). Bitte TT.MM.JJJJ verwenden."

    if parsed > date.today():
        return None, f"Das {feldname} ({s}) liegt in der Zukunft. Termine in der Zukunft sind unzulässig."

    return parsed, None


def clean_filename(name: str) -> str:
    """Bereinigt Strings für Dateinamen (keine unerlaubten Sonderzeichen)."""
    clean = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß_-]", "_", name.strip())
    clean = re.sub(r"_+", "_", clean)
    return clean.strip("_")


def pruefe_beleg_plausibilitaet(beleg_datum: date, kurs_datum: Optional[date]) -> Tuple[bool, str, str]:
    """
    Prüft Belegdatum gegen den Abrechnungszeitraum mit 4-Wochen-Puffer.
    Rückgabe: (ist_ok, warn_status, nachricht)
    warn_status: 'ok', 'vorlauf', 'nachlauf', 'alt'
    """
    if not kurs_datum:
        return True, "ok", ""

    p_start, p_ende, p_name = ferien_mgr.ermittle_abrechnungszeitraum(kurs_datum)
    if not p_start or not p_ende:
        return True, "ok", ""

    if beleg_datum > p_ende:
        return False, "nachlauf", (
            f"Das Belegdatum ({beleg_datum.strftime('%d.%m.%Y')}) liegt nach dem Ende "
            f"des aktuellen Abrechnungszeitraums ({p_ende.strftime('%d.%m.%Y')})."
        )

    puffer_start = p_start - timedelta(days=28)
    if beleg_datum < p_start:
        if beleg_datum >= puffer_start:
            return True, "vorlauf", (
                f"Vorlauf-Kauf ({beleg_datum.strftime('%d.%m.%Y')}, bis zu 4 Wochen vor Periodenstart). "
                f"Bitte prüfen, ob es sich um haltbaren Sachbedarf handelt."
            )
        else:
            return False, "alt", (
                f"Der Beleg ({beleg_datum.strftime('%d.%m.%Y')}) liegt mehr als 4 Wochen "
                f"vor Beginn des Abrechnungszeitraums ({p_name})."
            )

    return True, "ok", ""


def berechne_summen(kurs_dauer_str: str, stundensatz_str: str, belege: List[Dict[str, Any]]) -> Dict[str, float]:
    """Berechnet Arbeitsstunden, Honorar, Materialauslagen und Gesamtsumme."""
    try:
        dauer = float(kurs_dauer_str.replace(",", "."))
    except (ValueError, AttributeError):
        dauer = 0.0

    try:
        satz = float(stundensatz_str.replace(",", "."))
    except (ValueError, AttributeError):
        satz = 0.0

    honorar = dauer * satz
    auslagen = sum(b.get("betrag", 0.0) for b in belege)
    gesamt = honorar + auslagen

    return {
        "dauer": dauer,
        "satz": satz,
        "honorar": honorar,
        "auslagen": auslagen,
        "gesamt": gesamt
    }


def generiere_standard_dateinamen(kurs_datum_str: str, kurs_titel: str, kursleiter: str) -> str:
    """Erzeugt das Schema: Abrechnung_JJJJ-MM-TT_Kurstitel_Kursleiter.pdf."""
    kd_parsed, _ = parse_datum(kurs_datum_str, "Kursdatum")
    datum_str = kd_parsed.strftime("%Y-%m-%d") if kd_parsed else date.today().strftime("%Y-%m-%d")
    t_clean = clean_filename(kurs_titel) or "Kurs"
    l_clean = clean_filename(kursleiter) or "Abrechnung"
    return f"Abrechnung_{datum_str}_{t_clean}_{l_clean}.pdf"


# ==============================================================================
# 3. AUTOSAVE & PERSISTENZ (JSON)
# ==============================================================================
def lade_stammdaten() -> Dict[str, str]:
    daten = {"leiter": "", "iban": "", "satz": "20.00"}
    if os.path.exists(FILE_STAMM):
        try:
            with open(FILE_STAMM, "r", encoding="utf-8") as f:
                daten.update(json.load(f))
        except Exception:
            pass
    return daten


def speichere_stammdaten(stamm: Dict[str, str]) -> None:
    try:
        with open(FILE_STAMM, "w", encoding="utf-8") as f:
            json.dump(stamm, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def lade_entwurf() -> Dict[str, Any]:
    daten = {"titel": "", "ag": "", "datum": "", "dauer": "2.0", "belege": []}
    if os.path.exists(FILE_ENTWURF):
        try:
            with open(FILE_ENTWURF, "r", encoding="utf-8") as f:
                daten.update(json.load(f))
        except Exception:
            pass
    return daten


def speichere_entwurf(kurs: Dict[str, Any], belege: List[Dict[str, Any]]) -> None:
    payload = {
        "titel": kurs.get("titel", ""),
        "ag": kurs.get("ag", ""),
        "datum": kurs.get("datum", ""),
        "dauer": kurs.get("dauer", "2.0"),
        "belege": belege
    }
    try:
        with open(FILE_ENTWURF, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def loesche_entwurf() -> None:
    if os.path.exists(FILE_ENTWURF):
        try:
            os.remove(FILE_ENTWURF)
        except Exception:
            pass


# ==============================================================================
# 4. PDF-GENERIERUNG & BELEG-MERGE
# ==============================================================================
def erzeuge_abrechnung_pdf(stamm: Dict[str, str], kurs: Dict[str, Any], belege: List[Dict[str, Any]], zielpfad: str) -> None:
    """Rendert Deckblatt und hängt alle hinterlegten Belege (Bilder oder PDFs) hinten an."""
    deckblatt_temp = os.path.join(CACHE_DIR, "temp_deckblatt.pdf")
    doc = SimpleDocTemplate(deckblatt_temp, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    FARBE_PRIM = colors.HexColor("#1e3d59")
    FARBE_SEK = colors.HexColor("#d97706")
    FARBE_BG_HELL = colors.HexColor("#f8fafc")
    FARBE_BORDER = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=FARBE_PRIM
    )

    elements = []

    # Kopf
    kopf_tabelle = Table([
        [Paragraph("<b>FÖRDERVEREIN DER GRUNDSCHULE E.V.</b>", title_style),
         Paragraph(f"<font color='#666666'>Abrechnung v{__version__}</font>", styles['Normal'])],
        [Paragraph("<i>Abrechnung über Aufwandsentschädigung & Materialauslagen für Schul-AGs</i>", styles['Normal']), ""]
    ], colWidths=[380, 140])
    kopf_tabelle.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(kopf_tabelle)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=FARBE_SEK, spaceAfter=15))

    # Stammdaten
    parsed_kd, _ = parse_datum(kurs.get("datum", ""), "Kursdatum")
    _, _, p_name = ferien_mgr.ermittle_abrechnungszeitraum(parsed_kd) if parsed_kd else (None, None, "–")

    stamm_rows = [
        ["Kursleiter / Auftragnehmer:", stamm.get("leiter", "") or "–", "Kurstitel:", kurs.get("titel", "") or "–"],
        ["IBAN:", stamm.get("iban", "") or "–", "Gruppe / Klasse:", kurs.get("ag", "") or "–"],
        ["Vereinbarter Stundensatz:", f"{stamm.get('satz', '0')} €/h", "Abrechnungszeitraum:", p_name]
    ]
    t_stamm = Table(stamm_rows, colWidths=[140, 160, 110, 110])
    t_stamm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FARBE_BG_HELL),
        ('BOX', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_stamm)
    elements.append(Spacer(1, 15))

    # 1. Leistung
    summen = berechne_summen(kurs.get("dauer", "0"), stamm.get("satz", "0"), belege)
    dauer = summen["dauer"]
    honorar = summen["honorar"]

    elements.append(Paragraph("<b>1. Erbrachte Kursleistung</b>", styles['Heading3']))
    t_std = Table([
        ["Datum", "Kursbezeichnung / Inhalt", "Dauer", "Honoraranspruch"],
        [kurs.get("datum", ""), f"{kurs.get('titel', '')} ({kurs.get('ag', '')})", f"{dauer:.2f} Std.", f"{honorar:.2f} €"]
    ], colWidths=[80, 260, 90, 90])
    t_std.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_std)
    elements.append(Spacer(1, 15))

    # 2. Auslagen
    elements.append(Paragraph("<b>2. Auslagen für Kursmaterialien</b>", styles['Heading3']))
    t_bel_data = [["Datum", "Händler / Verwendungszweck", "Belegnachweis", "Betrag"]]
    idx = 1
    for b in belege:
        nachweis = f"Anhang #{idx}" if b.get("datei") else "Eigenbeleg/Kein Anhang"
        t_bel_data.append([b.get("datum", ""), b.get("zweck", ""), nachweis, f"{b.get('betrag', 0.0):.2f} €"])
        idx += 1

    gesamt_auslagen = summen["auslagen"]
    if not belege:
        t_bel_data.append(["–", "Keine Materialauslagen geltend gemacht", "–", "0.00 €"])
    t_bel_data.append(["Gesamtsumme Auslagen:", "", "", f"{gesamt_auslagen:.2f} €"])

    t_bel = Table(t_bel_data, colWidths=[80, 250, 100, 90])
    t_bel.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_bel)
    elements.append(Spacer(1, 18))

    # 3. Summe
    gesamt = summen["gesamt"]
    t_sum = Table([["Zur Auszahlung fälliger Gesamtbetrag:", f"{gesamt:.2f} €"]], colWidths=[370, 150])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#dcfce7")),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#14532d")),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#16a34a")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 28))

    # 4. Unterschriften
    t_sig = Table([
        ["________________________________________", "________________________________________"],
        ["Datum, Unterschrift Kursleiter", "Datum, Sachlich richtig / Vorstand Förderverein"]
    ], colWidths=[260, 260])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, 1), 8.5),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor("#334155")),
    ]))
    elements.append(t_sig)

    doc.build(elements)

    # Belege anhängen via PyPDF
    writer = PdfWriter()
    reader_deckblatt = PdfReader(deckblatt_temp)
    for p in reader_deckblatt.pages:
        writer.add_page(p)

    beleg_idx = 1
    for b in belege:
        d = b.get("datei")
        if not d or not os.path.exists(d):
            continue

        ext = os.path.splitext(d)[1].lower()
        if ext == ".pdf":
            try:
                r_bel = PdfReader(d)
                for p in r_bel.pages:
                    writer.add_page(p)
            except Exception:
                pass
        elif ext in [".jpg", ".jpeg", ".png"]:
            temp_img_pdf = os.path.join(CACHE_DIR, f"temp_bel_{beleg_idx}.pdf")
            img_doc = SimpleDocTemplate(temp_img_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            img_elems = [
                Paragraph(f"<b>Beleg #{beleg_idx}: {b.get('zweck', '')} ({b.get('betrag', 0.0):.2f} €)</b>", styles['Normal']),
                Spacer(1, 10)
            ]

            im = Image.open(d)
            w, h = im.size
            scale = min(500 / w, 700 / h, 1.0)
            from reportlab.platypus import Image as RLImage
            img_elems.append(RLImage(d, width=w * scale, height=h * scale))
            img_doc.build(img_elems)

            r_img = PdfReader(temp_img_pdf)
            for p in r_img.pages:
                writer.add_page(p)
            if os.path.exists(temp_img_pdf):
                os.remove(temp_img_pdf)

        beleg_idx += 1

    with open(zielpfad, "wb") as f_out:
        writer.write(f_out)

    if os.path.exists(deckblatt_temp):
        os.remove(deckblatt_temp)
"""
core.py - Förderverein Grundschule: Abrechnungs-Kernlogik
Plattformunabhängig für Windows, Web (NiceGUI/FastAPI) und Mobile.
"""

__app_name__ = "Förderverein Grundschule – Abrechnungs-Manager"
__version__ = "0.5.2"

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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Flowable
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
    API_URLS = [
        "https://ferien-api.de/api/v1/holidays/BW",
        "https://openholidaysapi.org/SchoolHolidays?countryIsoCode=DE&subdivisionCode=DE-BW"
    ]

    def __init__(self):
        self.ferien_liste: List[Dict[str, Any]] = []
        self._ferien_laden()

    def _ferien_laden(self) -> None:
        # 1. Online-Abruf über primäre und Fallback-APIs
        for url in self.API_URLS:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": f"FoerdervereinAbrechnung/{__version__}"}
                )
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        daten = json.loads(resp.read().decode("utf-8"))
                        if daten and isinstance(daten, list):
                            self._parse_api_daten(daten)
                            if self.ferien_liste:
                                with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                                    json.dump(daten, f, ensure_ascii=False, indent=2)
                                return
            except Exception:
                continue

        # 2. Lokaler Cache
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    self._parse_api_daten(daten)
                    if self.ferien_liste:
                        return
            except Exception:
                pass

        # 3. Offline-Fallback (Lückenlose BW-Ferienliste 2024–2028)
        self._lade_fallback_daten()

    def _parse_api_daten(self, raw_daten: List[Dict[str, Any]]) -> None:
        self.ferien_liste = []
        for item in raw_daten:
            try:
                # Unterstützt sowohl openholidaysapi (startDate/endDate) als auch ferien-api.de (start/end)
                s_val = item.get("startDate") or item.get("start") or ""
                e_val = item.get("endDate") or item.get("end") or ""
                if not s_val or not e_val:
                    continue
                start = datetime.strptime(str(s_val)[:10], "%Y-%m-%d").date()
                end = datetime.strptime(str(e_val)[:10], "%Y-%m-%d").date()

                name = "Schulferien"
                name_field = item.get("name")
                if isinstance(name_field, list) and name_field:
                    name = name_field[0].get("text", "Schulferien")
                elif isinstance(name_field, str):
                    # Bei ferien-api.de kommen englische Namen wie 'autumn', 'christmas'
                    de_names = {
                        "autumn": "Herbstferien",
                        "christmas": "Weihnachtsferien",
                        "easter": "Osterferien",
                        "pentecost": "Pfingstferien",
                        "summer": "Sommerferien",
                        "winter": "Winterferien"
                    }
                    name = de_names.get(name_field.lower(), name_field.capitalize())

                self.ferien_liste.append({"name": name, "start": start, "end": end})
            except Exception:
                continue
        self.ferien_liste.sort(key=lambda x: x["start"])

    def _lade_fallback_daten(self) -> None:
        fallback_eintraege = [
            # Schuljahr 2024/2025
            ("Herbstferien 2024", "2024-10-28", "2024-10-31"),
            ("Weihnachtsferien 2024/25", "2024-12-23", "2025-01-04"),
            ("Osterferien 2025", "2025-04-14", "2025-04-26"),
            ("Pfingstferien 2025", "2025-06-10", "2025-06-20"),
            ("Sommerferien 2025", "2025-07-31", "2025-09-13"),
            # Schuljahr 2025/2026
            ("Herbstferien 2025", "2025-10-27", "2025-10-30"),
            ("Weihnachtsferien 2025/26", "2025-12-22", "2026-01-05"),
            ("Osterferien 2026", "2026-03-30", "2026-04-10"),
            ("Pfingstferien 2026", "2026-05-26", "2026-06-05"),
            ("Sommerferien 2026", "2026-07-30", "2026-09-12"),
            # Schuljahr 2026/2027
            ("Herbstferien 2026", "2026-10-26", "2026-10-31"),
            ("Weihnachtsferien 2026/27", "2026-12-23", "2027-01-09"),
            ("Osterferien 2027", "2027-03-25", "2027-04-03"),
            ("Pfingstferien 2027", "2027-05-18", "2027-05-29"),
            ("Sommerferien 2027", "2027-07-29", "2027-09-11"),
            # Schuljahr 2027/2028
            ("Herbstferien 2027", "2027-11-02", "2027-11-06"),
            ("Weihnachtsferien 2027/28", "2027-12-23", "2028-01-08"),
            ("Osterferien 2028", "2028-04-10", "2028-04-21"),
            ("Pfingstferien 2028", "2028-06-06", "2028-06-16"),
            ("Sommerferien 2028", "2028-07-27", "2028-09-09"),
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
def ermittle_schuljahr(datum: date) -> str:
    """Gibt das Schuljahr als 'SJyyzz' zurück (z.B. SJ2627 für Schuljahr 2026/2027). Stichtag 1. August."""
    y = datum.year
    if datum.month >= 8:
        start_y = y % 100
        end_y = (y + 1) % 100
    else:
        start_y = (y - 1) % 100
        end_y = y % 100
    return f"SJ{start_y:02d}{end_y:02d}"


def generiere_kurs_id_vorschlag(kurs_titel: str, kurs_datum_str: str = "") -> str:
    """Erzeugt einen eindeutigen ID-Vorschlag wie 'SJ2627-SCHACH-01' nach Option 1."""
    kd_parsed, _ = parse_datum(kurs_datum_str, "Kursdatum")
    d = kd_parsed or date.today()
    sj = ermittle_schuljahr(d)

    clean = clean_filename(kurs_titel).upper()
    clean = re.sub(r"[^A-Z0-9]", "", clean)
    kuerzel = clean[:6] if clean else "KURS"
    return f"{sj}-{kuerzel}-01"


def validiere_kurs_id(kurs_id: str) -> Tuple[bool, Optional[str]]:
    """Prüft, ob die Kurs-ID angegeben und zulässig aufgebaut ist."""
    s = str(kurs_id).strip()
    if not s:
        return False, "Bitte eine Kurs-ID angeben (z. B. SJ2627-SCHACH-01)."
    if not re.match(r"^[A-Za-z0-9_-]{3,30}$", s):
        return False, "Die Kurs-ID darf nur aus Buchstaben, Ziffern und Bindestrichen bestehen (3–30 Zeichen)."
    return True, None


def validiere_iban(iban: str) -> Tuple[bool, Optional[str]]:
    """
    Validiert eine 22-stellige deutsche IBAN nach ISO 7064 (Modulo 97-10).
    Prüft:
      1. Nicht leer
      2. Genau 22 Stellen (nach Entfernung von Leerzeichen)
      3. Start mit Länder-Code 'DE'
      4. Nach 'DE' genau 20 Ziffern (2 Prüfziffern + 8 BLZ + 10 Kontonummer)
      5. Modulo-97-Prüfsumme == 1
    Rückgabe: (ist_gueltig, fehlermeldung_oder_none)
    """
    if not iban or not isinstance(iban, str):
        return False, "Bitte eine IBAN angeben."

    cleaned = iban.replace(" ", "").strip().upper()
    if not cleaned:
        return False, "Bitte eine IBAN angeben."

    if len(cleaned) != 22:
        return False, f"Eine deutsche IBAN muss genau 22 Zeichen lang sein (aktuell: {len(cleaned)} Zeichen)."

    if not cleaned.startswith("DE"):
        return False, "Es werden aktuell nur deutsche IBANs unterstützt (muss mit 'DE' beginnen)."

    if not cleaned[2:].isdigit():
        return False, "Die deutsche IBAN darf nach 'DE' nur aus 20 Ziffern bestehen."

    # ISO 7064 Modulo 97-10 Algorithmus:
    rearranged = cleaned[4:] + cleaned[:4]
    num_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)

    try:
        if int(num_str) % 97 != 1:
            return False, "Ungültige IBAN-Prüfsumme (Prüfziffern stimmen nicht. Bitte auf Tippfehler prüfen)."
    except ValueError:
        return False, "IBAN konnte nicht numerisch validiert werden."

    return True, None


def formatiere_iban(iban: str) -> str:
    """Formatiert eine IBAN in übersichtliche 4er-Blöcke (z. B. DE89 3704 0044 0532 0130 00)."""
    cleaned = iban.replace(" ", "").strip().upper()
    if not cleaned:
        return ""
    return " ".join(cleaned[i:i + 4] for i in range(0, len(cleaned), 4))


def pruefe_wochenende(pruef_datum: date) -> Optional[str]:
    """Prüft, ob ein Datum auf Samstag oder Sonntag fällt."""
    if pruef_datum.weekday() == 5:
        return "Samstag"
    elif pruef_datum.weekday() == 6:
        return "Sonntag"
    return None


def pruefe_kursdatum_plausibilitaet(kurs_datum: date, einreich_datum: Optional[date] = None) -> List[Dict[str, str]]:
    """
    Validiert das Kursdatum anhand der BW-Ferien und Schuljahresregeln:
    1. Harte Warnung: Einreichung außerhalb des laufenden Schuljahrs (Abrechnungsfrist verpasst).
    2. Weiche Warnung: Einreichung nach Ablauf des regulären Abrechnungszeitraums (Ferienende bis Ferienende), aber noch im laufenden Schuljahr.
    3. Ferien-Warnung: Kurstag fällt direkt in Schulferien (BW).
    4. Wochenend-Warnung: Kurstag fällt auf Samstag/Sonntag.

    Rückgabe: Liste von Warnungs-Dicts: [{"level": "hart"|"weich", "titel": "...", "nachricht": "..."}]
    """
    heute = einreich_datum or date.today()
    warnungen: List[Dict[str, str]] = []

    kurs_sj = ermittle_schuljahr(kurs_datum)
    aktuelles_sj = ermittle_schuljahr(heute)

    # 1. Schuljahr-Prüfung: Liegt der Termin in einem vergangenen Schuljahr? -> HARTE WARNUNG
    if kurs_datum < heute and kurs_sj != aktuelles_sj:
        warnungen.append({
            "level": "hart",
            "titel": "Abrechnungszeitraum verpasst (Schuljahr abgelaufen)",
            "nachricht": (
                f"Der Kurstermin ({kurs_datum.strftime('%d.%m.%Y')}) liegt im vorherigen Schuljahr ({kurs_sj}).\n"
                f"Die reguläre Frist zur Abrechnung im laufenden Schuljahr ({aktuelles_sj}) ist bereits abgelaufen.\n\n"
                f"Eine Abrechnung erfordert die ausdrückliche Sondergenehmigung des Vorstands."
            )
        })

    # 2. Abrechnungszeitraum: Grundsätzlich Ferienende bis Ferienende -> WEICHE WARNUNG
    p_start, p_ende, p_name = ferien_mgr.ermittle_abrechnungszeitraum(kurs_datum)
    if p_ende and heute > p_ende and kurs_sj == aktuelles_sj:
        warnungen.append({
            "level": "weich",
            "titel": "Abrechnungszeitraum überschritten (Weiche Warnung)",
            "nachricht": (
                f"Der Kurstermin ({kurs_datum.strftime('%d.%m.%Y')}) gehört zum Abrechnungszeitraum '{p_name}'.\n"
                f"Das reguläre Zeitfenster endete am {p_ende.strftime('%d.%m.%Y')}.\n\n"
                f"Da der Termin noch im laufenden Schuljahr ({aktuelles_sj}) liegt, kann die Abrechnung eingereicht werden."
            )
        })

    # 3. Liegt der Kurstag selbst in den Ferien?
    ferien_name = ferien_mgr.pruefe_in_ferien(kurs_datum)
    if ferien_name:
        warnungen.append({
            "level": "weich",
            "titel": "Kurstag in den Ferien",
            "nachricht": (
                f"Der Kurstag ({kurs_datum.strftime('%d.%m.%Y')}) liegt in den {ferien_name} (BW).\n\n"
                f"Handelt es sich um ein Ferienprogramm oder einen Sondertermin?"
            )
        })

    # 4. Liegt der Kurstag am Wochenende?
    wochenend_tag = pruefe_wochenende(kurs_datum)
    if wochenend_tag:
        warnungen.append({
            "level": "weich",
            "titel": "Kurstag am Wochenende",
            "nachricht": (
                f"Der Kurstag ({kurs_datum.strftime('%d.%m.%Y')}) fällt auf einen {wochenend_tag}.\n\n"
                f"Handelt es sich um eine Wochenend-Veranstaltung?"
            )
        })

    return warnungen


def validiere_kurs_dauer(dauer_str: str) -> Tuple[bool, float, Optional[str]]:
    """
    Prüft die Kursdauer auf das zulässige Intervall von 1 bis 480 Minuten (ca. 0.02 bis 8.0 Std.).
    Rückgabe: (ist_ok, dauer_in_stunden, fehlermeldung_oder_none)
    """
    try:
        val = float(str(dauer_str).replace(",", ".").strip())
    except (ValueError, AttributeError):
        return False, 0.0, "Bitte eine gültige Kursdauer in Stunden angeben (z. B. 2.0 oder 1.5)."

    minuten = val * 60.0
    if minuten < 1:
        return False, val, "Die Kursdauer muss mindestens 1 Minute betragen."
    if minuten > 480:
        return False, val, "Die Kursdauer darf maximal 480 Minuten (8.0 Stunden) pro Abrechnungstag betragen."

    return True, val, None


def parse_datum(datum_str: str, feldname: str = "Datum") -> Tuple[Optional[date], Optional[str]]:
    """
    Parst deutsche Formate (TT.MM.JJJJ, TT.MM.JJ) oder ISO (JJJJ-MM-TT).
    Verhindert Datumsangaben in der Zukunft.
    """
    s = str(datum_str).strip()
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
    clean = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß_-]", "_", str(name).strip())
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
        dauer = float(str(kurs_dauer_str).replace(",", "."))
    except (ValueError, AttributeError):
        dauer = 0.0

    try:
        satz = float(str(stundensatz_str).replace(",", "."))
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


def generiere_standard_dateinamen(kurs_datum_str: str, kurs_titel: str, kursleiter: str, kurs_id: str = "") -> str:
    """
    Erzeugt das feste Schema für Kassenwart-Apps:
    Abrechnung_[KursID]_[JJJJ-MM-TT]_[Kursleiter].pdf
    """
    kd_parsed, _ = parse_datum(kurs_datum_str, "Kursdatum")
    datum_str = kd_parsed.strftime("%Y-%m-%d") if kd_parsed else date.today().strftime("%Y-%m-%d")
    kid_clean = clean_filename(kurs_id).upper() if kurs_id else "KURS"
    l_clean = clean_filename(kursleiter) or "Abrechnung"
    return f"Abrechnung_{kid_clean}_{datum_str}_{l_clean}.pdf"


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
    daten = {"id": "", "titel": "", "ag": "", "datum": "", "dauer": "2.0", "belege": []}
    if os.path.exists(FILE_ENTWURF):
        try:
            with open(FILE_ENTWURF, "r", encoding="utf-8") as f:
                daten.update(json.load(f))
        except Exception:
            pass
    return daten


def speichere_entwurf(kurs: Dict[str, Any], belege: List[Dict[str, Any]]) -> None:
    payload = {
        "id": kurs.get("id", ""),
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


def lese_abrechnung_aus_pdf(pdf_quelle: Any) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Liest eingebettete Abrechnungsdaten (abrechnungsdaten.json) aus einem bestehenden PDF aus.
    Ermöglicht das nahtlose Wiederöffnen und digitale Weiterbearbeiten alter Abrechnungen.
    Rückgabe: (erfolg, daten_dict, fehlermeldung_oder_none)
    """
    try:
        reader = PdfReader(pdf_quelle)

        # 1. Prüfen auf Attachment 'abrechnungsdaten.json'
        if hasattr(reader, "attachments") and reader.attachments:
            for name, val in reader.attachments.items():
                if name == "abrechnungsdaten.json":
                    data = None
                    if isinstance(val, list) and len(val) > 0:
                        item = val[0]
                        data = getattr(item, "data", None) or (item if isinstance(item, (bytes, bytearray)) else None)
                    elif hasattr(val, "data"):
                        data = val.data
                    elif isinstance(val, (bytes, bytearray)):
                        data = val
                    if data:
                        daten = json.loads(data.decode("utf-8"))
                        return True, daten, None

        # 2. Fallback: Metadaten
        meta = reader.metadata
        if meta and meta.get("/Keywords") and "KursID=" in meta.get("/Keywords", ""):
            kw = meta.get("/Keywords", "")
            kid = ""
            for part in kw.split(";"):
                if part.startswith("KursID="):
                    kid = part.split("=", 1)[1]
            return True, {
                "stammdaten": {"leiter": meta.get("/Author", ""), "iban": "", "satz": "20.00"},
                "kurs": {"id": kid, "titel": meta.get("/Title", ""), "ag": "", "datum": "", "dauer": "2.0"},
                "belege": []
            }, None

        return False, None, "In dieser PDF wurden keine maschinenlesbaren Abrechnungsdaten gefunden."
    except Exception as ex:
        return False, None, f"Fehler beim Einlesen der PDF: {str(ex)}"


# ==============================================================================
# 4. REPORTLAB INTERAKTIVE FORMULARFELDER (ACROFORMS)
# ==============================================================================
class InteractiveTextField(Flowable):
    """
    Platypus Flowable für interaktive PDF-Formularfelder (AcroForms).
    Ermöglicht direktes Ausfüllen per Tastatur in Adobe Acrobat, Edge, Chrome etc.
    """
    def __init__(self, name: str, width: float = 100, height: float = 16, default: str = "", tooltip: str = "", border_style: str = "solid"):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height
        self.default = default
        self.tooltip = tooltip or name
        self.border_style = border_style

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        # 1. Visueller weißer Eingabekasten mit sichtbarem Rahmen
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor("#94a3b8"))
        self.canv.setFillColor(colors.HexColor("#ffffff"))
        self.canv.setLineWidth(0.75)
        self.canv.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)
        self.canv.restoreState()

        # 2. Interaktives AcroForm-Feld an den echten absoluten Seitenkoordinaten platzieren
        try:
            abs_x, abs_y = self.canv.absolutePosition(0, 0)
            self.canv.acroForm.textfield(
                name=self.name,
                tooltip=self.tooltip,
                x=abs_x,
                y=abs_y,
                width=self.width,
                height=self.height,
                value=self.default,
                borderStyle=self.border_style,
                borderColor=colors.HexColor("#64748b"),
                fillColor=colors.HexColor("#ffffff"),
                textColor=colors.HexColor("#0f172a"),
                fontSize=8.5
            )
        except Exception:
            pass


# ==============================================================================
# 5. PDF-GENERIERUNG & BELEG-MERGE
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
        fontSize=15,
        leading=18,
        textColor=FARBE_PRIM
    )

    # Styles für Tabellenzellen, um Überlappungen absolut zu verhindern
    c_label = ParagraphStyle(
        'CLabel',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        fontName='Helvetica-Bold'
    )
    c_val = ParagraphStyle(
        'CVal',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        fontName='Helvetica'
    )
    c_val_bold = ParagraphStyle(
        'CValBold',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        fontName='Helvetica-Bold'
    )
    th_left = ParagraphStyle(
        'THLeft',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        fontName='Helvetica-Bold'
    )
    th_right = ParagraphStyle(
        'THRight',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10.5,
        alignment=2,
        textColor=colors.HexColor("#0f172a"),
        fontName='Helvetica-Bold'
    )
    td_right = ParagraphStyle(
        'TDRight',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=10.5,
        alignment=2,
        textColor=colors.HexColor("#0f172a"),
        fontName='Helvetica'
    )

    elements = []

    # Kopf
    kopf_tabelle = Table([
        [Paragraph("<b>FÖRDERVEREIN DER GRUNDSCHULE E.V.</b>", title_style),
         Paragraph(f"<font color='#666666'>Abrechnung v{__version__}</font>", styles['Normal'])],
        [Paragraph("<i>Abrechnung über Aufwandsentschädigung & Materialauslagen für Schul-AGs</i>", styles['Normal']), ""]
    ], colWidths=[383, 140])
    kopf_tabelle.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(kopf_tabelle)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=FARBE_SEK, spaceAfter=12))

    # Stammdaten & Kurs-Referenz (Gesamtbreite: 523pt)
    parsed_kd, _ = parse_datum(kurs.get("datum", ""), "Kursdatum")
    _, _, p_name = ferien_mgr.ermittle_abrechnungszeitraum(parsed_kd) if parsed_kd else (None, None, "–")

    formatiertes_iban = formatiere_iban(stamm.get("iban", "")) or "–"
    kid_text = kurs.get("id", "").strip() or "–"

    stamm_rows = [
        [
            Paragraph("Kursleiter / Auftragnehmer:", c_label),
            Paragraph(stamm.get("leiter", "") or "–", c_val_bold),
            Paragraph("Kurs-ID / Referenz:", c_label),
            Paragraph(kid_text, c_val_bold)
        ],
        [
            Paragraph("IBAN:", c_label),
            Paragraph(formatiertes_iban, c_val),
            Paragraph("Kurstitel:", c_label),
            Paragraph(kurs.get("titel", "") or "–", c_val)
        ],
        [
            Paragraph("Stundensatz:", c_label),
            Paragraph(f"{stamm.get('satz', '0')} €/h", c_val),
            Paragraph("Gruppe / Klasse:", c_label),
            Paragraph(kurs.get("ag", "") or "–", c_val)
        ],
        [
            Paragraph("Kurstermin:", c_label),
            Paragraph(kurs.get("datum", "") or "–", c_val),
            Paragraph("Abrechnungszeitraum:", c_label),
            Paragraph(p_name, c_val)
        ]
    ]
    t_stamm = Table(stamm_rows, colWidths=[120, 145, 110, 148])
    t_stamm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FARBE_BG_HELL),
        ('BOX', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_stamm)
    elements.append(Spacer(1, 12))

    # 1. Leistung (Gesamtbreite: 523pt)
    summen = berechne_summen(kurs.get("dauer", "0"), stamm.get("satz", "0"), belege)
    dauer = summen["dauer"]
    honorar = summen["honorar"]

    elements.append(Paragraph("<b>1. Erbrachte Kursleistung</b>", styles['Heading3']))
    t_std = Table([
        [
            Paragraph("Datum", th_left),
            Paragraph("Kursbezeichnung / Inhalt", th_left),
            Paragraph("Dauer", th_right),
            Paragraph("Honoraranspruch", th_right)
        ],
        [
            Paragraph(kurs.get("datum", ""), c_val),
            Paragraph(f"{kurs.get('titel', '')} ({kurs.get('ag', '')})", c_val),
            Paragraph(f"{dauer:.2f} Std.", td_right),
            Paragraph(f"{honorar:.2f} €", td_right)
        ]
    ], colWidths=[75, 260, 88, 100])
    t_std.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_std)
    elements.append(Spacer(1, 12))

    # 2. Auslagen (Gesamtbreite: 523pt)
    elements.append(Paragraph("<b>2. Auslagen für Kursmaterialien</b>", styles['Heading3']))
    t_bel_data = [[
        Paragraph("Datum", th_left),
        Paragraph("Händler / Verwendungszweck", th_left),
        Paragraph("Belegnachweis", th_left),
        Paragraph("Betrag", th_right)
    ]]
    idx = 1
    for b in belege:
        nachweis = f"Anhang #{idx}" if b.get("datei") else "Eigenbeleg/Kein Anhang"
        t_bel_data.append([
            Paragraph(b.get("datum", ""), c_val),
            Paragraph(b.get("zweck", ""), c_val),
            Paragraph(nachweis, c_val),
            Paragraph(f"{b.get('betrag', 0.0):.2f} €", td_right)
        ])
        idx += 1

    gesamt_auslagen = summen["auslagen"]
    if not belege:
        t_bel_data.append([
            Paragraph("–", c_val),
            Paragraph("Keine Materialauslagen geltend gemacht", c_val),
            Paragraph("–", c_val),
            Paragraph("0.00 €", td_right)
        ])
    t_bel_data.append([
        Paragraph("<b>Gesamtsumme Auslagen:</b>", c_val_bold),
        "",
        "",
        Paragraph(f"<b>{gesamt_auslagen:.2f} €</b>", td_right)
    ])

    t_bel = Table(t_bel_data, colWidths=[75, 250, 98, 100])
    t_bel.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, FARBE_BORDER),
        ('SPAN', (0, -1), (2, -1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_bel)
    elements.append(Spacer(1, 14))

    # 3. Summe & Buchungs-Referenz für Überweisung (Gesamtbreite: 523pt)
    gesamt = summen["gesamt"]
    t_sum = Table([["Zur Auszahlung fälliger Gesamtbetrag:", f"{gesamt:.2f} €"]], colWidths=[370, 153])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#dcfce7")),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#14532d")),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#16a34a")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 4))

    # Kasten: Verwendungszweck für Kassenwart-App & Bankauszug
    ref_string = f"{kid_text} {stamm.get('leiter', '').strip()}"
    t_ref = Table([
        ["Empfohlener Verwendungszweck für Überweisung:", Paragraph(f"<b><font size='9' color='#1e3d59'>{ref_string}</font></b>", styles['Normal'])]
    ], colWidths=[230, 293])
    t_ref.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_ref)
    elements.append(Spacer(1, 16))

    # 4. Unterschriften (Kursleiter & Vorstand)
    t_sig = Table([
        ["________________________________________", "________________________________________"],
        ["Datum, Unterschrift Kursleiter", "Datum, Sachlich & rechnerisch richtig (Vorstand)"]
    ], colWidths=[256, 267])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor("#334155")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_sig)
    elements.append(Spacer(1, 12))

    # 5. Kassenwart-Auszahlungsfeld mit INTERAKTIVEN AcroForm-Feldern
    kw_box_data = [
        [
            Paragraph("<b>🏦 Zahlungsanweisung & Ausführungsvermerk des Kassenwarts</b> (digital ausfüllbar)", c_val_bold),
            ""
        ],
        [
            Table([
                [Paragraph("Angewiesener Betrag:", c_val),
                 InteractiveTextField("kassenwart_betrag", width=75, height=16, tooltip="Überweisener Betrag in €"),
                 Paragraph("€", c_val)]
            ], colWidths=[105, 80, 15]),
            Table([
                [Paragraph("Überwiesen am:", c_val),
                 InteractiveTextField("kassenwart_datum", width=85, height=16, tooltip="Überweisungsdatum (TT.MM.JJJJ)")]
            ], colWidths=[75, 90])
        ],
        [
            Paragraph("<font color='#64748b' size='7'><i>(Betrag kann bei Abschlägen / Korrekturen vom PDF-Gesamtbetrag abweichen)</i></font>", styles['Normal']),
            Table([
                [Paragraph("Kassenwart / Visum:", c_label),
                 InteractiveTextField("kassenwart_signatur", width=120, height=16, tooltip="Datum, Unterschrift oder Namenskürzel des Kassenwarts")]
            ], colWidths=[90, 125])
        ]
    ]
    t_kw = Table(kw_box_data, colWidths=[265, 258])
    t_kw.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
        ('SPAN', (0, 0), (1, 0)),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_kw)

    doc.build(elements)

    # Deckblatt anhängen & AcroForms vollständig erhalten
    writer = PdfWriter()
    reader_deckblatt = PdfReader(deckblatt_temp)
    writer.append(reader_deckblatt)

    # AcroForm-Formularfelder für alle gängigen PDF-Viewer aktivieren
    try:
        from pypdf.generic import NameObject, BooleanObject
        if hasattr(writer, "_root_object") and "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"].update({
                NameObject("/NeedAppearances"): BooleanObject(True)
            })
    except Exception:
        pass

    beleg_idx = 1
    for b in belege:
        d = b.get("datei")
        if not d or not os.path.exists(d):
            continue

        ext = os.path.splitext(d)[1].lower()
        if ext == ".pdf":
            try:
                r_bel = PdfReader(d)
                writer.append(r_bel)
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
            writer.append(r_img)
            if os.path.exists(temp_img_pdf):
                os.remove(temp_img_pdf)

        beleg_idx += 1

    # Standard-Metadaten für Kassenwart-App
    writer.add_metadata({
        "/Title": f"Abrechnung {kurs.get('id', '')} - {kurs.get('titel', '')}",
        "/Author": stamm.get("leiter", ""),
        "/Subject": f"Förderverein Abrechnung Kurs-ID: {kurs.get('id', '')}",
        "/Keywords": f"KursID={kurs.get('id', '')};Betrag={gesamt:.2f};IBAN={stamm.get('iban', '')};Datum={kurs.get('datum', '')}",
        "/Creator": f"{__app_name__} v{__version__}"
    })

    # Maschinenlesbares JSON-Attachment für Kassenwart-App & Re-Import
    meta_payload = {
        "schema_version": "1.0",
        "app_version": __version__,
        "erstellt_am": datetime.now().isoformat(),
        "stammdaten": {
            "leiter": stamm.get("leiter", ""),
            "iban": stamm.get("iban", ""),
            "satz": stamm.get("satz", "0")
        },
        "kurs": {
            "id": kurs.get("id", ""),
            "titel": kurs.get("titel", ""),
            "ag": kurs.get("ag", ""),
            "datum": kurs.get("datum", ""),
            "dauer": kurs.get("dauer", "0")
        },
        "summen": summen,
        "belege": [
            {
                "datum": b.get("datum", ""),
                "zweck": b.get("zweck", ""),
                "betrag": b.get("betrag", 0.0),
                "hat_datei": bool(b.get("datei"))
            }
            for b in belege
        ]
    }
    try:
        json_bytes = json.dumps(meta_payload, ensure_ascii=False, indent=2).encode("utf-8")
        writer.add_attachment("abrechnungsdaten.json", json_bytes)
    except Exception:
        pass

    with open(zielpfad, "wb") as f_out:
        writer.write(f_out)

    if os.path.exists(deckblatt_temp):
        os.remove(deckblatt_temp)

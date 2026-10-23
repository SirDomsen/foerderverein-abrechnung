"""
app_web.py - Web-Client (NiceGUI) für Desktop-Browser & Mobile (Android/iOS)
Setzt direkt auf core.py auf.
"""

import os
import sys

# Projekt-Wurzelverzeichnis zum Suchpfad hinzufügen, damit 'core' immer gefunden wird
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import socket
from datetime import datetime
from nicegui import ui, app

import core

# Web-spezifisches Upload-Verzeichnis
UPLOADS_DIR = core.UPLOADS_DIR


def get_local_ip() -> str:
    """Ermittelt die primäre lokale IPv4-Adresse im WLAN/Netzwerk."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@ui.page('/')
def index():
    ui.colors(primary='#1e3d59', secondary='#d97706', accent='#0f766e', positive='#15803d', negative='#dc2626')

    # Zustand aus dem Kern laden
    stamm = core.lade_stammdaten()
    entwurf = core.lade_entwurf()
    kurs = {
        "id": entwurf.get("id", ""),
        "titel": entwurf.get("titel", ""),
        "ag": entwurf.get("ag", ""),
        "datum": entwurf.get("datum", ""),
        "dauer": entwurf.get("dauer", "2.0"),
        "ist_mehrtaegig": bool(entwurf.get("ist_mehrtaegig", False)),
        "termine_anzahl": str(entwurf.get("termine_anzahl", "1")),
        "end_datum": entwurf.get("end_datum", "")
    }
    belege = entwurf.get("belege", [])
    aktuelle_datei = {"path": None, "name": None}

    def autosave():
        core.speichere_stammdaten(stamm)
        core.speichere_entwurf(kurs, belege)

    # Header
    with ui.header().classes('bg-primary text-white justify-between items-center py-2 px-4 shadow'):
        ui.label(f"🏫 {core.__app_name__}").classes('text-lg md:text-xl font-bold')
        with ui.row().classes('items-center gap-2'):
            def open_mobile_dialog():
                ip = get_local_ip()
                mobile_url = f"http://{ip}:8080"
                with ui.dialog() as mob_dialog, ui.card().classes('p-5 max-w-sm w-full text-center items-center'):
                    ui.label("📱 Auf dem Handy öffnen").classes('text-lg font-bold text-primary')
                    ui.label("Scanne den QR-Code mit der Smartphone-Kamera (im selben WLAN):").classes('text-xs text-slate-600')
                    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={mobile_url}"
                    ui.image(qr_url).classes('w-44 h-44 my-2 mx-auto rounded shadow-sm border')
                    ui.label(mobile_url).classes('font-mono font-bold text-sm bg-slate-100 p-2 rounded text-slate-800 select-all')
                    ui.label("Tipp: Im Handy-Browser 'Zum Startbildschirm hinzufügen' wählen.").classes('text-xs text-slate-500 italic mt-1')
                    with ui.row().classes('justify-center w-full mt-3'):
                        ui.button("Schließen", on_click=mob_dialog.close).classes('bg-primary text-white text-xs')
                mob_dialog.open()

            ui.button("📱 Handy-Link & QR", on_click=open_mobile_dialog).classes('bg-secondary hover:bg-amber-600 text-white text-xs py-1 px-2.5 rounded shadow-sm').props('dense')
            ui.badge(f"v{core.__version__}", color='secondary')

    # 2-Spalten / Responsive Grid
    with ui.row().classes('w-full max-w-6xl mx-auto p-3 md:p-6 gap-6'):

        # Linke Spalte: Eingabemaske
        with ui.column().classes('flex-1 w-full gap-4'):

            # 1. Person (Stammdaten)
            with ui.card().classes('w-full p-4 border border-slate-200'):
                ui.label("👤 1. Angaben zur Person (bleibt gespeichert)").classes('text-md font-bold text-primary mb-1')

                ui.label("Name des Kursleiters / Auftragnehmers:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. Maria Musterfrau', on_change=lambda e: (stamm.update(leiter=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'leiter').classes('w-full')

                ui.label("Anschrift (Straße, Hausnr., PLZ Ort):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. Musterstr. 1, 70123 Stuttgart', on_change=lambda e: (stamm.update(anschrift=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'anschrift').classes('w-full')

                ui.label("Telefonnummer / E-Mail:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. 0170 1234567', on_change=lambda e: (stamm.update(telefon=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'telefon').classes('w-full')

                ui.label("IBAN (deutsches Girokonto, 22 Stellen):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='DE89 3704 0044 0532 0130 00', on_change=lambda e: (stamm.update(iban=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'iban').classes('w-full')

                def open_admin_settings_modal():
                    einst = core.lade_einstellungen()
                    with ui.dialog() as settings_dialog, ui.card().classes('p-5 max-w-md w-full'):
                        ui.label("⚙️ Vereinseinstellungen (Admin)").classes('text-lg font-bold text-primary')
                        ui.label("Fester Stundensatz für alle Kursleiter und Admin-PIN:").classes('text-xs text-slate-600 mb-3')

                        ui.label("Standard-Stundensatz (€/h):").classes('text-xs font-semibold text-slate-700')
                        satz_in = ui.input(value=f"{float(einst.get('stundensatz', core.DEFAULT_STUNDENSATZ)):.2f}").classes('w-full')

                        ui.label("Admin-PIN:").classes('text-xs font-semibold text-slate-700 mt-2')
                        pin_in = ui.input(value=str(einst.get("admin_pin", core.DEFAULT_ADMIN_PIN))).classes('w-full')

                        def save_settings():
                            try:
                                neuer_satz = float(str(satz_in.value).replace(",", ".").strip())
                                if neuer_satz <= 0 or neuer_satz > 200:
                                    ui.notify("Bitte einen realistischen Stundensatz angeben (1–200 €).", color='negative')
                                    return
                            except ValueError:
                                ui.notify("Ungültiger Stundensatz.", color='negative')
                                return

                            neue_pin = str(pin_in.value).strip()
                            if len(neue_pin) < 4:
                                ui.notify("Die PIN muss mindestens 4 Zeichen lang sein.", color='negative')
                                return

                            core.speichere_einstellungen({"stundensatz": neuer_satz, "admin_pin": neue_pin})
                            stamm["satz"] = f"{neuer_satz:.2f}"
                            core.speichere_stammdaten(stamm)
                            satz_label.text = f"💰 {neuer_satz:.2f} € / Stunde"
                            update_summary()
                            settings_dialog.close()
                            ui.notify(f"Gespeichert! Neuer Satz: {neuer_satz:.2f} €/h", color='positive')

                        with ui.row().classes('justify-end w-full gap-2 mt-4'):
                            ui.button("Abbrechen", on_click=settings_dialog.close).classes('bg-gray-400 text-white text-xs')
                            ui.button("💾 Speichern", on_click=save_settings).classes('bg-positive text-white text-xs')
                    settings_dialog.open()

                def open_admin_pin_dialog():
                    with ui.dialog() as pin_dialog, ui.card().classes('p-4 max-w-sm w-full'):
                        ui.label("🔒 Admin-Bereich (Vorstand)").classes('text-md font-bold text-primary')
                        ui.label("Bitte 4-stellige Admin-PIN eingeben:").classes('text-xs text-slate-600')
                        pin_input = ui.input(placeholder='••••', password=True, password_toggle_button=True).classes('w-full mt-2')

                        def verify_pin():
                            einst = core.lade_einstellungen()
                            korrekt = str(einst.get("admin_pin", core.DEFAULT_ADMIN_PIN))
                            if (pin_input.value or "").strip() == korrekt:
                                pin_dialog.close()
                                open_admin_settings_modal()
                            else:
                                ui.notify("Falsche PIN! Zugriff verweigert.", color='negative')

                        pin_input.on('keydown.enter', verify_pin)

                        with ui.row().classes('justify-end w-full gap-2 mt-4'):
                            ui.button("Abbrechen", on_click=pin_dialog.close).classes('bg-gray-400 text-white text-xs')
                            ui.button("OK", on_click=verify_pin).classes('bg-primary text-white text-xs')
                    pin_dialog.open()

                with ui.row().classes('w-full justify-between items-center mt-3 p-2.5 bg-slate-100 border border-slate-200 rounded'):
                    with ui.column().classes('gap-0'):
                        ui.label("Vergütungssatz (fest):").classes('text-xs text-slate-500 font-semibold')
                        satz_label = ui.label(f"💰 {float(stamm.get('satz', core.DEFAULT_STUNDENSATZ)):.2f} € / Stunde").classes('text-sm font-bold text-slate-800')
                    ui.button("⚙️", on_click=open_admin_pin_dialog).classes('bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm py-1 px-2.5 rounded shadow-sm').props('flat dense')

            # 2. Kursdaten
            with ui.card().classes('w-full p-4 border border-slate-200'):
                ui.label("🏫 2. Kursdaten (dieser Vorgang)").classes('text-md font-bold text-secondary mb-1')

                with ui.row().classes('w-full justify-between items-center mt-2 mb-0.5'):
                    ui.label("Kurs-ID / Buchungs-Referenz:").classes('text-xs font-semibold text-slate-700')

                    def auto_suggest_id():
                        sugg = core.generiere_kurs_id_vorschlag(kurs["titel"], kurs["datum"])
                        kurs["id"] = sugg
                        kurs_id_input.value = sugg
                        autosave()
                        update_summary()
                        ui.notify(f"Kurs-ID vorgeschlagen: {sugg}", color='secondary')

                    ui.button("⚡ Vorschlagen", on_click=auto_suggest_id).classes('text-xs py-0 px-2 bg-amber-500 text-white')

                kurs_id_input = ui.input(placeholder='z. B. SJ2627-SCHACH-01', on_change=lambda e: (kurs.update(id=e.value), autosave(), update_summary())) \
                    .bind_value(kurs, 'id').classes('w-full')

                def on_titel_change(e):
                    kurs.update(titel=e.value)
                    if not kurs.get("id") and len(e.value or "") >= 3:
                        sugg = core.generiere_kurs_id_vorschlag(e.value, kurs.get("datum", ""))
                        kurs["id"] = sugg
                        kurs_id_input.value = sugg
                    autosave()
                    update_summary()

                ui.label("Titel des Kurses / AG:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. Robotik-AG oder Schach', on_change=on_titel_change) \
                    .bind_value(kurs, 'titel').classes('w-full')

                ui.label("Gruppe / Schulklasse:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. Klasse 3-4', on_change=lambda e: (kurs.update(ag=e.value), autosave(), update_summary())) \
                    .bind_value(kurs, 'ag').classes('w-full')

                def on_mehrtaegig_change(e):
                    kurs.update(ist_mehrtaegig=e.value)
                    mehrtaegig_container.set_visibility(e.value)
                    autosave()
                    update_summary()

                ui.checkbox("Kurs fand an mehreren Tagen statt", value=bool(kurs.get("ist_mehrtaegig", False)), on_change=on_mehrtaegig_change) \
                    .bind_value(kurs, 'ist_mehrtaegig').classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')

                ui.label("Startdatum des Kurses (TT.MM.JJJJ):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. 23.10.2026', on_change=lambda e: (kurs.update(datum=e.value), autosave(), update_summary())) \
                    .bind_value(kurs, 'datum').classes('w-full')

                with ui.column().classes('w-full p-0 gap-0') as mehrtaegig_container:
                    ui.label("Anzahl Termine:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                    ui.input(placeholder='z. B. 4', on_change=lambda e: (kurs.update(termine_anzahl=e.value), autosave(), update_summary())) \
                        .bind_value(kurs, 'termine_anzahl').classes('w-full')

                    ui.label("Enddatum des Kurses (TT.MM.JJJJ):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                    ui.input(placeholder='z. B. 20.11.2026', on_change=lambda e: (kurs.update(end_datum=e.value), autosave(), update_summary())) \
                        .bind_value(kurs, 'end_datum').classes('w-full')

                mehrtaegig_container.set_visibility(bool(kurs.get("ist_mehrtaegig", False)))

                ui.label("Gesamtdauer in Stunden (z. B. 2.0 oder 8.0):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='2.0', on_change=lambda e: (kurs.update(dauer=e.value), autosave(), update_summary())) \
                    .bind_value(kurs, 'dauer').classes('w-full')

            # 3. Materialauslagen & Belege
            with ui.card().classes('w-full p-4 border border-slate-200'):
                ui.label("🧾 3. Materialauslagen & Belege").classes('text-md font-bold text-accent mb-1')

                ui.label("Kaufdatum des Belegs (TT.MM.JJJJ):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                bel_datum = ui.input(placeholder='z. B. 15.10.2026').classes('w-full')

                ui.label("Händler / Verwendungszweck:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                bel_zweck = ui.input(placeholder='z. B. Bastelbedarf Müller').classes('w-full')

                ui.label("Rechnungsbetrag in €:").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                bel_betrag = ui.input(placeholder='z. B. 24.95').classes('w-full')

                ui.label("Beleg-Nachweis (Foto oder PDF):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                datei_label = ui.label("Kein Anhang gewählt").classes('text-xs text-gray-500 my-1')

                async def handle_upload(e):
                    fname = e.name
                    save_path = os.path.join(UPLOADS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{core.clean_filename(fname)}")
                    with open(save_path, 'wb') as f:
                        f.write(e.content.read())
                    aktuelle_datei["path"] = save_path
                    aktuelle_datei["name"] = fname
                    datei_label.text = f"📎 Gewählt: {fname}"
                    ui.notify(f"Datei '{fname}' bereitgestellt", color='positive')

                ui.upload(on_upload=handle_upload, max_files=1, auto_upload=True).props('accept="image/*,.pdf"').classes('w-full my-2')

                def add_beleg():
                    d_parsed, err = core.parse_datum(bel_datum.value or "", "Belegdatum")
                    if err:
                        ui.notify(err, color='negative')
                        return
                    if not bel_zweck.value:
                        ui.notify("Bitte Händler / Zweck angeben.", color='negative')
                        return
                    try:
                        b_val = float((bel_betrag.value or "0").replace(",", "."))
                        if b_val <= 0:
                            raise ValueError()
                    except ValueError:
                        ui.notify("Bitte einen gültigen Betrag größer als 0 eingeben.", color='negative')
                        return

                    # Plausibilität prüfen
                    kd_parsed, _ = core.parse_datum(kurs["datum"] or "", "Kursdatum")
                    ist_ok, warn_status, nachricht = core.pruefe_beleg_plausibilitaet(d_parsed, kd_parsed)

                    if not ist_ok:
                        ui.notify(nachricht, color='negative', close_button="Ignorieren")
                    elif warn_status == "vorlauf":
                        ui.notify(nachricht, color='warning')

                    belege.append({
                        "datum": d_parsed.strftime("%d.%m.%Y"),
                        "zweck": bel_zweck.value.strip(),
                        "betrag": b_val,
                        "datei": aktuelle_datei["path"],
                        "datei_name": aktuelle_datei["name"]
                    })

                    bel_datum.value = ""
                    bel_zweck.value = ""
                    bel_betrag.value = ""
                    aktuelle_datei["path"] = None
                    aktuelle_datei["name"] = None
                    datei_label.text = "Kein Anhang gewählt"

                    autosave()
                    render_belege()
                    update_summary()
                    ui.notify("Beleg hinzugefügt!", color='positive')

                ui.button("+ Beleg hinzufügen", on_click=add_beleg).classes('w-full bg-accent text-white')

                ui.separator().classes('my-3')
                ui.label("Angehängte Belegposten:").classes('text-sm font-semibold text-gray-700')
                belege_container = ui.column().classes('w-full gap-2')

                def render_belege():
                    belege_container.clear()
                    with belege_container:
                        if not belege:
                            ui.label("Noch keine Belege erfasst.").classes('text-xs text-gray-400')
                            return
                        for i, b in enumerate(belege):
                            with ui.row().classes('w-full justify-between items-center p-2 bg-slate-100 rounded border border-slate-200 text-sm'):
                                file_info = f" | 📎 {b['datei_name']}" if b.get('datei_name') else ""
                                ui.label(f"#{i+1}: {b['zweck'][:16]} ({b['betrag']:.2f} €){file_info}").classes('font-medium')

                                def remove_b(idx=i):
                                    belege.pop(idx)
                                    autosave()
                                    render_belege()
                                    update_summary()

                                ui.button('X', on_click=remove_b).classes('bg-negative text-white text-xs py-1 px-2')

                render_belege()

        # Rechte Spalte: Live-Übersicht & Aktionen
        with ui.column().classes('flex-1 w-full gap-4'):
            with ui.card().classes('w-full p-4 border border-slate-200 flex-1 flex flex-col justify-between'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label("📊 Live-Übersicht").classes('text-lg font-bold text-primary')

                    with ui.row().classes('gap-1'):
                        # PDF Importieren Dialog
                        def open_import_dialog():
                            with ui.dialog() as imp_dialog, ui.card().classes('p-4 max-w-md w-full'):
                                ui.label("📂 Vorhandene Abrechnung laden").classes('text-md font-bold text-primary')
                                ui.label("Lade ein bereits exportiertes Abrechnungs-PDF hoch, um alle Daten wiederherzustellen und weiterzubearbeiten:").classes('text-xs text-slate-600')

                                async def handle_pdf_import(e):
                                    erfolg, daten, err = core.lese_abrechnung_aus_pdf(e.content)
                                    if not erfolg or not daten:
                                        ui.notify(err or "Fehler beim Einlesen der PDF", color='negative')
                                        return

                                    stamm_neu = daten.get("stammdaten", {})
                                    if stamm_neu:
                                        stamm.update(stamm_neu)
                                        einst = core.lade_einstellungen()
                                        stamm["satz"] = f"{float(einst.get('stundensatz', core.DEFAULT_STUNDENSATZ)):.2f}"
                                        satz_label.text = f"💰 {float(stamm['satz']):.2f} € / Stunde"

                                    kurs_neu = daten.get("kurs", {})
                                    if kurs_neu:
                                        kurs.update(kurs_neu)
                                        kurs_id_input.value = kurs.get("id", "")
                                        mehrtaegig_container.set_visibility(bool(kurs.get("ist_mehrtaegig", False)))

                                    belege.clear()
                                    belege.extend(daten.get("belege", []))

                                    autosave()
                                    render_belege()
                                    update_summary()
                                    imp_dialog.close()
                                    ui.notify(f"Abrechnung '{kurs.get('id', '')}' erfolgreich geladen!", color='positive')

                                ui.upload(on_upload=handle_pdf_import, max_files=1, auto_upload=True).classes('w-full my-2')
                                with ui.row().classes('justify-end w-full mt-2'):
                                    ui.button("Abbrechen", on_click=imp_dialog.close).classes('bg-gray-400 text-white text-xs')
                            imp_dialog.open()

                        # Hinweis: Button 'PDF laden' für reguläre Erfasser vorerst ausgeblendet (Logik bleibt für spätere Prüf-App erhalten)
                        # ui.button("📂 PDF laden", on_click=open_import_dialog).classes('bg-sky-600 text-white text-xs')

                        def reset_kurs():
                            with ui.dialog() as dialog, ui.card():
                                ui.label("Neuen Kurs starten?").classes('font-bold')
                                ui.label("Kursdaten und Belege werden geleert. Personendaten bleiben erhalten.")
                                with ui.row().classes('justify-end w-full gap-2 mt-4'):
                                    ui.button("Abbrechen", on_click=dialog.close).classes('bg-gray-400 text-white')

                                    def confirm():
                                        kurs.update(id="", titel="", ag="", datum="", dauer="2.0", ist_mehrtaegig=False, termine_anzahl="1", end_datum="")
                                        kurs_id_input.value = ""
                                        mehrtaegig_container.set_visibility(False)
                                        belege.clear()
                                        core.loesche_entwurf()
                                        render_belege()
                                        update_summary()
                                        dialog.close()
                                        ui.notify("Neuer Kurs bereit!", color='positive')

                                    ui.button("Ja, leeren", on_click=confirm).classes('bg-secondary text-white')
                            dialog.open()

                        ui.button("🔄 Neuer Kurs", on_click=reset_kurs).classes('bg-secondary text-white text-xs')

                summary_container = ui.column().classes('w-full gap-3 flex-1')

                def update_summary():
                    summen = core.berechne_summen(kurs["dauer"], stamm["satz"], belege)

                    ist_m = bool(kurs.get("ist_mehrtaegig", False))
                    start_d = kurs.get("datum") or "–"
                    end_d = kurs.get("end_datum") or ""
                    anz_t = kurs.get("termine_anzahl") or "1"
                    if ist_m and end_d:
                        termin_anzeige = f"{start_d} bis {end_d} ({anz_t} Termine)"
                        pruef_datum_str = end_d
                    else:
                        termin_anzeige = start_d
                        pruef_datum_str = kurs.get("datum") or ""

                    kd_parsed, _ = core.parse_datum(pruef_datum_str, "Kursdatum")
                    periode_text = "–"
                    warns = []
                    if kd_parsed:
                        _, _, p_name = core.ferien_mgr.ermittle_abrechnungszeitraum(kd_parsed)
                        periode_text = p_name
                        warns = core.pruefe_kursdatum_plausibilitaet(kd_parsed)

                    iban_val = (stamm.get("iban") or "").strip()
                    if iban_val:
                        iban_ok, _ = core.validiere_iban(iban_val)
                    else:
                        iban_ok = False

                    kid_anzeige = kurs.get("id") or "Noch keine Kurs-ID"
                    titel_anzeige = kurs.get("titel") or "Kein Kurstitel"
                    leiter_anzeige = stamm.get("leiter") or "Kein Name hinterlegt"
                    fester_name = core.generiere_standard_dateinamen(
                        kurs.get("datum", ""),
                        kurs.get("titel", ""),
                        leiter_anzeige,
                        kurs.get("id", "")
                    )

                    summary_container.clear()
                    with summary_container:
                        # 1. Kurs & Person Info-Karte
                        with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 rounded-lg shadow-none'):
                            with ui.row().classes('w-full justify-between items-start gap-2'):
                                with ui.column().classes('gap-0.5 flex-1 min-w-[140px]'):
                                    ui.label(titel_anzeige).classes('font-bold text-slate-800 text-sm md:text-base leading-snug break-words')
                                    with ui.row().classes('items-center gap-1.5 text-xs text-slate-600 flex-wrap'):
                                        ui.badge(f"ID: {kid_anzeige}", color='primary').classes('text-[11px]')
                                        if kurs.get("ag"):
                                            ui.badge(f"Klasse: {kurs.get('ag')}", color='secondary').classes('text-[11px]')
                                with ui.column().classes('items-end gap-0.5 flex-shrink-0'):
                                    ui.label(leiter_anzeige).classes('font-semibold text-slate-700 text-xs text-right')
                                    if iban_val:
                                        ui.label(core.formatiere_iban(iban_val)).classes(f'font-mono text-[11px] {("text-emerald-600" if iban_ok else "text-amber-600 font-bold")}')
                                    else:
                                        ui.label("Keine IBAN").classes('text-[11px] text-red-500 italic')

                            ui.separator().classes('my-2')

                            # Termine & BW-Periode
                            with ui.row().classes('w-full justify-between items-center text-xs flex-wrap gap-2'):
                                with ui.row().classes('items-center gap-1.5'):
                                    ui.label("📅").classes('text-xs')
                                    ui.label(termin_anzeige).classes('font-medium text-slate-700')
                                with ui.row().classes('items-center gap-1.5'):
                                    ui.label("⏳").classes('text-xs')
                                    ui.label(periode_text).classes('text-slate-600')

                            # Warnungen falls Frist/Ferien
                            if warns:
                                with ui.column().classes('w-full mt-2 gap-1'):
                                    for w in warns:
                                        if w["level"] == "gesperrt":
                                            bg_c = "bg-red-50 border-red-200 text-red-700"
                                            icon = "⛔"
                                        elif w["level"] == "vorstand":
                                            bg_c = "bg-amber-50 border-amber-200 text-amber-800"
                                            icon = "⚠️"
                                        else:
                                            bg_c = "bg-sky-50 border-sky-200 text-sky-800"
                                            icon = "ℹ️"
                                        with ui.row().classes(f'w-full p-2 rounded border text-xs items-center gap-1.5 {bg_c}'):
                                            ui.label(icon).classes('text-sm flex-shrink-0')
                                            ui.label(w["titel"]).classes('font-semibold leading-tight')
                            elif kd_parsed:
                                with ui.row().classes('w-full mt-2 p-1.5 bg-emerald-50 border border-emerald-200 rounded text-xs items-center gap-1.5 text-emerald-700'):
                                    ui.label("✓ Im regulären Abrechnungszeitraum").classes('font-medium')

                        # 2. Kostenaufstellung
                        with ui.card().classes('w-full p-3 bg-white border border-slate-200 rounded-lg shadow-none'):
                            ui.label("ABRECHNUNGS-POSTEN").classes('text-[11px] font-bold text-slate-500 tracking-wider mb-1.5')

                            # Honorar
                            with ui.row().classes('w-full justify-between items-center py-1.5 text-sm'):
                                with ui.column().classes('gap-0'):
                                    ui.label("Aufwandsentschädigung").classes('font-medium text-slate-800')
                                    ui.label(f"{summen['dauer']:.2f} Std. × {summen['satz']:.2f} €/h").classes('text-xs text-slate-500')
                                ui.label(f"{summen['honorar']:.2f} €").classes('font-bold text-slate-800')

                            # Auslagen
                            with ui.row().classes('w-full justify-between items-center py-1.5 text-sm border-t border-slate-100'):
                                with ui.column().classes('gap-0'):
                                    ui.label(f"Materialauslagen ({len(belege)} Belege)").classes('font-medium text-slate-800')
                                    if belege:
                                        detail_text = ", ".join([f"{b['betrag']:.2f} €" for b in belege[:3]])
                                        if len(belege) > 3:
                                            detail_text += " ..."
                                        ui.label(detail_text).classes('text-xs text-slate-400')
                                    else:
                                        ui.label("Keine Auslagen erfasst").classes('text-xs text-slate-400 italic')
                                ui.label(f"{summen['auslagen']:.2f} €").classes('font-bold text-slate-800')

                            # Prominente Gesamtsumme
                            with ui.row().classes('w-full justify-between items-center p-3 mt-2 bg-emerald-50 border border-emerald-300 rounded-md'):
                                ui.label("Gesamtauszahlung:").classes('text-sm md:text-base font-bold text-emerald-950')
                                ui.label(f"{summen['gesamt']:.2f} €").classes('text-xl md:text-2xl font-black text-emerald-700')

                        # 3. Kassenwart Info & Dateiname
                        with ui.column().classes('w-full p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500 gap-1'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("Überweisungszweck:").classes('font-semibold text-slate-600')
                                ui.label(f"{kid_anzeige} {leiter_anzeige}").classes('font-mono font-bold text-slate-800 text-right text-xs')
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("Dateiname:").classes('font-semibold text-slate-600')
                                ui.label(fester_name).classes('font-mono text-[11px] text-slate-500 text-right truncate max-w-[220px]')

                update_summary()

                def export_action():
                    if not stamm["leiter"].strip():
                        ui.notify("Bitte Kursleiter angeben.", color='negative')
                        return

                    # Anschrift prüfen (Pflichtfeld)
                    anschrift_ok, anschrift_err = core.validiere_anschrift(stamm.get("anschrift", ""))
                    if not anschrift_ok:
                        ui.notify(anschrift_err, color='negative')
                        return

                    # Modulo-97 IBAN-Validierung
                    iban_ok, iban_err = core.validiere_iban(stamm.get("iban", ""))
                    if not iban_ok:
                        ui.notify(f"IBAN-Fehler: {iban_err}", color='negative')
                        return

                    # Kurs-ID Validierung (Option 1)
                    kid_ok, kid_err = core.validiere_kurs_id(kurs.get("id", ""))
                    if not kid_ok:
                        ui.notify(f"Kurs-ID Fehler: {kid_err}", color='negative')
                        return

                    if not kurs["titel"].strip():
                        ui.notify("Bitte Kurstitel angeben.", color='negative')
                        return

                    kd_parsed, err = core.parse_datum(kurs["datum"] or "", "Startdatum / Kurstermin")
                    if err:
                        ui.notify(err, color='negative')
                        return

                    ist_m = bool(kurs.get("ist_mehrtaegig", False))
                    pruef_datum_obj = kd_parsed

                    if ist_m:
                        end_str = (kurs.get("end_datum") or "").strip()
                        kd_end, end_err = core.parse_datum(end_str, "Enddatum des Kurses")
                        if end_err:
                            ui.notify(end_err, color='negative')
                            return
                        if kd_end < kd_parsed:
                            ui.notify("Das Enddatum darf nicht vor dem Startdatum liegen.", color='negative')
                            return
                        try:
                            if int(kurs.get("termine_anzahl", "1")) < 2:
                                ui.notify("Bei mehrtägigen Kursen muss die Anzahl der Termine mindestens 2 betragen.", color='negative')
                                return
                        except ValueError:
                            ui.notify("Bitte eine gültige Termin-Anzahl (ganze Zahl >= 2) angeben.", color='negative')
                            return
                        pruef_datum_obj = kd_end

                    # Kursdauer prüfen
                    dauer_ok, _, dauer_err = core.validiere_kurs_dauer(kurs.get("dauer", "0"))
                    if not dauer_ok:
                        ui.notify(f"Kursdauer-Fehler: {dauer_err}", color='negative')
                        return

                    # Kursdatum Plausibilität (Schuljahr, Ferienende-Fenster, Ferien, Wochentag)
                    warnungen = core.pruefe_kursdatum_plausibilitaet(pruef_datum_obj)
                    blockiert = False
                    for w in warnungen:
                        if w["level"] == "gesperrt":
                            ui.notify(f"⛔ {w['titel']}: {w['nachricht'].splitlines()[0]}", color='negative', timeout=9000)
                            blockiert = True
                        elif w["level"] == "vorstand":
                            ui.notify(f"⚠️ {w['titel']}: {w['nachricht'].splitlines()[0]}", color='warning', timeout=7000)
                        else:
                            ui.notify(f"ℹ️ {w['titel']}: {w['nachricht'].splitlines()[0]}", color='info', timeout=5000)

                    if blockiert:
                        return

                    # Fester Dateiname nach Kassenwart-Schema
                    pdf_filename = core.generiere_standard_dateinamen(
                        kurs["datum"],
                        kurs["titel"],
                        stamm["leiter"],
                        kurs.get("id", "")
                    )
                    zielpfad = os.path.join(core.EXPORT_DIR, pdf_filename)

                    try:
                        core.erzeuge_abrechnung_pdf(stamm, kurs, belege, zielpfad)
                        autosave()

                        with ui.dialog() as success_dialog, ui.card():
                            ui.label("✅ PDF erfolgreich für Kassenwart erstellt!").classes('text-md font-bold text-positive')
                            ui.label(f"Fester Dateiname: {pdf_filename}").classes('text-xs text-gray-700 font-mono')
                            ui.label(f"Überweisungs-Zweck: {kurs.get('id')} {stamm.get('leiter')}").classes('text-xs text-blue-700 font-semibold')
                            ui.label("Tipp: Die Kassenwart-Felder im PDF sind digital ausfüllbar.").classes('text-xs text-gray-500 italic mt-1')
                            with ui.row().classes('justify-end w-full gap-2 mt-4'):
                                ui.button("Schließen", on_click=success_dialog.close).classes('bg-gray-400 text-white')
                                ui.button("📄 PDF herunterladen", on_click=lambda: ui.download(zielpfad, filename=pdf_filename)).classes('bg-positive text-white')
                        success_dialog.open()
                    except Exception as ex:
                        ui.notify(f"Fehler: {str(ex)}", color='negative')

                ui.button("📄 Abrechnung prüfen & PDF exportieren", on_click=export_action) \
                    .classes('w-full py-3 bg-positive text-white font-bold text-md mt-4 shadow-md')


def ensure_port_free(port: int = 8080):
    """Prüft, ob der Port durch eine alte Python-Instanz belegt ist, und beendet diese."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return
    except OSError:
        s.close()
        import subprocess
        try:
            out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            curr_pid = str(os.getpid())
            for line in out.splitlines():
                if "LISTENING" in line or "ABH" in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit() and pid != curr_pid and pid != "0":
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
            import time
            time.sleep(0.5)
        except Exception:
            pass


if __name__ in {"__main__", "__mp_main__"}:
    ensure_port_free(8080)
    ui.run(title=f"{core.__app_name__} v{core.__version__}", port=8080, reload=False, show=True)

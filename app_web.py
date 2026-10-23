"""
app_web.py - Web-Client (NiceGUI) für Desktop-Browser & Mobile (Android/iOS)
Setzt direkt auf core.py auf.
"""

import os
from datetime import datetime
from nicegui import ui, app

import core

# Web-spezifisches Upload-Verzeichnis
UPLOADS_DIR = core.UPLOADS_DIR


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
        "dauer": entwurf.get("dauer", "2.0")
    }
    belege = entwurf.get("belege", [])
    aktuelle_datei = {"path": None, "name": None}

    def autosave():
        core.speichere_stammdaten(stamm)
        core.speichere_entwurf(kurs, belege)

    # Header
    with ui.header().classes('bg-primary text-white justify-between items-center py-2 px-4 shadow'):
        ui.label(f"🏫 {core.__app_name__}").classes('text-lg md:text-xl font-bold')
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

                ui.label("IBAN (deutsches Girokonto, 22 Stellen):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='DE89 3704 0044 0532 0130 00', on_change=lambda e: (stamm.update(iban=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'iban').classes('w-full')

                ui.label("Vereinbarter Stundensatz (€/h):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. 20.00', on_change=lambda e: (stamm.update(satz=e.value), autosave(), update_summary())) \
                    .bind_value(stamm, 'satz').classes('w-full')

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

                ui.label("Datum des Kurstermins (TT.MM.JJJJ):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
                ui.input(placeholder='z. B. 23.10.2026', on_change=lambda e: (kurs.update(datum=e.value), autosave(), update_summary())) \
                    .bind_value(kurs, 'datum').classes('w-full')

                ui.label("Dauer in Stunden (z. B. 2.0 für 120 Min):").classes('text-xs font-semibold text-slate-700 mt-2 mb-0.5')
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

                ui.upload(on_upload=handle_upload, max_files=1, auto_upload=True).classes('w-full my-2')

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

                                    kurs_neu = daten.get("kurs", {})
                                    if kurs_neu:
                                        kurs.update(kurs_neu)
                                        kurs_id_input.value = kurs.get("id", "")

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

                        ui.button("📂 PDF laden", on_click=open_import_dialog).classes('bg-sky-600 text-white text-xs')

                        def reset_kurs():
                            with ui.dialog() as dialog, ui.card():
                                ui.label("Neuen Kurs starten?").classes('font-bold')
                                ui.label("Kursdaten und Belege werden geleert. Personendaten bleiben erhalten.")
                                with ui.row().classes('justify-end w-full gap-2 mt-4'):
                                    ui.button("Abbrechen", on_click=dialog.close).classes('bg-gray-400 text-white')

                                    def confirm():
                                        kurs.update(id="", titel="", ag="", datum="", dauer="2.0")
                                        kurs_id_input.value = ""
                                        belege.clear()
                                        core.loesche_entwurf()
                                        render_belege()
                                        update_summary()
                                        dialog.close()
                                        ui.notify("Neuer Kurs bereit!", color='positive')

                                    ui.button("Ja, leeren", on_click=confirm).classes('bg-secondary text-white')
                            dialog.open()

                        ui.button("🔄 Neuer Kurs", on_click=reset_kurs).classes('bg-secondary text-white text-xs')

                summary_text = ui.textarea().classes('w-full font-mono text-xs flex-1 min-h-[300px]').props('readonly')

                def update_summary():
                    summen = core.berechne_summen(kurs["dauer"], stamm["satz"], belege)

                    kd_parsed, _ = core.parse_datum(kurs["datum"] or "", "Kursdatum")
                    periode_text = "–"
                    warn_status_text = ""
                    if kd_parsed:
                        _, _, p_name = core.ferien_mgr.ermittle_abrechnungszeitraum(kd_parsed)
                        periode_text = p_name
                        warns = core.pruefe_kursdatum_plausibilitaet(kd_parsed)
                        if warns:
                            for w in warns:
                                icon = "⛔" if w["level"] == "hart" else "⚠️"
                                warn_status_text += f"\n  {icon} {w['titel']}"
                        else:
                            warn_status_text = "\n  ✓ Im regulären Abrechnungszeitraum"

                    iban_val = (stamm.get("iban") or "").strip()
                    if iban_val:
                        i_ok, _ = core.validiere_iban(iban_val)
                        iban_text = f"{core.formatiere_iban(iban_val)} {'(Gültig ✓)' if i_ok else '(Ungültig ⚠)'}"
                    else:
                        iban_text = "– Nicht angegeben –"

                    kid_anzeige = kurs.get("id") or "– Noch keine Kurs-ID –"
                    leiter_anzeige = stamm.get("leiter") or "Kursleiter"

                    fester_name = core.generiere_standard_dateinamen(
                        kurs["datum"],
                        kurs["titel"],
                        leiter_anzeige,
                        kurs.get("id", "")
                    )

                    lines = [
                        "=" * 45,
                        f"KURS-ID:      {kid_anzeige}",
                        f"KURS:         {kurs['titel'] or '–'}",
                        f"KLASSE:       {kurs['ag'] or '–'}",
                        f"TERMIN:       {kurs['datum'] or '–'}",
                        f"PERIODE (BW): {periode_text}{warn_status_text}",
                        f"IBAN:         {iban_text}",
                        f"──> Ref-Zweck: {kid_anzeige} {leiter_anzeige}",
                        f"──> Dateiname: {fester_name}",
                        "=" * 45,
                        "",
                        "1. AUFWANDSENTSCHÄDIGUNG:",
                        f" • {summen['dauer']:.2f} Std. à {summen['satz']:.2f} €/h",
                        f" ──> Honorar: {summen['honorar']:.2f} €",
                        "",
                        f"2. MATERIALAUSLAGEN ({len(belege)} Posten):"
                    ]
                    for idx, b in enumerate(belege, 1):
                        lines.append(f" #{idx} | {b['datum']} | {b['zweck'][:15]}: {b['betrag']:.2f} €")
                    lines.extend([
                        f" ──> Auslagen gesamt: {summen['auslagen']:.2f} €",
                        "",
                        "=" * 45,
                        f"GESAMTAUSZAHLUNG: {summen['gesamt']:.2f} €",
                        "=" * 45
                    ])
                    summary_text.value = "\n".join(lines)

                update_summary()

                def export_action():
                    if not stamm["leiter"].strip():
                        ui.notify("Bitte Kursleiter angeben.", color='negative')
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

                    kd_parsed, err = core.parse_datum(kurs["datum"] or "", "Kursdatum")
                    if err:
                        ui.notify(err, color='negative')
                        return

                    # Kursdauer prüfen
                    dauer_ok, _, dauer_err = core.validiere_kurs_dauer(kurs.get("dauer", "0"))
                    if not dauer_ok:
                        ui.notify(f"Kursdauer-Fehler: {dauer_err}", color='negative')
                        return

                    # Kursdatum Plausibilität (Schuljahr, Ferienende-Fenster, Ferien, Wochentag)
                    warnungen = core.pruefe_kursdatum_plausibilitaet(kd_parsed)
                    for w in warnungen:
                        color = 'negative' if w["level"] == "hart" else 'warning'
                        icon = "⛔ " if w["level"] == "hart" else "⚠️ "
                        ui.notify(f"{icon}{w['titel']}: {w['nachricht'].splitlines()[0]}", color=color, timeout=7000)

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


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title=f"{core.__app_name__} v{core.__version__}", port=8080, reload=False, show=True)

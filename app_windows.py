"""
app_windows.py - Windows Desktop-Client für Förderverein Abrechnungs-Manager
Setzt direkt auf core.py auf.
"""

import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

import core

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class WindowsAbrechnungsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{core.__app_name__} v{core.__version__}")
        self.geometry("1100x850")
        self.minsize(980, 720)

        # Lokaler Zustand
        self.stamm = core.lade_stammdaten()
        entwurf = core.lade_entwurf()
        self.kurs = {
            "titel": entwurf.get("titel", ""),
            "ag": entwurf.get("ag", ""),
            "datum": entwurf.get("datum", ""),
            "dauer": entwurf.get("dauer", "2.0")
        }
        self.belege_liste = entwurf.get("belege", [])
        self.selected_file_path = None

        self._init_ui()
        self._belege_karten_rendern()
        self.liste_aktualisieren()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------------------------
        # Linke Spalte: Eingabemaske
        # ------------------------------------
        self.left_frame = ctk.CTkScrollableFrame(self, label_text="Eingabe & Abrechnungsdaten")
        self.left_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        # 1. Angaben zur Person (Stammdaten)
        stamm_card = ctk.CTkFrame(self.left_frame, fg_color=("gray92", "gray17"), corner_radius=10)
        stamm_card.pack(fill="x", pady=(0, 12), padx=4)

        ctk.CTkLabel(
            stamm_card,
            text="👤 1. Angaben zur Person (dauerhaft gespeichert)",
            font=("Arial", 13, "bold"),
            text_color=("#1e3d59", "#64b5f6")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.entry_leiter = self._create_entry(stamm_card, "Name des Kursleiters", self.stamm.get("leiter", ""))
        self.entry_iban = self._create_entry(stamm_card, "IBAN", self.stamm.get("iban", ""))
        self.entry_satz = self._create_entry(stamm_card, "Stundensatz (€/h, z. B. 20.00)", self.stamm.get("satz", "20.00"))

        # 2. Kursdaten (dieser Vorgang)
        kurs_card = ctk.CTkFrame(self.left_frame, fg_color=("gray92", "gray17"), corner_radius=10)
        kurs_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(
            kurs_card,
            text="🏫 2. Kursdaten (dieser Vorgang)",
            font=("Arial", 13, "bold"),
            text_color=("#d97706", "#fbbf24")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.entry_kurs_titel = self._create_entry(kurs_card, "Titel des Kurses (z. B. Robotik-AG)", self.kurs.get("titel", ""))
        self.entry_ag = self._create_entry(kurs_card, "Gruppe / Klasse (z. B. Klasse 3-4)", self.kurs.get("ag", ""))
        self.entry_kurs_datum = self._create_entry(kurs_card, "Datum des Kurses (TT.MM.JJJJ)", self.kurs.get("datum", ""))
        self.entry_kurs_dauer = self._create_entry(kurs_card, "Dauer in Stunden (z. B. 2.0)", self.kurs.get("dauer", "2.0"))

        for e in [self.entry_leiter, self.entry_iban, self.entry_satz,
                  self.entry_kurs_titel, self.entry_ag, self.entry_kurs_datum, self.entry_kurs_dauer]:
            e.bind("<KeyRelease>", lambda event: self._on_input_changed())

        # 3. Materialauslagen & Belege
        beleg_card = ctk.CTkFrame(self.left_frame, fg_color=("gray92", "gray17"), corner_radius=10)
        beleg_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(
            beleg_card,
            text="🧾 3. Materialauslagen & Belege",
            font=("Arial", 13, "bold"),
            text_color=("#0f766e", "#2dd4bf")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.entry_bel_datum = self._create_entry(beleg_card, "Kaufdatum (TT.MM.JJJJ)")
        self.entry_bel_haendler = self._create_entry(beleg_card, "Händler / Verwendungszweck (z. B. Bastelbedarf Müller)")
        self.entry_bel_betrag = self._create_entry(beleg_card, "Betrag in € (z. B. 24.95)")

        self.btn_file = ctk.CTkButton(
            beleg_card,
            text="📎 Beleg-Datei wählen (Bild/PDF)",
            fg_color=("gray80", "gray28"),
            hover_color=("gray70", "gray35"),
            text_color=("black", "white"),
            command=self.datei_auswaehlen
        )
        self.btn_file.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            beleg_card,
            text="+ Beleg hinzufügen",
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="white",
            font=("Arial", 12, "bold"),
            command=self.beleg_hinzufuegen
        ).pack(fill="x", padx=10, pady=(5, 8))

        ctk.CTkLabel(self.left_frame, text="Angehängte Belegposten:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 2))
        self.belege_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.belege_container.pack(fill="x", pady=2)

        # ------------------------------------
        # Rechte Spalte: Live-Übersicht & Aktionen
        # ------------------------------------
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        header_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="📊 Abrechnungs-Übersicht",
            font=("Arial", 17, "bold"),
            text_color=("#1e3d59", "#90caf9")
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="🔄 Neuen Kurs abrechnen",
            fg_color=("#d97706", "#b45309"),
            hover_color="#92400e",
            text_color="white",
            font=("Arial", 11, "bold"),
            command=self.neuen_kurs_starten
        ).pack(side="right")

        self.summary_box = ctk.CTkTextbox(self.right_frame, font=("Consolas", 12))
        self.summary_box.pack(fill="both", expand=True, padx=10, pady=8)

        btn_action_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.btn_export = ctk.CTkButton(
            btn_action_frame,
            text="📄 Abrechnung prüfen & als PDF exportieren",
            fg_color="#15803d",
            hover_color="#166534",
            text_color="white",
            height=46,
            font=("Arial", 14, "bold"),
            command=self.pdf_erstellen
        )
        self.btn_export.pack(fill="x", pady=4)

        self.btn_open_folder = ctk.CTkButton(
            btn_action_frame,
            text="📁 Export-Ordner im Explorer öffnen",
            fg_color=("gray80", "gray28"),
            hover_color=("gray70", "gray35"),
            text_color=("black", "white"),
            command=self.open_export_dir
        )
        self.btn_open_folder.pack(fill="x", pady=2)

    def _create_entry(self, parent, placeholder, initial=""):
        e = ctk.CTkEntry(parent, placeholder_text=placeholder)
        if initial:
            e.insert(0, str(initial))
        e.pack(fill="x", padx=10, pady=4)
        return e

    def _on_input_changed(self):
        self.stamm["leiter"] = self.entry_leiter.get()
        self.stamm["iban"] = self.entry_iban.get()
        self.stamm["satz"] = self.entry_satz.get()

        self.kurs["titel"] = self.entry_kurs_titel.get()
        self.kurs["ag"] = self.entry_ag.get()
        self.kurs["datum"] = self.entry_kurs_datum.get()
        self.kurs["dauer"] = self.entry_kurs_dauer.get()

        core.speichere_stammdaten(self.stamm)
        core.speichere_entwurf(self.kurs, self.belege_liste)
        self.liste_aktualisieren()

    def open_export_dir(self):
        try:
            os.startfile(core.EXPORT_DIR)
        except Exception:
            subprocess.Popen(["explorer", core.EXPORT_DIR])

    def datei_auswaehlen(self):
        filetypes = [
            ("Dokumente & Bilder", "*.pdf *.jpg *.jpeg *.png"),
            ("PDFs", "*.pdf"),
            ("Bilder", "*.jpg *.jpeg *.png")
        ]
        pfad = filedialog.askopenfilename(title="Beleg wählen", filetypes=filetypes)
        if pfad:
            self.selected_file_path = pfad
            name = os.path.basename(pfad)
            display_name = name[:27] + "..." if len(name) > 30 else name
            self.btn_file.configure(
                text=f"📎 Gewählt: {display_name}",
                fg_color="#0f766e",
                text_color="white"
            )

    def beleg_hinzufuegen(self):
        d_str = self.entry_bel_datum.get().strip()
        zweck = self.entry_bel_haendler.get().strip()
        b_str = self.entry_bel_betrag.get().strip()

        parsed_bel, err = core.parse_datum(d_str, "Belegdatum")
        if err:
            messagebox.showwarning("Plausibilitätsprüfung", err)
            return

        if not zweck:
            messagebox.showwarning("Plausibilitätsprüfung", "Bitte Händler / Verwendungszweck angeben.")
            return

        try:
            betrag = float(b_str.replace(",", "."))
            if betrag <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Fehler", "Bitte einen gültigen Betrag größer als 0 eingeben.")
            return

        # Plausibilität gegen Kursdatum prüfen
        kd_parsed, _ = core.parse_datum(self.entry_kurs_datum.get().strip(), "Kursdatum")
        ist_ok, warn_status, nachricht = core.pruefe_beleg_plausibilitaet(parsed_bel, kd_parsed)

        if not ist_ok:
            if not messagebox.askyesno("Plausibilitätswarnung", f"{nachricht}\n\nMöchtest du den Beleg trotzdem anfügen?"):
                return
        elif warn_status == "vorlauf":
            if not messagebox.askyesno("Vorlauf-Einkauf", f"{nachricht}\n\nTrotzdem übernehmen?"):
                return

        self.belege_liste.append({
            "datum": parsed_bel.strftime("%d.%m.%Y"),
            "zweck": zweck,
            "betrag": betrag,
            "datei": self.selected_file_path
        })

        self.entry_bel_betrag.delete(0, "end")
        self.entry_bel_haendler.delete(0, "end")
        self.entry_bel_datum.delete(0, "end")
        self.selected_file_path = None
        self.btn_file.configure(
            text="📎 Beleg-Datei wählen (Bild/PDF)",
            fg_color=("gray80", "gray28"),
            text_color=("black", "white")
        )

        self._belege_karten_rendern()
        self._on_input_changed()

    def beleg_loeschen(self, index):
        if 0 <= index < len(self.belege_liste):
            self.belege_liste.pop(index)
            self._belege_karten_rendern()
            self._on_input_changed()

    def _belege_karten_rendern(self):
        for widget in self.belege_container.winfo_children():
            widget.destroy()

        if not self.belege_liste:
            lbl = ctk.CTkLabel(
                self.belege_container,
                text="Noch keine Belege für diesen Kurs erfasst.",
                text_color=("gray45", "gray65"),
                font=("Arial", 11)
            )
            lbl.pack(anchor="w", pady=2)
            return

        for idx, b in enumerate(self.belege_liste):
            row = ctk.CTkFrame(self.belege_container, fg_color=("gray85", "gray20"), corner_radius=6)
            row.pack(fill="x", pady=3, padx=2)

            datei_name = os.path.basename(b["datei"]) if b.get("datei") else "Kein Dateianhang"
            if len(datei_name) > 20:
                datei_name = datei_name[:17] + "..."

            info_text = f"#{idx+1}: {b['zweck'][:16]} ({b['betrag']:.2f} €) | {datei_name}"
            lbl = ctk.CTkLabel(
                row,
                text=info_text,
                font=("Arial", 11, "bold"),
                text_color=("gray10", "gray95"),
                anchor="w"
            )
            lbl.pack(side="left", padx=8, pady=5, fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row,
                text="X",
                width=28,
                height=24,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                text_color="white",
                font=("Arial", 11, "bold"),
                command=lambda i=idx: self.beleg_loeschen(i)
            )
            del_btn.pack(side="right", padx=6, pady=4)

    def liste_aktualisieren(self):
        self.summary_box.delete("1.0", "end")

        summen = core.berechne_summen(
            self.entry_kurs_dauer.get(),
            self.entry_satz.get(),
            self.belege_liste
        )

        kurs_titel = self.entry_kurs_titel.get().strip() or "– Kein Kurstitel –"
        gruppe = self.entry_ag.get().strip() or "– Keine Gruppe –"
        kurs_datum_str = self.entry_kurs_datum.get().strip() or "– Kein Datum –"

        periode_text = "–"
        parsed_kd, _ = core.parse_datum(kurs_datum_str, "Kursdatum")
        if parsed_kd:
            _, _, p_name = core.ferien_mgr.ermittle_abrechnungszeitraum(parsed_kd)
            periode_text = p_name

        text = (
            f"═══════════════════════════════════════════════════════\n"
            f" KURS: {kurs_titel}\n"
            f" Gruppe/Klasse: {gruppe}\n"
            f" Termin: {kurs_datum_str}\n"
            f" Abrechnungsperiode (BW): {periode_text}\n"
            f"═══════════════════════════════════════════════════════\n\n"
            f"1. AUFWANDSENTSCHÄDIGUNG (STUNDEN)\n"
            f" • Dauer: {summen['dauer']:.2f} Stunden\n"
            f" • Satz:  {summen['satz']:.2f} €/h\n"
            f" ──> Honoraranspruch: {summen['honorar']:.2f} €\n\n"
            f"2. MATERIALAUSLAGEN ({len(self.belege_liste)} Posten)\n"
        )
        for idx, b in enumerate(self.belege_liste, 1):
            anhang = " [Anhang da]" if b.get("datei") else " [Kein Beleg]"
            text += f" #{idx} | {b['datum']} | {b['zweck'][:20]}: {b['betrag']:.2f} €{anhang}\n"

        text += (
            f" ──> Auslagensumme:   {summen['auslagen']:.2f} €\n\n"
            f"═══════════════════════════════════════════════════════\n"
            f" GESAMTAUSZAHLUNG:    {summen['gesamt']:.2f} €\n"
            f"═══════════════════════════════════════════════════════\n"
        )
        self.summary_box.insert("1.0", text)

    def neuen_kurs_starten(self):
        msg = (
            "Möchtest du wirklich einen neuen Kurs abrechnen?\n\n"
            "• Kursdaten und Belege werden geleert.\n"
            "• Deine Personendaten (Name, IBAN, Stundensatz) bleiben erhalten."
        )
        if messagebox.askyesno("Neuen Kurs starten", msg):
            self.entry_kurs_titel.delete(0, "end")
            self.entry_ag.delete(0, "end")
            self.entry_kurs_datum.delete(0, "end")
            self.entry_kurs_dauer.delete(0, "end")
            self.entry_kurs_dauer.insert(0, "2.0")

            self.belege_liste.clear()
            core.loesche_entwurf()
            self._belege_karten_rendern()
            self._on_input_changed()

    def pdf_erstellen(self):
        if not self.entry_leiter.get().strip():
            messagebox.showwarning("Plausibilitätsprüfung", "Bitte den Namen des Kursleiters angeben.")
            return

        if not self.entry_kurs_titel.get().strip():
            messagebox.showwarning("Plausibilitätsprüfung", "Bitte den Kurstitel angeben.")
            return

        kurs_datum_str = self.entry_kurs_datum.get().strip()
        kd_parsed, err = core.parse_datum(kurs_datum_str, "Kursdatum")
        if err:
            messagebox.showwarning("Plausibilitätsprüfung", err)
            return

        ferien_name = core.ferien_mgr.pruefe_in_ferien(kd_parsed)
        if ferien_name:
            msg = (
                f"Hinweis zu Schulferien in BW:\n"
                f"Der Kurstag ({kd_parsed.strftime('%d.%m.%Y')}) liegt in den {ferien_name}.\n\n"
                f"Handelt es sich um ein Ferienprogramm / Sondertermin?\n"
                f"Möchtest du die Abrechnung trotzdem fortsetzen?"
            )
            if not messagebox.askyesno("Kurstag in den Ferien", msg):
                return

        vorschlag_name = core.generiere_standard_dateinamen(
            kurs_datum_str,
            self.entry_kurs_titel.get(),
            self.entry_leiter.get()
        )

        zielpfad = filedialog.asksaveasfilename(
            initialdir=core.EXPORT_DIR,
            initialfile=vorschlag_name,
            defaultextension=".pdf",
            filetypes=[("PDF-Dokument", "*.pdf")],
            title="Abrechnung als PDF speichern"
        )
        if not zielpfad:
            return

        try:
            core.erzeuge_abrechnung_pdf(self.stamm, self.kurs, self.belege_liste, zielpfad)
            self._on_input_changed()

            msg = (
                f"Die PDF wurde erfolgreich gespeichert unter:\n\n"
                f"{zielpfad}\n\n"
                f"Möchtest du den Ordner im Explorer öffnen?"
            )
            if messagebox.askyesno("PDF erfolgreich erstellt", msg):
                self.open_export_dir()
        except Exception as ex:
            messagebox.showerror("Fehler beim Erstellen", f"Fehler aufgetreten:\n{str(ex)}")


if __name__ == "__main__":
    app = WindowsAbrechnungsApp()
    app.mainloop()
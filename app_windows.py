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
            "id": entwurf.get("id", ""),
            "titel": entwurf.get("titel", ""),
            "ag": entwurf.get("ag", ""),
            "datum": entwurf.get("datum", ""),
            "dauer": entwurf.get("dauer", "2.0"),
            "ist_mehrtaegig": bool(entwurf.get("ist_mehrtaegig", False)),
            "termine_anzahl": str(entwurf.get("termine_anzahl", "1")),
            "end_datum": entwurf.get("end_datum", "")
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

        self.entry_leiter = self._create_labeled_entry(
            stamm_card,
            "Name des Kursleiters / Auftragnehmers:",
            "z. B. Maria Musterfrau",
            self.stamm.get("leiter", "")
        )
        self.entry_anschrift = self._create_labeled_entry(
            stamm_card,
            "Anschrift (Straße, Hausnr., PLZ Ort):",
            "z. B. Musterstr. 1, 70123 Stuttgart",
            self.stamm.get("anschrift", "")
        )
        self.entry_telefon = self._create_labeled_entry(
            stamm_card,
            "Telefonnummer / E-Mail:",
            "z. B. 0170 1234567",
            self.stamm.get("telefon", "")
        )
        self.entry_iban = self._create_labeled_entry(
            stamm_card,
            "IBAN (deutsches Girokonto, 22 Stellen):",
            "DE89 3704 0044 0532 0130 00",
            self.stamm.get("iban", "")
        )

        # Stundensatz Anzeige & Admin-Button
        satz_card = ctk.CTkFrame(stamm_card, fg_color=("gray85", "gray22"), corner_radius=6)
        satz_card.pack(fill="x", padx=10, pady=(6, 10))

        self.lbl_satz = ctk.CTkLabel(
            satz_card,
            text=f"💰 Vereinssatz: {float(self.stamm.get('satz', core.DEFAULT_STUNDENSATZ)):.2f} €/h (fest)",
            font=("Arial", 11, "bold"),
            text_color=("gray20", "gray85")
        )
        self.lbl_satz.pack(side="left", padx=10, pady=6)

        self.btn_admin_satz = ctk.CTkButton(
            satz_card,
            text="⚙️",
            width=32,
            height=26,
            font=("Arial", 12),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            text_color=("gray10", "gray95"),
            command=self._admin_pin_dialog
        )
        self.btn_admin_satz.pack(side="right", padx=6, pady=4)

        # 2. Kursdaten (dieser Vorgang)
        kurs_card = ctk.CTkFrame(self.left_frame, fg_color=("gray92", "gray17"), corner_radius=10)
        kurs_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(
            kurs_card,
            text="🏫 2. Kursdaten (dieser Vorgang)",
            font=("Arial", 13, "bold"),
            text_color=("#d97706", "#fbbf24")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # Kurs-ID mit Auto-Vorschlag
        id_header = ctk.CTkFrame(kurs_card, fg_color="transparent")
        id_header.pack(fill="x", padx=10, pady=(6, 1))

        ctk.CTkLabel(
            id_header,
            text="Kurs-ID / Buchungs-Referenz:",
            font=("Arial", 11, "bold"),
            text_color=("#334155", "#cbd5e1")
        ).pack(side="left")

        ctk.CTkButton(
            id_header,
            text="⚡ Neu vorschlagen",
            width=110,
            height=20,
            font=("Arial", 10),
            fg_color=("#d97706", "#b45309"),
            hover_color="#92400e",
            text_color="white",
            command=self.kurs_id_vorschlag_generieren
        ).pack(side="right")

        self.entry_kurs_id = ctk.CTkEntry(kurs_card, placeholder_text="z. B. SJ2627-SCHACH-01")
        if self.kurs.get("id"):
            self.entry_kurs_id.insert(0, str(self.kurs.get("id")))
        self.entry_kurs_id.pack(fill="x", padx=10, pady=(0, 4))

        self.entry_kurs_titel = self._create_labeled_entry(
            kurs_card,
            "Titel des Kurses / AG:",
            "z. B. Robotik-AG oder Schach",
            self.kurs.get("titel", "")
        )
        self.entry_ag = self._create_labeled_entry(
            kurs_card,
            "Gruppe / Schulklasse:",
            "z. B. Klasse 3-4",
            self.kurs.get("ag", "")
        )

        # Checkbox für mehrtägige Kurse
        self.var_mehrtaegig = ctk.BooleanVar(value=bool(self.kurs.get("ist_mehrtaegig", False)))
        self.check_mehrtaegig = ctk.CTkCheckBox(
            kurs_card,
            text="Kurs fand an mehreren Tagen statt",
            variable=self.var_mehrtaegig,
            font=("Arial", 11, "bold"),
            text_color=("#1e3d59", "#90caf9"),
            command=self._on_mehrtaegig_toggled
        )
        self.check_mehrtaegig.pack(anchor="w", padx=10, pady=(6, 4))

        self.entry_kurs_datum = self._create_labeled_entry(
            kurs_card,
            "Datum des Kurstermins (TT.MM.JJJJ):",
            "z. B. 23.10.2026",
            self.kurs.get("datum", "")
        )

        self.frame_mehrtaegig = ctk.CTkFrame(kurs_card, fg_color="transparent")
        self.entry_termine_anzahl = self._create_labeled_entry(
            self.frame_mehrtaegig,
            "Anzahl Termine:",
            "z. B. 4",
            str(self.kurs.get("termine_anzahl", "1"))
        )
        self.entry_kurs_end_datum = self._create_labeled_entry(
            self.frame_mehrtaegig,
            "Enddatum des Kurses (TT.MM.JJJJ):",
            "z. B. 20.11.2026",
            self.kurs.get("end_datum", "")
        )
        if self.var_mehrtaegig.get():
            self.frame_mehrtaegig.pack(fill="x", padx=0, pady=0)

        self.frame_dauer = ctk.CTkFrame(kurs_card, fg_color="transparent")
        self.frame_dauer.pack(fill="x", padx=0, pady=0)
        self.entry_kurs_dauer = self._create_labeled_entry(
            self.frame_dauer,
            "Gesamtdauer in Stunden (z. B. 2.0 oder 8.0):",
            "2.0",
            self.kurs.get("dauer", "2.0")
        )

        for e in [self.entry_leiter, self.entry_anschrift, self.entry_telefon,
                  self.entry_iban,
                  self.entry_kurs_id, self.entry_kurs_titel, self.entry_ag,
                  self.entry_kurs_datum, self.entry_termine_anzahl, self.entry_kurs_end_datum,
                  self.entry_kurs_dauer]:
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

        self.entry_bel_datum = self._create_labeled_entry(
            beleg_card,
            "Kaufdatum des Belegs (TT.MM.JJJJ):",
            "z. B. 15.10.2026"
        )
        self.entry_bel_haendler = self._create_labeled_entry(
            beleg_card,
            "Händler / Verwendungszweck:",
            "z. B. Bastelbedarf Müller"
        )
        self.entry_bel_betrag = self._create_labeled_entry(
            beleg_card,
            "Rechnungsbetrag in €:",
            "z. B. 24.95"
        )

        ctk.CTkLabel(
            beleg_card,
            text="Beleg-Nachweis (Foto oder PDF):",
            font=("Arial", 11, "bold"),
            text_color=("#334155", "#94a3b8"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.btn_file = ctk.CTkButton(
            beleg_card,
            text="📎 Beleg-Datei wählen (Bild/PDF)",
            fg_color=("gray80", "gray28"),
            hover_color=("gray70", "gray35"),
            text_color=("black", "white"),
            command=self.datei_auswaehlen
        )
        self.btn_file.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkButton(
            beleg_card,
            text="+ Beleg hinzufügen",
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="white",
            font=("Arial", 12, "bold"),
            command=self.beleg_hinzufuegen
        ).pack(fill="x", padx=10, pady=(4, 8))

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

        header_btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_btn_frame.pack(side="right")

        ctk.CTkButton(
            header_btn_frame,
            text="🔄 Neu",
            fg_color=("#d97706", "#b45309"),
            hover_color="#92400e",
            text_color="white",
            width=60,
            font=("Arial", 11, "bold"),
            command=self.neuen_kurs_starten
        ).pack(side="left")

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

    def _create_labeled_entry(self, parent, label_text: str, placeholder: str = "", initial: str = ""):
        """Erzeugt ein festes, dauerhaft sichtbares Label und direkt darunter das Eingabefeld."""
        lbl = ctk.CTkLabel(
            parent,
            text=label_text,
            font=("Arial", 11, "bold"),
            text_color=("#334155", "#cbd5e1"),
            anchor="w"
        )
        lbl.pack(anchor="w", padx=10, pady=(6, 1))

        e = ctk.CTkEntry(parent, placeholder_text=placeholder)
        if initial:
            e.insert(0, str(initial))
        e.pack(fill="x", padx=10, pady=(0, 4))
        return e

    def kurs_id_vorschlag_generieren(self):
        titel = self.entry_kurs_titel.get().strip()
        datum = self.entry_kurs_datum.get().strip()
        vorschlag = core.generiere_kurs_id_vorschlag(titel, datum)
        self.entry_kurs_id.delete(0, "end")
        self.entry_kurs_id.insert(0, vorschlag)
        self._on_input_changed()

    def pdf_oeffnen_und_laden(self):
        """Öffnet eine bestehende PDF-Abrechnung und stellt alle Daten zur Weiterbearbeitung her."""
        pfad = filedialog.askopenfilename(
            title="Bestehende Abrechnung öffnen",
            initialdir=core.EXPORT_DIR,
            filetypes=[("PDF-Abrechnungsdokument", "*.pdf")]
        )
        if not pfad:
            return

        erfolg, daten, err = core.lese_abrechnung_aus_pdf(pfad)
        if not erfolg or not daten:
            messagebox.showwarning("Fehler beim Öffnen", err or "Unbekannter Fehler beim Einlesen der PDF.")
            return

        # Stammdaten befüllen
        stamm_neu = daten.get("stammdaten", {})
        if stamm_neu:
            self.stamm.update(stamm_neu)
            self.entry_leiter.delete(0, "end")
            self.entry_leiter.insert(0, self.stamm.get("leiter", ""))
            self.entry_anschrift.delete(0, "end")
            self.entry_anschrift.insert(0, self.stamm.get("anschrift", ""))
            self.entry_telefon.delete(0, "end")
            self.entry_telefon.insert(0, self.stamm.get("telefon", ""))
            self.entry_iban.delete(0, "end")
            self.entry_iban.insert(0, self.stamm.get("iban", ""))
            
            # Stundensatz immer aus geschützten Vereinseinstellungen
            einst = core.lade_einstellungen()
            akt_satz = float(einst.get("stundensatz", core.DEFAULT_STUNDENSATZ))
            self.stamm["satz"] = f"{akt_satz:.2f}"
            self.lbl_satz.configure(text=f"💰 Vereinssatz: {akt_satz:.2f} €/h (fest)")

        # Kursdaten befüllen
        kurs_neu = daten.get("kurs", {})
        if kurs_neu:
            self.kurs.update(kurs_neu)
            self.entry_kurs_id.delete(0, "end")
            self.entry_kurs_id.insert(0, self.kurs.get("id", ""))
            self.entry_kurs_titel.delete(0, "end")
            self.entry_kurs_titel.insert(0, self.kurs.get("titel", ""))
            self.entry_ag.delete(0, "end")
            self.entry_ag.insert(0, self.kurs.get("ag", ""))
            self.entry_kurs_datum.delete(0, "end")
            self.entry_kurs_datum.insert(0, self.kurs.get("datum", ""))
            self.entry_kurs_dauer.delete(0, "end")
            self.entry_kurs_dauer.insert(0, str(self.kurs.get("dauer", "2.0")))

            ist_m = bool(self.kurs.get("ist_mehrtaegig", False))
            self.var_mehrtaegig.set(ist_m)
            self.entry_termine_anzahl.delete(0, "end")
            self.entry_termine_anzahl.insert(0, str(self.kurs.get("termine_anzahl", "1")))
            self.entry_kurs_end_datum.delete(0, "end")
            self.entry_kurs_end_datum.insert(0, self.kurs.get("end_datum", ""))
            if ist_m:
                self.frame_mehrtaegig.pack(fill="x", padx=0, pady=0)
            else:
                self.frame_mehrtaegig.pack_forget()

        # Belege befüllen
        self.belege_liste = daten.get("belege", [])

        core.speichere_stammdaten(self.stamm)
        core.speichere_entwurf(self.kurs, self.belege_liste)

        self._belege_karten_rendern()
        self.liste_aktualisieren()

        kid = self.kurs.get("id") or "Unbekannt"
        messagebox.showinfo("Abrechnung geladen", f"Die Abrechnung '{kid}' wurde erfolgreich geladen!\n\nAlle Felder können nun direkt digital bearbeitet werden.")

    def _on_mehrtaegig_toggled(self):
        if self.var_mehrtaegig.get():
            self.frame_mehrtaegig.pack(fill="x", padx=0, pady=0, before=self.frame_dauer)
        else:
            self.frame_mehrtaegig.pack_forget()
        self._on_input_changed()

    def _on_input_changed(self):
        self.stamm["leiter"] = self.entry_leiter.get()
        self.stamm["anschrift"] = self.entry_anschrift.get()
        self.stamm["telefon"] = self.entry_telefon.get()
        self.stamm["iban"] = self.entry_iban.get()

        # Automatischer Vorschlag für Kurs-ID, falls Titel getippt wird und ID noch leer ist
        aktuelle_id = self.entry_kurs_id.get().strip()
        titel = self.entry_kurs_titel.get().strip()
        if not aktuelle_id and len(titel) >= 3:
            vorschlag = core.generiere_kurs_id_vorschlag(titel, self.entry_kurs_datum.get().strip())
            self.entry_kurs_id.insert(0, vorschlag)

        self.kurs["id"] = self.entry_kurs_id.get().strip()
        self.kurs["titel"] = self.entry_kurs_titel.get()
        self.kurs["ag"] = self.entry_ag.get()
        self.kurs["datum"] = self.entry_kurs_datum.get()
        self.kurs["dauer"] = self.entry_kurs_dauer.get()
        self.kurs["ist_mehrtaegig"] = bool(self.var_mehrtaegig.get())
        self.kurs["termine_anzahl"] = self.entry_termine_anzahl.get().strip()
        self.kurs["end_datum"] = self.entry_kurs_end_datum.get().strip()

        core.speichere_stammdaten(self.stamm)
        core.speichere_entwurf(self.kurs, self.belege_liste)
        self.liste_aktualisieren()

    def _admin_pin_dialog(self):
        dialog = ctk.CTkInputDialog(
            text="Bitte Admin-PIN für Vereinseinstellungen eingeben:",
            title="Admin-Zugang (Vorstand)"
        )
        pin = dialog.get_input()
        if pin is None:
            return  # Abgebrochen
        einst = core.lade_einstellungen()
        korrekt = str(einst.get("admin_pin", core.DEFAULT_ADMIN_PIN))
        if pin.strip() == korrekt:
            self._admin_einstellungen_oeffnen()
        else:
            messagebox.showerror("Zugriff verweigert", "Falsche Admin-PIN!")

    def _admin_einstellungen_oeffnen(self):
        einst = core.lade_einstellungen()
        top = ctk.CTkToplevel(self)
        top.title("⚙️ Vereinseinstellungen (Admin / Vorstand)")
        top.geometry("440x280")
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        ctk.CTkLabel(
            top,
            text="⚙️ Vereinseinstellungen",
            font=("Arial", 14, "bold"),
            text_color=("#1e3d59", "#64b5f6")
        ).pack(anchor="w", padx=20, pady=(15, 4))

        ctk.CTkLabel(
            top,
            text="Hier kann der feste Stundensatz für alle Kursleiter\nsowie die Admin-PIN geändert werden.",
            font=("Arial", 11),
            text_color=("gray40", "gray70"),
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Stundensatz
        f_satz = ctk.CTkFrame(top, fg_color="transparent")
        f_satz.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_satz, text="Stundensatz (€/h):", font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left")
        e_satz = ctk.CTkEntry(f_satz, width=120)
        e_satz.insert(0, f"{float(einst.get('stundensatz', core.DEFAULT_STUNDENSATZ)):.2f}")
        e_satz.pack(side="left")

        # Admin-PIN
        f_pin = ctk.CTkFrame(top, fg_color="transparent")
        f_pin.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_pin, text="Admin-PIN:", font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left")
        e_pin = ctk.CTkEntry(f_pin, width=120)
        e_pin.insert(0, str(einst.get("admin_pin", core.DEFAULT_ADMIN_PIN)))
        e_pin.pack(side="left")

        def speichern():
            try:
                neuer_satz = float(e_satz.get().replace(",", ".").strip())
                if neuer_satz <= 0 or neuer_satz > 200:
                    messagebox.showerror("Fehler", "Bitte einen realistischen Stundensatz angeben (1–200 €).", parent=top)
                    return
            except ValueError:
                messagebox.showerror("Fehler", "Bitte einen gültigen Zahlenwert für den Stundensatz eingeben.", parent=top)
                return

            neue_pin = e_pin.get().strip()
            if len(neue_pin) < 4:
                messagebox.showerror("Fehler", "Die PIN muss mindestens 4 Zeichen lang sein.", parent=top)
                return

            core.speichere_einstellungen({"stundensatz": neuer_satz, "admin_pin": neue_pin})
            self.stamm["satz"] = f"{neuer_satz:.2f}"
            core.speichere_stammdaten(self.stamm)
            self.lbl_satz.configure(text=f"💰 Vereinssatz: {neuer_satz:.2f} €/h (fest)")
            self.liste_aktualisieren()
            messagebox.showinfo("Gespeichert", f"Vereinseinstellungen wurden aktualisiert!\nNeuer Stundensatz: {neuer_satz:.2f} €/h", parent=top)
            top.destroy()

        btn_box = ctk.CTkFrame(top, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkButton(btn_box, text="Abbrechen", fg_color=("gray60", "gray40"), hover_color="gray50", width=100, command=top.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_box, text="💾 Speichern", fg_color=("#15803d", "#16a34a"), hover_color="#15803d", width=120, command=speichern).pack(side="right")

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
            self.stamm.get("satz", f"{core.DEFAULT_STUNDENSATZ:.2f}"),
            self.belege_liste
        )

        kurs_id = self.entry_kurs_id.get().strip() or "– Noch keine Kurs-ID –"
        kurs_titel = self.entry_kurs_titel.get().strip() or "– Kein Kurstitel –"
        gruppe = self.entry_ag.get().strip() or "– Keine Gruppe –"
        kurs_datum_str = self.entry_kurs_datum.get().strip() or "– Kein Datum –"
        leiter_name = self.entry_leiter.get().strip() or "Kursleiter"

        ist_m = bool(self.var_mehrtaegig.get())
        end_d_str = self.entry_kurs_end_datum.get().strip()
        termine_anz = self.entry_termine_anzahl.get().strip() or "1"

        if ist_m and end_d_str:
            termin_anzeige = f"{kurs_datum_str} bis {end_d_str} ({termine_anz} Termine)"
            pruef_datum_str = end_d_str
        else:
            termin_anzeige = kurs_datum_str
            pruef_datum_str = kurs_datum_str

        periode_text = "–"
        warn_text = ""
        parsed_kd, _ = core.parse_datum(pruef_datum_str, "Kursdatum")
        if parsed_kd:
            _, _, p_name = core.ferien_mgr.ermittle_abrechnungszeitraum(parsed_kd)
            periode_text = p_name
            k_warns = core.pruefe_kursdatum_plausibilitaet(parsed_kd)
            if k_warns:
                for w in k_warns:
                    if w["level"] == "gesperrt":
                        icon = "⛔"
                    elif w["level"] == "vorstand":
                        icon = "⚠️"
                    else:
                        icon = "ℹ️"
                    warn_text += f"\n  {icon} {w['titel']}"
            else:
                warn_text = "\n  ✓ Im regulären Abrechnungszeitraum"

        iban_str = self.entry_iban.get().strip()
        if iban_str:
            iban_ok, _ = core.validiere_iban(iban_str)
            iban_status = f"{core.formatiere_iban(iban_str)} (Gültig ✓)" if iban_ok else f"{iban_str} (Prüfung ausstehend / Ungültig ⚠)"
        else:
            iban_status = "– Nicht angegeben –"

        anschrift_val = self.entry_anschrift.get().strip() or "– Nicht angegeben –"
        telefon_val = self.entry_telefon.get().strip() or "– Nicht angegeben –"

        # Fester Dateiname als Vorschau
        fester_name = core.generiere_standard_dateinamen(
            kurs_datum_str,
            kurs_titel,
            leiter_name,
            kurs_id
        )

        text = (
            f"═══════════════════════════════════════════════════════\n"
            f" KURS-ID:      {kurs_id}\n"
            f" KURS:         {kurs_titel}\n"
            f" Person:       {leiter_name} ({telefon_val})\n"
            f" Anschrift:    {anschrift_val}\n"
            f" Gruppe/Klasse: {gruppe}\n"
            f" Termin/Zeit:  {termin_anzeige}\n"
            f" Periode (BW): {periode_text}{warn_text}\n"
            f" IBAN:         {iban_status}\n"
            f" ──> Überweisungs-Ref: {kurs_id} {leiter_name}\n"
            f" ──> Fester Dateiname: {fester_name}\n"
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
            self.entry_kurs_id.delete(0, "end")
            self.entry_kurs_titel.delete(0, "end")
            self.entry_ag.delete(0, "end")
            self.entry_kurs_datum.delete(0, "end")
            self.entry_kurs_dauer.delete(0, "end")
            self.entry_kurs_dauer.insert(0, "2.0")

            self.var_mehrtaegig.set(False)
            self.entry_termine_anzahl.delete(0, "end")
            self.entry_termine_anzahl.insert(0, "1")
            self.entry_kurs_end_datum.delete(0, "end")
            self.frame_mehrtaegig.pack_forget()

            self.belege_liste.clear()
            core.loesche_entwurf()
            self._belege_karten_rendern()
            self._on_input_changed()

    def pdf_erstellen(self):
        # 1. Kursleiter & Anschrift prüfen
        if not self.entry_leiter.get().strip():
            messagebox.showwarning("Plausibilitätsprüfung", "Bitte den Namen des Kursleiters angeben.")
            return

        anschrift_ok, anschrift_err = core.validiere_anschrift(self.entry_anschrift.get())
        if not anschrift_ok:
            messagebox.showwarning("Plausibilitätsprüfung (Anschrift)", anschrift_err)
            return

        # 2. IBAN Modulo-97 validieren
        iban_val = self.entry_iban.get().strip()
        iban_ok, iban_err = core.validiere_iban(iban_val)
        if not iban_ok:
            messagebox.showwarning("IBAN-Prüfung", f"Die angegebene IBAN ist ungültig:\n{iban_err}")
            return

        # 3. Kurs-ID validieren (Option 1)
        kurs_id_val = self.entry_kurs_id.get().strip()
        id_ok, id_err = core.validiere_kurs_id(kurs_id_val)
        if not id_ok:
            messagebox.showwarning("Kurs-ID Prüfung", id_err)
            return

        # 4. Kurstitel prüfen
        if not self.entry_kurs_titel.get().strip():
            messagebox.showwarning("Plausibilitätsprüfung", "Bitte den Kurstitel angeben.")
            return

        # 5. Kursdatum & Mehrteiligkeit prüfen
        kurs_datum_str = self.entry_kurs_datum.get().strip()
        kd_parsed, err = core.parse_datum(kurs_datum_str, "Startdatum / Kurstermin")
        if err:
            messagebox.showwarning("Plausibilitätsprüfung", err)
            return

        ist_m = bool(self.var_mehrtaegig.get())
        pruef_datum_obj = kd_parsed

        if ist_m:
            end_datum_str = self.entry_kurs_end_datum.get().strip()
            kd_end_parsed, end_err = core.parse_datum(end_datum_str, "Enddatum des Kurses")
            if end_err:
                messagebox.showwarning("Plausibilitätsprüfung (Enddatum)", end_err)
                return
            if kd_end_parsed < kd_parsed:
                messagebox.showwarning("Plausibilitätsprüfung", "Das Enddatum des Kurses darf nicht vor dem Startdatum liegen.")
                return

            termine_str = self.entry_termine_anzahl.get().strip()
            try:
                t_count = int(termine_str)
                if t_count < 2:
                    messagebox.showwarning("Plausibilitätsprüfung", "Bei mehrtägigen Kursen muss die Anzahl der Termine mindestens 2 betragen.")
                    return
            except ValueError:
                messagebox.showwarning("Plausibilitätsprüfung", "Bitte eine gültige Termin-Anzahl (ganze Zahl >= 2) angeben.")
                return

            # Bei mehrtägigen Kursen ist das Enddatum für Frist und Abrechnungszeitraum maßgeblich!
            pruef_datum_obj = kd_end_parsed

        # 6. Kursdauer prüfen
        dauer_ok, _, dauer_err = core.validiere_kurs_dauer(self.entry_kurs_dauer.get())
        if not dauer_ok:
            messagebox.showwarning("Plausibilitätsprüfung (Kursdauer)", dauer_err)
            return

        # 7. Plausibilitätsprüfungen zum Kurstermin (Schuljahr, Ferienende-Abrechnungsfenster, Ferien, Wochentag)
        warnungen = core.pruefe_kursdatum_plausibilitaet(pruef_datum_obj)
        for w in warnungen:
            if w["level"] == "gesperrt":
                messagebox.showerror(
                    w["titel"],
                    f"{w['nachricht']}\n\nEin PDF-Export ist nicht möglich."
                )
                return
            elif w["level"] == "vorstand":
                msg = (
                    f"⚠️ {w['titel']}:\n\n"
                    f"{w['nachricht']}\n\n"
                    f"Möchtest du die Abrechnung zur Einreichung beim Vorstand erstellen?"
                )
                if not messagebox.askyesno(w["titel"], msg, icon="warning"):
                    return
            else:
                msg = (
                    f"ℹ️ {w['titel']}:\n\n"
                    f"{w['nachricht']}\n\n"
                    f"Möchtest du fortfahren?"
                )
                if not messagebox.askyesno(w["titel"], msg, icon="question"):
                    return

        # Fester Dateiname für automatisiertes Einlesen durch Kassenwart-App
        fester_dateiname = core.generiere_standard_dateinamen(
            kurs_datum_str,
            self.entry_kurs_titel.get(),
            self.entry_leiter.get(),
            kurs_id_val
        )
        zielpfad = os.path.join(core.EXPORT_DIR, fester_dateiname)

        # Prüfung auf Überschreiben
        if os.path.exists(zielpfad):
            confirm = messagebox.askyesno(
                "Datei existiert bereits",
                f"Die Abrechnung mit dem festen Kassenwart-Dateinamen existiert bereits:\n\n"
                f"'{fester_dateiname}'\n\n"
                f"Möchtest du die Datei überschreiben?"
            )
            if not confirm:
                return

        try:
            core.erzeuge_abrechnung_pdf(self.stamm, self.kurs, self.belege_liste, zielpfad)
            self._on_input_changed()

            msg = (
                f"Die PDF wurde erfolgreich mit festem Kassenwart-Schema gespeichert:\n\n"
                f"📄 {fester_dateiname}\n\n"
                f"Speicherort:\n{zielpfad}\n\n"
                f"Möchtest du den Export-Ordner im Explorer öffnen?"
            )
            if messagebox.askyesno("PDF erfolgreich erstellt", msg):
                self.open_export_dir()
        except Exception as ex:
            messagebox.showerror("Fehler beim Erstellen", f"Fehler aufgetreten:\n{str(ex)}")


if __name__ == "__main__":
    app = WindowsAbrechnungsApp()
    app.mainloop()

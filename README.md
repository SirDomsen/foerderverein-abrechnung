# Förderverein Grundschule – Abrechnungs-Manager (v1.0.0)

Plattformunabhängige Abrechnungssoftware für AG- und Kursleiter an Grundschulen mit integrierter Baden-Württemberg-Ferienprüfung, Plausibilitätskontrollen, mobiler Beleg-Erfassung, E-Mail-Einreichung und Kassenwart-AcroForms.

---

## 🎯 Überblick & Frontends

Das System bietet für jeden Einsatzzweck das passende Frontend:

1. **🌐 Universelle Offline-App (PWA) – `apps/pwa/` (NEU & EMPFOHLEN):**
   - **Läuft 100 % lokal ohne Server** im Browser jedes Geräts (iPhone, Android, Windows, Mac, iPad).
   - Kann direkt auf GitHub Pages gehostet oder als PWA auf dem Smartphone-Homescreen installiert werden.
   - **Kamera-Upload:** Belege direkt mit der Handykamera fotografieren oder als PDF hochladen.
   - **Direktes Einreichen per E-Mail:** Erzeugte PDFs werden über das native Smartphone-Teilen-Menü oder Mail-Programm direkt an `foerderverein.riedlen-gs@gmx.de` übergeben.
   - **100 % Client-Side & Datenschutz:** Keine Daten verlassen das Gerät.

2. **💻 Native Windows-Desktop-Anwendung – `apps/windows/`:**
   - Klassisches Windows-Programm auf Basis von CustomTkinter. Kann über PyInstaller als eigenständige `.exe` gepackt werden.

3. **🐍 Lokaler Python-Webserver – `apps/web/`:**
   - NiceGUI-Server für lokale Netzwerke/WLAN mit QR-Code-Freigabe.

---

### Hauptfunktionen
- **Feste Vergütung mit Schutz:** Standard-Stundensatz von **21,00 €/h**, schreibgeschützt. PIN-Bereich (Standard: **`4711`**) für den Vorstand.
- **BW-Ferien- & Schuljahreslogik:** Dynamische Abrechnungszeiträume nach BW-Sommerferien (2024–2028 offline hinterlegt).
- **Fristen- & Plausibilitätsprüfung:** Harte Sperren bei Einreichungen nach Kassenprüfungsbeginn (Sommerferien) oder Vorjahresterminen; Vorstandsvermerk bei Periodenüberschreitung; 4-Wochen-Belegpuffer; ISO 7064 Modulo-97 IBAN-Validierung.
- **PDF-Engine & AcroForms:** Generiert nach Kassenwart-Standard (`Abrechnung_[KursID]_[Datum]_[Leiter].pdf`) mit 3 Unterschriftenblöcken und digital ausfüllbaren Feldern für Vorstand & Kassenwart sowie eingebetteter `abrechnungsdaten.json`.

---

## 📂 Projektstruktur

```text
foerderverein-abrechnung/
│
├── 📂 apps/
│   ├── 📂 pwa/                      # 🌟 Universelle Offline-Webapp (HTML/JS/PWA, ohne Server!)
│   │   ├── index.html               # Anwendungs-Frontend (Tailwind CSS)
│   │   ├── manifest.json            # PWA-Konfiguration (App-Icon, Standalone)
│   │   ├── sw.js                    # Service Worker für 100% Offline-Betrieb
│   │   ├── icon.svg                 # App-Icon
│   │   └── js/
│   │       ├── core.js              # Ferienlogik, IBAN Modulo-97, Plausibilitäten
│   │       ├── pdf_engine.js        # PDF-Generierung im Browser (pdf-lib) mit AcroForms
│   │       └── app.js               # UI-Controller, Kamera & Mail-Teilen
│   │
│   ├── 📂 windows/                  # Native Desktop-Anwendung (CustomTkinter)
│   │   └── app_windows.py
│   ├── 📂 web/                      # Python Web-Server (NiceGUI / FastAPI)
│   │   └── app_web.py
│   └── 📂 kassenwart/               # [Vorbereitet] Prüf- und Freigabe-App
│
├── 📂 data/                         # Lokale Daten (auf GitHub ignoriert)
│   ├── 📂 cache/                    # Entwürfe & Uploads
│   └── 📂 export/                   # Exportierte PDFs
│
├── 📂 build_tools/                  # PyInstaller Specs & Build-Skripte
│
├── 🚀 Start_Offline_PWA.bat         # 1-Klick-Starter für die serverlose Offline-PWA
├── 🚀 Start_Web_App.bat             # 1-Klick-Starter für den Python-Webserver
├── 🚀 Start_Windows_App.bat         # 1-Klick-Starter für Windows-Desktop
└── README.md
```

---

## 🚀 Schnellstart

### 1. Universelle Offline-App (PWA) starten (Empfohlen):
- Doppelklick auf [`Start_Offline_PWA.bat`](file:///c:/#Coding/Github/foerderverein-abrechnung/Start_Offline_PWA.bat) (oder in VS Code auf den grünen Button *Offline-App (PWA)*).
- Öffnet sich sofort in jedem Browser – **ohne Server, ohne Python, ohne Wartezeit**.
- **Auf Handys:** Sobald der Ordner `apps/pwa/` auf GitHub Pages aktiviert ist, genügt der Link im Safari/Chrome des Handys. Danach läuft sie 100 % offline.

### 2. PDF per E-Mail einreichen:
- Nach dem Klick auf *„Abrechnung prüfen & PDF exportieren“* erscheint der Button:  
  **`📤 Abrechnung per E-Mail einreichen`**
- Auf Smartphones öffnet sich das native E-Mail-Teilen-Menü mit vorbefülltem Empfänger (`foerderverein.riedlen-gs@gmx.de`), Betreff, Nachrichtentext und der fertigen PDF als Anhang!

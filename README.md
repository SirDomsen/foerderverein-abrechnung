# Förderverein Grundschule – Abrechnungs-Manager (v1.0.0)

Plattformunabhängige Abrechnungssoftware für AG- und Kursleiter an Grundschulen mit integrierter Baden-Württemberg-Ferienprüfung, Plausibilitätskontrollen, Beleg-Scanning und Kassenwart-AcroForms.

---

## 📂 Projektstruktur

```text
foerderverein-abrechnung/
│
├── 📂 core/                         # Gemeinsamer Kern & Business-Logik
│   ├── __init__.py
│   └── core.py                      # Berechnungen, BW-Ferienprüfung, PDF-Engine, AcroForms
│
├── 📂 apps/                         # Alle Benutzeroberflächen
│   ├── 📂 windows/                  # Native Desktop-Anwendung (CustomTkinter)
│   │   └── app_windows.py
│   ├── 📂 web/                      # Web- & Smartphone-App (NiceGUI)
│   │   └── app_web.py
│   └── 📂 kassenwart/               # [Vorbereitet] Prüf- und Freigabe-App
│       └── README.md
│
├── 📂 data/                         # Lokale Anwendungsdaten (auf GitHub ignoriert)
│   ├── 📂 cache/                    # Zwischengespeicherte Entwürfe, Einstellungen, Beleg-Uploads
│   └── 📂 export/                   # Exportierte fertige Abrechnungs-PDFs
│
├── 📂 build_tools/                  # Werkzeuge zur Erstellung eigenständiger .exe-Dateien
│   ├── AbrechnungsManager.spec
│   └── build_exe.bat
│
├── 🚀 Start_Web_App.bat             # 1-Klick-Starter für Web & Smartphone (inkl. IP-Erkennung)
├── 🚀 Start_Windows_App.bat         # 1-Klick-Starter für Windows-Desktop
├── requirements.txt                 # Benötigte Python-Pakete
└── .gitignore
```

---

## 🚀 Schnellstart

### 1. Web- & Smartphone-App starten:
- Doppelklick auf `Start_Web_App.bat`.
- Am PC: Browser öffnen unter `http://localhost:8080`.
- Am Smartphone (im selben WLAN): QR-Code am PC scannen oder angezeigte IP im mobilen Browser aufrufen.

### 2. Windows-Desktop-App starten:
- Doppelklick auf `Start_Windows_App.bat`.

/**
 * app.js - UI-Controller & State-Management der PWA
 * Lokale Speicherung in localStorage, reaktive Live-Übersicht,
 * Kamera-Upload und native Teilen- / Mail-Funktion.
 */

// Globaler Zustand
const AppState = {
  stamm: {
    leiter: "",
    anschrift: "",
    telefon: "",
    iban: "",
    satz: "21.00"
  },
  kurs: {
    id: "",
    titel: "",
    ag: "",
    datum: "",
    dauer: "2.0",
    ist_mehrtaegig: false,
    termine_anzahl: "1",
    end_datum: ""
  },
  belege: [],
  settings: {
    stundensatz: DEFAULT_STUNDENSATZ,
    admin_pin: DEFAULT_ADMIN_PIN
  },
  aktuelleDatei: null // { name, type, data (Uint8Array) }
};

// Initialisierung beim Laden
document.addEventListener('DOMContentLoaded', () => {
  ladeLokaleDaten();
  initEventListeners();
  renderUI();
  updateLiveUebersicht();
  registriereServiceWorker();
});

// PWA Service Worker registrieren
function registriereServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch(err => {
      console.warn("SW Registrierung:", err);
    });
  }
}

// Lokale Daten aus localStorage laden
function ladeLokaleDaten() {
  try {
    const sSettings = localStorage.getItem('fv_settings');
    if (sSettings) {
      AppState.settings = Object.assign(AppState.settings, JSON.parse(sSettings));
    }

    const sStamm = localStorage.getItem('fv_stammdaten');
    if (sStamm) {
      AppState.stamm = Object.assign(AppState.stamm, JSON.parse(sStamm));
    }
    // Stundensatz immer aus den geschützten Einstellungen synchronisieren
    AppState.stamm.satz = parseFloat(AppState.settings.stundensatz || DEFAULT_STUNDENSATZ).toFixed(2);

    const sKurs = localStorage.getItem('fv_aktueller_kurs');
    if (sKurs) {
      AppState.kurs = Object.assign(AppState.kurs, JSON.parse(sKurs));
    }

    const sBelege = localStorage.getItem('fv_belege');
    if (sBelege) {
      AppState.belege = JSON.parse(sBelege) || [];
    }
  } catch (e) {
    console.error("Fehler beim Laden von localStorage:", e);
  }
}

// Autosave
function autosave() {
  try {
    localStorage.setItem('fv_settings', JSON.stringify(AppState.settings));
    localStorage.setItem('fv_stammdaten', JSON.stringify(AppState.stamm));
    localStorage.setItem('fv_aktueller_kurs', JSON.stringify(AppState.kurs));
    // Belege ohne die rohen Byte-Daten im localStorage puffern (für Entwurf)
    const belegeMetadaten = AppState.belege.map(b => ({
      datum: b.datum,
      zweck: b.zweck,
      betrag: b.betrag,
      dateiName: b.dateiName,
      dateiType: b.dateiType
    }));
    localStorage.setItem('fv_belege', JSON.stringify(belegeMetadaten));
  } catch (e) {
    console.warn("Autosave Quota:", e);
  }
}

// Formularfelder mit Werten befüllen
function renderUI() {
  document.getElementById('inLeiter').value = AppState.stamm.leiter || "";
  document.getElementById('inAnschrift').value = AppState.stamm.anschrift || "";
  document.getElementById('inTelefon').value = AppState.stamm.telefon || "";
  document.getElementById('inIban').value = AppState.stamm.iban || "";
  document.getElementById('lblStundensatz').textContent = `💰 ${parseFloat(AppState.stamm.satz || 21).toFixed(2)} € / Stunde`;

  document.getElementById('inKursId').value = AppState.kurs.id || "";
  document.getElementById('inKursTitel').value = AppState.kurs.titel || "";
  document.getElementById('inKursAg').value = AppState.kurs.ag || "";
  document.getElementById('checkMehrtaegig').checked = Boolean(AppState.kurs.ist_mehrtaegig);
  toggleMehrtaegigUI(Boolean(AppState.kurs.ist_mehrtaegig));

  document.getElementById('inKursDatum').value = AppState.kurs.datum || "";
  document.getElementById('inTermineAnzahl').value = AppState.kurs.termine_anzahl || "1";
  document.getElementById('inKursEndDatum').value = AppState.kurs.end_datum || "";
  document.getElementById('inKursDauer').value = AppState.kurs.dauer || "2.0";

  renderBelegeListe();
}

function toggleMehrtaegigUI(isMehr) {
  const box = document.getElementById('boxMehrtaegig');
  if (isMehr) {
    box.classList.remove('hidden');
  } else {
    box.classList.add('hidden');
  }
}

// Event-Listener verdrahten
function initEventListeners() {
  // Stammdaten Input
  ['inLeiter', 'inAnschrift', 'inTelefon', 'inIban'].forEach(id => {
    document.getElementById(id).addEventListener('input', (e) => {
      const prop = id.replace('in', '').toLowerCase();
      AppState.stamm[prop] = e.target.value;
      autosave();
      updateLiveUebersicht();
    });
  });

  // Kursdaten Input
  ['inKursId', 'inKursAg', 'inKursDatum', 'inTermineAnzahl', 'inKursEndDatum', 'inKursDauer'].forEach(id => {
    document.getElementById(id).addEventListener('input', (e) => {
      let prop = id.replace('inKurs', '').toLowerCase();
      if (id === 'inTermineAnzahl') prop = 'termine_anzahl';
      if (id === 'inKursEndDatum') prop = 'end_datum';
      AppState.kurs[prop] = e.target.value;
      autosave();
      updateLiveUebersicht();
    });
  });

  // Kurstitel mit Auto-Vorschlag
  document.getElementById('inKursTitel').addEventListener('input', (e) => {
    AppState.kurs.titel = e.target.value;
    if (!AppState.kurs.id && e.target.value.trim().length >= 3) {
      const sugg = generiereKursIdVorschlag(e.target.value, AppState.kurs.datum);
      AppState.kurs.id = sugg;
      document.getElementById('inKursId').value = sugg;
    }
    autosave();
    updateLiveUebersicht();
  });

  // Mehrtaegig Checkbox
  document.getElementById('checkMehrtaegig').addEventListener('change', (e) => {
    AppState.kurs.ist_mehrtaegig = e.target.checked;
    toggleMehrtaegigUI(e.target.checked);
    autosave();
    updateLiveUebersicht();
  });

  // ID Neu vorschlagen Button
  document.getElementById('btnSuggestId').addEventListener('click', () => {
    const sugg = generiereKursIdVorschlag(AppState.kurs.titel, AppState.kurs.datum);
    AppState.kurs.id = sugg;
    document.getElementById('inKursId').value = sugg;
    autosave();
    updateLiveUebersicht();
  });

  // Zahnrad / Admin-PIN Dialog
  document.getElementById('btnAdminSettings').addEventListener('click', oeffneAdminPinModal);

  // Beleg Dateiupload / Kamera
  const fileInput = document.getElementById('inBelegDatei');
  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const arrayBuffer = await file.arrayBuffer();
    AppState.aktuelleDatei = {
      name: file.name,
      type: file.type,
      data: new Uint8Array(arrayBuffer)
    };
    document.getElementById('lblGewaehlteDatei').textContent = `📎 Gewählt: ${file.name}`;
    document.getElementById('lblGewaehlteDatei').classList.add('text-teal-700', 'font-medium');
  });

  // Beleg Hinzufügen Button
  document.getElementById('btnAddBeleg').addEventListener('click', addBeleg);

  // Neuer Kurs Button
  document.getElementById('btnNeuerKurs').addEventListener('click', () => {
    if (confirm("Möchtest du wirklich einen neuen Kurs abrechnen?\n\n• Kursdaten und Belege werden geleert.\n• Personendaten (Name, IBAN, Stundensatz) bleiben erhalten.")) {
      AppState.kurs = { id: "", titel: "", ag: "", datum: "", dauer: "2.0", ist_mehrtaegig: false, termine_anzahl: "1", end_datum: "" };
      AppState.belege = [];
      autosave();
      renderUI();
      updateLiveUebersicht();
    }
  });

  // PDF Export & Senden
  document.getElementById('btnExportPdf').addEventListener('click', starteExportProzess);
}

// Beleg hinzufügen
function addBeleg() {
  const dStr = document.getElementById('inBelegDatum').value.trim();
  const zweck = document.getElementById('inBelegZweck').value.trim();
  const bStr = document.getElementById('inBelegBetrag').value.trim();

  const dParsed = parseGermanDate(dStr);
  if (!dParsed) {
    alert("Bitte ein gültiges Belegdatum angeben (z. B. 15.10.2026).");
    return;
  }
  if (!zweck) {
    alert("Bitte einen Händler oder Verwendungszweck angeben.");
    return;
  }
  const betrag = parseFloat(bStr.replace(',', '.'));
  if (isNaN(betrag) || betrag <= 0) {
    alert("Bitte einen gültigen Rechnungsbetrag größer als 0 eingeben.");
    return;
  }

  // Plausibilität
  const kdParsed = parseGermanDate(AppState.kurs.datum);
  const plausi = pruefeBelegPlausibilitaet(dParsed, kdParsed);
  if (!plausi.ok) {
    if (!confirm(`⚠️ Plausibilitätshinweis:\n\n${plausi.msg}\n\nMöchtest du den Beleg trotzdem übernehmen?`)) {
      return;
    }
  } else if (plausi.status === 'vorlauf') {
    if (!confirm(`ℹ️ Vorlauf-Einkauf:\n\n${plausi.msg}\n\nTrotzdem übernehmen?`)) {
      return;
    }
  }

  AppState.belege.push({
    datum: formatDateGerman(dParsed),
    zweck: zweck,
    betrag: betrag,
    dateiName: AppState.aktuelleDatei ? AppState.aktuelleDatei.name : null,
    dateiType: AppState.aktuelleDatei ? AppState.aktuelleDatei.type : null,
    dateiData: AppState.aktuelleDatei ? AppState.aktuelleDatei.data : null
  });

  // Inputs leeren
  document.getElementById('inBelegDatum').value = "";
  document.getElementById('inBelegZweck').value = "";
  document.getElementById('inBelegBetrag').value = "";
  document.getElementById('inBelegDatei').value = "";
  document.getElementById('lblGewaehlteDatei').textContent = "Kein Anhang gewählt";
  document.getElementById('lblGewaehlteDatei').classList.remove('text-teal-700', 'font-medium');
  AppState.aktuelleDatei = null;

  autosave();
  renderBelegeListe();
  updateLiveUebersicht();
}

// Belegliste rendern
function renderBelegeListe() {
  const container = document.getElementById('belegeContainer');
  container.innerHTML = "";

  if (AppState.belege.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-400 italic">Noch keine Belege für diesen Kurs erfasst.</p>';
    return;
  }

  AppState.belege.forEach((b, idx) => {
    const row = document.createElement('div');
    row.className = "flex justify-between items-center p-2.5 bg-slate-100 rounded-lg border border-slate-200 text-xs";
    const fileBadge = b.dateiName ? `<span class="text-teal-700 ml-1 font-semibold">📎 ${b.dateiName.slice(0, 16)}</span>` : "";
    row.innerHTML = `
      <div class="truncate mr-2">
        <span class="font-bold text-slate-800">#${idx + 1}</span>
        <span class="text-slate-500 ml-1">${b.datum}:</span>
        <span class="font-medium text-slate-700 ml-1">${b.zweck}</span>
        <span class="font-bold text-slate-900 ml-1">(${parseFloat(b.betrag).toFixed(2)} €)</span>
        ${fileBadge}
      </div>
      <button class="bg-red-500 hover:bg-red-600 text-white font-bold py-1 px-2 rounded text-xs transition" onclick="loescheBeleg(${idx})">X</button>
    `;
    container.appendChild(row);
  });
}

window.loescheBeleg = function(idx) {
  AppState.belege.splice(idx, 1);
  autosave();
  renderBelegeListe();
  updateLiveUebersicht();
};

// Live-Übersicht berechnen und aktualisieren
function updateLiveUebersicht() {
  const summen = berechneSummen(AppState.kurs.dauer, AppState.stamm.satz, AppState.belege);

  const istM = Boolean(AppState.kurs.ist_mehrtaegig);
  const startD = AppState.kurs.datum || "–";
  const endD = AppState.kurs.end_datum || "";
  const anzT = AppState.kurs.termine_anzahl || "1";
  const terminText = (istM && endD) ? `${startD} bis ${endD} (${anzT} Termine)` : startD;

  const pruefDStr = (istM && endD) ? endD : AppState.kurs.datum;
  const kdParsed = parseGermanDate(pruefDStr);

  let periodeText = "–";
  let warns = [];
  if (kdParsed) {
    const z = ermittleAbrechnungszeitraum(kdParsed);
    periodeText = z.name;
    warns = pruefeKursdatumPlausibilitaet(kdParsed);
  }

  const ibanVal = (AppState.stamm.iban || "").trim();
  const ibanCheck = validiereIBAN(ibanVal);

  const kid = AppState.kurs.id || "Noch keine Kurs-ID";
  const titel = AppState.kurs.titel || "Kein Kurstitel";
  const leiter = AppState.stamm.leiter || "Kein Name hinterlegt";
  const festerName = generiereDateiname(AppState.kurs.datum, AppState.kurs.titel, leiter, AppState.kurs.id);

  // DOM updaten
  document.getElementById('sumTitel').textContent = titel;
  document.getElementById('sumKursId').textContent = `ID: ${kid}`;
  document.getElementById('sumLeiter').textContent = leiter;

  const sumIban = document.getElementById('sumIban');
  if (ibanVal) {
    sumIban.textContent = formatiereIBAN(ibanVal);
    sumIban.className = `font-mono text-[11px] ${ibanCheck.ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-bold'}`;
  } else {
    sumIban.textContent = "Keine IBAN";
    sumIban.className = "text-[11px] text-red-500 italic";
  }

  document.getElementById('sumTermin').textContent = terminText;
  document.getElementById('sumPeriode').textContent = periodeText;

  // Warnungen Box
  const warnContainer = document.getElementById('sumWarnContainer');
  warnContainer.innerHTML = "";
  if (warns.length > 0) {
    warns.forEach(w => {
      const box = document.createElement('div');
      let colorClass = "bg-sky-50 border-sky-200 text-sky-800";
      let icon = "ℹ️";
      if (w.level === "gesperrt") {
        colorClass = "bg-red-50 border-red-200 text-red-700";
        icon = "⛔";
      } else if (w.level === "vorstand") {
        colorClass = "bg-amber-50 border-amber-200 text-amber-800";
        icon = "⚠️";
      }
      box.className = `p-2 rounded border text-xs flex items-center gap-1.5 ${colorClass}`;
      box.innerHTML = `<span>${icon}</span><span class="font-semibold">${w.titel}</span>`;
      warnContainer.appendChild(box);
    });
  } else if (kdParsed) {
    warnContainer.innerHTML = '<div class="p-1.5 bg-emerald-50 border border-emerald-200 rounded text-xs flex items-center gap-1 text-emerald-700 font-medium"><span>✓</span> Im regulären Abrechnungszeitraum</div>';
  }

  // Zahlen
  document.getElementById('sumHonorarDetail').textContent = `${summen.dauer.toFixed(2)} Std. × ${summen.satz.toFixed(2)} €/h`;
  document.getElementById('sumHonorarBetrag').textContent = `${summen.honorar.toFixed(2)} €`;
  document.getElementById('sumAuslagenDetail').textContent = `Materialauslagen (${AppState.belege.length} Belege)`;
  document.getElementById('sumAuslagenBetrag').textContent = `${summen.auslagen.toFixed(2)} €`;
  document.getElementById('sumGesamtBetrag').textContent = `${summen.gesamt.toFixed(2)} €`;

  document.getElementById('sumRefZweck').textContent = `${kid} ${leiter}`.trim();
  document.getElementById('sumDateiname').textContent = festerName;
}

// Admin-PIN Modal
function oeffneAdminPinModal() {
  const pin = prompt("🔒 Admin-Bereich (Vorstand)\n\nBitte 4-stellige Admin-PIN eingeben:");
  if (pin === null) return;

  const korrekt = String(AppState.settings.admin_pin || DEFAULT_ADMIN_PIN);
  if (pin.trim() === korrekt) {
    oeffneAdminSettingsModal();
  } else {
    alert("Falsche PIN! Zugriff verweigert.");
  }
}

function oeffneAdminSettingsModal() {
  const aktSatz = parseFloat(AppState.settings.stundensatz || DEFAULT_STUNDENSATZ).toFixed(2);
  const neuerSatzStr = prompt("⚙️ Vereinseinstellungen (Vorstand)\n\nFester Standard-Stundensatz für alle Kursleiter (€/h):", aktSatz);
  if (neuerSatzStr === null) return;

  const neuerSatz = parseFloat(neuerSatzStr.replace(',', '.'));
  if (isNaN(neuerSatz) || neuerSatz <= 0 || neuerSatz > 200) {
    alert("Bitte einen realistischen Stundensatz eingeben (1–200 €).");
    return;
  }

  const neuePin = prompt("Admin-PIN ändern (leer lassen für keine Änderung):", "");
  if (neuePin !== null && neuePin.trim().length >= 4) {
    AppState.settings.admin_pin = neuePin.trim();
  }

  AppState.settings.stundensatz = neuerSatz;
  AppState.stamm.satz = neuerSatz.toFixed(2);
  autosave();
  renderUI();
  updateLiveUebersicht();
  alert(`Erfolgreich gespeichert!\nNeuer Stundensatz: ${neuerSatz.toFixed(2)} €/h`);
}

// PDF-Export & Senden
async function starteExportProzess() {
  if (!AppState.stamm.leiter.trim()) {
    alert("Bitte den Namen des Kursleiters angeben.");
    return;
  }
  if (!AppState.stamm.anschrift.trim()) {
    alert("Bitte die vollständige Anschrift (Straße, PLZ, Ort) angeben.");
    return;
  }
  const iCheck = validiereIBAN(AppState.stamm.iban);
  if (!iCheck.ok) {
    alert(`IBAN-Fehler:\n${iCheck.err}`);
    return;
  }
  if (!AppState.kurs.id.trim()) {
    alert("Bitte eine Kurs-ID angeben.");
    return;
  }
  if (!AppState.kurs.titel.trim()) {
    alert("Bitte den Kurstitel angeben.");
    return;
  }
  const kdParsed = parseGermanDate(AppState.kurs.datum);
  if (!kdParsed) {
    alert("Bitte ein gültiges Kursdatum angeben.");
    return;
  }

  // Fristen-Check
  const pruefD = (AppState.kurs.ist_mehrtaegig && AppState.kurs.end_datum) ? parseGermanDate(AppState.kurs.end_datum) : kdParsed;
  const warns = pruefeKursdatumPlausibilitaet(pruefD);
  const gesperrt = warns.find(w => w.level === "gesperrt");
  if (gesperrt) {
    alert(`⛔ ${gesperrt.titel}:\n\n${gesperrt.nachricht}\n\nEin Export ist nicht möglich.`);
    return;
  }

  const vorstandWarn = warns.find(w => w.level === "vorstand");
  if (vorstandWarn) {
    if (!confirm(`⚠️ ${vorstandWarn.titel}:\n\n${vorstandWarn.nachricht}\n\nMöchtest du die Abrechnung zur Genehmigung beim Vorstand einreichen?`)) {
      return;
    }
  }

  const btn = document.getElementById('btnExportPdf');
  btn.disabled = true;
  btn.textContent = "⏳ PDF wird erstellt & Belege eingebettet...";

  try {
    const pdfBytes = await erzeugeAbrechnungPDF(AppState.stamm, AppState.kurs, AppState.belege);
    const dateiname = generiereDateiname(AppState.kurs.datum, AppState.kurs.titel, AppState.stamm.leiter, AppState.kurs.id);
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });

    btn.disabled = false;
    btn.textContent = "📄 Abrechnung prüfen & als PDF exportieren";

    oeffneErfolgsModal(blob, dateiname);
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "📄 Abrechnung prüfen & als PDF exportieren";
    alert(`Fehler bei der PDF-Erstellung:\n${err.message}`);
    console.error(err);
  }
}

// Erfolgs-Modal mit Download & Sendefunktion
function oeffneErfolgsModal(blob, dateiname) {
  const modal = document.getElementById('modalErfolg');
  const summen = berechneSummen(AppState.kurs.dauer, AppState.stamm.satz, AppState.belege);
  document.getElementById('lblModalDateiname').textContent = dateiname;

  const downloadUrl = URL.createObjectURL(blob);
  const btnDownload = document.getElementById('btnModalDownload');
  btnDownload.href = downloadUrl;
  btnDownload.download = dateiname;

  // Sendefunktion konfigurieren
  const btnShare = document.getElementById('btnModalShare');
  const emailBetreff = encodeURIComponent(`Abrechnung ${AppState.kurs.id} - ${AppState.stamm.leiter}`);
  const emailBody = encodeURIComponent(
    `Hallo Vorstand,\n\nanbei sende ich meine Abrechnung für den Kurs "${AppState.kurs.titel}" (${summen.dauer.toFixed(2)} Stunden, Gesamtauszahlung: ${summen.gesamt.toFixed(2)} €).\n\nKurs-ID: ${AppState.kurs.id}\nLeiter: ${AppState.stamm.leiter}\n\nViele Grüße,\n${AppState.stamm.leiter}`
  );
  const mailtoLink = `mailto:${VEREIN_EMAIL}?subject=${emailBetreff}&body=${emailBody}`;

  btnShare.onclick = async () => {
    const file = new File([blob], dateiname, { type: 'application/pdf' });
    // Prüfen, ob navigator.share mit Dateien unterstützt wird (Smartphones)
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({
          files: [file],
          title: `Abrechnung ${AppState.kurs.id}`,
          text: `Abrechnung für Kurs "${AppState.kurs.titel}" von ${AppState.stamm.leiter}`
        });
      } catch (e) {
        if (e.name !== 'AbortError') {
          window.location.href = mailtoLink;
        }
      }
    } else {
      // Fallback für Desktop-PCs: Mailprogramm öffnen
      window.location.href = mailtoLink;
    }
  };

  modal.classList.remove('hidden');
}

window.schliesseErfolgsModal = function() {
  document.getElementById('modalErfolg').classList.add('hidden');
};

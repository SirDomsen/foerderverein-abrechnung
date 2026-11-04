/**
 * pdf_engine.js - Browser-basierte PDF-Generierung mit pdf-lib
 * Rendert das identische Deckblatt inkl. 3 Unterschriftenkästen, AcroForms-Formularfeldern
 * und bettet Belege (Bilder/PDFs) sowie die maschinenlesbare abrechnungsdaten.json ein.
 */

// Filtert Texte auf WinAnsi (Standard-PDF Helvetica Zeichensatz), verhindert Encoding-Crashes
function sanitizeForPdf(str) {
  if (str === null || str === undefined) return "";
  let s = String(str);
  // Entferne Emojis & Variations-Selektoren
  s = s.replace(/[\u{1F000}-\u{1FAFF}]/gu, '');
  s = s.replace(/[\u{2600}-\u{27BF}]/gu, '');
  s = s.replace(/[\u{FE00}-\u{FE0F}]/gu, '');

  return s.split('').map(c => {
    const code = c.charCodeAt(0);
    // ASCII druckbar + Latin-1 (ä, ö, ü, Ä, Ö, Ü, ß, §, usw.)
    if ((code >= 32 && code <= 126) || (code >= 160 && code <= 255)) {
      return c;
    }
    // Erlaubte WinAnsi Sonderzeichen (Euro, typografische Anführungszeichen, Gedankenstrich)
    if ([0x20AC, 0x2013, 0x2014, 0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E, 0x2020, 0x2021, 0x2022, 0x2026, 0x2030, 0x0152, 0x0153, 0x0160, 0x0161, 0x0178, 0x017D, 0x017E].includes(code)) {
      return c;
    }
    if (c === '–' || c === '—') return '-';
    return '';
  }).join('');
}

async function erzeugeAbrechnungPDF(stamm, kurs, belege) {
  const { PDFDocument, rgb, StandardFonts } = PDFLib;

  const pdfDoc = await PDFDocument.create();
  const fontRegular = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
  const fontItalic = await pdfDoc.embedFont(StandardFonts.HelveticaOblique);

  // A4 Maße in Punkten: 595.28 x 841.89
  const page = pdfDoc.addPage([595.28, 841.89]);
  const { width, height } = page.getSize();

  // Sichere drawText Funktion
  const drawSafe = (txt, opts) => {
    page.drawText(sanitizeForPdf(txt), opts);
  };

  // Farbdefinitionen
  const cPrim = rgb(0.118, 0.239, 0.349); // #1e3d59
  const cSek = rgb(0.851, 0.467, 0.024);  // #d97706
  const cBorder = rgb(0.796, 0.835, 0.882); // #cbd5e1
  const cBgHell = rgb(0.973, 0.980, 0.988); // #f8fafc
  const cDark = rgb(0.059, 0.090, 0.165); // #0f172a
  const cGray = rgb(0.278, 0.333, 0.412); // #475569

  let y = height - 36;
  const leftX = 36;
  const rightX = width - 36;
  const contentWidth = rightX - leftX;

  // --- KOPFZEILE ---
  drawSafe("FÖRDERVEREIN DER GRUNDSCHULE E.V.", {
    x: leftX,
    y: y - 14,
    size: 14,
    font: fontBold,
    color: cPrim,
  });

  const heuteStr = formatDateGerman(new Date());
  drawSafe(`Datum: ${heuteStr}`, {
    x: rightX - 120,
    y: y - 10,
    size: 8.5,
    font: fontBold,
    color: cDark,
  });
  drawSafe("v1.0.0 (Web/Mobile)", {
    x: rightX - 120,
    y: y - 22,
    size: 7,
    font: fontRegular,
    color: rgb(0.58, 0.64, 0.72),
  });

  y -= 30;
  drawSafe("Abrechnung über Aufwandsentschädigung & Materialauslagen für Schul-AGs", {
    x: leftX,
    y: y,
    size: 9,
    font: fontItalic,
    color: cGray,
  });

  y -= 8;
  page.drawLine({
    start: { x: leftX, y },
    end: { x: rightX, y },
    thickness: 2,
    color: cSek,
  });

  // --- STAMMDATEN-KASTEN ---
  y -= 14;
  const kastenHeight = 94;
  const boxTop = y;
  page.drawRectangle({
    x: leftX,
    y: boxTop - kastenHeight,
    width: contentWidth,
    height: kastenHeight,
    borderColor: cBorder,
    borderWidth: 0.5,
    color: cBgHell,
  });

  const istMehrtaegig = Boolean(kurs.ist_mehrtaegig);
  const startD = kurs.datum ? formatDateGerman(parseGermanDate(kurs.datum)) : "–";
  const endD = kurs.end_datum ? formatDateGerman(parseGermanDate(kurs.end_datum)) : "";
  const termineAnz = kurs.termine_anzahl || "1";
  const terminText = (istMehrtaegig && endD) ? `${startD} – ${endD} (${termineAnz} Termine)` : startD;

  const kdParsed = parseGermanDate(istMehrtaegig && endD ? kurs.end_datum : kurs.datum);
  const zeitraum = kdParsed ? ermittleAbrechnungszeitraum(kdParsed) : { name: "–" };

  const stammFields = [
    { label1: "Kursleiter / Person:", val1: stamm.leiter || "–", label2: "Kurs-ID / Referenz:", val2: kurs.id || "–", bold: true },
    { label1: "Anschrift:", val1: stamm.anschrift || "–", label2: "Kurstitel:", val2: kurs.titel || "–" },
    { label1: "Telefon / E-Mail:", val1: stamm.telefon || "–", label2: "Gruppe / Klasse:", val2: kurs.ag || "–" },
    { label1: "IBAN:", val1: formatiereIBAN(stamm.iban) || "–", label2: istMehrtaegig ? "Kurszeitraum:" : "Kurstermin:", val2: terminText },
    { label1: "Stundensatz:", val1: `${parseFloat(stamm.satz || 21).toFixed(2)} €/h`, label2: "Abrechnungszeitraum:", val2: zeitraum.name }
  ];

  let rowY = boxTop - 14;
  for (const row of stammFields) {
    drawSafe(row.label1, { x: leftX + 8, y: rowY, size: 7.5, font: fontBold, color: cGray });
    drawSafe(String(row.val1).slice(0, 32), { x: leftX + 110, y: rowY, size: 8, font: row.bold ? fontBold : fontRegular, color: cDark });

    drawSafe(row.label2, { x: leftX + 265, y: rowY, size: 7.5, font: fontBold, color: cGray });
    drawSafe(String(row.val2).slice(0, 38), { x: leftX + 375, y: rowY, size: 8, font: row.bold ? fontBold : fontRegular, color: cDark });
    rowY -= 17;
  }

  y = boxTop - kastenHeight - 16;

  // --- 1. ERBRACHTE KURSLEISTUNG ---
  drawSafe("1. Erbrachte Kursleistung", { x: leftX, y, size: 10, font: fontBold, color: cPrim });
  y -= 6;

  const summen = berechneSummen(kurs.dauer, stamm.satz, belege);

  // Tabellen-Header
  const tblW = contentWidth;
  page.drawRectangle({ x: leftX, y: y - 16, width: tblW, height: 16, color: rgb(0.886, 0.910, 0.941), borderColor: cBorder, borderWidth: 0.5 });
  drawSafe("Datum", { x: leftX + 6, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Kursbezeichnung / Inhalt", { x: leftX + 85, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Dauer", { x: leftX + 355, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Honoraranspruch", { x: rightX - 85, y: y - 11, size: 8, font: fontBold, color: cDark });

  y -= 16;
  // Tabellen-Zeile
  page.drawRectangle({ x: leftX, y: y - 18, width: tblW, height: 18, color: rgb(1, 1, 1), borderColor: cBorder, borderWidth: 0.5 });
  drawSafe(startD, { x: leftX + 6, y: y - 12, size: 8, font: fontRegular, color: cDark });
  drawSafe(`${kurs.titel || '–'} (${kurs.ag || '–'})`.slice(0, 50), { x: leftX + 85, y: y - 12, size: 8, font: fontRegular, color: cDark });
  drawSafe(`${summen.dauer.toFixed(2)} Std.`, { x: leftX + 355, y: y - 12, size: 8, font: fontRegular, color: cDark });
  drawSafe(`${summen.honorar.toFixed(2)} €`, { x: rightX - 65, y: y - 12, size: 8, font: fontBold, color: cDark });

  y -= 28;

  // --- 2. MATERIALAUSLAGEN ---
  drawSafe("2. Auslagen für Kursmaterialien", { x: leftX, y, size: 10, font: fontBold, color: cPrim });
  y -= 6;

  page.drawRectangle({ x: leftX, y: y - 16, width: tblW, height: 16, color: rgb(0.886, 0.910, 0.941), borderColor: cBorder, borderWidth: 0.5 });
  drawSafe("Datum", { x: leftX + 6, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Händler / Verwendungszweck", { x: leftX + 85, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Belegnachweis", { x: leftX + 345, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe("Betrag", { x: rightX - 60, y: y - 11, size: 8, font: fontBold, color: cDark });
  y -= 16;

  const belList = belege && belege.length > 0 ? belege : [{ datum: "–", zweck: "Keine Materialauslagen geltend gemacht", betrag: 0, datei: null }];
  let bIdx = 1;
  for (const b of belList) {
    page.drawRectangle({ x: leftX, y: y - 16, width: tblW, height: 16, color: rgb(1, 1, 1), borderColor: cBorder, borderWidth: 0.5 });
    drawSafe(String(b.datum || '–'), { x: leftX + 6, y: y - 11, size: 7.5, font: fontRegular, color: cDark });
    drawSafe(String(b.zweck || '').slice(0, 48), { x: leftX + 85, y: y - 11, size: 7.5, font: fontRegular, color: cDark });
    const nachweis = b.datei ? `Anhang #${bIdx}` : (b.datum === '–' ? '–' : 'Eigenbeleg');
    drawSafe(nachweis, { x: leftX + 345, y: y - 11, size: 7.5, font: fontRegular, color: cDark });
    drawSafe(`${parseFloat(b.betrag || 0).toFixed(2)} €`, { x: rightX - 60, y: y - 11, size: 7.5, font: fontRegular, color: cDark });
    y -= 16;
    if (b.datei) bIdx++;
  }

  // Summenzeile Auslagen
  page.drawRectangle({ x: leftX, y: y - 16, width: tblW, height: 16, color: cBgHell, borderColor: cBorder, borderWidth: 0.5 });
  drawSafe("Gesamtsumme Auslagen:", { x: leftX + 6, y: y - 11, size: 8, font: fontBold, color: cDark });
  drawSafe(`${summen.auslagen.toFixed(2)} €`, { x: rightX - 60, y: y - 11, size: 8, font: fontBold, color: cDark });
  y -= 24;

  // --- 3. GESAMTAUSZAHLUNG & VERWENDUNGSZWECK ---
  page.drawRectangle({
    x: leftX,
    y: y - 26,
    width: contentWidth,
    height: 26,
    color: rgb(0.863, 0.988, 0.906), // #dcfce7
    borderColor: rgb(0.086, 0.639, 0.290), // #16a34a
    borderWidth: 1,
  });
  drawSafe("Zur Auszahlung fälliger Gesamtbetrag:", { x: leftX + 10, y: y - 17, size: 10, font: fontBold, color: rgb(0.078, 0.325, 0.176) });
  drawSafe(`${summen.gesamt.toFixed(2)} €`, { x: rightX - 85, y: y - 17, size: 11, font: fontBold, color: rgb(0.078, 0.325, 0.176) });
  y -= 32;

  // Referenz / Verwendungszweck Kasten
  const refText = `${kurs.id || 'KURS'} ${stamm.leiter || ''}`.trim();
  page.drawRectangle({ x: leftX, y: y - 18, width: contentWidth, height: 18, color: rgb(0.945, 0.961, 0.976), borderColor: rgb(0.58, 0.64, 0.72), borderWidth: 0.5 });
  drawSafe("Empfohlener Verwendungszweck für Überweisung:", { x: leftX + 8, y: y - 12, size: 8, font: fontRegular, color: cDark });
  drawSafe(refText, { x: leftX + 235, y: y - 12, size: 8.5, font: fontBold, color: cPrim });
  y -= 24;

  // --- 4. RECHTLICHE HINWEISE & AUSSCHLUSSFRIST ---
  page.drawRectangle({ x: leftX, y: y - 36, width: contentWidth, height: 36, color: cBgHell, borderColor: cBorder, borderWidth: 0.5 });
  const rechtstext = "Wichtige Hinweise & Ausschlussfrist: Die Abrechnung für geleistete Stunden hat jeweils blockweise zu erfolgen. Der Abrechnungszeitraum läuft vom Tag nach Ferienende bis zum letzten Tag der kommenden Schulferien bzw. den letzten Schultag vor den Sommerferien. Später eingehende Honorar- oder Aufwandsansprüche verfallen aus gemeinnützigkeitsrechtlichen Gründen endgültig nach Beginn der Kassenprüfung vor den Sommerferien.";
  drawSafe(rechtstext.slice(0, 155), { x: leftX + 6, y: y - 11, size: 6.2, font: fontRegular, color: cGray });
  drawSafe(rechtstext.slice(155, 310), { x: leftX + 6, y: y - 19, size: 6.2, font: fontRegular, color: cGray });
  drawSafe(rechtstext.slice(310), { x: leftX + 6, y: y - 27, size: 6.2, font: fontRegular, color: cGray });
  y -= 42;

  // Formular (AcroForms) initialisieren
  const form = pdfDoc.getForm();

  // --- KASTEN 1: KURSLEITER ---
  const k1H = 50;
  page.drawRectangle({ x: leftX, y: y - k1H, width: contentWidth, height: k1H, color: cBgHell, borderColor: rgb(0.58, 0.64, 0.72), borderWidth: 0.65 });
  drawSafe("1. Kursleiter / Auftragnehmer (Eigenerklärung & Unterschrift)", { x: leftX + 8, y: y - 11, size: 8, font: fontBold, color: cDark });
  const steuerText = "Ich versichere, dass die Leistungen ordnungsgemäß erbracht wurden und im Rahmen des Ehrenamts- bzw. Übungsleiterfreibetrags (§ 3 Nr. 26/26a EStG) erfolgen. Freibeträge werden nicht überschritten.";
  drawSafe(steuerText, { x: leftX + 8, y: y - 22, size: 6.2, font: fontRegular, color: cGray });
  drawSafe(`Ort & Datum: Ulm, den ${heuteStr}`, { x: leftX + 8, y: y - 38, size: 8, font: fontRegular, color: cDark });
  page.drawLine({ start: { x: rightX - 180, y: y - 36 }, end: { x: rightX - 10, y: y - 36 }, thickness: 0.5, color: cGray });
  drawSafe("Unterschrift des Kursleiters", { x: rightX - 145, y: y - 44, size: 6.5, font: fontRegular, color: cGray });
  y -= (k1H + 6);

  // --- KASTEN 2: VORSTAND (AcroForms) ---
  const k2H = 54;
  page.drawRectangle({ x: leftX, y: y - k2H, width: contentWidth, height: k2H, color: cBgHell, borderColor: rgb(0.58, 0.64, 0.72), borderWidth: 0.65 });
  drawSafe("2. Sachlich & rechnerisch geprüft / Auszahlung genehmigt (Vorstand)", { x: leftX + 8, y: y - 11, size: 8, font: fontBold, color: cDark });

  drawSafe("Geprüft & genehmigt am:", { x: leftX + 8, y: y - 26, size: 7.5, font: fontRegular, color: cDark });
  const tfVorstandDatum = form.createTextField('vorstand_datum');
  tfVorstandDatum.setText('');
  tfVorstandDatum.addToPage(page, { x: leftX + 115, y: y - 30, width: 85, height: 16 });

  drawSafe("Vorstand / Visum:", { x: leftX + 245, y: y - 26, size: 7.5, font: fontBold, color: cGray });
  const tfVorstandSignatur = form.createTextField('vorstand_signatur');
  tfVorstandSignatur.setText('');
  tfVorstandSignatur.addToPage(page, { x: leftX + 340, y: y - 30, width: 140, height: 16 });

  drawSafe("Notizen / Prüfvermerk:", { x: leftX + 8, y: y - 44, size: 7.5, font: fontBold, color: cGray });
  const tfVorstandNotizen = form.createTextField('vorstand_notizen');
  tfVorstandNotizen.setText('');
  tfVorstandNotizen.addToPage(page, { x: leftX + 115, y: y - 48, width: 365, height: 16 });
  y -= (k2H + 6);

  // --- KASTEN 3: KASSENWART (AcroForms) ---
  const k3H = 58;
  page.drawRectangle({ x: leftX, y: y - k3H, width: contentWidth, height: k3H, color: rgb(0.941, 0.992, 0.957), borderColor: rgb(0.086, 0.639, 0.290), borderWidth: 0.75 });
  drawSafe("3. Zahlungsanweisung & Ausführungsvermerk des Kassenwarts", { x: leftX + 8, y: y - 11, size: 8, font: fontBold, color: cDark });

  drawSafe("Angewiesener Betrag:", { x: leftX + 8, y: y - 26, size: 7.5, font: fontRegular, color: cDark });
  const tfKwBetrag = form.createTextField('kassenwart_betrag');
  tfKwBetrag.setText('');
  tfKwBetrag.addToPage(page, { x: leftX + 110, y: y - 30, width: 65, height: 16 });
  drawSafe("€", { x: leftX + 180, y: y - 26, size: 8, font: fontRegular, color: cDark });

  drawSafe("Überwiesen am:", { x: leftX + 215, y: y - 26, size: 7.5, font: fontRegular, color: cDark });
  const tfKwDatum = form.createTextField('kassenwart_datum');
  tfKwDatum.setText('');
  tfKwDatum.addToPage(page, { x: leftX + 285, y: y - 30, width: 75, height: 16 });

  drawSafe("Kassenwart / Visum:", { x: leftX + 375, y: y - 26, size: 7, font: fontBold, color: cGray });
  const tfKwSignatur = form.createTextField('kassenwart_signatur');
  tfKwSignatur.setText('');
  tfKwSignatur.addToPage(page, { x: leftX + 450, y: y - 30, width: 65, height: 16 });

  drawSafe("Notizen / Buchungsvermerk:", { x: leftX + 8, y: y - 48, size: 7.5, font: fontBold, color: cGray });
  const tfKwNotizen = form.createTextField('kassenwart_notizen');
  tfKwNotizen.setText('');
  tfKwNotizen.addToPage(page, { x: leftX + 130, y: y - 52, width: 350, height: 16 });

  // --- BELEGE ANHÄNGEN (BILDER & PDFS) ---
  let belegNr = 1;
  for (const b of (belege || [])) {
    if (!b.dateiData) continue;

    try {
      if (b.dateiType === 'application/pdf' || b.dateiName?.toLowerCase().endsWith('.pdf')) {
        // PDF-Beleg einbetten
        const belegDoc = await PDFDocument.load(b.dateiData);
        const copiedPages = await pdfDoc.copyPages(belegDoc, belegDoc.getPageIndices());
        for (const p of copiedPages) {
          pdfDoc.addPage(p);
        }
      } else {
        // Bild-Beleg einbetten (JPEG/PNG)
        let img;
        if (b.dateiType === 'image/png' || b.dateiName?.toLowerCase().endsWith('.png')) {
          img = await pdfDoc.embedPng(b.dateiData);
        } else {
          img = await pdfDoc.embedJpg(b.dateiData);
        }

        const imgPage = pdfDoc.addPage([595.28, 841.89]);
        const imgDims = img.scaleToFit(520, 720);

        imgPage.drawText(sanitizeForPdf(`Beleg #${belegNr}: ${b.zweck || ''} (${parseFloat(b.betrag || 0).toFixed(2)} €)`), {
          x: 36,
          y: 841.89 - 36,
          size: 11,
          font: fontBold,
          color: cPrim,
        });

        imgPage.drawImage(img, {
          x: (595.28 - imgDims.width) / 2,
          y: (841.89 - 60 - imgDims.height),
          width: imgDims.width,
          height: imgDims.height,
        });
      }
      belegNr++;
    } catch (err) {
      console.warn("Fehler beim Einbetten von Beleg:", err);
    }
  }

  // --- METADATEN & ATTACHMENT ---
  pdfDoc.setTitle(sanitizeForPdf(`Abrechnung ${kurs.id || ''} - ${kurs.titel || ''}`));
  pdfDoc.setAuthor(sanitizeForPdf(stamm.leiter || ''));
  pdfDoc.setSubject(sanitizeForPdf(`Förderverein Abrechnung Kurs-ID: ${kurs.id || ''}`));
  pdfDoc.setKeywords([
    sanitizeForPdf(`KursID=${kurs.id || ''}`),
    sanitizeForPdf(`Betrag=${summen.gesamt.toFixed(2)}`),
    sanitizeForPdf(`IBAN=${stamm.iban || ''}`),
    sanitizeForPdf(`Datum=${kurs.datum || ''}`)
  ]);
  pdfDoc.setCreator("Förderverein Grundschule – Abrechnungs-Manager v1.0.0 (PWA)");

  // Maschinenlesbares JSON-Attachment einbetten
  const metaPayload = {
    schema_version: "1.0",
    app_version: "1.0.0",
    erstellt_am: new Date().toISOString(),
    stammdaten: stamm,
    kurs: kurs,
    summen: summen,
    belege: (belege || []).map(b => ({
      datum: b.datum,
      zweck: b.zweck,
      betrag: b.betrag,
      hat_datei: Boolean(b.dateiName)
    }))
  };

  const jsonStr = JSON.stringify(metaPayload, null, 2);
  const jsonBytes = new TextEncoder().encode(jsonStr);
  await pdfDoc.attach(jsonBytes, 'abrechnungsdaten.json', {
    mimeType: 'application/json',
    description: 'Maschinenlesbare Abrechnungsdaten für Kassenwart-App',
    creationDate: new Date(),
    modificationDate: new Date(),
  });

  return await pdfDoc.save();
}

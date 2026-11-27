// HTML -> PDF (und optional PNG-Vorschau je Seite) mit dem Chromium von Playwright.
// Aufruf: node werkzeuge/pdf.cjs <eingabe.html> <ausgabe.pdf> [vorschau-ordner]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const [html, pdf, vorschau] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(html), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  // Rätselseiten: Plan so groß wie möglich, aber "Wer war's?" muss mit 12 mm
  // Abstand zum unteren Rand auf die Seite passen.
  const breiten = await page.evaluate(() => {
    const mm = 96 / 25.4, ergebnis = [];
    for (const s of document.querySelectorAll('section.seite.fall')) {
      const fig = s.querySelector('.haupt figure'), u = s.querySelector('.urteil');
      if (!fig || !u) continue;
      const grenze = s.getBoundingClientRect().bottom - 12 * mm;
      // Reicht die kleinste Planbreite nicht, wird die Seite stufenweise
      // dichter gesetzt (lange Einleitung, viele Gegenstände).
      let w = 102, stufe = 0;
      for (const klasse of ['', 'eng', 'enger']) {
        if (klasse) { s.classList.add(klasse); stufe++; }
        w = 102;
        fig.style.width = w + 'mm';
        while (u.getBoundingClientRect().bottom > grenze && w > 70) { w -= 1; fig.style.width = w + 'mm'; }
        if (u.getBoundingClientRect().bottom <= grenze) break;
      }
      ergebnis.push(stufe ? `${w} (dicht ${stufe})` : w);
    }
    return ergebnis;
  });
  console.log('Planbreiten (mm):', breiten.join(', '));
  await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true });
  if (vorschau) {
    fs.mkdirSync(vorschau, { recursive: true });
    await page.setViewportSize({ width: 794, height: 1123 });
    const seiten = await page.$$('section.seite');
    for (let i = 0; i < seiten.length; i++) {
      await seiten[i].screenshot({ path: path.join(vorschau, `seite-${String(i + 1).padStart(2, '0')}.png`) });
    }
  }
  await browser.close();
})();

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

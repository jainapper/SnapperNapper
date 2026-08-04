// Print the Napper Valley Estate deck to a shareable PDF.
//
//   npm i --no-save playwright-core
//   node scripts/export_nve_pdf.mjs
//
// Sources are the print.html decks written by scripts/generate_nve_brand.py
// (A4 landscape, one idea per page). Fonts are embedded in the HTML, so each
// PDF is self-contained.
import { chromium } from 'playwright-core';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BRAND = resolve(ROOT, 'brand/napper-valley-estate');
const DECKS = [
  ['print.html', 'napper-valley-estate-monograms.pdf'],
  ['print-wordmarks.html', 'napper-valley-estate-wordmarks.pdf'],
];

const executablePath = process.env.CHROMIUM_PATH; // optional, for preinstalled builds
const browser = await chromium.launch(executablePath ? { executablePath, args: ['--no-sandbox'] }
                                                     : { args: ['--no-sandbox'] });
const page = await browser.newPage();
for (const [src, out] of DECKS) {
  const outPath = resolve(BRAND, out);
  await page.goto('file://' + resolve(BRAND, src), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: outPath,
    width: '297mm',
    height: '210mm',
    printBackground: true,
    preferCSSPageSize: true,
  });
  console.log('  wrote', outPath.slice(ROOT.length + 1));
}
await browser.close();

// Print the Napper Valley Estate deck to a shareable PDF.
//
//   npm i --no-save playwright-core
//   node scripts/export_nve_pdf.mjs
//
// Source is brand/napper-valley-estate/print.html (A4 landscape, one idea per
// page) written by scripts/generate_nve_brand.py. Fonts are embedded in the
// HTML, so the PDF is self-contained.
import { chromium } from 'playwright-core';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = resolve(ROOT, 'brand/napper-valley-estate/print.html');
const OUT = resolve(ROOT, 'brand/napper-valley-estate/napper-valley-estate-monograms.pdf');

const executablePath = process.env.CHROMIUM_PATH; // optional, for preinstalled builds
const browser = await chromium.launch(executablePath ? { executablePath, args: ['--no-sandbox'] }
                                                     : { args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.goto('file://' + SRC, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.pdf({
  path: OUT,
  width: '297mm',
  height: '210mm',
  printBackground: true,
  preferCSSPageSize: true,
});
await browser.close();
console.log('  wrote', OUT.slice(ROOT.length + 1));

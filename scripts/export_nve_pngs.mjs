// Export the Napper Valley Estate monogram tiles to 1024 px PNGs.
//
//   npm i --no-save playwright-core   (or npx playwright-core)
//   node scripts/export_nve_pngs.mjs
//
// The SVGs are the master artwork; these PNGs exist only for suppliers and
// previews that cannot take vector files.
import { chromium } from 'playwright-core';
import { readdirSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = resolve(ROOT, 'brand/napper-valley-estate/monograms');
const OUT = resolve(ROOT, 'brand/napper-valley-estate/png');
const SIZE = 1024;

const executablePath = process.env.CHROMIUM_PATH; // optional, for preinstalled builds
const browser = await chromium.launch(executablePath ? { executablePath, args: ['--no-sandbox'] }
                                                     : { args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE } });
mkdirSync(OUT, { recursive: true });

for (const file of readdirSync(SRC).filter(f => f.endsWith('.svg') && !f.endsWith('-1c.svg'))) {
  await page.setContent(
    `<body style="margin:0"><img src="file://${resolve(SRC, file)}" width="${SIZE}" height="${SIZE}"></body>`);
  await page.waitForTimeout(120);
  const out = resolve(OUT, file.replace(/\.svg$/, '.png'));
  await page.screenshot({ path: out, omitBackground: true });
  console.log('  wrote', out.slice(ROOT.length + 1));
}
await browser.close();

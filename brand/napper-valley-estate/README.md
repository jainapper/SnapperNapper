# Napper Valley Estate — NVE monogram system

Ten variations on the NVE monogram for an estate in the Mount Tamborine
hinterland. One family of letterforms, one burgundy world, ten ways to wear it —
each simple enough to survive an umbrella panel, an embroidery needle or a
20 mm pin.

Open [`index.html`](index.html) for the full board: palette, all ten marks, the
one-colour cuts, mockups and the usage rules.

## The ten

| # | Variation | The idea | Made for |
|---|---|---|---|
| 01 | Heirloom Ligature | The original, tightened — N, V and E overlapped beneath one hairline swash | Front-of-house signage, stationery, wine labels, foil |
| 02 | Nested V | A tall centre V carrying a small N and E on its shoulders | Menus, guest compendiums, press |
| 03 | Estate Seal | Roundel, name arced over the crown | Umbrella centre panel, cap crowns, wax seals, coasters |
| 04 | Valley | The V opened into a ridgeline with the sun in the notch | Trail signage, hampers, tote prints |
| 05 | Arch | Gatehouse vault framing the monogram | Gate and room signage, menu headers, key fobs |
| 06 | Monoline | One stroke weight throughout, no hairlines to lose | Embroidery to 20 mm, deboss, etched glass, laser |
| 07 | Lozenge | Keylined diamond topped with a single leaf | Swing tags, buttons, pins, soap and candle labels |
| 08 | Band | Letters ruled top and bottom, diamond points between | Umbrella sleeves, webbing, box edges, robe cuffs, ribbon |
| 09 | Sprig | Old-style letterforms under a single leaf | Spa and garden collateral, candles, preserves, cards |
| 10 | Patch | The mark as an object, reversed in a rounded field | Woven patches, caps, luggage tags, enamel pins, app icon |

## Palette

| Name | Hex | Role |
|---|---|---|
| Oxblood | `#2E0B13` | Deepest ground — night signage, foiled boxes |
| Burgundy | `#4E1220` | The estate colour, primary ground |
| Claret | `#66172A` | Lifted burgundy — panels, tonal stripes |
| Cream | `#F4EDE1` | The mark, reversed out |
| Antique brass | `#C2A15B` | Hairlines and foil — never a fill |
| Dusty rose | `#C79AA2` | Botanical accents, secondary text |

Type behind the letterforms: **Bodoni Moda** (display), **Cormorant Garamond**
(Sprig), **Jost** (spaced capitals) — all SIL OFL. Every mark is converted to
outlines, so no font travels with the artwork and no supplier can substitute one.

## Files

```
monograms/nve-NN-name.svg      cream + brass on a burgundy tile
monograms/nve-NN-name-1c.svg   one colour on transparent — embroidery, deboss, foil
lockups/nve-NN-name-lockup.svg mark + NAPPER VALLEY ESTATE wordmark
png/nve-NN-name.png            1024 px raster of the tile, for suppliers who need it
index.html                     the brand board (self-contained, fonts embedded)
```

## Using them

- **Clear space** — the height of the N on every side. On umbrella panels double
  it; the canopy curves away from the eye.
- **Minimum size** — hairline marks (Heirloom, Seal, Lozenge, Arch) hold to 35 mm
  wide. Below that switch to Monoline, Band or Patch.
- **Colour** — cream on burgundy is the default, burgundy on cream the reverse.
  Brass is a hairline and a foil, never a fill.
- **Don't** — outline the letterforms, add shadows, stretch, introduce a third
  colour, or rotate the mark off its baseline.

## Regenerating

```bash
pip install fonttools brotli
python3 scripts/generate_nve_brand.py     # SVGs + index.html
node scripts/export_nve_pngs.mjs          # PNGs (needs playwright-core)
```

Fonts are downloaded to `.fontcache/` on first run and are not committed.

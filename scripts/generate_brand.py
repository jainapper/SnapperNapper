#!/usr/bin/env python3
"""Generate the FYBRE brand assets (logos, favicons, OG image, web fonts).

Identity (per the FYBRE Brand DNA guide): the F glyph — four fibre-blades
with 45-degree cuts and wind-swept tips, stacked into a forward-leaning F.
Wordmark: FYBRE(TM) in extended grotesk caps. Tagline: ENGINEERED FOR
GROWTH, tracked out and width-matched to the wordmark.

Palette: carbon black / paper white / volt (the volt gradient runs pale
sage to acid green). Type: Archivo (variable width+weight) and Space Mono
for data labels. Fonts are SIL OFL licensed and cached on first run; the
script also subsets them into the self-hosted woff2 files used by the site.

Usage:  python3 scripts/generate_brand.py
Deps:   pip install fonttools brotli pillow
"""

import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets" / "brand"
ASSETS = ROOT / "assets"
FONTS = ROOT / "assets" / "fonts"
CACHE = ROOT / ".fontcache"

# ---------------------------------------------------------------- palette ----
CARBON = "#0A0A0B"
PAPER = "#F5F5F2"
WHITE = "#FFFFFF"
VOLT = "#D8F231"          # flat UI accent
VOLT_ACID = "#E5FA46"     # gradient hot corner
VOLT_PALE = "#F1F3E2"     # gradient cool corner
VOLT_MID = "#E0EC8C"
GRAY = "#55555A"

GF_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl"
FONT_URLS = {
    "Archivo-var.ttf": f"{GF_RAW}/archivo/Archivo%5Bwdth%2Cwght%5D.ttf",
    "SpaceMono-Regular.ttf": f"{GF_RAW}/spacemono/SpaceMono-Regular.ttf",
    "SpaceMono-Bold.ttf": f"{GF_RAW}/spacemono/SpaceMono-Bold.ttf",
}

# latin + punctuation + arrows + (TM)/(R) for the lockups and UI copy
SUBSET_UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+2013-2014,U+2018-201A,U+201C-201E,"
    "U+2022,U+2026,U+2039-203A,U+2190-2199,U+00D7,U+2212,U+2122"
)

WORDMARK_WGHT = 640       # extended grotesk caps, per the lockup
WORDMARK_WDTH = 125
WORD_TRACK = 0.055        # em
TAG_WGHT = 600


def font_path(name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    p = CACHE / name
    if not p.exists():
        urllib.request.urlretrieve(FONT_URLS[name], p)
    return p


def archivo_static(wght: int, wdth: int) -> Path:
    """Instance the Archivo variable font at a fixed weight/width."""
    CACHE.mkdir(exist_ok=True)
    p = CACHE / f"archivo-{wght}-{wdth}.ttf"
    if not p.exists():
        font = TTFont(font_path("Archivo-var.ttf"))
        instantiateVariableFont(font, {"wght": wght, "wdth": wdth}, inplace=True)
        font.save(p)
    return p


# ---------------------------------------------------------------- F glyph ----
# Four fibre-blades in a 120 x 171 box: two long blades (rounded top-left,
# 45-degree beak) and two leaves (vertical right edge, 45-degree cut down to
# a wind-swept tip on the left edge).
GLYPH_W, GLYPH_H = 120.0, 171.0
GLYPH_BASELINE = 137.0    # the stem's right edge ends on the type baseline


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _blade(x, y, w=52.0, h=32.0, r=11.0, blend=13.0, tip=3.0):
    xr = x + w + h
    return (
        f"M{fmt(x)} {fmt(y + r)} "
        f"Q{fmt(x)} {fmt(y)} {fmt(x + r)} {fmt(y)} "
        f"H{fmt(xr - tip)} "
        f"Q{fmt(xr + tip * 0.4)} {fmt(y - tip * 0.4 + 1.4)} {fmt(xr - tip * 0.4)} {fmt(y + tip * 1.1)} "
        f"L{fmt(x + w + blend * 0.7)} {fmt(y + h - blend * 0.7)} "
        f"Q{fmt(x + w)} {fmt(y + h)} {fmt(x + w - blend)} {fmt(y + h)} "
        f"H{fmt(x)} Z "
    )


def _leaf(x, y, right, r=11.0, blend=7.0, tip=3.0):
    w = 34.0
    tip_y = right + w
    return (
        f"M{fmt(x + r)} {fmt(y)} "
        f"H{fmt(x + w)} "
        f"V{fmt(right - blend)} "
        f"Q{fmt(x + w)} {fmt(right)} {fmt(x + w - blend * 0.7)} {fmt(right + blend * 0.7)} "
        f"L{fmt(x + tip * 0.8)} {fmt(tip_y - tip * 0.8)} "
        f"Q{fmt(x - tip * 0.45)} {fmt(tip_y + tip * 0.45 - 1)} {fmt(x)} {fmt(tip_y - tip * 1.4)} "
        f"V{fmt(y + r)} "
        f"Q{fmt(x)} {fmt(y)} {fmt(x + r)} {fmt(y)} Z "
    )


def f_glyph_path(scale: float = 1.0, dx: float = 0.0, dy: float = 0.0) -> str:
    """The F glyph path, optionally scaled/translated (for raw embedding)."""
    d = _blade(34, 0) + _leaf(0, 32, 52) + _blade(34, 66) + _leaf(0, 102, 137)
    if scale == 1.0 and dx == 0.0 and dy == 0.0:
        return d.strip()
    # cheap transform: wrap in a group when writing SVG instead
    raise NotImplementedError("use <g transform=...> for scaled placement")


# ------------------------------------------------------------- text paths ----
def text_path(font_file: Path, text: str, size: float, x: float, baseline: float,
              tracking_em: float = 0.0) -> tuple[str, float]:
    """Return (svg path d, end_x) for text set at `size` px, baseline at y."""
    font = TTFont(font_file)
    upem = font["head"].unitsPerEm
    scale = size / upem
    cmap = font.getBestCmap()
    glyphset = font.getGlyphSet()
    hmtx = font["hmtx"]
    d_parts = []
    cursor = x
    for ch in text:
        gname = cmap[ord(ch)]
        if ch != " ":
            spen = SVGPathPen(glyphset, ntos=fmt)
            tpen = TransformPen(spen, Transform(scale, 0, 0, -scale, cursor, baseline))
            glyphset[gname].draw(tpen)
            cmds = spen.getCommands()
            if cmds:
                d_parts.append(cmds)
        cursor += hmtx[gname][0] * scale + tracking_em * size
    end_x = cursor - tracking_em * size
    return " ".join(d_parts), end_x


def text_width(font_file: Path, text: str, size: float, tracking_em: float = 0.0) -> float:
    _, end = text_path(font_file, text, size, 0, 0, tracking_em)
    return end


def cap_height(font_file: Path) -> float:
    font = TTFont(font_file)
    return font["OS/2"].sCapHeight / font["head"].unitsPerEm


# -------------------------------------------------------------- svg output ----
def svg_doc(inner: str, w: float, h: float, label: str = "FYBRE") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" '
        f'width="{fmt(w)}" height="{fmt(h)}" role="img" aria-label="{label}">{inner}</svg>'
    )


def write(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n")
    print(f"  wrote {p.relative_to(ROOT)}")


def glyph_group(height: float, x: float, y: float, color: str) -> tuple[str, float]:
    """F glyph scaled to `height`, top-left at (x, y). Returns (svg, width)."""
    s = height / GLYPH_H
    d = f_glyph_path()
    g = (f'<g transform="translate({fmt(x)} {fmt(y)}) scale({fmt(s)})">'
         f'<path d="{d}" fill="{color}"/></g>')
    return g, GLYPH_W * s


def gen_marks():
    pad = 4.0
    h = 76.0
    for name, color in [("mark.svg", CARBON), ("mark-dark.svg", PAPER),
                        ("mark-volt.svg", VOLT)]:
        g, w = glyph_group(h, pad, pad, color)
        write(BRAND / name, svg_doc(g, w + 2 * pad, h + 2 * pad))


def lockup(cap: float, glyph_color: str, word_color: str, tagline: bool,
           tag_color: str | None = None, pad: float = 6.0):
    """Glyph + FYBRE(TM) [+ tagline]. Returns (inner, w, h)."""
    display = archivo_static(WORDMARK_WGHT, WORDMARK_WDTH)
    small = archivo_static(TAG_WGHT, 110)
    caph = cap_height(display)
    size = cap / caph

    glyph_h = 1.9 * cap
    baseline = pad + (GLYPH_BASELINE / GLYPH_H) * glyph_h
    g, gw = glyph_group(glyph_h, pad, pad, glyph_color)

    wx = pad + gw + 0.9 * cap
    d, end_x = text_path(display, "FYBRE", size, wx, baseline, tracking_em=WORD_TRACK)
    inner = g + f'<path d="{d}" fill="{word_color}"/>'

    # trademark: "TM" top-aligned with the caps
    tm_size = size * 0.22
    tm_baseline = baseline - cap + tm_size * caph
    tm_d, tm_end = text_path(display, "TM", tm_size, end_x + 0.10 * cap,
                             tm_baseline, tracking_em=0.08)
    inner += f'<path d="{tm_d}" fill="{word_color}"/>'

    total_w = max(tm_end, end_x) + pad
    total_h = pad + glyph_h + pad

    if tagline:
        text = "ENGINEERED FOR GROWTH"
        tsize = 0.185 * cap / cap_height(small)
        natural = text_width(small, text, tsize, 0.0)
        target = end_x - wx
        track_em = (target - natural) / (len(text) - 1) / tsize
        ty = baseline + 0.62 * cap
        td, _ = text_path(small, text, tsize, wx, ty, tracking_em=track_em)
        inner += f'<path d="{td}" fill="{tag_color or word_color}"/>'
        total_h = max(total_h, ty + 0.1 * cap + pad)

    return inner, total_w, total_h


def gen_lockups():
    # plain lockups (nav/footer/email use): light bg carbon, dark bg paper+volt glyph
    for name, gc, wc, tag in [
        ("logo-light.svg", CARBON, CARBON, False),
        ("logo-dark.svg", VOLT, PAPER, False),
        ("logo-tagline-light.svg", CARBON, CARBON, True),
        ("logo-tagline-dark.svg", VOLT, PAPER, True),
    ]:
        inner, w, h = lockup(30.0, gc, wc, tag)
        write(BRAND / name, svg_doc(inner, w, h))


def gen_favicon_svg():
    h = 60.0
    g, gw = glyph_group(h, (96 - h * GLYPH_W / GLYPH_H) / 2, (96 - h) / 2, VOLT)
    inner = f'<rect width="96" height="96" rx="20" fill="{CARBON}"/>{g}'
    write(BRAND / "favicon.svg", svg_doc(inner, 96, 96))


# ----------------------------------------------------------------- raster ----
def hex_rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _bezier(p0, p1, p2, steps=24):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _path_polygons(d: str):
    """Parse our simple path grammar (M/H/V/L/Q/Z absolute) into polygons."""
    import re
    tokens = re.findall(r"[MHVLQZ]|-?\d+(?:\.\d+)?", d)
    polys, cur, i = [], [], 0
    start = None
    while i < len(tokens):
        t = tokens[i]
        if t == "M":
            if cur: polys.append(cur)
            cur = [(float(tokens[i + 1]), float(tokens[i + 2]))]
            start = cur[0]; i += 3
        elif t == "H":
            cur.append((float(tokens[i + 1]), cur[-1][1])); i += 2
        elif t == "V":
            cur.append((cur[-1][0], float(tokens[i + 1]))); i += 2
        elif t == "L":
            cur.append((float(tokens[i + 1]), float(tokens[i + 2]))); i += 3
        elif t == "Q":
            c = (float(tokens[i + 1]), float(tokens[i + 2]))
            e = (float(tokens[i + 3]), float(tokens[i + 4]))
            cur.extend(_bezier(cur[-1], c, e)); i += 5
        elif t == "Z":
            if start: cur.append(start)
            polys.append(cur); cur = []; start = None; i += 1
        else:
            i += 1
    if cur: polys.append(cur)
    return [p for p in polys if len(p) >= 3]


# split the glyph path on piece boundaries so each Z closes one polygon
def _glyph_pieces():
    return [_blade(34, 0), _leaf(0, 32, 52), _blade(34, 66), _leaf(0, 102, 137)]


def draw_glyph(d: ImageDraw.ImageDraw, height: float, x: float, y: float, fill):
    s = height / GLYPH_H
    for piece in _glyph_pieces():
        for poly in _path_polygons(piece):
            pts = [(x + px * s, y + py * s) for px, py in poly]
            d.polygon(pts, fill=fill)


def volt_gradient(w: int, h: int) -> Image.Image:
    """Diagonal pale-sage -> acid-volt gradient, like the brand deck panels."""
    top = hex_rgb(VOLT_PALE)[:3]
    mid = hex_rgb(VOLT_MID)[:3]
    hot = hex_rgb(VOLT_ACID)[:3]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for yy in range(h):
        for xx in range(0, w, 4):          # 4px bands, then smooth resize
            t = (xx / w * 0.55 + yy / h * 0.45)
            if t < 0.55:
                u = t / 0.55
                c = tuple(round(top[i] + (mid[i] - top[i]) * u) for i in range(3))
            else:
                u = (t - 0.55) / 0.45
                c = tuple(round(mid[i] + (hot[i] - mid[i]) * u) for i in range(3))
            for k in range(4):
                if xx + k < w:
                    px[xx + k, yy] = c
    return img


def tile(size: int, rounded: bool) -> Image.Image:
    """Carbon tile with the volt F glyph centred."""
    ss = 4
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=n * 0.21, fill=hex_rgb(CARBON))
    else:
        d.rectangle([0, 0, n, n], fill=hex_rgb(CARBON))
    gh = n * 60 / 96
    gw = gh * GLYPH_W / GLYPH_H
    draw_glyph(d, gh, (n - gw) / 2, (n - gh) / 2, hex_rgb(VOLT))
    return img.resize((size, size), Image.LANCZOS)


def gen_icons():
    tile(180, rounded=False).convert("RGB").save(BRAND / "apple-touch-icon.png")
    print("  wrote assets/brand/apple-touch-icon.png")
    tile(48, rounded=True).save(BRAND / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    print("  wrote assets/brand/favicon.ico")


def gen_og():
    W, H, ss = 1200, 630, 2
    w, h = W * ss, H * ss
    img = volt_gradient(w, h).convert("RGBA")
    d = ImageDraw.Draw(img)

    # ghost glyph bleeding off the right edge
    ghost = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_glyph(ImageDraw.Draw(ghost), h * 1.5, w * 0.72, h * -0.12, hex_rgb(CARBON, 16))
    img = Image.alpha_composite(img, ghost)
    d = ImageDraw.Draw(img)

    # centred lockup: glyph + FYBRE(TM) + tagline
    display = str(archivo_static(WORDMARK_WGHT, WORDMARK_WDTH))
    small = str(archivo_static(TAG_WGHT, 110))
    mono = ImageFont.truetype(str(font_path("SpaceMono-Bold.ttf")), 23 * ss)

    cap = 100 * ss
    ratio = cap_height(CACHE / f"archivo-{WORDMARK_WGHT}-{WORDMARK_WDTH}.ttf")
    word = ImageFont.truetype(display, round(cap / ratio))
    gh = 1.9 * cap
    gwid = gh * GLYPH_W / GLYPH_H

    track_px = WORD_TRACK * cap / ratio
    word_w = d.textlength("FYBRE", font=word) + track_px * 4
    gap = 0.9 * cap
    tm_probe = ImageFont.truetype(display, round(cap * 0.30 / ratio))
    total = gwid + gap + word_w + 0.10 * cap + d.textlength("TM", font=tm_probe)
    x0 = (w - total) / 2
    baseline = h * 0.475
    gy = baseline - (GLYPH_BASELINE / GLYPH_H) * gh
    draw_glyph(d, gh, x0, gy, hex_rgb(CARBON))

    # letter-by-letter for tracking
    cx = x0 + gwid + gap
    for chn in "FYBRE":
        d.text((cx, baseline), chn, font=word, fill=hex_rgb(CARBON), anchor="ls")
        cx += d.textlength(chn, font=word) + track_px
    word_end = cx - track_px
    tm = ImageFont.truetype(display, round(cap * 0.30 / ratio))
    d.text((word_end + 0.10 * cap, baseline - cap), "TM", font=tm,
           fill=hex_rgb(CARBON), anchor="ls")

    # tagline, width-matched under the wordmark
    tag = "ENGINEERED FOR GROWTH"
    tsize = round(0.185 * cap / 0.72)
    tfont = ImageFont.truetype(small, tsize)
    natural = d.textlength(tag, font=tfont)
    extra = (word_end - (x0 + gwid + gap) - natural) / (len(tag) - 1)
    tx = x0 + gwid + gap
    ty = baseline + 0.62 * cap
    for chn in tag:
        d.text((tx, ty), chn, font=tfont, fill=hex_rgb(CARBON), anchor="ls")
        tx += d.textlength(chn, font=tfont) + extra

    d.text((w / 2, h * 0.86), "FYBRELAB.COM — THE 24-HOUR GROWTH SYSTEM",
           font=mono, fill=hex_rgb("#3A3F14"), anchor="ms")

    img.resize((W, H), Image.LANCZOS).convert("RGB").save(ASSETS / "og-image.png", quality=92)
    print("  wrote assets/og-image.png")


# -------------------------------------------------------------- web fonts ----
def subset_font(src: Path, out: Path):
    args = [
        str(src),
        f"--output-file={out}",
        "--flavor=woff2",
        f"--unicodes={SUBSET_UNICODES}",
        "--layout-features=*",
        "--notdef-outline",
        "--no-hinting",
        "--desubroutinize",
    ]
    subset.main(args)
    print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def gen_fonts():
    FONTS.mkdir(parents=True, exist_ok=True)
    subset_font(font_path("Archivo-var.ttf"), FONTS / "archivo-var-latin.woff2")
    subset_font(font_path("SpaceMono-Regular.ttf"), FONTS / "spacemono-400-latin.woff2")
    subset_font(font_path("SpaceMono-Bold.ttf"), FONTS / "spacemono-700-latin.woff2")


if __name__ == "__main__":
    print("Generating FYBRE brand assets…")
    gen_marks()
    gen_lockups()
    gen_favicon_svg()
    gen_icons()
    gen_og()
    gen_fonts()
    print("Done.")

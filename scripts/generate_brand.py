#!/usr/bin/env python3
"""Generate the FYBRE brand assets (logos, favicons, OG image, web fonts).

Identity: the growth bars — three ascending strands, rounded at the tip,
planted on a shared baseline. Hair fibre × bar chart × signal meter: growth
you can measure. The bars are the brand's atomic element, reused across the
site as bullets, dividers and data punctuation.

Palette: carbon black / bone white / volt green.
Type: Archivo (variable width+weight; Expanded Black for display) and
Space Mono for data labels. Fonts are SIL OFL licensed and cached on first
run; the script also subsets them into the self-hosted woff2 files used by
the site.

Usage:  python3 scripts/generate_brand.py
Deps:   pip install fonttools brotli pillow
"""

import io
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
CARBON_2 = "#121214"
BONE = "#F2F0EA"
WHITE = "#FFFFFF"
VOLT = "#C8FF2E"
GRAY = "#B9B9C0"

GF_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl"
FONT_URLS = {
    "Archivo-var.ttf": f"{GF_RAW}/archivo/Archivo%5Bwdth%2Cwght%5D.ttf",
    "SpaceMono-Regular.ttf": f"{GF_RAW}/spacemono/SpaceMono-Regular.ttf",
    "SpaceMono-Bold.ttf": f"{GF_RAW}/spacemono/SpaceMono-Bold.ttf",
}

# latin + punctuation + the arrows the site uses for data callouts
SUBSET_UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+2013-2014,U+2018-201A,U+201C-201E,"
    "U+2022,U+2026,U+2039-203A,U+2190-2199,U+00D7,U+2212"
)


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


# ------------------------------------------------------------ mark ratios ----
# The growth bars, in units of the wordmark cap height (baseline-aligned).
BAR_W = 0.19          # bar width / cap height
BAR_GAP = 0.135       # gap between bars / cap height
BAR_HEIGHTS = (0.46, 0.73, 1.0)   # ascending strand heights / cap height
MARK_GAP = 0.36       # gap between bars and wordmark / cap height
WORD_TRACK = 0.012    # tracking for the FYBRE wordmark (em)


# ------------------------------------------------------------- text paths ----
def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


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


def cap_height(font_file: Path) -> float:
    font = TTFont(font_file)
    return font["OS/2"].sCapHeight / font["head"].unitsPerEm


# -------------------------------------------------------------- bars (svg) ----
def bar_path(x: float, baseline: float, w: float, h: float) -> str:
    """One strand: flat foot on the baseline, rounded tip."""
    r = w / 2
    return (
        f"M{fmt(x)} {fmt(baseline)} "
        f"V{fmt(baseline - h + r)} "
        f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(baseline - h + r)} "
        f"V{fmt(baseline)} Z"
    )


def bars_svg(cap: float, x: float, baseline: float, color: str) -> tuple[str, float]:
    """The growth bars. Returns (svg fragment, end_x)."""
    w = BAR_W * cap
    gap = BAR_GAP * cap
    parts = []
    cx = x
    for hr in BAR_HEIGHTS:
        parts.append(bar_path(cx, baseline, w, hr * cap))
        cx += w + gap
    d = " ".join(parts)
    return f'<path d="{d}" fill="{color}"/>', cx - gap


def svg_doc(inner: str, w: float, h: float, label: str = "FYBRE") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" '
        f'width="{fmt(w)}" height="{fmt(h)}" role="img" aria-label="{label}">{inner}</svg>'
    )


def write(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n")
    print(f"  wrote {p.relative_to(ROOT)}")


def gen_marks():
    cap, pad = 44.0, 4.0
    baseline = pad + cap
    # bars alone — carbon (light bg), bone (dark bg), volt (accent)
    for name, color in [("mark.svg", CARBON), ("mark-dark.svg", BONE),
                        ("mark-volt.svg", VOLT)]:
        inner, end = bars_svg(cap, pad, baseline, color)
        write(BRAND / name, svg_doc(inner, end + pad, cap + 2 * pad))


def gen_lockups():
    cap, pad = 30.0, 4.0
    baseline = pad + cap
    display = archivo_static(900, 125)
    size = cap / cap_height(display)
    # light bg: all carbon · dark bg: volt bars + bone wordmark
    for name, bar_color, word_color in [
        ("logo-light.svg", CARBON, CARBON),
        ("logo-dark.svg", VOLT, BONE),
    ]:
        bars, bars_end = bars_svg(cap, pad, baseline, bar_color)
        d, end_x = text_path(display, "FYBRE", size, bars_end + MARK_GAP * cap,
                             baseline, tracking_em=WORD_TRACK)
        inner = bars + f'<path d="{d}" fill="{word_color}"/>'
        write(BRAND / name, svg_doc(inner, end_x + pad, cap + 2 * pad))


def gen_favicon_svg():
    # carbon rounded tile, volt bars centred
    cap = 54.0
    w = (3 * BAR_W + 2 * BAR_GAP) * cap
    x = (96 - w) / 2
    baseline = (96 + cap) / 2
    bars, _ = bars_svg(cap, x, baseline, VOLT)
    inner = f'<rect width="96" height="96" rx="20" fill="{CARBON}"/>{bars}'
    write(BRAND / "favicon.svg", svg_doc(inner, 96, 96))


# ----------------------------------------------------------------- raster ----
def hex_rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def draw_bars(d: ImageDraw.ImageDraw, cap: float, x: float, baseline: float,
              fill) -> float:
    """Raster twin of bars_svg. Returns the end x."""
    w = BAR_W * cap
    gap = BAR_GAP * cap
    cx = x
    for hr in BAR_HEIGHTS:
        h = hr * cap
        d.rounded_rectangle([cx, baseline - h, cx + w, baseline],
                            radius=w / 2, corners=(True, True, False, False),
                            fill=fill)
        cx += w + gap
    return cx - gap


def tile(size: int, rounded: bool) -> Image.Image:
    """Carbon tile with the volt growth bars centred."""
    ss = 4
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=n * 0.21, fill=hex_rgb(CARBON))
    else:
        d.rectangle([0, 0, n, n], fill=hex_rgb(CARBON))
    cap = n * 54 / 96
    w = (3 * BAR_W + 2 * BAR_GAP) * cap
    draw_bars(d, cap, (n - w) / 2, (n + cap) / 2, hex_rgb(VOLT))
    return img.resize((size, size), Image.LANCZOS)


def gen_icons():
    tile(180, rounded=False).convert("RGB").save(BRAND / "apple-touch-icon.png")
    print("  wrote assets/brand/apple-touch-icon.png")
    tile(48, rounded=True).save(BRAND / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    print("  wrote assets/brand/favicon.ico")


def gen_og():
    W, H, ss = 1200, 630, 2
    w, h = W * ss, H * ss
    img = Image.new("RGBA", (w, h), hex_rgb(CARBON))
    d = ImageDraw.Draw(img)

    # faint lab grid
    step = 60 * ss
    for gx in range(0, w, step):
        d.line([gx, 0, gx, h], fill=(255, 255, 255, 7), width=1)
    for gy in range(0, h, step):
        d.line([0, gy, w, gy], fill=(255, 255, 255, 7), width=1)

    # ghost bars bleeding off the bottom-right
    ghost = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_bars(ImageDraw.Draw(ghost), h * 1.1, w * 0.66, h * 1.28, hex_rgb(VOLT, 26))
    img = Image.alpha_composite(img, ghost)
    d = ImageDraw.Draw(img)

    margin = 96 * ss
    display = str(archivo_static(900, 125))
    sub = ImageFont.truetype(str(archivo_static(600, 100)), 40 * ss)
    mono = ImageFont.truetype(str(font_path("SpaceMono-Bold.ttf")), 25 * ss)

    # volt bars mark
    draw_bars(d, 60 * ss, margin, 148 * ss, hex_rgb(VOLT))

    # FYBRE wordmark
    cap_ratio = cap_height(CACHE / "archivo-900-125.ttf")
    word = ImageFont.truetype(display, round(128 * ss / cap_ratio))
    d.text((margin - 6 * ss, 352 * ss), "FYBRE", font=word,
           fill=hex_rgb(WHITE), anchor="ls")

    d.text((margin, 424 * ss), "The 24-hour growth system. Engineered, not promised.",
           font=sub, fill=hex_rgb(GRAY))
    d.line([margin, 500 * ss, margin + 56 * ss, 500 * ss],
           fill=hex_rgb(VOLT), width=3 * ss)
    d.text((margin, 520 * ss), "FYBRELAB.COM — PERFORMANCE HAIR SCIENCE",
           font=mono, fill=hex_rgb(VOLT))

    img.resize((W, H), Image.LANCZOS).convert("RGB").save(ASSETS / "og-image.png", quality=92)
    print("  wrote assets/og-image.png")


# -------------------------------------------------------------- web fonts ----
def subset_font(src: Path, out: Path, keep_variations: bool = True):
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

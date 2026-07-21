#!/usr/bin/env python3
"""Generate the VC Limited brand assets (logos, favicons, OG image).

Identity: "VC." — the full stop. Space Grotesk letterforms (converted to
vector paths, so no font dependency) closed by an orange square period:
we identify. we implement. we deliver. The orange square is the brand's
atomic element, reused across the site as bullets and punctuation.
Orange / black / white. Fonts are SIL OFL licensed and cached on first run.

Usage:  python3 scripts/generate_brand.py
Deps:   pip install fonttools brotli pillow
"""

import urllib.request
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets" / "brand"
ASSETS = ROOT / "assets"
CACHE = ROOT / ".fontcache"

# ---------------------------------------------------------------- palette ----
BLACK = "#0B0B0C"
WHITE = "#FFFFFF"
ORANGE = "#FF4D00"
ORANGE_SOFT = "#FF7A3D"
GRAY = "#A3A3AA"

FONT_URLS = {
    "spacegrotesk-700.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf",
    "spacegrotesk-500.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf",
    "plexmono-500.ttf": "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJ8lc.ttf",
}


def font_path(name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    p = CACHE / name
    if not p.exists():
        urllib.request.urlretrieve(FONT_URLS[name], p)
    return p


# ------------------------------------------------------------ mark ratios ----
# The period square is sized relative to cap height, sitting on the baseline.
SQUARE_RATIO = 0.24   # square side / cap height
SQUARE_GAP = 0.10     # gap between letters and square / cap height


# ------------------------------------------------------------ text paths ----
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


# ------------------------------------------------------------- svg files ----
def write(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n")
    print(f"  wrote {p.relative_to(ROOT)}")


def vc_dot_svg(text: str, cap_px: float, color: str, pad: float = 4.0,
               tracking: float = -0.02) -> tuple[str, float, float]:
    """Return (inner svg, width, height) for `text` + orange square period."""
    grotesk = font_path("spacegrotesk-700.ttf")
    caph = cap_height(grotesk)
    size = cap_px / caph
    height = cap_px + 2 * pad
    baseline = pad + cap_px
    d, end_x = text_path(grotesk, text, size, pad, baseline, tracking_em=tracking)
    sq = SQUARE_RATIO * cap_px
    sx = end_x + SQUARE_GAP * cap_px
    inner = (
        f'<path d="{d}" fill="{color}"/>'
        f'<rect x="{fmt(sx)}" y="{fmt(baseline - sq)}" width="{fmt(sq)}" height="{fmt(sq)}" fill="{ORANGE}"/>'
    )
    return inner, sx + sq + pad, height


def gen_marks():
    # standalone "VC." marks, transparent background
    for name, color in [("mark.svg", BLACK), ("mark-dark.svg", WHITE)]:
        inner, w, h = vc_dot_svg("VC", 44, color)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" '
            f'width="{fmt(w)}" height="{fmt(h)}" role="img" aria-label="VC Limited">{inner}</svg>'
        )
        write(BRAND / name, svg)

    # tile: black rounded square, "VC." centred
    inner, w, h = vc_dot_svg("VC", 34, WHITE, pad=0)
    ox = (96 - (w)) / 2
    oy = (96 - 34) / 2
    fav = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
        f'<rect width="96" height="96" rx="20" fill="{BLACK}"/>'
        f'<g transform="translate({fmt(ox)} {fmt(oy)})">{inner}</g></svg>'
    )
    write(BRAND / "favicon.svg", fav)


def gen_lockups():
    # full wordmark: "VC LIMITED" closed by the orange square
    for name, color in [("logo-light.svg", BLACK), ("logo-dark.svg", WHITE)]:
        inner, w, h = vc_dot_svg("VC LIMITED", 30, color, tracking=-0.012)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" '
            f'width="{fmt(w)}" height="{fmt(h)}" role="img" aria-label="VC Limited">{inner}</svg>'
        )
        write(BRAND / name, svg)


# ---------------------------------------------------------------- raster ----
def hex_rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def draw_vc_dot(d: ImageDraw.ImageDraw, x: float, baseline: float, cap_px: float,
                text_rgba, orange_rgba, text: str = "VC") -> float:
    """Raster twin of vc_dot_svg. Returns the end x."""
    grotesk = font_path("spacegrotesk-700.ttf")
    ratio = cap_height(grotesk)
    font = ImageFont.truetype(str(grotesk), round(cap_px / ratio))
    d.text((x, baseline), text, font=font, fill=text_rgba, anchor="ls")
    end = x + d.textlength(text, font=font)
    sq = SQUARE_RATIO * cap_px
    sx = end + SQUARE_GAP * cap_px
    d.rectangle([sx, baseline - sq, sx + sq, baseline], fill=orange_rgba)
    return sx + sq


def tile(size: int, rounded: bool) -> Image.Image:
    ss = 4
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=n * 0.21, fill=hex_rgb(BLACK))
    else:
        d.rectangle([0, 0, n, n], fill=hex_rgb(BLACK))
    cap = n * 34 / 96
    grotesk = font_path("spacegrotesk-700.ttf")
    font = ImageFont.truetype(str(grotesk), round(cap / cap_height(grotesk)))
    total = d.textlength("VC", font=font) + (SQUARE_GAP + SQUARE_RATIO) * cap
    baseline = (n + cap) / 2
    draw_vc_dot(d, (n - total) / 2, baseline, cap, hex_rgb(WHITE), hex_rgb(ORANGE))
    return img.resize((size, size), Image.LANCZOS)


def gen_icons():
    tile(180, rounded=False).convert("RGB").save(BRAND / "apple-touch-icon.png")
    print("  wrote assets/brand/apple-touch-icon.png")
    tile(48, rounded=True).save(BRAND / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    print("  wrote assets/brand/favicon.ico")


def gen_og():
    W, H, ss = 1200, 630, 2
    w, h = W * ss, H * ss
    img = Image.new("RGBA", (w, h), hex_rgb(BLACK))

    # ghost "VC." bleeding off the right edge
    ghost = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_vc_dot(ImageDraw.Draw(ghost), w * 0.60, h * 0.86, h * 0.62,
                hex_rgb(WHITE, 12), hex_rgb(ORANGE, 55))
    img = Image.alpha_composite(img, ghost)
    d = ImageDraw.Draw(img)

    margin = 96 * ss
    sg_m = ImageFont.truetype(str(font_path("spacegrotesk-500.ttf")), 40 * ss)
    mono = ImageFont.truetype(str(font_path("plexmono-500.ttf")), 26 * ss)

    draw_vc_dot(d, margin, 300 * ss, 88 * ss, hex_rgb(WHITE), hex_rgb(ORANGE),
                text="VC LIMITED")
    d.text((margin, 356 * ss), "Logistics × manufacturing, engineered for results.",
           font=sg_m, fill=hex_rgb(GRAY))
    d.line([margin, 476 * ss, margin + 56 * ss, 476 * ss],
           fill=hex_rgb(ORANGE), width=3 * ss)
    d.text((margin, 494 * ss), "VCLTD.CO — BUSINESS BAY, DUBAI",
           font=mono, fill=hex_rgb(ORANGE_SOFT))

    img.resize((W, H), Image.LANCZOS).convert("RGB").save(ASSETS / "og-image.png", quality=92)
    print("  wrote assets/og-image.png")


if __name__ == "__main__":
    print("Generating VC Limited brand assets…")
    gen_marks()
    gen_lockups()
    gen_icons()
    gen_og()
    print("Done.")

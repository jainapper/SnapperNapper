#!/usr/bin/env python3
"""Generate the VC Limited brand assets (logos, favicons, OG image).

Identity: the "route V" — two supply nodes converging along a route to a
single sharp vertex. Orange / black / white. Wordmark set in Space Grotesk
(converted to vector paths, so no font dependency). Fonts are SIL OFL
licensed and cached locally on first run.

Usage:  python3 scripts/generate_brand.py
Deps:   pip install fonttools brotli pillow
"""

import math
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


# --------------------------------------------------------- mark geometry ----
# 96x96 box. An asymmetric route: down to a sharp vertex, then up and past
# the start to a terminal node — the destination, marked in orange.
V_TOPS = ((24.0, 32.0), (74.0, 20.0))
V_APEX = (46.0, 74.0)
V_STROKE = 11.0
NODE_R = 8.5


def mark_svg_elements(v_color: str, node_color: str) -> str:
    (x1, y1), (x2, y2) = V_TOPS
    ax, ay = V_APEX
    return (
        f'<path d="M {x1} {y1} L {ax} {ay} L {x2} {y2}" fill="none" '
        f'stroke="{v_color}" stroke-width="{V_STROKE}" '
        f'stroke-linecap="butt" stroke-linejoin="miter"/>'
        f'<circle cx="{x2}" cy="{y2}" r="{NODE_R}" fill="{node_color}"/>'
    )


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


def gen_marks():
    for name, v, node in [
        ("mark.svg", BLACK, ORANGE),        # for light backgrounds
        ("mark-dark.svg", WHITE, ORANGE),   # for dark backgrounds
    ]:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" '
            f'width="96" height="96" role="img" aria-label="VC Limited mark">'
            f"{mark_svg_elements(v, node)}</svg>"
        )
        write(BRAND / name, svg)

    fav = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
        f'<rect width="96" height="96" rx="20" fill="{BLACK}"/>'
        '<g transform="translate(48 48) scale(0.8) translate(-48 -48)">'
        + mark_svg_elements(WHITE, ORANGE)
        + "</g></svg>"
    )
    write(BRAND / "favicon.svg", fav)


def gen_lockups():
    grotesk = font_path("spacegrotesk-700.ttf")
    caph = cap_height(grotesk)
    text_cap_px = 30.0
    size = text_cap_px / caph
    baseline = 48 + text_cap_px / 2
    gap = 20.0
    d, end_x = text_path(grotesk, "VC LIMITED", size, 96 + gap, baseline,
                         tracking_em=-0.008)
    width = end_x + 4
    for name, color in [
        ("logo-light.svg", BLACK),   # on light backgrounds
        ("logo-dark.svg", WHITE),    # on dark backgrounds
    ]:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(width)} 96" '
            f'width="{fmt(width)}" height="96" role="img" aria-label="VC Limited">'
            + mark_svg_elements(color, ORANGE)
            + f'<path d="{d}" fill="{color}"/>'
            + "</svg>"
        )
        write(BRAND / name, svg)


# ---------------------------------------------------------------- raster ----
def hex_rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def draw_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float,
              v_rgba, node_rgba):
    """Draw the mark; `scale` = pixels per unit of the 96 box."""
    def pt(p):
        return (cx + (p[0] - 48) * scale, cy + (p[1] - 48) * scale)

    a = pt(V_APEX)
    t1 = pt(V_TOPS[0])
    t2 = pt(V_TOPS[1])
    hw = V_STROKE * scale / 2

    def unit(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    u1 = unit(a, t1)
    u2 = unit(a, t2)
    n1 = (u1[1], -u1[0])
    n2 = (-u2[1], u2[0])
    bis = (-(u1[0] + u2[0]), -(u1[1] + u2[1]))
    bn = math.hypot(*bis)
    bis = (bis[0] / bn, bis[1] / bn)
    half_angle = math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1]))) / 2
    miter = hw / math.sin(half_angle)
    tip = (a[0] + bis[0] * miter, a[1] + bis[1] * miter)
    inner = (a[0] - bis[0] * miter, a[1] - bis[1] * miter)
    poly = [
        (t1[0] + n1[0] * hw, t1[1] + n1[1] * hw), tip,
        (t2[0] + n2[0] * hw, t2[1] + n2[1] * hw),
        (t2[0] - n2[0] * hw, t2[1] - n2[1] * hw), inner,
        (t1[0] - n1[0] * hw, t1[1] - n1[1] * hw),
    ]
    draw.polygon(poly, fill=v_rgba)
    r = NODE_R * scale
    draw.ellipse([t2[0] - r, t2[1] - r, t2[0] + r, t2[1] + r], fill=node_rgba)


def gen_icons():
    ss = 4
    size = 180 * ss
    img = Image.new("RGBA", (size, size), hex_rgb(BLACK))
    d = ImageDraw.Draw(img)
    draw_mark(d, size / 2, size / 2, (size * 0.62) / 96, hex_rgb(WHITE), hex_rgb(ORANGE))
    img.resize((180, 180), Image.LANCZOS).convert("RGB").save(BRAND / "apple-touch-icon.png")
    print("  wrote assets/brand/apple-touch-icon.png")

    base = 48 * ss
    img = Image.new("RGBA", (base, base), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, base - 1, base - 1], radius=base * 0.21, fill=hex_rgb(BLACK))
    draw_mark(d, base / 2, base / 2, (base * 0.78) / 96, hex_rgb(WHITE), hex_rgb(ORANGE))
    img48 = img.resize((48, 48), Image.LANCZOS)
    img48.save(BRAND / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    print("  wrote assets/brand/favicon.ico")


def gen_og():
    W, H, ss = 1200, 630, 2
    w, h = W * ss, H * ss
    img = Image.new("RGBA", (w, h), hex_rgb(BLACK))

    ghost = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(ghost), w * 0.87, h * 0.55, (h * 1.3) / 96,
              hex_rgb(WHITE, 14), hex_rgb(ORANGE, 60))
    img = Image.alpha_composite(img, ghost)
    d = ImageDraw.Draw(img)

    margin = 96 * ss
    sg_b = ImageFont.truetype(str(font_path("spacegrotesk-700.ttf")), 108 * ss)
    sg_m = ImageFont.truetype(str(font_path("spacegrotesk-500.ttf")), 40 * ss)
    mono = ImageFont.truetype(str(font_path("plexmono-500.ttf")), 26 * ss)

    draw_mark(d, margin + 40 * ss, 148 * ss, (84 * ss) / 96,
              hex_rgb(WHITE), hex_rgb(ORANGE))

    d.text((margin, 258 * ss), "VC LIMITED", font=sg_b, fill=hex_rgb(WHITE))
    d.text((margin, 400 * ss), "Logistics × manufacturing, engineered for results.",
           font=sg_m, fill=hex_rgb(GRAY))
    d.line([margin, 496 * ss, margin + 56 * ss, 496 * ss],
           fill=hex_rgb(ORANGE), width=3 * ss)
    d.text((margin, 514 * ss), "VCLTD.CO — BUSINESS BAY, DUBAI",
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

#!/usr/bin/env python3
"""Generate the VC Limited brand assets (logos, favicons, OG image).

Outputs into assets/brand/ and assets/. Fonts (Archivo, IBM Plex Mono — both
SIL OFL licensed) are downloaded to a local cache on first run.

Usage:  python3 scripts/generate_brand.py
Deps:   pip install fonttools brotli pillow
"""

import math
import os
import re
import struct
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
INK = "#0A0E17"        # near-black navy — primary dark
PAPER = "#F6F4EF"      # warm porcelain — primary light
GOLD = "#C9A227"       # brass gold — accent
GOLD_SOFT = "#E8C766"  # lighter gold for dark surfaces
MUTED_DARK = "#98A2B3" # secondary text on ink

FONT_URLS = {
    "archivo-600.ttf": "https://fonts.gstatic.com/s/archivo/v25/k3k6o8UDI-1M0wlSV9XAw6lQkqWY8Q82sJaRE-NWIDdgffTT6jRp8A.ttf",
    "archivo-700.ttf": "https://fonts.gstatic.com/s/archivo/v25/k3k6o8UDI-1M0wlSV9XAw6lQkqWY8Q82sJaRE-NWIDdgffTT0zRp8A.ttf",
    "archivo-500.ttf": "https://fonts.gstatic.com/s/archivo/v25/k3k6o8UDI-1M0wlSV9XAw6lQkqWY8Q82sJaRE-NWIDdgffTTBjNp8A.ttf",
    "plexmono-500.ttf": "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJ8lc.ttf",
}


def font_path(name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    p = CACHE / name
    if not p.exists():
        urllib.request.urlretrieve(FONT_URLS[name], p)
    return p


# --------------------------------------------------------- mark geometry ----
# The mark lives in a 96x96 box: an open gold arc (the "C", opening east)
# holding a sharp V — a compass for trade routes.
CX, CY, R, STROKE = 48.0, 48.0, 33.0, 9.0
GAP_HALF_DEG = 42.0                      # half-angle of the arc's opening
V_APEX = (48.0, 63.0)
V_TOPS = ((33.0, 34.0), (63.0, 34.0))
V_STROKE = 9.0


def arc_endpoints():
    a = math.radians(GAP_HALF_DEG)
    top = (CX + R * math.cos(-a), CY + R * math.sin(-a))
    bot = (CX + R * math.cos(a), CY + R * math.sin(a))
    return top, bot


def mark_svg_elements(arc_color: str, v_color: str, opacity: float = 1.0) -> str:
    (tx, ty), (bx, by) = arc_endpoints()
    o = f' opacity="{opacity}"' if opacity < 1 else ""
    return (
        f'<g{o}>'
        f'<path d="M {tx:.3f} {ty:.3f} A {R} {R} 0 1 0 {bx:.3f} {by:.3f}" '
        f'fill="none" stroke="{arc_color}" stroke-width="{STROKE}" stroke-linecap="round"/>'
        f'<path d="M {V_TOPS[0][0]} {V_TOPS[0][1]} L {V_APEX[0]} {V_APEX[1]} L {V_TOPS[1][0]} {V_TOPS[1][1]}" '
        f'fill="none" stroke="{v_color}" stroke-width="{V_STROKE}" '
        f'stroke-linecap="round" stroke-linejoin="miter"/>'
        f"</g>"
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
    for name, arc, v, bg in [
        ("mark.svg", GOLD, INK, None),           # for light backgrounds
        ("mark-dark.svg", GOLD, "#FFFFFF", None) # for dark backgrounds
    ]:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" '
            f'width="96" height="96" role="img" aria-label="VC Limited mark">'
            f"{mark_svg_elements(arc, v)}</svg>"
        )
        write(BRAND / name, svg)

    # favicon: mark on an ink rounded square
    fav = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
        f'<rect width="96" height="96" rx="20" fill="{INK}"/>'
        '<g transform="translate(48 48) scale(0.82) translate(-48 -48)">'
        + mark_svg_elements(GOLD, "#FFFFFF")
        + "</g></svg>"
    )
    write(BRAND / "favicon.svg", fav)


def gen_lockups():
    archivo = font_path("archivo-600.ttf")
    caph = cap_height(archivo)          # in em
    text_cap_px = 30.0                  # cap height of wordmark in the 96 box
    size = text_cap_px / caph
    baseline = 48 + text_cap_px / 2
    gap = 21.0
    d, end_x = text_path(archivo, "VC LIMITED", size, 96 + gap, baseline,
                         tracking_em=-0.012)
    width = end_x + 4
    for name, text_color, v_color in [
        ("logo-light.svg", INK, INK),        # on light backgrounds
        ("logo-dark.svg", "#FFFFFF", "#FFFFFF"),  # on dark backgrounds
    ]:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(width)} 96" '
            f'width="{fmt(width)}" height="96" role="img" aria-label="VC Limited">'
            + mark_svg_elements(GOLD, v_color)
            + f'<path d="{d}" fill="{text_color}"/>'
            + "</svg>"
        )
        write(BRAND / name, svg)


# ---------------------------------------------------------------- raster ----
def hex_rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def draw_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float,
              arc_rgba, v_rgba):
    """Draw the mark scaled so that `scale` = pixels per unit of the 96 box."""
    def pt(x, y):
        return (cx + (x - 48) * scale, cy + (y - 48) * scale)

    w = STROKE * scale
    # PIL thickens arcs inward from the bbox edge, so push the bbox out by
    # half a stroke to keep the stroke centerline on radius R.
    r = (R + STROKE / 2) * scale
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(bbox, start=GAP_HALF_DEG, end=360 - GAP_HALF_DEG, fill=arc_rgba,
             width=max(1, round(w)))
    # round caps on the arc ends
    for p in arc_endpoints():
        x, y = pt(*p)
        hw = w / 2
        draw.ellipse([x - hw, y - hw, x + hw, y + hw], fill=arc_rgba)

    # V as a mitred polygon with round top caps
    a = pt(*V_APEX)
    t1 = pt(*V_TOPS[0])
    t2 = pt(*V_TOPS[1])
    hw = V_STROKE * scale / 2

    def unit(p, q):
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    u1 = unit(a, t1)               # apex -> left top
    u2 = unit(a, t2)               # apex -> right top
    n1 = (u1[1], -u1[0])           # outward normal of left arm (points left)
    n2 = (-u2[1], u2[0])           # outward normal of right arm (points right)
    bis = (-(u1[0] + u2[0]), -(u1[1] + u2[1]))
    bn = math.hypot(*bis)
    bis = (bis[0] / bn, bis[1] / bn)         # downward bisector
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
    for t in (t1, t2):
        draw.ellipse([t[0] - hw, t[1] - hw, t[0] + hw, t[1] + hw], fill=v_rgba)


def gen_icons():
    ss = 4  # supersample
    # apple touch icon 180x180
    size = 180 * ss
    img = Image.new("RGBA", (size, size), hex_rgb(INK))
    d = ImageDraw.Draw(img)
    draw_mark(d, size / 2, size / 2, (size * 0.66) / 96, hex_rgb(GOLD), hex_rgb("#FFFFFF"))
    img.resize((180, 180), Image.LANCZOS).convert("RGB").save(BRAND / "apple-touch-icon.png")
    print("  wrote assets/brand/apple-touch-icon.png")

    # favicon.ico 48/32/16 with rounded-square ink tile
    base = 48 * ss
    img = Image.new("RGBA", (base, base), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, base - 1, base - 1], radius=base * 0.21, fill=hex_rgb(INK))
    draw_mark(d, base / 2, base / 2, (base * 0.80) / 96, hex_rgb(GOLD), hex_rgb("#FFFFFF"))
    img48 = img.resize((48, 48), Image.LANCZOS)
    img48.save(BRAND / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)])
    print("  wrote assets/brand/favicon.ico")


def gen_og():
    W, H, ss = 1200, 630, 2
    w, h = W * ss, H * ss
    img = Image.new("RGBA", (w, h), hex_rgb(INK))

    # ghost mark, oversized off the right edge, on its own layer so the low
    # alpha actually composites instead of replacing pixels
    ghost = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(ghost), w * 0.88, h * 0.54, (h * 1.35) / 96,
              hex_rgb(GOLD, 30), hex_rgb("#FFFFFF", 14))
    img = Image.alpha_composite(img, ghost)
    d = ImageDraw.Draw(img)

    margin = 96 * ss
    archivo_b = ImageFont.truetype(str(font_path("archivo-700.ttf")), 104 * ss)
    archivo_m = ImageFont.truetype(str(font_path("archivo-500.ttf")), 40 * ss)
    mono = ImageFont.truetype(str(font_path("plexmono-500.ttf")), 26 * ss)

    draw_mark(d, margin + 44 * ss, 150 * ss, (88 * ss) / 96,
              hex_rgb(GOLD), hex_rgb("#FFFFFF"))

    d.text((margin, 262 * ss), "VC LIMITED", font=archivo_b, fill=hex_rgb("#FFFFFF"))
    d.text((margin, 398 * ss), "Global trade. Executed with precision.",
           font=archivo_m, fill=hex_rgb(MUTED_DARK))
    d.line([margin, 494 * ss, margin + 56 * ss, 494 * ss],
           fill=hex_rgb(GOLD), width=3 * ss)
    d.text((margin, 512 * ss), "VCLTD.CO  —  DUBAI, UNITED ARAB EMIRATES",
           font=mono, fill=hex_rgb(GOLD_SOFT))

    img.resize((W, H), Image.LANCZOS).convert("RGB").save(ASSETS / "og-image.png", quality=92)
    print("  wrote assets/og-image.png")


if __name__ == "__main__":
    print("Generating VC Limited brand assets…")
    gen_marks()
    gen_lockups()
    gen_icons()
    gen_og()
    print("Done.")

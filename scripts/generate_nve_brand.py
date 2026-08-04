#!/usr/bin/env python3
"""Generate the Napper Valley Estate monogram system.

Ten NVE monogram variations built for an estate in the Mount Tamborine
hinterland: burgundy and rich tones, quiet luxury, no Roman/inscriptional
cues. Every mark is drawn as outlines (letterforms converted to vector
paths) so the artwork carries no font dependency and can be handed to an
umbrella, embroidery, foil or signage supplier as-is.

Each variation ships three files:
    monograms/nve-NN-name.svg       full colour, burgundy tile
    monograms/nve-NN-name-1c.svg    one colour on transparent (embroidery, foil)
    lockups/nve-NN-name-lockup.svg  mark + wordmark

Usage:  python3 scripts/generate_nve_brand.py
Deps:   pip install fonttools brotli
Fonts:  Bodoni Moda, Cormorant Garamond, Jost (all SIL OFL), cached on first run.
"""

import base64
import io
import math
import urllib.request
from pathlib import Path

from fontTools import subset

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "napper-valley-estate"
CACHE = ROOT / ".fontcache"

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
FONT_URLS = {
    "BodoniModa.ttf": f"{GF}/bodonimoda/BodoniModa%5Bopsz%2Cwght%5D.ttf",
    "CormorantGaramond.ttf": f"{GF}/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
    "Jost.ttf": f"{GF}/jost/Jost%5Bwght%5D.ttf",
}

# ---------------------------------------------------------------- palette ----
OXBLOOD = "#2E0B13"    # deepest tone — signage, night applications
BURGUNDY = "#4E1220"   # primary ground
CLARET = "#66172A"     # lifted burgundy, tonal detail
CREAM = "#F4EDE1"      # primary mark colour
GOLD = "#C2A15B"       # antique brass hairlines, foil
ROSE = "#C79AA2"       # dusty rose, botanical accents

CANVAS = 512           # every monogram tile
CX = CANVAS / 2


# ------------------------------------------------------------------ type ----
def font_path(name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    p = CACHE / name
    if not p.exists():
        urllib.request.urlretrieve(FONT_URLS[name], p)
    return p


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


class Face:
    """A variable font pinned to one instance, drawn as outlines."""

    def __init__(self, file_name: str, **axes):
        font = TTFont(font_path(file_name))
        if "fvar" in font:
            font = instantiateVariableFont(font, axes, inplace=True, updateFontNames=False)
        self.font = font
        self.upem = font["head"].unitsPerEm
        self.cmap = font.getBestCmap()
        self.glyphs = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self.cap_ratio = font["OS/2"].sCapHeight / self.upem

    def size_for_cap(self, cap: float) -> float:
        return cap / self.cap_ratio

    def advance(self, ch: str, size: float) -> float:
        return self.hmtx[self.cmap[ord(ch)]][0] * size / self.upem

    def ink(self, ch: str, size: float) -> tuple[float, float, float, float]:
        """Ink bounds (x0, y0, x1, y1) in y-up units, baseline at 0."""
        pen = BoundsPen(self.glyphs)
        self.glyphs[self.cmap[ord(ch)]].draw(pen)
        if pen.bounds is None:
            return (0.0, 0.0, 0.0, 0.0)
        s = size / self.upem
        return tuple(v * s for v in pen.bounds)

    def glyph(self, ch: str, size: float, x: float = 0.0, y: float = 0.0,
              extra: Transform | None = None) -> str:
        """Outline for one glyph, baseline origin at (x, y) in SVG (y-down) space."""
        s = size / self.upem
        t = Transform(1, 0, 0, 1, x, y).scale(s, -s)
        if extra is not None:
            t = extra.translate(x, y).scale(s, -s)
        pen = SVGPathPen(self.glyphs, ntos=fmt)
        self.glyphs[self.cmap[ord(ch)]].draw(TransformPen(pen, t))
        return pen.getCommands()

    def run_width(self, text: str, size: float, tracking: float = 0.0) -> float:
        if not text:
            return 0.0
        return sum(self.advance(c, size) for c in text) + tracking * (len(text) - 1)

    def run(self, text: str, size: float, x: float, y: float,
            tracking: float = 0.0, anchor: str = "middle") -> str:
        """Outlines for a line of text. anchor: start | middle | end."""
        total = self.run_width(text, size, tracking)
        cursor = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
        parts = []
        for ch in text:
            if ch != " ":
                parts.append(self.glyph(ch, size, cursor, y))
            cursor += self.advance(ch, size) + tracking
        return " ".join(parts)

    def arc_run(self, text: str, size: float, cx: float, cy: float, radius: float,
                tracking: float = 0.0, top: bool = True) -> str:
        """Text set around a circle. Top arc reads over the crown, bottom arc
        reads along the base with letter tops turned inward."""
        total = self.run_width(text, size, tracking)
        span = math.degrees(total / radius)
        cursor = -span / 2
        parts = []
        for ch in text:
            step = math.degrees((self.advance(ch, size) + tracking) / radius)
            if ch != " ":
                mid = cursor + step / 2
                angle = mid if top else -mid
                w = self.advance(ch, size)
                t = Transform().translate(cx, cy).rotate(math.radians(angle))
                t = t.translate(0, -radius if top else radius)
                parts.append(self.glyph(ch, size, -w / 2, 0, extra=t))
            cursor += step
        return " ".join(parts)


# ------------------------------------------------------------- primitives ----
def leaf(x: float, y: float, length: float, width: float, angle: float,
         fill: str, midrib: str | None = None) -> str:
    """A single simple leaf, tip pointing along `angle` degrees (0 = up)."""
    t = Transform().translate(x, y).rotate(math.radians(angle))
    pts = []
    for px, py in ((0, 0), (width / 2, -length * 0.45), (0, -length),
                   (-width / 2, -length * 0.45)):
        pts.append(t.transformPoint((px, py)))
    (bx, by), (rx, ry), (tx, ty), (lx, ly) = pts
    d = (f"M{fmt(bx)} {fmt(by)}Q{fmt(rx)} {fmt(ry)} {fmt(tx)} {fmt(ty)}"
         f"Q{fmt(lx)} {fmt(ly)} {fmt(bx)} {fmt(by)}Z")
    out = f'<path d="{d}" fill="{fill}"/>'
    if midrib:
        out += (f'<path d="M{fmt(bx)} {fmt(by)}L{fmt(tx)} {fmt(ty)}" stroke="{midrib}"'
                f' stroke-width="1.2" fill="none" opacity="0.55"/>')
    return out


def rule(x1: float, y: float, x2: float, colour: str, w: float = 1.6) -> str:
    return (f'<path d="M{fmt(x1)} {fmt(y)}H{fmt(x2)}" stroke="{colour}"'
            f' stroke-width="{fmt(w)}" fill="none"/>')


def diamond(x: float, y: float, r: float, fill: str) -> str:
    return (f'<path d="M{fmt(x)} {fmt(y - r)}L{fmt(x + r)} {fmt(y)}'
            f'L{fmt(x)} {fmt(y + r)}L{fmt(x - r)} {fmt(y)}Z" fill="{fill}"/>')


def svg(body: str, w: float = CANVAS, h: float = CANVAS, bg: str | None = None,
        title: str = "") -> str:
    ground = f'<rect width="{fmt(w)}" height="{fmt(h)}" fill="{bg}"/>' if bg else ""
    label = f"<title>{title}</title>" if title else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}"'
            f' width="{fmt(w)}" height="{fmt(h)}" role="img">{label}{ground}{body}</svg>')


# ------------------------------------------------------------------ faces ----
def faces() -> dict[str, Face]:
    return {
        "display": Face("BodoniModa.ttf", wght=500, opsz=96),
        "display_light": Face("BodoniModa.ttf", wght=400, opsz=96),
        "old": Face("CormorantGaramond.ttf", wght=500),
        "sans": Face("Jost.ttf", wght=300),
    }


F: dict[str, Face] = {}


# ------------------------------------------------------------- variations ----
# Every builder returns SVG body drawn on the 512 tile, parameterised by the
# two ink colours so the same geometry serves the tile, the one-colour cut and
# the lockup.

def v01_heirloom(ink: str, accent: str) -> str:
    """Heirloom ligature — the original, tightened: N, V and E overlapped
    under one continuous hairline swash."""
    f = F["display"]
    cap = 162.0
    size = f.size_for_cap(cap)
    base = 316.0
    wn = f.ink("N", size)[2] - f.ink("N", size)[0]
    wv = f.ink("V", size)[2] - f.ink("V", size)[0]
    we = f.ink("E", size)[2] - f.ink("E", size)[0]
    ov1, ov2 = wn * 0.20, wv * 0.12
    total = wn + wv + we - ov1 - ov2
    x = CX - total / 2
    parts = []
    for ch, w, gap in (("N", wn, wn - ov1), ("V", wv, wv - ov2), ("E", we, 0)):
        x0 = f.ink(ch, size)[0]
        parts.append(f'<path d="{f.glyph(ch, size, x - x0, base)}" fill="{ink}"/>')
        x += gap
    left, right = CX - total / 2, CX + total / 2
    # crest: a hairline that rises left of the N and breaks over the ligature
    crest = (f"M{fmt(left - 44)} {fmt(base - cap * 0.60)}"
             f"C{fmt(left - 4)} {fmt(base - cap * 1.32)}"
             f" {fmt(left + total * 0.44)} {fmt(base - cap * 1.36)}"
             f" {fmt(left + total * 0.68)} {fmt(base - cap * 1.04)}")
    # sweep: the tail, carried out to the right the way the original did
    sweep = (f"M{fmt(left + total * 0.16)} {fmt(base + 32)}"
             f"C{fmt(left + total * 0.52)} {fmt(base + 52)}"
             f" {fmt(right - 4)} {fmt(base + 42)}"
             f" {fmt(right + 52)} {fmt(base - 4)}")
    for d in (crest, sweep):
        parts.append(f'<path d="{d}" stroke="{ink}" stroke-width="3" fill="none"'
                     ' stroke-linecap="round"/>')
    return "".join(parts)


def v02_nested(ink: str, accent: str) -> str:
    """Nested V — a tall centre V with the N and E set small on its shoulders."""
    f = F["display"]
    big = f.size_for_cap(198.0)
    small = f.size_for_cap(108.0)
    base = 318.0
    vx0, _, vx1, _ = f.ink("V", big)
    vw = vx1 - vx0
    nw = f.ink("N", small)[2] - f.ink("N", small)[0]
    ew = f.ink("E", small)[2] - f.ink("E", small)[0]
    gap = 12.0
    total = nw + vw + ew + gap * 2
    x = CX - total / 2
    parts = [
        f'<path d="{f.glyph("N", small, x - f.ink("N", small)[0], base)}" fill="{ink}"/>',
        f'<path d="{f.glyph("V", big, x + nw + gap - vx0, base + 26)}" fill="{ink}"/>',
        f'<path d="{f.glyph("E", small, x + nw + gap + vw + gap - f.ink("E", small)[0], base)}"'
        f' fill="{ink}"/>',
    ]
    parts.append(rule(CX - total / 2, base + 62, CX + total / 2, accent, 1.4))
    return "".join(parts)


def v03_seal(ink: str, accent: str) -> str:
    """Estate seal — the roundel for cap crowns, umbrella panels and wax."""
    f, s = F["display"], F["sans"]
    r_out, r_in = 232.0, 210.0
    parts = [
        f'<circle cx="{CX}" cy="{CX}" r="{fmt(r_out)}" stroke="{ink}"'
        ' stroke-width="3" fill="none"/>',
        f'<circle cx="{CX}" cy="{CX}" r="{fmt(r_in)}" stroke="{accent}"'
        ' stroke-width="1.2" fill="none"/>',
    ]
    cap = 108.0
    size = f.size_for_cap(cap)
    parts.append(f'<path d="{f.run("NVE", size, CX, CX + cap / 2 - 10, tracking=8)}"'
                 f' fill="{ink}"/>')
    parts.append(f'<path d="{s.arc_run("NAPPER VALLEY ESTATE", 30, CX, CX, 176, tracking=6)}"'
                 f' fill="{ink}"/>')
    parts.append(f'<path d="{s.arc_run("MOUNT TAMBORINE", 24, CX, CX, 178, tracking=5, top=False)}"'
                 f' fill="{accent}"/>')
    parts.append(rule(CX - 44, CX + 62, CX + 44, accent, 1.2))
    parts.append(diamond(CX - 196, CX, 5, accent))
    parts.append(diamond(CX + 196, CX, 5, accent))
    return "".join(parts)


def v04_valley(ink: str, accent: str) -> str:
    """Valley — the V opened out into the hinterland ridgeline between N and E."""
    f = F["display"]
    cap = 146.0
    size = f.size_for_cap(cap)
    base = 306.0
    nw = f.ink("N", size)[2] - f.ink("N", size)[0]
    ew = f.ink("E", size)[2] - f.ink("E", size)[0]
    span = 132.0                       # width of the splayed V
    gap = 26.0
    total = nw + span + ew + gap * 2
    x = CX - total / 2
    parts = [f'<path d="{f.glyph("N", size, x - f.ink("N", size)[0], base)}" fill="{ink}"/>']
    vx = x + nw + gap
    apex_x = vx + span / 2
    top = base - cap - 18
    v = f"M{fmt(vx)} {fmt(top)}L{fmt(apex_x)} {fmt(base)}L{fmt(vx + span)} {fmt(top)}"
    # sun over the valley, sitting clear inside the ridgeline
    parts.append(f'<circle cx="{fmt(apex_x)}" cy="{fmt(top + 54)}" r="30" stroke="{accent}"'
                 ' stroke-width="2.2" fill="none"/>')
    parts.append(f'<path d="{v}" stroke="{ink}" stroke-width="11" fill="none"'
                 ' stroke-linejoin="miter" stroke-linecap="butt"/>')
    parts.append(f'<path d="{f.glyph("E", size, x + nw + gap + span + gap - f.ink("E", size)[0], base)}"'
                 f' fill="{ink}"/>')
    parts.append(rule(CX - total / 2 - 10, base + 40, CX + total / 2 + 10, accent, 1.4))
    return "".join(parts)


def v05_arch(ink: str, accent: str) -> str:
    """Arch — the gatehouse silhouette, monogram framed under a soft vault."""
    f, s = F["display"], F["sans"]
    w, top, bottom = 278.0, 108.0, 412.0
    left, right = CX - w / 2, CX + w / 2
    r = w / 2
    arch = (f"M{fmt(left)} {fmt(bottom)}L{fmt(left)} {fmt(top + r)}"
            f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(right)} {fmt(top + r)}"
            f"L{fmt(right)} {fmt(bottom)}Z")
    parts = [f'<path d="{arch}" stroke="{ink}" stroke-width="3" fill="none"/>']
    inset = 14.0
    ri = r - inset
    arch2 = (f"M{fmt(left + inset)} {fmt(bottom - inset)}L{fmt(left + inset)} {fmt(top + r)}"
             f"A{fmt(ri)} {fmt(ri)} 0 0 1 {fmt(right - inset)} {fmt(top + r)}"
             f"L{fmt(right - inset)} {fmt(bottom - inset)}")
    parts.append(f'<path d="{arch2}" stroke="{accent}" stroke-width="1.2" fill="none"/>')
    cap = 88.0
    size = f.size_for_cap(cap)
    parts.append(f'<path d="{f.run("NVE", size, CX, 296, tracking=9)}" fill="{ink}"/>')
    parts.append(rule(CX - 48, 328, CX + 48, accent, 1.2))
    parts.append(f'<path d="{s.run("ESTATE", 19, CX, 366, tracking=8)}" fill="{ink}"/>')
    return "".join(parts)


def v06_monoline(ink: str, accent: str) -> str:
    """Monoline — one stroke weight throughout, the small-scale workhorse for
    embroidery, deboss and etched glass."""
    sw = 15.0
    cap = 176.0
    base = 330.0
    top = base - cap
    lw = 104.0          # letter width
    gap = 30.0
    total = lw * 3 + gap * 2
    x = CX - total / 2
    p = []
    # N
    p.append(f"M{fmt(x)} {fmt(base)}V{fmt(top)}L{fmt(x + lw)} {fmt(base)}V{fmt(top)}")
    # V
    xv = x + lw + gap
    p.append(f"M{fmt(xv)} {fmt(top)}L{fmt(xv + lw / 2)} {fmt(base)}L{fmt(xv + lw)} {fmt(top)}")
    # E
    xe = xv + lw + gap
    p.append(f"M{fmt(xe + lw)} {fmt(top)}H{fmt(xe)}V{fmt(base)}H{fmt(xe + lw)}")
    body = [f'<path d="{" ".join(p)}" stroke="{ink}" stroke-width="{fmt(sw)}" fill="none"'
            ' stroke-linecap="butt" stroke-linejoin="miter"/>']
    body.append(f'<path d="M{fmt(xe)} {fmt(base - cap / 2)}H{fmt(xe + lw * 0.62)}"'
                f' stroke="{ink}" stroke-width="{fmt(sw)}" fill="none"/>')
    body.append(rule(CX - total / 2, base + 46, CX + total / 2, accent, sw * 0.22))
    return "".join(body)


def v07_lozenge(ink: str, accent: str) -> str:
    """Lozenge — the tag mark: keylined diamond for buttons, tags and pins."""
    f = F["display"]
    r = 208.0
    dia = (f"M{fmt(CX)} {fmt(CX - r)}L{fmt(CX + r)} {fmt(CX)}"
           f"L{fmt(CX)} {fmt(CX + r)}L{fmt(CX - r)} {fmt(CX)}Z")
    ri = r - 18
    dia2 = (f"M{fmt(CX)} {fmt(CX - ri)}L{fmt(CX + ri)} {fmt(CX)}"
            f"L{fmt(CX)} {fmt(CX + ri)}L{fmt(CX - ri)} {fmt(CX)}Z")
    parts = [f'<path d="{dia}" stroke="{ink}" stroke-width="3" fill="none"'
             ' stroke-linejoin="miter"/>',
             f'<path d="{dia2}" stroke="{accent}" stroke-width="1.2" fill="none"'
             ' stroke-linejoin="miter"/>']
    cap = 88.0
    size = f.size_for_cap(cap)
    parts.append(f'<path d="{f.run("NVE", size, CX, CX + cap / 2, tracking=13)}" fill="{ink}"/>')
    parts.append(rule(CX - 62, CX - 84, CX + 62, accent, 1.2))
    parts.append(leaf(CX, CX - 104, 36, 18, 0, accent))
    return "".join(parts)


def v08_band(ink: str, accent: str) -> str:
    """Band — letters spaced between two rules: the merch stripe for webbing,
    umbrella sleeves, box edges and labels."""
    f, s = F["display"], F["sans"]
    cap = 128.0
    size = f.size_for_cap(cap)
    base = CX + cap / 2 - 4
    letters = "NVE"
    widths = [f.ink(c, size)[2] - f.ink(c, size)[0] for c in letters]
    gap = 54.0
    total = sum(widths) + gap * 2
    x = CX - total / 2
    parts = []
    for i, ch in enumerate(letters):
        parts.append(f'<path d="{f.glyph(ch, size, x - f.ink(ch, size)[0], base)}" fill="{ink}"/>')
        if i < 2:
            parts.append(diamond(x + widths[i] + gap / 2, base - cap / 2, 5.5, accent))
        x += widths[i] + gap
    half = total / 2 + 34
    parts.append(rule(CX - half, base - cap - 46, CX + half, ink, 2.2))
    parts.append(rule(CX - half, base + 46, CX + half, ink, 2.2))
    parts.append(f'<path d="{s.run("MOUNT TAMBORINE HINTERLAND", 18, CX, base + 88, tracking=6)}"'
                 f' fill="{accent}"/>')
    return "".join(parts)


def v09_sprig(ink: str, accent: str) -> str:
    """Sprig — old-style letterforms under a single leaf: the softest, most
    botanical of the set."""
    f = F["old"]
    cap = 148.0
    size = f.size_for_cap(cap)
    base = 342.0
    parts = [f'<path d="{f.run("NVE", size, CX, base, tracking=2)}" fill="{ink}"/>']
    stem_top, stem_bottom = 138.0, 176.0
    parts.append(f'<path d="M{fmt(CX)} {fmt(stem_bottom)}V{fmt(stem_top - 30)}"'
                 f' stroke="{accent}" stroke-width="1.6" fill="none"/>')
    parts.append(leaf(CX, stem_top, 62, 30, 0, ink))
    parts.append(leaf(CX - 3, stem_bottom - 4, 40, 20, -52, accent))
    parts.append(leaf(CX + 3, stem_bottom - 4, 40, 20, 52, accent))
    parts.append(rule(CX - 86, base + 44, CX + 86, accent, 1.2))
    return "".join(parts)


def v10_patch(ink: str, accent: str, ground: str = BURGUNDY, field: bool = True) -> str:
    """Patch — the mark as an object: a rounded field for woven patches, caps,
    luggage tags and pins. `field=False` gives the keyline cut for one colour."""
    f, s = F["display"], F["sans"]
    m, rr = 46.0, 86.0
    side = CANVAS - m * 2
    letter = ground if field else ink
    parts = [f'<rect x="{fmt(m)}" y="{fmt(m)}" width="{fmt(side)}" height="{fmt(side)}"'
             f' rx="{fmt(rr)}" fill="{ink}"/>' if field else
             f'<rect x="{fmt(m)}" y="{fmt(m)}" width="{fmt(side)}" height="{fmt(side)}"'
             f' rx="{fmt(rr)}" fill="none" stroke="{ink}" stroke-width="3"/>']
    parts.append(f'<rect x="{fmt(m + 16)}" y="{fmt(m + 16)}" width="{fmt(side - 32)}"'
                 f' height="{fmt(side - 32)}" rx="{fmt(rr - 14)}" stroke="{accent}"'
                 ' stroke-width="1.6" fill="none"/>')
    cap = 118.0
    size = f.size_for_cap(cap)
    parts.append(f'<path d="{f.run("NVE", size, CX, CX + cap / 2 - 6, tracking=8)}"'
                 f' fill="{letter}"/>')
    parts.append(rule(CX - 58, CX + 54, CX + 58, letter, 1.6))
    parts.append(f'<path d="{s.run("ESTATE", 22, CX, CX + 96, tracking=9)}" fill="{letter}"/>')
    parts.append(f'<path d="{s.run("EST. MT TAMBORINE", 17, CX, m + 68, tracking=5)}"'
                 f' fill="{letter}"/>')
    return "".join(parts)


def v10_patch_cut(ink: str, accent: str) -> str:
    """One-colour cut of the patch — keyline field, letters set solid."""
    return v10_patch(ink, accent, field=False)


VARIATIONS = [
    dict(num="01", slug="heirloom", name="Heirloom Ligature", fn=v01_heirloom, scale=0.78,
         note="The original, tightened — N, V and E overlapped beneath one hairline swash.",
         use="Primary signature: front-of-house signage, stationery, wine labels, foil."),
    dict(num="02", slug="nested", name="Nested V", fn=v02_nested, scale=0.82,
         note="A tall centre V carrying a small N and E on its shoulders.",
         use="Editorial marque for menus, guest compendiums and press."),
    dict(num="03", slug="seal", name="Estate Seal", fn=v03_seal, scale=1.0,
         note="Roundel for cap crowns, umbrella panels, wax seals and coasters.",
         use="Umbrella centre panel, cap crown embroidery, wax seals, coasters."),
    dict(num="04", slug="valley", name="Valley", fn=v04_valley, scale=0.84,
         note="The V opened into a hinterland ridgeline, sun held in the notch.",
         use="Trail signage, hampers, tote prints — the landscape story."),
    dict(num="05", slug="arch", name="Arch", fn=v05_arch, scale=0.96,
         note="Gatehouse vault framing the monogram.",
         use="Gate and room signage, menu headers, key fobs."),
    dict(num="06", slug="monoline", name="Monoline", fn=v06_monoline, scale=0.78,
         note="One stroke weight throughout, no hairlines to lose.",
         use="Embroidery down to 20 mm, deboss, etched glass, laser engraving."),
    dict(num="07", slug="lozenge", name="Lozenge", fn=v07_lozenge, scale=1.0,
         note="Keylined diamond tag topped with a single leaf.",
         use="Swing tags, buttons, pins, hardware, soap and candle labels."),
    dict(num="08", slug="band", name="Band", fn=v08_band, scale=0.94,
         note="Letters ruled top and bottom, diamond points between.",
         use="Umbrella sleeves, webbing, box edges, robe cuffs, ribbon."),
    dict(num="09", slug="sprig", name="Sprig", fn=v09_sprig, scale=0.80,
         note="Old-style letterforms under a single leaf; the softest of the set.",
         use="Spa and garden collateral, candles, preserves, thank-you cards."),
    dict(num="10", slug="patch", name="Patch", fn=v10_patch, one_fn=v10_patch_cut, scale=0.96,
         note="Reversed rounded field — the mark as an object.",
         use="Woven patches, caps, luggage tags, enamel pins, app icon."),
]


# --------------------------------------------------------------- wordmark ----
def wordmark(x: float, y: float, ink: str, accent: str) -> str:
    """NAPPER VALLEY / ESTATE / MOUNT TAMBORINE HINTERLAND, centred on x with
    the first baseline at y. The block runs ~110 deep."""
    f, s = F["display_light"], F["sans"]
    size = f.size_for_cap(46.0)
    track = 12.0
    parts = [f'<path d="{f.run("NAPPER VALLEY", size, x, y, tracking=track)}" fill="{ink}"/>']
    w1 = f.run_width("NAPPER VALLEY", size, track)
    small = f.size_for_cap(26.0)
    est_w = f.run_width("ESTATE", small, 18.0)
    parts.append(f'<path d="{f.run("ESTATE", small, x, y + 54, tracking=18)}" fill="{ink}"/>')
    parts.append(rule(x - w1 / 2, y + 45, x - est_w / 2 - 20, accent, 1.3))
    parts.append(rule(x + est_w / 2 + 20, y + 45, x + w1 / 2, accent, 1.3))
    parts.append(f'<path d="{s.run("MOUNT TAMBORINE HINTERLAND", 19, x, y + 102, tracking=8)}"'
                 f' fill="{accent}"/>')
    return "".join(parts)


PALETTE = [
    ("Oxblood", OXBLOOD, "Deepest ground — night signage, foiled boxes"),
    ("Burgundy", BURGUNDY, "The estate colour — primary ground"),
    ("Claret", CLARET, "Lifted burgundy — panels, tonal stripes"),
    ("Cream", CREAM, "The mark, reversed out"),
    ("Antique brass", GOLD, "Hairlines and foil — never fills"),
    ("Dusty rose", ROSE, "Botanical accents, secondary text"),
]

PAGE_CSS = """
:root {
  --oxblood: #2E0B13; --burgundy: #4E1220; --claret: #66172A;
  --cream: #F4EDE1; --gold: #C2A15B; --rose: #C79AA2; --panel: #3A0E18;
  --ink: var(--cream); --muted: #C3A7AC; --line: rgba(194,161,91,.32);
  --display: "NVE Display", Georgia, "Times New Roman", serif;
  --text: "NVE Sans", "Helvetica Neue", Arial, sans-serif;
}
/* This board commits to one world — the estate's burgundy — in either theme. */
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--oxblood); color: var(--ink);
  font-family: var(--text); font-weight: 300; font-size: 16px; line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 1140px; margin: 0 auto; padding: 0 28px 96px; }
.eyebrow {
  font-size: 11px; letter-spacing: .42em; text-transform: uppercase;
  color: var(--gold); margin: 0;
}
h1, h2, h3 { font-family: var(--display); font-weight: 400; text-wrap: balance; margin: 0; }
h2 { font-size: clamp(26px, 3.4vw, 38px); letter-spacing: .02em; }
h3 { font-size: 19px; letter-spacing: .06em; }
p { max-width: 62ch; }
.lede { color: var(--muted); font-size: 17px; }
section { padding-top: 76px; }
.head { display: flex; flex-direction: column; gap: 10px; margin-bottom: 34px; }
.head .rule { height: 1px; background: var(--line); margin-top: 6px; }

.masthead { padding: 72px 0 8px; display: grid; gap: 40px; justify-items: center; }
.masthead svg { width: min(520px, 100%); height: auto; display: block; }
.masthead .intro { text-align: center; display: grid; gap: 14px; justify-items: center; }

.swatches { display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); gap: 14px; }
.swatch { border: 1px solid var(--line); }
.swatch .chip { height: 92px; }
.swatch .meta { padding: 12px 14px 16px; display: grid; gap: 4px; }
.swatch b { font-family: var(--display); font-weight: 400; font-size: 17px; }
.swatch code, .files code { font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 12px; letter-spacing: .06em; color: var(--gold); }
.swatch small { color: var(--muted); font-size: 12.5px; line-height: 1.5; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(258px, 1fr)); gap: 26px; }
.card { display: grid; gap: 14px; }
.card .mark { width: 100%; height: auto; display: block; border: 1px solid var(--line); }
.card .num { font-size: 11px; letter-spacing: .34em; color: var(--gold); }
.card .note { color: var(--muted); font-size: 13.5px; margin: 0; }
.card .use { font-size: 12.5px; color: var(--rose); margin: 0; }
.card .files { font-size: 11.5px; color: rgba(244,237,225,.45); word-break: break-all; }

.cuts { background: var(--cream); padding: 34px 30px; display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); gap: 24px; align-items: center; }
.cuts svg { width: 100%; height: auto; display: block; }

.apps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 26px; }
.app { display: grid; gap: 12px; }
.app-art { width: 100%; height: auto; display: block; background: var(--panel);
  border: 1px solid var(--line); }
.app b { font-family: var(--display); font-weight: 400; font-size: 17px; }
.app small { color: var(--muted); font-size: 13px; }

table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--line);
  vertical-align: top; }
th { font-size: 11px; letter-spacing: .28em; text-transform: uppercase; color: var(--gold);
  font-weight: 400; }
td:first-child { white-space: nowrap; }
.scroll { overflow-x: auto; }
.rules { display: grid; grid-template-columns: repeat(auto-fit, minmax(238px, 1fr)); gap: 24px; }
.rules div { border-top: 1px solid var(--line); padding-top: 14px; }
.rules b { display: block; font-family: var(--display); font-weight: 400; font-size: 17px;
  margin-bottom: 6px; }
.rules p { color: var(--muted); font-size: 13.5px; margin: 0; }
footer { margin-top: 84px; border-top: 1px solid var(--line); padding-top: 20px;
  color: rgba(244,237,225,.45); font-size: 12.5px; letter-spacing: .04em; }
@media (max-width: 640px) { .masthead { padding-top: 44px; } section { padding-top: 56px; } }
"""


def preview_body(built: list[dict]) -> str:
    primary = next(b for b in built if b["slug"] == "heirloom")
    lock = (f'<svg viewBox="0 0 {fmt(LOCK_W)} {fmt(LOCK_H)}" xmlns="http://www.w3.org/2000/svg"'
            f' role="img" aria-label="Napper Valley Estate">'
            f'<rect width="{fmt(LOCK_W)}" height="{fmt(LOCK_H)}" fill="{BURGUNDY}"/>'
            f'<g transform="translate({fmt((LOCK_W - CANVAS * primary["scale"]) / 2)} 40)'
            f' scale({fmt(primary["scale"])})">{primary["tile"]}</g>'
            f'{wordmark(LOCK_W / 2, 600, CREAM, ROSE)}</svg>')

    swatches = "".join(
        f'<div class="swatch"><div class="chip" style="background:{hex_}"></div>'
        f'<div class="meta"><b>{name}</b><code>{hex_}</code><small>{role}</small></div></div>'
        for name, hex_, role in PALETTE)

    cards = "".join(
        f'<article class="card">{tile_svg(b["tile"])}'
        f'<div class="num">{b["num"]}</div><h3>{b["name"]}</h3>'
        f'<p class="note">{b["note"]}</p><p class="use">{b["use"]}</p>'
        f'<div class="files">{b["stem"]}.svg · -1c.svg · -lockup.svg</div></article>'
        for b in built)

    cuts = "".join(
        f'<svg viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" role="img"'
        f' aria-label="{b["name"]}, one colour">{b["one"]}</svg>' for b in built)

    by = {b["slug"]: b["tile"] for b in built}
    apps = [
        (umbrella(by["seal"]), "Garden umbrella",
         "Estate Seal on alternate panels, brass rib line, oxblood finial."),
        (cap(by["monoline"]), "Cap",
         "Monoline embroidered on the crown — no hairline finer than the needle."),
        (tote(v08_band(BURGUNDY, CLARET)), "Canvas tote",
         "Band mark screen-printed burgundy on natural canvas."),
        (seal_wax(by["patch"]), "Coaster / wax seal",
         "Patch reversed into claret for pressed and debossed surfaces."),
    ]
    apps_html = "".join(
        f'<figure class="app"><div>{art}</div><figcaption><b>{title}</b><br>'
        f'<small>{note}</small></figcaption></figure>' for art, title, note in apps)

    rows = "".join(
        f'<tr><td><code>nve-{b["num"]}-{b["slug"]}</code></td><td>{b["name"]}</td>'
        f'<td>{b["use"]}</td></tr>' for b in built)

    return f"""
<div class="wrap">
  <header class="masthead">
    {lock}
    <div class="intro">
      <p class="eyebrow">Monogram system · ten variations</p>
      <p class="lede">The NVE monogram rebuilt as a family: one set of letterforms,
      one burgundy world, ten ways to wear it. Every mark is outlined vector art with
      no live type, so it can go straight to an umbrella maker, an embroiderer or a
      foil block without a font licence in sight.</p>
    </div>
  </header>

  <section>
    <div class="head"><p class="eyebrow">Palette</p><h2>Burgundy, brass and one soft rose</h2>
      <div class="rule"></div></div>
    <div class="swatches">{swatches}</div>
  </section>

  <section>
    <div class="head"><p class="eyebrow">The ten</p><h2>Variations</h2>
      <div class="rule"></div></div>
    <div class="grid">{cards}</div>
  </section>

  <section>
    <div class="head"><p class="eyebrow">Production</p><h2>One-colour cuts</h2>
      <div class="rule"></div>
      <p class="lede">Every mark also ships flat, on transparent ground, for embroidery
      files, deboss dies, etched glass and single-screen printing.</p></div>
    <div class="cuts">{cuts}</div>
  </section>

  <section>
    <div class="head"><p class="eyebrow">In use</p><h2>On the estate</h2>
      <div class="rule"></div></div>
    <div class="apps">{apps_html}</div>
  </section>

  <section>
    <div class="head"><p class="eyebrow">Using them</p><h2>Rules of the house</h2>
      <div class="rule"></div></div>
    <div class="rules">
      <div><b>Clear space</b><p>Keep the height of the N clear on every side. On umbrella
      panels, double it — the canopy curves away from the eye.</p></div>
      <div><b>Minimum size</b><p>Hairline marks (Heirloom, Seal, Lozenge, Arch) hold to
      35&nbsp;mm wide. Below that use Monoline, Band or Patch.</p></div>
      <div><b>Colour</b><p>Cream on burgundy is the default. Burgundy on cream is the
      reverse. Brass is a hairline and a foil, never a fill.</p></div>
      <div><b>Don't</b><p>No outlines on the letterforms, no drop shadows, no stretching,
      no third colour, no rotating the mark off its baseline.</p></div>
    </div>
  </section>

  <section>
    <div class="head"><p class="eyebrow">Files</p><h2>What's in the folder</h2>
      <div class="rule"></div>
      <p class="lede">Each variation ships three SVGs — the burgundy tile, the one-colour
      cut and the full lockup — plus a 1024&nbsp;px PNG of the tile.</p></div>
    <div class="scroll"><table>
      <thead><tr><th>File stem</th><th>Variation</th><th>Made for</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>

  <footer>Napper Valley Estate · Mount Tamborine hinterland · monogram system, ten variations</footer>
</div>
"""


# ------------------------------------------------------------------- deck ----
# A4 landscape, one idea per page, printed straight to PDF by
# scripts/export_nve_pdf.mjs. Same tokens as the board — this is the version
# that gets emailed to a supplier or handed across a table.
DECK_CSS = """
@page { size: 297mm 210mm; margin: 0; }
:root {
  --oxblood: #2E0B13; --burgundy: #4E1220; --claret: #66172A;
  --cream: #F4EDE1; --gold: #C2A15B; --rose: #C79AA2; --panel: #3A0E18;
  --muted: #C3A7AC; --line: rgba(194,161,91,.34);
  --display: "NVE Display", Georgia, serif;
  --text: "NVE Sans", Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #1a060c; }
body { font-family: var(--text); font-weight: 300; color: var(--cream);
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page {
  position: relative; width: 297mm; height: 210mm; overflow: hidden;
  background: var(--oxblood); padding: 16mm 18mm 14mm;
  display: flex; flex-direction: column; page-break-after: always; break-after: page;
}
.page:last-child { page-break-after: auto; break-after: auto; }
@media screen { .page { margin: 0 auto 8mm; box-shadow: 0 2mm 12mm rgba(0,0,0,.5); } }
.eyebrow { font-size: 7.5pt; letter-spacing: .40em; text-transform: uppercase;
  color: var(--gold); margin: 0; }
h1, h2, h3 { font-family: var(--display); font-weight: 400; margin: 0; }
h1 { font-size: 30pt; letter-spacing: .02em; }
h2 { font-size: 21pt; letter-spacing: .02em; }
h3 { font-size: 13pt; letter-spacing: .05em; }
p { margin: 0; }
.page > .top { display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: .3mm solid var(--line); padding-bottom: 3mm; margin-bottom: 8mm; }
.page > .top .folio { font-size: 7.5pt; letter-spacing: .3em; color: var(--rose); }
.body { flex: 1; min-height: 0; }
.muted { color: var(--muted); font-size: 10pt; line-height: 1.6; }
.rose { color: var(--rose); font-size: 9.5pt; line-height: 1.6; }
code { font-family: ui-monospace, Menlo, monospace; font-size: 8pt; letter-spacing: .05em;
  color: var(--gold); }

/* cover */
.cover { padding: 0; background: var(--burgundy); align-items: center; justify-content: center; }
.cover svg { width: 150mm; height: auto; display: block; }
.cover .caption { position: absolute; left: 18mm; right: 18mm; bottom: 14mm;
  display: flex; justify-content: space-between; align-items: baseline;
  border-top: .3mm solid var(--line); padding-top: 4mm; }

/* overview */
.contact { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6mm; }
.contact figure { margin: 0; display: grid; gap: 2mm; }
.contact svg { width: 100%; height: auto; display: block; border: .25mm solid var(--line); }
.contact figcaption { font-size: 8pt; letter-spacing: .04em; }
.contact .n { color: var(--gold); font-size: 7pt; letter-spacing: .28em; }

/* variation page */
.spread { display: grid; grid-template-columns: 118mm 1fr; gap: 12mm; height: 100%; }
.spread .hero svg { width: 118mm; height: auto; display: block; border: .25mm solid var(--line); }
.spread .side { display: flex; flex-direction: column; gap: 6mm; }
.spread .side .lede { font-size: 11pt; line-height: 1.65; color: var(--cream); max-width: 92mm; }
.alt { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-top: auto; }
.alt .chip { display: grid; gap: 2mm; }
.alt .chip .frame { border: .25mm solid var(--line); background: var(--cream); padding: 3mm; }
.alt .chip .frame.dark { background: var(--burgundy); padding: 0; }
.alt .chip svg { width: 100%; height: auto; display: block; }
.alt .chip span { font-size: 7.5pt; letter-spacing: .22em; text-transform: uppercase;
  color: var(--gold); }

/* palette + type */
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14mm; height: 100%; }
.chips { display: grid; gap: 4mm; }
.chips .row { display: grid; grid-template-columns: 26mm 1fr; gap: 5mm; align-items: center; }
.chips .sw { height: 16mm; border: .25mm solid var(--line); }
.chips b { font-family: var(--display); font-weight: 400; font-size: 12pt; }
.spec { display: grid; gap: 5mm; align-content: start; }
.spec .item { border-top: .3mm solid var(--line); padding-top: 3mm; }
.spec .big { font-family: var(--display); font-size: 22pt; letter-spacing: .12em; }
.spec .big.sans { font-family: var(--text); font-size: 15pt; letter-spacing: .32em; }

/* applications + rules */
.four { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8mm; }
.four figure { margin: 0; display: grid; gap: 3mm; }
.four svg { width: 100%; height: auto; display: block; background: var(--panel);
  border: .25mm solid var(--line); }
.rulegrid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8mm 12mm;
  align-content: start; }
.rulegrid div { border-top: .3mm solid var(--line); padding-top: 3mm; }
.filetable { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
.filetable th, .filetable td { text-align: left; padding: 2mm 3mm;
  border-bottom: .25mm solid var(--line); }
.filetable th { font-size: 7pt; letter-spacing: .24em; text-transform: uppercase;
  color: var(--gold); font-weight: 400; }
"""


def deck(built: list[dict]) -> str:
    """The presentation deck — A4 landscape, printed to PDF."""
    primary = next(b for b in built if b["slug"] == "heirloom")
    total = len(built) + 5

    def page(inner: str, eyebrow: str, title: str, folio: int, cls: str = "") -> str:
        return (f'<section class="page {cls}"><div class="top"><div>'
                f'<p class="eyebrow">{eyebrow}</p><h2>{title}</h2></div>'
                f'<div class="folio">{folio:02d} / {total:02d}</div></div>'
                f'<div class="body">{inner}</div></section>')

    def mark_svg(body: str, ground: str | None = BURGUNDY, w: float = CANVAS,
                 h: float = CANVAS, label: str = "") -> str:
        rect = f'<rect width="{fmt(w)}" height="{fmt(h)}" fill="{ground}"/>' if ground else ""
        return (f'<svg viewBox="0 0 {fmt(w)} {fmt(h)}" xmlns="http://www.w3.org/2000/svg"'
                f' role="img" aria-label="{label}">{rect}{body}</svg>')

    lock = (f'<svg viewBox="0 0 {fmt(LOCK_W)} {fmt(LOCK_H)}" xmlns="http://www.w3.org/2000/svg"'
            f' role="img" aria-label="Napper Valley Estate">'
            f'<g transform="translate({fmt((LOCK_W - CANVAS * primary["scale"]) / 2)} 40)'
            f' scale({fmt(primary["scale"])})">{primary["tile"]}</g>'
            f'{wordmark(LOCK_W / 2, 600, CREAM, ROSE)}</svg>')
    cover = (f'<section class="page cover">{lock}<div class="caption">'
             f'<p class="eyebrow">Monogram system · ten variations</p>'
             f'<p class="eyebrow">Mount Tamborine hinterland</p></div></section>')

    contact = "".join(
        f'<figure>{mark_svg(b["tile"], label=b["name"])}'
        f'<figcaption><div class="n">{b["num"]}</div>{b["name"]}</figcaption></figure>'
        for b in built)
    overview = page(
        f'<div class="contact">{contact}</div>'
        f'<p class="muted" style="margin-top:9mm;max-width:170mm">One family of letterforms in '
        f'burgundy, brass and cream. Marks 01–05 carry the estate at full size; 06–10 are the '
        f'small-scale and merch cuts, drawn to hold together at a stitch or a stamp.</p>',
        "Contents", "The ten at a glance", 2)

    chips = "".join(
        f'<div class="row"><div class="sw" style="background:{hex_}"></div>'
        f'<div><b>{name}</b> <code>{hex_}</code><br>'
        f'<span class="muted" style="font-size:9pt">{role}</span></div></div>'
        for name, hex_, role in PALETTE)
    palette_page = page(
        f'<div class="cols2"><div class="chips">{chips}</div>'
        f'<div class="spec">'
        f'<div class="item"><p class="eyebrow">Display</p>'
        f'<div class="big">NAPPER VALLEY</div>'
        f'<p class="muted">Bodoni Moda — high contrast, no inscriptional serifs. '
        f'Set in capitals, tracked wide, never below 12&nbsp;pt.</p></div>'
        f'<div class="item"><p class="eyebrow">Supporting</p>'
        f'<div class="big sans">MOUNT TAMBORINE</div>'
        f'<p class="muted">Jost Light in spaced capitals for locality lines, labels and '
        f'small print.</p></div>'
        f'<div class="item"><p class="eyebrow">Artwork</p>'
        f'<p class="muted">Every mark is outlined vector — no live type, no font licence '
        f'travelling with the files, nothing for a supplier to substitute.</p></div>'
        f"</div></div>",
        "Foundations", "Palette and type", 3)

    variation_pages = []
    for i, b in enumerate(built):
        lockup = (f'<svg viewBox="0 0 {fmt(LOCK_W)} {fmt(LOCK_H)}"'
                  f' xmlns="http://www.w3.org/2000/svg" role="img" aria-label="lockup">'
                  f'<rect width="{fmt(LOCK_W)}" height="{fmt(LOCK_H)}" fill="{BURGUNDY}"/>'
                  f'<g transform="translate({fmt((LOCK_W - CANVAS * b["scale"]) / 2)} 40)'
                  f' scale({fmt(b["scale"])})">{b["tile"]}</g>'
                  f'{wordmark(LOCK_W / 2, 600, CREAM, ROSE)}</svg>')
        variation_pages.append(page(
            f'<div class="spread">'
            f'<div class="hero">{mark_svg(b["tile"], label=b["name"])}</div>'
            f'<div class="side">'
            f'<p class="lede">{b["note"]}</p>'
            f'<p class="rose">{b["use"]}</p>'
            f'<p class="muted"><code>{b["stem"]}.svg</code><br>'
            f'<code>{b["stem"]}-1c.svg</code><br><code>{b["stem"]}-lockup.svg</code></p>'
            f'<div class="alt">'
            f'<div class="chip"><span>One colour</span>'
            f'<div class="frame">{mark_svg(b["one"], ground=None, label="one colour")}</div></div>'
            f'<div class="chip"><span>Lockup</span>'
            f'<div class="frame dark">{lockup}</div></div>'
            f"</div></div></div>",
            f"Variation {b['num']}", b["name"], 4 + i))

    by = {b["slug"]: b["tile"] for b in built}
    apps = [
        (umbrella(by["seal"]), "Garden umbrella", "Estate Seal on alternate panels."),
        (cap(by["monoline"]), "Cap", "Monoline embroidered on the crown."),
        (tote(v08_band(BURGUNDY, CLARET)), "Canvas tote", "Band printed burgundy on natural."),
        (seal_wax(by["patch"]), "Coaster / wax seal", "Patch reversed into claret."),
    ]
    apps_page = page(
        '<div class="four">' + "".join(
            f'<figure>{art}<figcaption><h3>{title}</h3>'
            f'<p class="muted" style="font-size:9pt">{note}</p></figcaption></figure>'
            for art, title, note in apps) + "</div>"
        f'<p class="muted" style="margin-top:10mm;max-width:190mm">Mockups are indicative — '
        f'the artwork supplied to each maker is vector, at full scale, in the single colour '
        f'their process needs.</p>',
        "In use", "On the estate", total - 1)

    rows = "".join(
        f'<tr><td><code>{b["stem"]}</code></td><td>{b["name"]}</td><td>{b["use"]}</td></tr>'
        for b in built)
    rules_page = page(
        f'<div class="cols2"><div class="rulegrid">'
        f'<div><h3>Clear space</h3><p class="muted">The height of the N on every side. '
        f'On umbrella panels double it — the canopy curves away from the eye.</p></div>'
        f'<div><h3>Minimum size</h3><p class="muted">Hairline marks (Heirloom, Seal, Lozenge, '
        f'Arch) hold to 35&nbsp;mm wide. Below that use Monoline, Band or Patch.</p></div>'
        f'<div><h3>Colour</h3><p class="muted">Cream on burgundy is the default, burgundy on '
        f'cream the reverse. Brass is a hairline and a foil, never a fill.</p></div>'
        f'<div><h3>Don\'t</h3><p class="muted">No outlines on the letterforms, no shadows, no '
        f'stretching, no third colour, no rotating the mark off its baseline.</p></div>'
        f'</div><div><table class="filetable"><thead><tr><th>File stem</th><th>Variation</th>'
        f'<th>Made for</th></tr></thead><tbody>{rows}</tbody></table>'
        f'<p class="muted" style="margin-top:5mm;font-size:8.5pt">Each stem ships '
        f'<code>.svg</code>, <code>-1c.svg</code>, <code>-lockup.svg</code> and a 1024&nbsp;px '
        f'PNG.</p></div></div>',
        "Using them", "Rules of the house", total)

    pages = [cover, overview, palette_page, *variation_pages, apps_page, rules_page]
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<title>Napper Valley Estate — monogram system</title>'
            f"<style>{font_face_css()}{DECK_CSS}</style></head><body>"
            + "".join(pages) + "</body></html>")


def preview(built: list[dict]) -> str:
    body = preview_body(built)
    return (f"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>Napper Valley Estate — monogram system</title>"
            f"<style>{font_face_css()}{PAGE_CSS}</style></head><body>{body}</body></html>")


_FONT_CSS: str | None = None


def font_face_css() -> str:
    global _FONT_CSS
    if _FONT_CSS is not None:
        return _FONT_CSS
    display = web_font("BodoniModa.ttf", wght=400, opsz=48)
    sans = web_font("Jost.ttf", wght=300)
    _FONT_CSS = (f"@font-face{{font-family:'NVE Display';font-style:normal;font-weight:400;"
                 f"src:url(data:font/woff2;base64,{display}) format('woff2');font-display:swap;}}"
                 f"@font-face{{font-family:'NVE Sans';font-style:normal;font-weight:300;"
                 f"src:url(data:font/woff2;base64,{sans}) format('woff2');font-display:swap;}}")
    return _FONT_CSS


# ----------------------------------------------------------------- output ----
def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")
    print(f"  wrote {path.relative_to(ROOT)}")


LOCK_W, LOCK_H = 900.0, 800.0


# ---------------------------------------------------------------- preview ----
def web_font(file_name: str, **axes) -> str:
    """Instance + subset a variable font to a base64 woff2 for inline embedding."""
    font = TTFont(font_path(file_name))
    if "fvar" in font:
        font = instantiateVariableFont(font, axes, inplace=True, updateFontNames=False)
    opts = subset.Options(flavor="woff2", desubroutinize=True, notdef_outline=True)
    opts.layout_features = ["kern", "liga", "calt"]
    sub = subset.Subsetter(options=opts)
    sub.populate(text="".join(chr(c) for c in range(32, 127)) + "—·’“”")
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tile_svg(body: str, ground: str | None = BURGUNDY) -> str:
    """Inline (responsive) copy of a mark for the preview page."""
    ground_rect = f'<rect width="512" height="512" fill="{ground}"/>' if ground else ""
    return (f'<svg viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" '
            f'class="mark" aria-hidden="true">{ground_rect}{body}</svg>')


def umbrella(mark: str) -> str:
    """Top-down canopy: eight panels, alternating tones, seal on four of them."""
    cx = cy = 200.0
    r = 190.0
    wedges = []
    for i in range(8):
        a0 = math.radians(i * 45 - 90)
        a1 = math.radians((i + 1) * 45 - 90)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        fill = BURGUNDY if i % 2 == 0 else CLARET
        wedges.append(f'<path d="M{fmt(cx)} {fmt(cy)}L{fmt(x0)} {fmt(y0)}'
                      f'A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x1)} {fmt(y1)}Z" fill="{fill}"/>')
        if i % 2 == 0:
            am = (a0 + a1) / 2
            mx, my = cx + r * 0.62 * math.cos(am), cy + r * 0.62 * math.sin(am)
            deg = math.degrees(am) + 90
            wedges.append(
                f'<g transform="translate({fmt(mx)} {fmt(my)}) rotate({fmt(deg)})'
                f' scale(0.17) translate(-256 -256)">{mark}</g>')
    ribs = "".join(
        f'<path d="M{fmt(cx)} {fmt(cy)}L{fmt(cx + r * math.cos(math.radians(i * 45 - 90)))}'
        f' {fmt(cy + r * math.sin(math.radians(i * 45 - 90)))}" stroke="{OXBLOOD}"'
        ' stroke-width="1.2" opacity="0.5"/>' for i in range(8))
    return (f'<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" class="app-art"'
            f' aria-hidden="true">{"".join(wedges)}{ribs}'
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" fill="none"'
            f' stroke="{GOLD}" stroke-width="1.4" opacity="0.7"/>'
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="9" fill="{GOLD}"/></svg>')


def cap(mark: str) -> str:
    """Front panel of a cap, mark centred on the crown."""
    return (f'<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" class="app-art"'
            ' aria-hidden="true">'
            f'<path d="M62 250C62 150 110 96 200 96S338 150 338 250Z" fill="{BURGUNDY}"/>'
            f'<path d="M200 96V250" stroke="{OXBLOOD}" stroke-width="2" opacity="0.55"/>'
            f'<path d="M56 250h288c26 0 46 20 46 42s-24 34-52 34H62c-28 0-46-14-46-34'
            f's20-42 40-42Z" fill="{OXBLOOD}"/>'
            f'<g transform="translate(200 196) scale(0.26) translate(-256 -256)">{mark}</g>'
            "</svg>")


def tote(mark: str) -> str:
    """Canvas tote in cream with the mark printed in burgundy."""
    return (f'<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" class="app-art"'
            ' aria-hidden="true">'
            f'<rect x="86" y="120" width="228" height="252" rx="6" fill="{CREAM}"/>'
            f'<path d="M132 120v-24a68 68 0 0 1 136 0v24" fill="none" stroke="{CREAM}"'
            ' stroke-width="13" stroke-linecap="round"/>'
            f'<g transform="translate(200 232) scale(0.34) translate(-256 -256)">{mark}</g>'
            "</svg>")


def seal_wax(mark: str) -> str:
    """Coaster / wax seal disc."""
    return (f'<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" class="app-art"'
            ' aria-hidden="true">'
            f'<circle cx="200" cy="200" r="150" fill="{CLARET}"/>'
            f'<circle cx="200" cy="200" r="150" fill="none" stroke="{OXBLOOD}"'
            ' stroke-width="6" opacity="0.5"/>'
            f'<g transform="translate(200 200) scale(0.50) translate(-256 -256)">{mark}</g>'
            "</svg>")


def build() -> list[dict]:
    built = []
    for v in VARIATIONS:
        fn, slug, name = v["fn"], v["slug"], v["name"]
        stem = f"nve-{v['num']}-{slug}"
        tile = fn(CREAM, GOLD)
        one = v.get("one_fn", fn)(BURGUNDY, BURGUNDY)
        write(OUT / "monograms" / f"{stem}.svg",
              svg(tile, bg=BURGUNDY, title=f"Napper Valley Estate — {name}"))
        write(OUT / "monograms" / f"{stem}-1c.svg",
              svg(one, title=f"Napper Valley Estate — {name}, one colour"))

        s = v["scale"]
        x0 = (LOCK_W - CANVAS * s) / 2
        mark = f'<g transform="translate({fmt(x0)} 40) scale({fmt(s)})">{tile}</g>'
        body = mark + wordmark(LOCK_W / 2, 600, CREAM, ROSE)
        write(OUT / "lockups" / f"{stem}-lockup.svg",
              svg(body, w=LOCK_W, h=LOCK_H, bg=BURGUNDY,
                  title=f"Napper Valley Estate — {name} lockup"))
        built.append({**v, "stem": stem, "tile": tile, "one": one})
    return built


def main() -> None:
    global F
    F = faces()
    print("Napper Valley Estate — building monogram system")
    built = build()
    write(OUT / "index.html", preview(built))
    write(OUT / "print.html", deck(built))
    print(f"done — {len(built)} variations")


if __name__ == "__main__":
    main()

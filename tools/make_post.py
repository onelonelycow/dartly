"""
make_post.py — the weekly social image for @nabbly.co.

One 1080x1080 square per week, built from the brand's own language: amber on
near-black. This week's theme is the feed itself — a loose field of gig cards,
quiet and dim, with one lighting up amber the instant it lands. Deliberately
rectilinear rather than radial, so it reads as a different piece from the
radar sweep (week 1) and the converging lines (the first draft of week 2).

Run:  .venv/bin/python tools/make_post.py
Out:  brand/posts/<name>.png   (1080x1080, ready to post)

Each week this file gets rewritten with a NEW visual idea rather than a new seed
of the same one — the point is a fresh piece, not a recolour.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts"
OUT.mkdir(parents=True, exist_ok=True)

S = 1080          # final size
SS = 2            # supersample factor for the vector work
W = S * SS

# Brand palette
BG      = (11, 13, 16)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)
INK     = (240, 242, 245)
MUTE    = (138, 145, 156)

SF = "/System/Library/Fonts/SFNS.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(size, variation="Bold", fallback=ARIAL_B):
    for p in (SF, fallback):
        try:
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_name(variation)
            except Exception:
                pass
            return f
        except Exception:
            continue
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


img = Image.new("RGB", (W, W), BG).convert("RGBA")

# ---------------------------------------------------------------------------
# A loose field of gig cards, upper ~60% of the frame. A regular grid with a
# little jitter per cell so it reads as a glimpsed board, not a spreadsheet.
# ---------------------------------------------------------------------------
GX0, GX1 = W * 0.09, W * 0.91
GY0, GY1 = W * 0.085, W * 0.615
COLS, ROWS = 7, 6
cell_w = (GX1 - GX0) / COLS
cell_h = (GY1 - GY0) / ROWS

HOT_COL, HOT_ROW = 4, 2   # upper right of centre — a rule-of-thirds point

card_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
cd = ImageDraw.Draw(card_layer)
glow_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow_layer)

CARD_FILL = (19, 21, 25, 255)
CARD_EDGE = (255, 255, 255, 16)
BAR_HI = (108, 114, 123, 140)
BAR_LO = (108, 114, 123, 80)

hot_box = None

for row in range(ROWS):
    for col in range(COLS):
        hot = (col == HOT_COL and row == HOT_ROW)

        # deterministic jitter from cell position, not randomness — keeps the
        # grid feeling hand placed without needing a seeded RNG
        jx = math.sin(row * 12.9 + col * 3.7) * cell_w * 0.10
        jy = math.cos(row * 7.3 + col * 5.1) * cell_h * 0.10
        jw = 0.90 + 0.08 * math.sin(row * 4.1 + col * 9.3)
        jh = 0.88 + 0.07 * math.cos(row * 6.7 + col * 2.4)

        ccx = GX0 + (col + 0.5) * cell_w + jx
        ccy = GY0 + (row + 0.5) * cell_h + jy
        cw = cell_w * 0.76 * jw
        ch = cell_h * 0.70 * jh
        x0, y0 = ccx - cw / 2, ccy - ch / 2
        x1, y1 = ccx + cw / 2, ccy + ch / 2
        rad = ch * 0.22

        if hot:
            hot_box = (x0, y0, x1, y1, rad)
            fill = tuple(int(c) for c in lerp(BG, AMBER, 0.16)) + (255,)
            edge = (247, 181, 105, 200)
            edge_w = max(1, int(1.8 * SS))
        else:
            fill = CARD_FILL
            edge = CARD_EDGE
            edge_w = max(1, int(1.0 * SS))

        cd.rounded_rectangle([x0, y0, x1, y1], radius=rad, fill=fill,
                              outline=edge, width=edge_w)

        pad_x = cw * 0.13
        bar_y1 = y0 + ch * 0.36
        bar_y2 = y0 + ch * 0.60
        bar1_col = (252, 232, 208, 235) if hot else BAR_HI
        bar2_col = (238, 187, 130, 170) if hot else BAR_LO
        cd.rounded_rectangle([x0 + pad_x, bar_y1, x0 + pad_x + cw * 0.56, bar_y1 + ch * 0.075],
                              radius=ch * 0.03, fill=bar1_col)
        cd.rounded_rectangle([x0 + pad_x, bar_y2, x0 + pad_x + cw * 0.34, bar_y2 + ch * 0.06],
                              radius=ch * 0.03, fill=bar2_col)

        # a small category dot, top left of every card
        dr = ch * 0.075
        ddx, ddy = x0 + pad_x + dr, y0 + ch * 0.20
        dot_col = (247, 197, 145, 235) if hot else (90, 96, 104, 150)
        cd.ellipse([ddx - dr, ddy - dr, ddx + dr, ddy + dr], fill=dot_col)

        if hot:
            # a small "just arrived" mark at the top right corner
            nr = ch * 0.085
            nx, ny = x1 - cw * 0.12, y0 + ch * 0.14
            gd.ellipse([nx - nr * 3.4, ny - nr * 3.4, nx + nr * 3.4, ny + nr * 3.4],
                       fill=(232, 147, 58, 95))
            cd.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=(252, 232, 205, 255))

# a quiet bloom behind the one card that matters, nothing else
hx0, hy0, hx1, hy1, hrad = hot_box
hcx, hcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
bloom_r = (hx1 - hx0) * 1.35
gd.ellipse([hcx - bloom_r, hcy - bloom_r, hcx + bloom_r, hcy + bloom_r],
           fill=(232, 147, 58, 70))

glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=26 * SS))
img = Image.alpha_composite(img, glow_layer)
img = Image.alpha_composite(img, card_layer)
img = img.convert("RGB")


def nabbly_mark(size, ss=3):
    """
    The logo mark: amber rounded square, the check/N stroke, and the ping ring.
    Same geometry as assets/icon.svg so it matches the app and the avatar.
    """
    s = size * ss
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (s, s))
    gp = grad.load()
    for y in range(s):
        for x in range(s):
            t = min(1.0, x / s * 0.5 + y / s * 0.5)
            gp[x, y] = tuple(int(AMBER_L[i] + (203, 111, 22)[i] * 0 +
                                 ((203, 111, 22)[i] - AMBER_L[i]) * t) for i in range(3))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.23), fill=255)
    tile.paste(grad, (0, 0), mask)
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle([s * .022, s * .022, s - s * .022, s - s * .022],
                         radius=int(s * 0.23 - s * .022),
                         outline=(255, 255, 255, 62), width=max(2, int(s * .009)))
    cxx, cyy, rr = s * .715, s * .238, s * .098
    td.ellipse([cxx - rr, cyy - rr, cxx + rr, cyy + rr],
               outline=(255, 255, 255, 92), width=max(2, int(s * .011)))
    lw = int(s * .072)
    td.line([(s * .29, s * .70), (s * .29, s * .355)],
            fill=(255, 255, 255, 132), width=lw)
    td.line([(s * .29, s * .355), (s * .48, s * .645), (s * .67, s * .30)],
            fill=(255, 255, 255, 255), width=lw, joint="curve")
    td.ellipse([cxx - rr * .44, cyy - rr * .44, cxx + rr * .44, cyy + rr * .44],
               fill=(255, 255, 255, 255))
    return tile.resize((size, size), Image.LANCZOS)


img = img.resize((S, S), Image.LANCZOS)

# ---------------------------------------------------------------------------
# 4. Type — set on the finished art, at final scale, so it stays crisp
# ---------------------------------------------------------------------------
d = ImageDraw.Draw(img)

f_h = font(58, "Semibold")            # smaller and a shade lighter than Bold
f_sub = font(27, "Regular", ARIAL)
f_url = font(24, "Semibold", ARIAL_B)
SOFT_AMBER = (214, 152, 88)           # the accent, pulled back from full strength

# No eyebrow label — the headline says it, and the empty space above it does
# more for the composition than a second line of type would.
d.text((S * 0.5, S * 0.782), "Every gig,", font=f_h, fill=(226, 229, 234), anchor="mm")
d.text((S * 0.5, S * 0.845), "the moment it drops.", font=f_h, fill=SOFT_AMBER,
       anchor="mm")
d.text((S * 0.5, S * 0.905), "Design, writing, dev, video, and more. One feed.",
       font=f_sub, fill=(126, 133, 143), anchor="mm")

# Sign-off lockup: the mark beside the domain, centred as one unit. Small enough
# to read as a signature rather than a second focal point.
MK = 36
GAP = 11
_t = "nabbly.co"
_tw = d.textlength(_t, font=f_url)
_x0 = (S - (MK + GAP + _tw)) / 2
_y = S * 0.949
mark = nabbly_mark(MK)
img.paste(mark, (int(_x0), int(_y - MK / 2)), mark)
d.text((_x0 + MK + GAP, _y), _t, font=f_url, fill=(190, 140, 92), anchor="lm")

path = OUT / "week-02-cards.png"
img.save(path, "PNG", optimize=True)
print("wrote", path, img.size)

"""
make_post.py — the weekly social image for @nabbly.co.

One 1080x1080 square per week, built from the brand's own language: amber on
near-black, and the radar-ping mark that's already in the logo. This week's
theme is the sweep itself — a radar finding live gigs — because that IS the
product: something out there is watching for you, all the time.

Run:  .venv/bin/python tools/make_post.py
Out:  brand/posts/<name>.png   (1080x1080, ready to post)

Each week this file gets rewritten with a NEW visual idea rather than a new seed
of the same one — the point is a fresh piece, not a recolour.
"""
import math
from pathlib import Path

import numpy as np
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


# ---------------------------------------------------------------------------
# 1. The ground: near-black with a warm bloom behind the radar
# ---------------------------------------------------------------------------
cx, cy = W * 0.5, W * 0.375         # radar centre, sitting high so type gets room
R = W * 0.325                        # outer ring radius

yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
dx, dy = xx - cx, yy - cy
rad = np.sqrt(dx * dx + dy * dy)
ang = np.arctan2(dy, dx)             # -pi..pi

base = np.zeros((W, W, 3), np.float32)
base[:] = BG

# warm bloom, strongest at the centre and gone by the outer ring. Kept faint —
# it should feel like the page is quietly lit, not like a spotlight.
bloom = np.clip(1.0 - rad / (R * 1.55), 0, 1) ** 2.2
for i, c in enumerate(AMBER):
    base[:, :, i] += bloom * (c - BG[i]) * 0.10

# ---------------------------------------------------------------------------
# 2. The sweep: a wedge trailing behind the leading edge, fading as it goes
# ---------------------------------------------------------------------------
LEAD = math.radians(-52)             # where the beam currently points
trail = (LEAD - ang) % (2 * math.pi)  # 0 at the edge, growing backwards
TAIL = math.radians(115)

sweep = np.clip(1.0 - trail / TAIL, 0, 1) ** 2.6      # angular falloff
sweep *= np.clip(1.0 - rad / R, 0, 1) ** 0.45          # dimmer toward the rim
sweep *= (rad < R)                                     # clipped to the dish
# Blur the beam so its leading edge is a soft gradient rather than a hard blade.
# The knife edge was most of what made this read as loud.
sweep = np.asarray(
    Image.fromarray((sweep * 255).astype(np.uint8), "L")
         .filter(ImageFilter.GaussianBlur(radius=7 * SS))
).astype(np.float32) / 255.0
for i, c in enumerate(AMBER_L):
    base[:, :, i] += sweep * (c - BG[i]) * 0.26

img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")

# ---------------------------------------------------------------------------
# 3. Rings, grid, and the gigs the sweep is finding
# ---------------------------------------------------------------------------
ov = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)

for k in (0.28, 0.52, 0.76, 1.0):                      # concentric rings
    r = R * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              outline=(232, 147, 58, 30), width=max(1, int(1.6 * SS)))

for a in range(0, 360, 30):                            # faint spokes
    t = math.radians(a)
    d.line([(cx, cy), (cx + R * math.cos(t), cy + R * math.sin(t))],
           fill=(232, 147, 58, 12), width=max(1, int(1.0 * SS)))

# Gigs on the board. Polar (angle°, radius fraction, size, hot?) — the ones near
# the leading edge read as "just found", which is the whole story of the brand.
# Only ONE gig is "just found" — a single point of emphasis reads as confident;
# three competing highlights read as busy.
BLIPS = [
    (-52, 0.62, 9, True),     # right on the beam
    (-38, 0.40, 5,  False),
    (-70, 0.83, 5,  False),
    (-95, 0.55, 4,  False),
    (-14, 0.74, 4,  False),
    (18,  0.47, 4,  False),
    (58,  0.68, 4,  False),
    (104, 0.35, 3,  False),
    (140, 0.60, 3,  False),
    (176, 0.79, 3,  False),
    (-130, 0.70, 3, False),
    (-166, 0.45, 3, False),
]
glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for a_deg, rf, size, hot in BLIPS:
    t = math.radians(a_deg)
    x, y = cx + R * rf * math.cos(t), cy + R * rf * math.sin(t)
    s = size * SS
    halo = s * (3.4 if hot else 2.4)
    gd.ellipse([x - halo, y - halo, x + halo, y + halo],
               fill=(232, 147, 58, 78 if hot else 30))
    # warm, never pure white — white is what made these pop like flashbulbs
    d.ellipse([x - s, y - s, x + s, y + s],
              fill=(252, 228, 198, 235) if hot else (226, 176, 122, 140))

glow = glow.filter(ImageFilter.GaussianBlur(radius=11 * SS))
ov = Image.alpha_composite(glow, ov)
img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


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


# (The mark was tried at the centre of the dish: it needed a dark pad to sit on,
# which read as a smudge, and a solid amber square became the loudest thing in a
# deliberately quiet picture. It signs off at the bottom instead — see below.)

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
d.text((S * 0.5, S * 0.905), "One feed for every freelance board", font=f_sub,
       fill=(126, 133, 143), anchor="mm")

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

path = OUT / "week-01-radar.png"
img.save(path, "PNG", optimize=True)
print("wrote", path, img.size)

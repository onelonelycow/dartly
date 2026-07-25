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

img = img.resize((S, S), Image.LANCZOS)

# ---------------------------------------------------------------------------
# 4. Type — set on the finished art, at final scale, so it stays crisp
# ---------------------------------------------------------------------------
d = ImageDraw.Draw(img)

f_h = font(58, "Semibold")            # smaller and a shade lighter than Bold
f_sub = font(27, "Regular", ARIAL)
f_url = font(24, "Semibold", ARIAL_B)
f_kick = font(20, "Semibold", ARIAL_B)
SOFT_AMBER = (214, 152, 88)           # the accent, pulled back from full strength

# eyebrow, letterspaced by hand for a considered look
kick, kx, ky = "LIVE FREELANCE DEMAND", S * 0.5, S * 0.722
kw = sum(d.textlength(ch, font=f_kick) + 4.0 for ch in kick) - 4.0
x = kx - kw / 2
for ch in kick:
    d.text((x, ky), ch, font=f_kick, fill=(118, 100, 80), anchor="lm")
    x += d.textlength(ch, font=f_kick) + 4.0

d.text((S * 0.5, S * 0.790), "Every gig,", font=f_h, fill=(226, 229, 234), anchor="mm")
d.text((S * 0.5, S * 0.853), "the moment it drops.", font=f_h, fill=SOFT_AMBER,
       anchor="mm")
d.text((S * 0.5, S * 0.916), "One feed for every freelance board", font=f_sub,
       fill=(126, 133, 143), anchor="mm")
d.text((S * 0.5, S * 0.955), "nabbly.co", font=f_url, fill=(190, 140, 92), anchor="mm")

path = OUT / "week-01-radar.png"
img.save(path, "PNG", optimize=True)
print("wrote", path, img.size)

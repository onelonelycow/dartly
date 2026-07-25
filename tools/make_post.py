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

# warm bloom, strongest at the centre and gone by the outer ring
bloom = np.clip(1.0 - rad / (R * 1.55), 0, 1) ** 2.2
for i, c in enumerate(AMBER):
    base[:, :, i] += bloom * (c - BG[i]) * 0.22

# ---------------------------------------------------------------------------
# 2. The sweep: a wedge trailing behind the leading edge, fading as it goes
# ---------------------------------------------------------------------------
LEAD = math.radians(-52)             # where the beam currently points
trail = (LEAD - ang) % (2 * math.pi)  # 0 at the edge, growing backwards
TAIL = math.radians(115)

sweep = np.clip(1.0 - trail / TAIL, 0, 1) ** 2.6      # angular falloff
sweep *= np.clip(1.0 - rad / R, 0, 1) ** 0.45          # dimmer toward the rim
sweep *= (rad < R)                                     # clipped to the dish
for i, c in enumerate(AMBER_L):
    base[:, :, i] += sweep * (c - BG[i]) * 0.55

img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")

# ---------------------------------------------------------------------------
# 3. Rings, grid, and the gigs the sweep is finding
# ---------------------------------------------------------------------------
ov = Image.new("RGBA", (W, W), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)

for k in (0.28, 0.52, 0.76, 1.0):                      # concentric rings
    r = R * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              outline=(232, 147, 58, 46), width=max(1, int(2.0 * SS)))

for a in range(0, 360, 30):                            # faint spokes
    t = math.radians(a)
    d.line([(cx, cy), (cx + R * math.cos(t), cy + R * math.sin(t))],
           fill=(232, 147, 58, 20), width=max(1, int(1.2 * SS)))

# Gigs on the board. Polar (angle°, radius fraction, size, hot?) — the ones near
# the leading edge read as "just found", which is the whole story of the brand.
BLIPS = [
    (-52, 0.62, 12, True),    # right on the beam
    (-38, 0.40, 8,  True),
    (-70, 0.83, 7,  True),
    (-95, 0.55, 6,  False),
    (-14, 0.74, 6,  False),
    (18,  0.47, 5,  False),
    (58,  0.68, 5,  False),
    (104, 0.35, 4,  False),
    (140, 0.60, 4,  False),
    (176, 0.79, 4,  False),
    (-130, 0.70, 4, False),
    (-166, 0.45, 3, False),
]
glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for a_deg, rf, size, hot in BLIPS:
    t = math.radians(a_deg)
    x, y = cx + R * rf * math.cos(t), cy + R * rf * math.sin(t)
    s = size * SS
    halo = s * (4.6 if hot else 3.0)
    gd.ellipse([x - halo, y - halo, x + halo, y + halo],
               fill=(232, 147, 58, 130 if hot else 55))
    d.ellipse([x - s, y - s, x + s, y + s],
              fill=(255, 240, 224, 255) if hot else (240, 190, 130, 190))

glow = glow.filter(ImageFilter.GaussianBlur(radius=9 * SS))
ov = Image.alpha_composite(glow, ov)
img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

img = img.resize((S, S), Image.LANCZOS)

# ---------------------------------------------------------------------------
# 4. Type — set on the finished art, at final scale, so it stays crisp
# ---------------------------------------------------------------------------
d = ImageDraw.Draw(img)

f_h = font(70, "Bold")
f_sub = font(29, "Regular", ARIAL)
f_url = font(26, "Semibold", ARIAL_B)
f_kick = font(23, "Semibold", ARIAL_B)

# eyebrow, letterspaced by hand for a considered look
kick, kx, ky = "LIVE FREELANCE DEMAND", S * 0.5, S * 0.715
kw = sum(d.textlength(ch, font=f_kick) + 3.4 for ch in kick) - 3.4
x = kx - kw / 2
for ch in kick:
    d.text((x, ky), ch, font=f_kick, fill=(150, 120, 88), anchor="lm")
    x += d.textlength(ch, font=f_kick) + 3.4

d.text((S * 0.5, S * 0.785), "Every gig,", font=f_h, fill=INK, anchor="mm")
d.text((S * 0.5, S * 0.858), "the moment it drops.", font=f_h, fill=AMBER, anchor="mm")
d.text((S * 0.5, S * 0.921), "One feed for every freelance board", font=f_sub,
       fill=MUTE, anchor="mm")
d.text((S * 0.5, S * 0.957), "nabbly.co", font=f_url, fill=AMBER_L, anchor="mm")

path = OUT / "week-01-radar.png"
img.save(path, "PNG", optimize=True)
print("wrote", path, img.size)

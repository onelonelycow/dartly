"""
make_og.py — the 1200x630 social preview card for nabbly.co.

This is the image that shows when a Nabbly link is dropped in Slack, iMessage,
LinkedIn or a Google result. Same visual language as the weekly posts: a soft
radar sweep finding one live gig, warm amber on near-black, restrained rather
than loud. Type sits left, the dish bleeds off the right edge.

Run:  .venv/bin/python tools/make_og.py
Out:  site/og-image.png
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "og-image.png"

W, H = 1200, 630
SS = 2                      # supersample for the vector work
BW, BH = W * SS, H * SS

BG      = (11, 13, 16)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)
AMBER_D = (203, 111, 22)
INK     = (226, 229, 234)
MUTE    = (126, 133, 143)
SOFT_AMBER = (214, 152, 88)     # accent pulled back from full strength

SF = "/System/Library/Fonts/SFNS.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(size, variation="Semibold", fallback=ARIAL_B):
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
# 1. Ground + the dish, sitting right of centre and bleeding off the edge
# ---------------------------------------------------------------------------
cx, cy = BW * 0.775, BH * 0.50
R = BH * 0.46

yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
dx, dy = xx - cx, yy - cy
rad = np.sqrt(dx * dx + dy * dy)
ang = np.arctan2(dy, dx)

base = np.zeros((BH, BW, 3), np.float32)
base[:] = BG

bloom = np.clip(1.0 - rad / (R * 1.6), 0, 1) ** 2.2
for i, c in enumerate(AMBER):
    base[:, :, i] += bloom * (c - BG[i]) * 0.10

# The sweep, blurred so its leading edge is a gradient rather than a blade.
LEAD = math.radians(-46)
trail = (LEAD - ang) % (2 * math.pi)
TAIL = math.radians(112)
sweep = np.clip(1.0 - trail / TAIL, 0, 1) ** 2.6
sweep *= np.clip(1.0 - rad / R, 0, 1) ** 0.45
sweep *= (rad < R)
sweep = np.asarray(
    Image.fromarray((sweep * 255).astype(np.uint8), "L")
         .filter(ImageFilter.GaussianBlur(radius=7 * SS))
).astype(np.float32) / 255.0
for i, c in enumerate(AMBER_L):
    base[:, :, i] += sweep * (c - BG[i]) * 0.26

img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")

# ---------------------------------------------------------------------------
# 2. Rings, spokes, and the one gig the beam just found
# ---------------------------------------------------------------------------
ov = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)

for k in (0.30, 0.55, 0.78, 1.0):
    r = R * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              outline=(232, 147, 58, 28), width=max(1, int(1.6 * SS)))
for a in range(0, 360, 30):
    t = math.radians(a)
    d.line([(cx, cy), (cx + R * math.cos(t), cy + R * math.sin(t))],
           fill=(232, 147, 58, 11), width=max(1, int(1.0 * SS)))

BLIPS = [
    (-46, 0.60, 9, True),
    (-30, 0.38, 5, False),
    (-66, 0.82, 5, False),
    (-100, 0.52, 4, False),
    (-8,  0.72, 4, False),
    (26,  0.45, 4, False),
    (64,  0.66, 4, False),
    (112, 0.34, 3, False),
    (150, 0.58, 3, False),
    (-140, 0.68, 3, False),
]
glow = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for a_deg, rf, size, hot in BLIPS:
    t = math.radians(a_deg)
    x, y = cx + R * rf * math.cos(t), cy + R * rf * math.sin(t)
    s = size * SS
    halo = s * (3.4 if hot else 2.4)
    gd.ellipse([x - halo, y - halo, x + halo, y + halo],
               fill=(232, 147, 58, 78 if hot else 30))
    d.ellipse([x - s, y - s, x + s, y + s],
              fill=(252, 228, 198, 235) if hot else (226, 176, 122, 140))
glow = glow.filter(ImageFilter.GaussianBlur(radius=11 * SS))
ov = Image.alpha_composite(glow, ov)
img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

# A soft fade on the left so the dish never competes with the headline.
fade = np.clip((np.linspace(0, 1, BW) - 0.13) / 0.30, 0, 1).astype(np.float32)
arr = np.asarray(img).astype(np.float32)
for i in range(3):
    arr[:, :, i] = BG[i] + (arr[:, :, i] - BG[i]) * fade[None, :]
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

img = img.resize((W, H), Image.LANCZOS)

# ---------------------------------------------------------------------------
# 3. The mark, drawn to match assets/icon.svg
# ---------------------------------------------------------------------------
def nabbly_mark(size, ss=3):
    s = size * ss
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (s, s))
    gp = grad.load()
    for y in range(s):
        for x in range(s):
            t = min(1.0, x / s * 0.5 + y / s * 0.5)
            gp[x, y] = tuple(int(AMBER_L[i] + (AMBER_D[i] - AMBER_L[i]) * t)
                             for i in range(3))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.23), fill=255)
    tile.paste(grad, (0, 0), mask)
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle([s * .022, s * .022, s - s * .022, s - s * .022],
                         radius=int(s * 0.23 - s * .022),
                         outline=(255, 255, 255, 62), width=max(2, int(s * .009)))
    mx, my, rr = s * .715, s * .238, s * .098
    td.ellipse([mx - rr, my - rr, mx + rr, my + rr],
               outline=(255, 255, 255, 92), width=max(2, int(s * .011)))
    lw = int(s * .072)
    td.line([(s * .29, s * .70), (s * .29, s * .355)],
            fill=(255, 255, 255, 132), width=lw)
    td.line([(s * .29, s * .355), (s * .48, s * .645), (s * .67, s * .30)],
            fill=(255, 255, 255, 255), width=lw, joint="curve")
    td.ellipse([mx - rr * .44, my - rr * .44, mx + rr * .44, my + rr * .44],
               fill=(255, 255, 255, 255))
    return tile.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# 4. Type, set at final scale so it stays crisp
# ---------------------------------------------------------------------------
d = ImageDraw.Draw(img)
X = int(W * 0.068)                  # left margin, well inside any crop

f_h = font(56, "Semibold")
f_sub = font(24, "Regular", ARIAL)
f_url = font(23, "Semibold", ARIAL_B)

d.text((X, H * 0.335), "Every freelance gig,", font=f_h, fill=INK, anchor="lm")
d.text((X, H * 0.445), "the moment it drops.", font=f_h, fill=SOFT_AMBER, anchor="lm")
d.text((X, H * 0.565), "One feed for every freelance board,", font=f_sub,
       fill=MUTE, anchor="lm")
d.text((X, H * 0.625), "so you reply first.", font=f_sub, fill=MUTE, anchor="lm")

# Sign-off lockup: the mark beside the domain, same as the weekly posts.
MK = 34
mark = nabbly_mark(MK)
my = int(H * 0.755)
img.paste(mark, (X, my - MK // 2), mark)
d.text((X + MK + 11, my), "nabbly.co", font=f_url, fill=(190, 140, 92), anchor="lm")

img.save(OUT, "PNG", optimize=True)
print("wrote", OUT, img.size)

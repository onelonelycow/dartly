"""
make_post.py — the weekly social image for @nabbly.co.

One 1080x1080 square per week, built from the brand's own language: amber on
near-black. This week's theme is the clock. A single quiet rail runs down the
frame with a day's worth of gigs landing against it, timestamped, from just
after midnight to late evening. The one that landed at 4:12 in the morning is
lit amber and everything else stays grey, so the frame makes its point without
saying it: the board does not keep office hours.

Editorial and vertical, so it reads as a different piece from the radar sweep
(week 1), the field of gig cards (week 2) and the pack of racing trails
(week 3).

Run:  .venv/bin/python tools/make_post.py
Out:  brand/posts/<name>.png   (1080x1080, ready to post)

Each week this file gets rewritten with a NEW visual idea rather than a new seed
of the same one — the point is a fresh piece, not a recolour. Git history keeps
the previous weeks' generators.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts"
OUT.mkdir(parents=True, exist_ok=True)

S = 1080          # final size
SS = 3            # supersample factor for the vector work
W = S * SS

# Brand palette
BG      = (11, 13, 16)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)

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
# The day. Seven moments, ordered, spanning midnight to late evening. The hot
# one sits third so the emphasis lands in the upper third of the artwork rather
# than dead centre, and it is deliberately the small-hours one.
# ---------------------------------------------------------------------------
ROWS = [
    ("12:41 am", "Podcast editing"),
    ("2:26 am",  "Brand identity"),
    ("4:12 am",  "Motion graphics"),        # <- the one that carries the idea
    ("7:58 am",  "Copywriting"),
    ("11:30 am", "React development"),
    ("3:04 pm",  "Product photography"),
    ("9:47 pm",  "Illustration"),
]
HOT = 2

ROW_Y0, ROW_Y1 = 168, 700                  # final-scale, well inside the edges
GAP = 34                                   # breathing room either side of rail

f_time    = font(25, "Regular", ARIAL)
f_time_h  = font(25, "Semibold", ARIAL_B)
f_field   = font(31, "Regular", ARIAL)
f_field_h = font(31, "Semibold", ARIAL_B)

# Measure at final scale, then centre the whole two-column block on the canvas.
_m = ImageDraw.Draw(Image.new("RGB", (10, 10)))
time_w = max(_m.textlength(t, font=(f_time_h if i == HOT else f_time))
             for i, (t, _) in enumerate(ROWS))
field_w = max(_m.textlength(g, font=(f_field_h if i == HOT else f_field))
              for i, (_, g) in enumerate(ROWS))
RAIL_X = (S + time_w - field_w) / 2         # block centred, not the rail

row_y = [ROW_Y0 + (ROW_Y1 - ROW_Y0) * i / (len(ROWS) - 1) for i in range(len(ROWS))]
hot_y = row_y[HOT]

img = Image.new("RGB", (W, W), BG).convert("RGBA")

# ---------------------------------------------------------------------------
# The rail and its one bloom, drawn supersampled. The rail is brightest beside
# the amber row and falls away to nothing at both ends, so the eye is given a
# single place to go and the line never reads as a hard-edged border.
# ---------------------------------------------------------------------------
rail = Image.new("RGBA", (W, W), (0, 0, 0, 0))
rd = ImageDraw.Draw(rail)

RAIL_TOP, RAIL_BOT = 120 * SS, 748 * SS
rx = RAIL_X * SS
half = 1.05 * SS

for y in range(int(RAIL_TOP), int(RAIL_BOT)):
    span = RAIL_BOT - RAIL_TOP
    t = (y - RAIL_TOP) / span
    edge = min(t, 1 - t) / 0.5                      # 0 at the ends, 1 mid-rail
    edge = min(1.0, edge * 2.2) ** 1.4              # hold, then fall off fast
    near = max(0.0, 1 - abs(y - hot_y * SS) / (210 * SS))
    a = 34 * edge + 92 * edge * near ** 2
    c = tuple(int(58 + (172 - 58) * near ** 2) for _ in range(1))[0]
    rd.rectangle([rx - half, y, rx + half, y + 1],
                 fill=(c, int(c * 0.93), int(c * 0.88), int(a)))

glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gr = 320 * SS
gcx = (S / 2) * SS                                  # centred on the text block
gd.ellipse([gcx - gr, hot_y * SS - gr * 0.66, gcx + gr, hot_y * SS + gr * 0.66],
           fill=(232, 147, 58, 23))
gr2 = 74 * SS
gd.ellipse([rx - gr2, hot_y * SS - gr2, rx + gr2, hot_y * SS + gr2],
           fill=(240, 168, 92, 74))
glow = glow.filter(ImageFilter.GaussianBlur(radius=46 * SS))
img = Image.alpha_composite(img, glow)

# The markers on the rail: quiet dots for the day, one lit for the small hours.
for i, y in enumerate(row_y):
    yy = y * SS
    if i == HOT:
        r = 5.6 * SS
        rd.ellipse([rx - r, yy - r, rx + r, yy + r], fill=(253, 235, 210, 255))
        r2 = 10.5 * SS
        rd.ellipse([rx - r2, yy - r2, rx + r2, yy + r2],
                   outline=(240, 168, 92, 128), width=int(1.4 * SS))
    else:
        r = 2.9 * SS
        rd.ellipse([rx - r, yy - r, rx + r, yy + r], fill=(120, 127, 137, 190))

img = Image.alpha_composite(img, rail).convert("RGB")
img = img.resize((S, S), Image.LANCZOS)


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
            gp[x, y] = tuple(int(AMBER_L[i] + ((203, 111, 22)[i] - AMBER_L[i]) * t)
                             for i in range(3))
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


# ---------------------------------------------------------------------------
# Type — set on the finished art, at final scale, so it stays crisp
# ---------------------------------------------------------------------------
d = ImageDraw.Draw(img)

SOFT_AMBER = (214, 152, 88)           # the accent, pulled back from full strength

for i, (t, g) in enumerate(ROWS):
    y = row_y[i]
    if i == HOT:
        d.text((RAIL_X - GAP, y), t, font=f_time_h, fill=(206, 150, 92), anchor="rm")
        d.text((RAIL_X + GAP, y), g, font=f_field_h, fill=(243, 190, 128), anchor="lm")
        continue
    # The rest of the day falls away with distance from the lit row, so the
    # amber one keeps the frame to itself instead of sharing it with six others.
    k = 1.0 - 0.30 * (abs(i - HOT) - 1) / (len(ROWS) - 1 - 1)
    d.text((RAIL_X - GAP, y), t, font=f_time,
           fill=tuple(int(c * k) for c in (100, 107, 117)), anchor="rm")
    d.text((RAIL_X + GAP, y), g, font=f_field,
           fill=tuple(int(c * k) for c in (144, 151, 162)), anchor="lm")

f_h = font(58, "Semibold")             # smaller and a shade lighter than Bold
f_sub = font(27, "Regular", ARIAL)
f_url = font(24, "Semibold", ARIAL_B)

# No eyebrow label — the headline says it, and the empty space above it does
# more for the composition than a second line of type would.
d.text((S * 0.5, S * 0.782), "Every gig,", font=f_h, fill=(226, 229, 234), anchor="mm")
d.text((S * 0.5, S * 0.845), "the moment it drops.", font=f_h, fill=SOFT_AMBER,
       anchor="mm")
d.text((S * 0.5, S * 0.905), "Gigs land at 4am too.",
       font=f_sub, fill=(126, 133, 143), anchor="mm")

# Sign-off lockup: the mark beside the domain, centred as one unit. Small enough
# to read as a signature rather than a second focal point.
MK = 36
LGAP = 11
_t = "nabbly.co"
_tw = d.textlength(_t, font=f_url)
_x0 = (S - (MK + LGAP + _tw)) / 2
_y = S * 0.949
mark = nabbly_mark(MK)
img.paste(mark, (int(_x0), int(_y - MK / 2)), mark)
d.text((_x0 + MK + LGAP, _y), _t, font=f_url, fill=(190, 140, 92), anchor="lm")

path = OUT / "week-04-around-the-clock.png"
img.save(path, "PNG", optimize=True)
print("wrote", path, img.size)

"""
make_og.py — the 1200x630 social-preview card for nabbly.co.

This is the image that shows when a Nabbly link is dropped in Slack, iMessage,
LinkedIn, X or a Google result. Drawn to match the app: amber mark on a dark
ground, the wordmark, one true line about what it does. Regenerate with:

    .venv/bin/python tools/make_og.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
OUT = Path(__file__).resolve().parent.parent / "site" / "og-image.png"

# Brand palette (from the app + logo.svg)
BG      = (18, 20, 24)       # #121418, a touch darker than the app for contrast
CARD    = (21, 24, 29)       # #15181d
BORDER  = (38, 42, 49)       # #262a31
INK     = (236, 238, 241)    # #ECEEF1
MUTE    = (150, 157, 167)
AMBER   = (232, 147, 58)     # #E8933A
AMBER_L = (247, 181, 105)    # #F7B569
AMBER_D = (203, 111, 22)     # #CB6F16


def _font(paths, size, variation=None):
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            if variation:
                try:
                    f.set_variation_by_name(variation)
                except Exception:
                    pass
            return f
        except Exception:
            continue
    return ImageFont.load_default()


SF = "/System/Library/Fonts/SFNS.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

f_word = _font([SF, ARIAL_B], 62, "Bold")
f_head = _font([SF, ARIAL_B], 68, "Bold")
f_head2 = _font([SF, ARIAL_B], 68, "Semibold")
f_sub  = _font([SF, ARIAL], 33, "Regular")
f_pill = _font([SF, ARIAL], 26, "Medium")
f_url  = _font([SF, ARIAL_B], 30, "Semibold")


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def amber_tile(size, radius):
    """The rounded-square icon with the diagonal amber gradient, drawn crisp
    via 3x supersampling."""
    s = size * 3
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (s, s))
    gd = grad.load()
    for y in range(s):
        for x in range(s):
            t = (x / s * 0.5 + y / s * 0.5)          # diagonal 0..1
            gd[x, y] = _lerp(AMBER_L, AMBER_D, min(1, t))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius * 3, fill=255)
    tile.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(tile)
    # inner hairline
    d.rounded_rectangle([4, 4, s - 5, s - 5], radius=radius * 3 - 4,
                        outline=(255, 255, 255, 70), width=3)
    # the radar ping ring, top-right
    cx, cy, rr = s * 0.72, s * 0.24, s * 0.10
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 95), width=4)
    # the check / "N" stroke
    lw = int(s * 0.075)
    d.line([(s * 0.28, s * 0.70), (s * 0.28, s * 0.35)], fill=(255, 255, 255, 130), width=lw)
    d.line([(s * 0.28, s * 0.35), (s * 0.48, s * 0.64), (s * 0.67, s * 0.29)],
           fill=(255, 255, 255, 255), width=lw, joint="curve")
    # ping dot fill
    d.ellipse([cx - rr * 0.42, cy - rr * 0.42, cx + rr * 0.42, cy + rr * 0.42],
              fill=(255, 255, 255, 255))
    return tile.resize((size, size), Image.LANCZOS)


def pill(draw, x, y, text, font):
    tw = draw.textlength(text, font=font)
    pad = 20
    h = 46
    rounded(draw, [x, y, x + tw + pad * 2, y + h], 23,
            fill=(26, 30, 36), outline=BORDER, width=2)
    draw.text((x + pad, y + h / 2), text, font=font, fill=MUTE, anchor="lm")
    return x + tw + pad * 2 + 12


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# faint amber glow, top-left, so it isn't a flat rectangle
glow = Image.new("RGB", (W, H), BG)
gd = glow.load()
for y in range(0, 300):
    for x in range(0, 460):
        dist = ((x / 460) ** 2 + (y / 300) ** 2) ** 0.5
        if dist < 1:
            t = (1 - dist) * 0.10
            gd[x, y] = _lerp(BG, AMBER, t)
img = Image.blend(img, glow, 0.6)
d = ImageDraw.Draw(img)

M = 84  # margin

# --- brand lockup, top ---
tile = amber_tile(84, 24)
img.paste(tile, (M, M), tile)
d.text((M + 104, M + 42), "Nabb", font=f_word, fill=INK, anchor="lm")
w_nabb = d.textlength("Nabb", font=f_word)
d.text((M + 104 + w_nabb, M + 42), "ly", font=f_word, fill=AMBER, anchor="lm")

# --- headline ---
hy = 250
d.text((M, hy), "Every freelance gig,", font=f_head, fill=INK, anchor="lm")
d.text((M, hy + 84), "the moment it drops.", font=f_head, fill=AMBER, anchor="lm")

# --- subhead ---
d.text((M, hy + 168),
       "Real-time demand from every board and community,",
       font=f_sub, fill=MUTE, anchor="lm")
d.text((M, hy + 168 + 44),
       "in one place — so you reply first.",
       font=f_sub, fill=MUTE, anchor="lm")

# --- vertical pills ---
py = 545
x = M
for label in ("Design", "Writing", "Dev", "Video", "Marketing", "+17 more"):
    x = pill(d, x, py, label, f_pill)

# --- url, bottom-right ---
d.text((W - M, H - M + 20), "nabbly.co", font=f_url, fill=AMBER_L, anchor="rm")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, "PNG")
print("wrote", OUT, img.size)

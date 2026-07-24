"""
make_social.py — profile + banner art for the social accounts.

Same mark and palette as the app and the og card, sized for each platform:
  brand/avatar-1000.png    square profile picture (LinkedIn, IG, Reddit, TikTok, Bluesky)
  brand/linkedin-banner.png   1584x396 company/profile cover
  brand/social-banner.png     1500x500 wide cover (X/Bluesky sizing, reusable)

Run:  .venv/bin/python tools/make_social.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand"
OUT.mkdir(exist_ok=True)

BG      = (18, 20, 24)
BORDER  = (38, 42, 49)
INK     = (236, 238, 241)
MUTE    = (150, 157, 167)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)
AMBER_D = (203, 111, 22)

SF = "/System/Library/Fonts/SFNS.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"


def _font(size, variation, fallback=ARIAL):
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


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def amber_tile(size, radius, ss=3):
    """The rounded-square icon with the diagonal amber gradient + radar check."""
    s = size * ss
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (s, s))
    gd = grad.load()
    for y in range(s):
        for x in range(s):
            t = (x / s * 0.5 + y / s * 0.5)
            gd[x, y] = _lerp(AMBER_L, AMBER_D, min(1, t))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius * ss, fill=255)
    tile.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle([s*0.02, s*0.02, s - s*0.02, s - s*0.02],
                        radius=radius * ss - s*0.02, outline=(255, 255, 255, 70),
                        width=max(2, int(s*0.008)))
    cx, cy, rr = s * 0.72, s * 0.24, s * 0.105
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 95),
              width=max(2, int(s*0.010)))
    lw = int(s * 0.072)
    d.line([(s * 0.28, s * 0.70), (s * 0.28, s * 0.35)], fill=(255, 255, 255, 130), width=lw)
    d.line([(s * 0.28, s * 0.35), (s * 0.48, s * 0.64), (s * 0.67, s * 0.29)],
           fill=(255, 255, 255, 255), width=lw, joint="curve")
    d.ellipse([cx - rr * 0.42, cy - rr * 0.42, cx + rr * 0.42, cy + rr * 0.42],
              fill=(255, 255, 255, 255))
    return tile.resize((size, size), Image.LANCZOS)


# ── avatar: the tile, centred on a dark round-safe square ────────────────
def make_avatar(size=1000):
    img = Image.new("RGB", (size, size), BG)
    tile = amber_tile(int(size * 0.72), int(size * 0.72 * 0.26))
    off = (size - tile.width) // 2
    img.paste(tile, (off, off), tile)
    img.save(OUT / "avatar-1000.png")
    # a tight, no-margin variant for platforms that mask to a circle
    amber_tile(size, int(size * 0.26)).convert("RGB").save(OUT / "avatar-tight-1000.png")
    print("avatar-1000.png, avatar-tight-1000.png")


# ── banner ───────────────────────────────────────────────────────────────
def make_banner(w, h, name, tagline_y_shift=0):
    img = Image.new("RGB", (w, h), BG)
    # amber glow lower-left so it isn't flat
    glow = Image.new("RGB", (w, h), BG)
    gd = glow.load()
    gx, gy, gr = int(w * 0.30), int(h * 0.5), int(h * 1.5)
    for y in range(h):
        for x in range(0, int(w * 0.7)):
            dist = (((x - gx) / gr) ** 2 + ((y - gy) / gr) ** 2) ** 0.5
            if dist < 1:
                gd[x, y] = _lerp(BG, AMBER, (1 - dist) * 0.14)
    img = Image.blend(img, glow, 0.7)
    d = ImageDraw.Draw(img)

    tile_sz = int(h * 0.30)
    m = int(w * 0.055)
    cy = int(h * 0.40) + tagline_y_shift
    tile = amber_tile(tile_sz, int(tile_sz * 0.26))
    img.paste(tile, (m, cy - tile_sz // 2), tile)

    f_word = _font(int(h * 0.16), "Bold", ARIAL_B)
    tx = m + tile_sz + int(w * 0.02)
    d.text((tx, cy), "Nabb", font=f_word, fill=INK, anchor="lm")
    wn = d.textlength("Nabb", font=f_word)
    d.text((tx + wn, cy), "ly", font=f_word, fill=AMBER, anchor="lm")

    f_tag = _font(int(h * 0.072), "Regular", ARIAL)
    d.text((tx, cy + int(h * 0.155)),
           "Every freelance gig, the moment it drops.",
           font=f_tag, fill=MUTE, anchor="lm")
    d.text((w - m, h - int(h * 0.11)), "nabbly.co", font=_font(int(h*0.075), "Semibold", ARIAL_B),
           fill=AMBER_L, anchor="rm")
    img.save(OUT / name)
    print(name, img.size)


make_avatar()
make_banner(1584, 396, "linkedin-banner.png")
make_banner(1500, 500, "social-banner.png", tagline_y_shift=-10)

"""
make_social.py — profile + banner art for the social accounts.

Same mark and palette as the app and the og card, sized for each platform:
  brand/avatar-1000.png            square profile picture (LinkedIn, IG, Reddit, TikTok, Bluesky)
  brand/linkedin-banner.png        1584x396 — a PERSONAL LinkedIn profile's
                                    background photo (4:1). Do not upload this
                                    to the Company Page — LinkedIn crops a
                                    Company Page cover to a much wider ~6:1
                                    strip, so a 4:1 image gets its top and
                                    bottom aggressively cut off.
  brand/linkedin-company-cover.png 4200x700 — the Company Page cover (~6:1,
                                    LinkedIn's current spec). Use THIS one
                                    when setting up the nabbly-co page.
  brand/social-banner.png          1500x500 wide cover (X/Bluesky sizing, reusable)

Run:  .venv/bin/python tools/make_social.py
"""
from pathlib import Path
import numpy as np
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


def dither(img, amount=4, seed=1):
    """
    Add a tiny bit of random noise before saving. A perfectly smooth dark
    gradient (like the cover art's glow) is the one thing JPEG re-encoding
    handles worst — flat/smooth areas are exactly where 8-bit banding turns
    into visible blocky "pixelated" rings once a platform recompresses the
    upload. A few levels of noise breaks up the banding; it's invisible at
    normal viewing size but keeps the recompressed version smooth instead of
    stair-stepped. Deterministic seed so re-running the script doesn't
    produce a different-looking file each time.
    """
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.int16)
    noise = rng.integers(-amount, amount + 1, arr.shape[:2] + (1,))
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode=img.mode)


def amber_tile(size, radius, ss=3):
    """The rounded-square icon with the diagonal amber gradient + radar check."""
    s = size * ss
    grad = Image.new("RGB", (s, s))
    gd = grad.load()
    for y in range(s):
        for x in range(s):
            t = (x / s * 0.5 + y / s * 0.5)
            gd[x, y] = _lerp(AMBER_L, AMBER_D, min(1, t))
    # The detail strokes below are semi-transparent white and MUST be drawn
    # onto this RGB gradient now, not onto the RGBA tile after pasting.
    # Pillow only actually blends a semi-transparent fill against what's
    # already there when the target has no alpha channel of its own — draw
    # the identical (255,255,255,130) onto an RGBA image instead and it just
    # SETS the pixel to that literal (mostly-transparent) value, with no
    # amber underneath it at all. That "transparent" pixel only picks up a
    # visible color later, from whatever this tile eventually gets pasted
    # onto — gray on the cover's dark background, cream here on amber. Same
    # numbers, two different-looking marks. Blending here first, against the
    # gradient that's actually supposed to show through, fixes it for every
    # future use of this tile regardless of what it's placed on.
    d = ImageDraw.Draw(grad, "RGBA")
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
    # NOW cut the rounded-rect shape out of the fully-blended artwork.
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius * ss, fill=255)
    tile.paste(grad, (0, 0), mask)
    return tile.resize((size, size), Image.LANCZOS)


def dark_tile(size, radius, ss=3):
    """
    Same mark as amber_tile, inverted: a dark charcoal tile (matching the app's
    own BG) with the check drawn in amber instead of white. Built for sitting
    next to the dark cover/banner art, where the solid amber tile reads as a
    loud, disconnected block rather than part of the same brand system.
    """
    s = size * ss
    # a faint amber glow lower-right, echoing the cover art's glow instead of
    # sitting perfectly flat
    grad = Image.new("RGB", (s, s), BG)
    gd = grad.load()
    gx, gy, gr = s * 0.75, s * 0.8, s * 1.3
    for y in range(s):
        for x in range(s):
            dist = (((x - gx) / gr) ** 2 + ((y - gy) / gr) ** 2) ** 0.5
            if dist < 1:
                gd[x, y] = _lerp(BG, AMBER_D, (1 - dist) * 0.35)
    # detail strokes blended onto the RGB gradient — see amber_tile's comment
    d = ImageDraw.Draw(grad, "RGBA")
    d.rounded_rectangle([s*0.02, s*0.02, s - s*0.02, s - s*0.02],
                        radius=radius * ss - s*0.02, outline=(*AMBER, 90),
                        width=max(2, int(s*0.008)))
    cx, cy, rr = s * 0.72, s * 0.24, s * 0.105
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*AMBER_L, 140),
              width=max(2, int(s*0.010)))
    lw = int(s * 0.072)
    d.line([(s * 0.28, s * 0.70), (s * 0.28, s * 0.35)], fill=(*AMBER, 190), width=lw)
    d.line([(s * 0.28, s * 0.35), (s * 0.48, s * 0.64), (s * 0.67, s * 0.29)],
           fill=(*AMBER_L, 255), width=lw, joint="curve")
    d.ellipse([cx - rr * 0.42, cy - rr * 0.42, cx + rr * 0.42, cy + rr * 0.42],
              fill=(*AMBER_L, 255))
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius * ss, fill=255)
    tile.paste(grad, (0, 0), mask)
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


# ── profile picture: full-bleed amber, built for a CIRCULAR crop ──────────
def make_pfp(size=1080, ss=3):
    """
    The social profile picture. Every platform masks a PFP to a circle, so this
    fills the whole frame with the amber gradient (no rounded corners, no dark
    background) — cropped to a circle it becomes a clean amber disc — and centres
    the mark well inside the safe zone so nothing clips, even at avatar size.
    """
    s = size * ss
    img = Image.new("RGB", (s, s))
    px = img.load()
    for y in range(s):                       # full-bleed diagonal amber gradient
        for x in range(s):
            px[x, y] = _lerp(AMBER_L, AMBER_D, min(1, (x / s * 0.5 + y / s * 0.5)))
    # a soft top-left sheen for depth, like the app icon
    sheen = Image.new("RGB", (s, s))
    sd = sheen.load()
    for y in range(int(s * 0.55)):
        for x in range(int(s * 0.55)):
            dist = (((x) / (s * 0.55)) ** 2 + ((y) / (s * 0.55)) ** 2) ** 0.5
            sd[x, y] = _lerp((255, 255, 255), AMBER_L, min(1, dist)) if dist < 1 else AMBER_L
    img = Image.blend(img, sheen, 0.0)       # (kept subtle; gradient already lights top-left)
    d = ImageDraw.Draw(img, "RGBA")

    # radar ping ring + dot, upper-right but inside the circle
    cx, cy, rr = s * 0.695, s * 0.30, s * 0.093
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(255, 255, 255, 120),
              width=int(s * 0.011))
    lw = int(s * 0.076)
    # the "N": a left leg, then the check that rises to the ping
    d.line([(s * 0.315, s * 0.70), (s * 0.315, s * 0.375)],
           fill=(255, 255, 255, 205), width=lw)
    d.line([(s * 0.315, s * 0.375), (s * 0.505, s * 0.655), (s * 0.675, s * 0.335)],
           fill=(255, 255, 255, 255), width=lw, joint="curve")
    d.ellipse([cx - rr * 0.44, cy - rr * 0.44, cx + rr * 0.44, cy + rr * 0.44],
              fill=(255, 255, 255, 255))
    img.resize((size, size), Image.LANCZOS).save(OUT / "avatar-pfp-1080.png")
    print("avatar-pfp-1080.png (circle-optimized profile picture)")


# ── profile picture, dark variant: full-bleed, built for a CIRCULAR crop ──
def make_pfp_dark(size=1080, ss=3):
    """
    Dark counterpart to make_pfp — same full-bleed, no-corners construction
    (LinkedIn's logo slot, like every platform's avatar upload, expects art
    that fills the whole frame; a rounded tile with transparent/dark corners
    like logo-dark.png leaves a gap between our shape and LinkedIn's own
    circular crop, which is what shows as a "white line" around it). Dark
    diagonal gradient instead of amber, mark drawn in amber instead of white.
    """
    s = size * ss
    img = Image.new("RGB", (s, s))
    px = img.load()
    DARK_L, DARK_D = BG, (46, 29, 14)
    for y in range(s):
        for x in range(s):
            px[x, y] = _lerp(DARK_L, DARK_D, min(1, (x / s * 0.5 + y / s * 0.5)))
    d = ImageDraw.Draw(img, "RGBA")

    cx, cy, rr = s * 0.695, s * 0.30, s * 0.093
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*AMBER_L, 160),
              width=int(s * 0.011))
    lw = int(s * 0.076)
    d.line([(s * 0.315, s * 0.70), (s * 0.315, s * 0.375)],
           fill=(*AMBER, 210), width=lw)
    d.line([(s * 0.315, s * 0.375), (s * 0.505, s * 0.655), (s * 0.675, s * 0.335)],
           fill=(*AMBER_L, 255), width=lw, joint="curve")
    d.ellipse([cx - rr * 0.44, cy - rr * 0.44, cx + rr * 0.44, cy + rr * 0.44],
              fill=(*AMBER_L, 255))
    img = dither(img.resize((size, size), Image.LANCZOS), amount=3)
    img.save(OUT / "pfp-dark-1080.png")
    print("pfp-dark-1080.png (circle-optimized, dark variant)")


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


# ── company-page cover ──────────────────────────────────────────────────
def make_company_cover(w, h, name, safe_w):
    """
    LinkedIn shows the full width on desktop but crops a Company Page cover
    to its centered middle `safe_w` px on mobile — a left-aligned lockup
    (like make_banner's) would lose the logo on one edge and the URL on the
    other. Everything here is centered on the canvas instead, sized to fit
    inside that centered strip on its own.
    """
    img = Image.new("RGB", (w, h), BG)
    glow = Image.new("RGB", (w, h), BG)
    gd = glow.load()
    gx, gy, gr = w // 2, h // 2, int(h * 1.6)
    for y in range(h):
        for x in range(w):
            dist = (((x - gx) / gr) ** 2 + ((y - gy) / gr) ** 2) ** 0.5
            if dist < 1:
                gd[x, y] = _lerp(BG, AMBER, (1 - dist) * 0.14)
    img = Image.blend(img, glow, 0.7)
    d = ImageDraw.Draw(img)
    cx = w // 2

    # Sized to actually fill most of the mobile-safe strip, not just survive
    # inside it — the first version used only 547 of 900 available px and
    # read as tiny and lost once the full-width desktop banner made that gap
    # obvious. This targets ~80-85% of safe_w instead.
    tile_sz = int(h * 0.36)
    f_word = _font(int(h * 0.19), "Bold", ARIAL_B)
    # LinkedIn renders this cover at a small fraction of its source height —
    # MUTE at a "reads fine at 700px" size was a near-invisible smudge once
    # scaled down to actual on-page size. Bumped size, weight, and switched
    # to INK (near-white, ~6.7:1 on BG at full size, and Semibold holds up
    # far better than Regular once shrunk) instead of guessing again.
    f_tag = _font(int(h * 0.078), "Semibold", ARIAL_B)
    tag = "Every freelance gig, the moment it drops."

    word_w = d.textlength("Nabbly", font=f_word)
    gap = int(w * 0.014)
    lockup_w = tile_sz + gap + word_w
    lx = cx - int(lockup_w / 2)
    cy = int(h * 0.43)

    tile = amber_tile(tile_sz, int(tile_sz * 0.26))
    img.paste(tile, (lx, cy - tile_sz // 2), tile)
    tx = lx + tile_sz + gap
    d.text((tx, cy), "Nabb", font=f_word, fill=INK, anchor="lm")
    wn = d.textlength("Nabb", font=f_word)
    d.text((tx + wn, cy), "ly", font=f_word, fill=AMBER, anchor="lm")

    d.text((cx, cy + int(h * 0.27)), tag, font=f_tag, fill=INK, anchor="mm")
    img = dither(img)
    img.save(OUT / name)
    print(name, img.size, f"(lockup {int(lockup_w)}px, safe zone {safe_w}px)")


make_avatar()
make_pfp()
make_pfp_dark()
dark_tile(1000, int(1000 * 0.26)).convert("RGB").save(OUT / "logo-dark.png")
print("logo-dark.png (dark-bg / amber-mark logo variant)")
make_banner(1584, 396, "linkedin-banner.png")
make_company_cover(4200, 700, "linkedin-company-cover.png", safe_w=900)
make_banner(1500, 500, "social-banner.png", tagline_y_shift=-10)

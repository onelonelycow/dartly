"""
make_post.py — the weekly social image for @nabbly.co.

  brand/posts/week-07-one-feed.png
      Five real postings from five fields that have nothing to do with each
      other: a telehealth nursing shift, a product spot, a monthly close, a
      subtitling job, renders for a remodel. Read straight down, the surprise
      is the range, not any one line. It closes on the only true claim the
      picture needs: more than 20 fields, one feed.

Editorial and text-first, in the spirit of weeks 4 and 6 — real gig titles and
real field names on the canvas rather than a shape standing in for the idea.
Structurally and argumentatively its own piece: the previous weeks all argued
speed (radar sweep, field of cards, racing trails, the timestamped rail, the
shipping list, the same gig found seven hours apart). This one argues breadth,
and it is the first week with no clock on the canvas at all.

One accent only: the closing half-line. The five postings are set in greys so
the eye reads the range first and lands on the turn at the bottom.

Run:  .venv/bin/python tools/make_post.py

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
SS = 3            # supersample factor for the hairlines

# Brand palette
BG      = (11, 13, 16)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)

DIM   = (112, 119, 130)
GREY  = (150, 157, 168)
BODY  = (219, 223, 229)
HOT   = (233, 175, 116)          # amber, pulled back so it sits in the text

M = 96            # side margin, ~9% in from every edge

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


def ground(glow_box, strength=106):
    """
    Near-black with one soft warm bloom, so the amber has somewhere to sit
    instead of floating on flat black.
    """
    img = Image.new("RGB", (S, S), BG)
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse(glow_box, fill=strength)
    glow = glow.filter(ImageFilter.GaussianBlur(170))
    return Image.composite(Image.new("RGB", (S, S), (92, 56, 22)), img, glow)


def hairlines(img, ys):
    """Rules drawn at 3x and downscaled, so they land soft rather than wiry."""
    rules = Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rules)
    for y in ys:
        rd.line([(M * SS, y * SS), ((S - M) * SS, y * SS)],
                fill=(255, 255, 255, 26), width=SS)
    return Image.alpha_composite(img.convert("RGBA"),
                                 rules.resize((S, S), Image.LANCZOS)).convert("RGB")


def runs(d, x, y, segments, f):
    """Draw coloured runs of text along one baseline and return the end x."""
    for text, colour in segments:
        d.text((x, y), text, font=f, fill=colour, anchor="lm")
        x += d.textlength(text, font=f)
    return x


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


def signature(img, d):
    """
    The mark beside the domain, centred as one unit at the foot of the frame.
    Small enough to read as a signature rather than a second focal point, and
    identical every week.
    """
    f_url = font(24, "Semibold", ARIAL_B)
    mk, gap, t = 36, 11, "nabbly.co"
    x0 = (S - (mk + gap + d.textlength(t, font=f_url))) / 2
    y = S * 0.949
    mark = nabbly_mark(mk)
    img.paste(mark, (int(x0), int(y - mk / 2)), mark)
    d.text((x0 + mk + gap, y), t, font=f_url, fill=(190, 140, 92), anchor="lm")


# ===========================================================================
# Week 7 — five fields, one feed
#
# Each posting is written the way it would arrive on the board: the title as a
# person would read it, the field under it in the smaller grey. Nothing is
# highlighted among the five, because the argument is the set and not a member
# of it. The distance between a telehealth shift and a product spot is the
# whole picture.
# ===========================================================================
OPEN = "All of this posted before lunch."

POSTINGS = [
    ("Registered nurse, weekend telehealth shifts", "Healthcare / medical"),
    ("Motion designer for a 30 second product spot", "Video / animation"),
    ("Bookkeeper, monthly close for two entities",   "Finance / accounting"),
    ("German to English subtitler, six episodes",    "Translation / language"),
    ("Interior renders for a four unit remodel",     "Architecture / 3D"),
]

# The turn. The floor is deliberate: 24 fields today and the number only grows,
# so the picture stays true long after the week it goes up.
CLOSE = [("More than 20 fields.  ", (198, 203, 211)), ("One feed.", HOT)]


def week_seven():
    # The bloom sits low and wide, under the last postings and behind the turn,
    # so the frame warms as it falls toward the amber rather than glowing at
    # the top where there is nothing to light.
    img = ground([M - 220, 640, S - M + 60, 960], strength=118)
    img = hairlines(img, (232, 858))
    d = ImageDraw.Draw(img)

    f_open = font(30, "Regular", ARIAL)
    f_gig = font(36, "Semibold")
    f_field = font(24, "Regular", ARIAL)
    f_close = font(38, "Semibold")

    # The frame for the list, set quietly so it reads as the caption to the
    # five postings rather than as a headline over them.
    d.text((M, 176), OPEN, font=f_open, fill=GREY, anchor="lm")

    # The five. Even weight and even pitch on purpose: no entry wins, the range
    # between them is what carries.
    # The field sits close under its title and the next posting sits well clear
    # of it, so each pair reads as one block rather than as ten loose lines.
    y = 296
    for title, field in POSTINGS:
        d.text((M, y), title, font=f_gig, fill=(210, 215, 222), anchor="lm")
        d.text((M, y + 38), field, font=f_field, fill=DIM, anchor="lm")
        y += 118

    runs(d, M, 906, CLOSE, f_close)

    signature(img, d)
    return img, OUT / "week-07-one-feed.png"


if __name__ == "__main__":
    for render in (week_seven,):
        im, path = render()
        im.save(path, "PNG", optimize=True)
        print("wrote", path, im.size)

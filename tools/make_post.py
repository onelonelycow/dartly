"""
make_post.py — the weekly social image for @nabbly.co.

  brand/posts/week-06-seven-hours-apart.png
      One real gig posting, then the two people who found it. Maya at 9:06am,
      four minutes after it went up. Sam at 4:41pm, seven hours after. Same
      posting, same field, same day; the only variable on the canvas is the
      hour each of them found out. It closes on the turn that makes the point:
      Maya was not faster, Maya just knew first.

Editorial and text-first, in the spirit of week 4 — real times and a real field
on the canvas rather than a shape standing in for the idea. Structurally it is
its own piece: a single posting with two readers under it, not the radar sweep
(week 1), the field of gig cards (week 2), the pack of racing trails (week 3),
the timestamped rail down the day (week 4) or the dated shipping list (week 5).

Only two things carry amber: the 9:06 am timestamp and the closing half-line.
Sam's whole entry is dimmed a step, so the contrast between the two entries is
the composition rather than a second highlight.

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

# The late entry, dimmed a step below its neighbours so the two entries read as
# near and far without spending a second accent colour on the difference.
LATE      = (124, 131, 142)
LATE_NOTE = (90, 96, 106)

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
# Week 6 — the same gig, seven hours apart
#
# The posting sits at the top the way it would on the board: the title, then
# the field and the minute it went up. Everything under the rule is just the
# two people who found it, written as plainly as the posting itself.
# ===========================================================================
GIG = "Technical writer, API documentation"
META = "Writing / content  ·  posted 9:02 am"

# Only the 9:06 carries the accent. The rest of both entries is set in greys so
# the eye lands on the timestamp and then reads down into the gap underneath.
EARLY = [("Maya saw it at ", BODY), ("9:06 am", HOT)]
EARLY_NOTE = "Four minutes after it posted."

LATE_LINE = [("Sam saw it at ", LATE), ("4:41 pm", LATE)]
LATE_NOTE_TEXT = "Seven hours after it posted."

# The turn. The value is not speed, it is the hour you find out, and saying so
# in two short beats lands it without a claim that needs a number behind it.
CLOSE = [
    ("Maya was not faster.", (198, 203, 211)),
    ("Maya just knew first.", (219, 158, 96)),
]


def week_six():
    # The bloom sits behind Maya's line, low and wide, so the amber timestamp
    # has warmth under it and the frame still falls away toward Sam.
    img = ground([M - 210, 310, S - M + 40, 570], strength=104)
    img = hairlines(img, (312, 768))
    d = ImageDraw.Draw(img)

    # The posting is context, not the headline, so it is set a step smaller and
    # a step duller than the two entries under it. At full weight it read as
    # the message of the frame and the point underneath lost the argument.
    f_gig = font(38, "Semibold")
    f_meta = font(25, "Regular", ARIAL)
    f_line = font(40, "Regular", ARIAL)
    f_note = font(26, "Regular", ARIAL)
    f_close = font(38, "Semibold")

    # The posting.
    d.text((M, 196), GIG, font=f_gig, fill=(176, 182, 191), anchor="lm")
    d.text((M, 246), META, font=f_meta, fill=DIM, anchor="lm")

    # The two people who found it, near entry first.
    runs(d, M, 442, EARLY, f_line)
    d.text((M, 492), EARLY_NOTE, font=f_note, fill=(138, 128, 118), anchor="lm")

    runs(d, M, 620, LATE_LINE, f_line)
    d.text((M, 670), LATE_NOTE_TEXT, font=f_note, fill=LATE_NOTE, anchor="lm")

    # The turn.
    cy = 846
    for text, colour in CLOSE:
        d.text((M, cy), text, font=f_close, fill=colour, anchor="lm")
        cy += 52

    signature(img, d)
    return img, OUT / "week-06-seven-hours-apart.png"


if __name__ == "__main__":
    for render in (week_six,):
        im, path = render()
        im.save(path, "PNG", optimize=True)
        print("wrote", path, im.size)

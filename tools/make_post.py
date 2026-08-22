"""
make_post.py — the weekly social image for @nabbly.co.

This week is a two card post about the new draft-voice controls, plus one
spare single that can go up later in the week.

  brand/posts/week-05-voice-carousel/01-draft.png
      The hook. A real gig, the reply Nabbly drafted for it, and the four
      settings that produced it. The clause the writer told Nabbly to always
      work in is the only thing lit, and it appears a second time beside the
      Include label, so the amber in the body and the amber in the footer
      rhyme and the causality reads without an arrow. Self-contained, because
      most people never swipe.

  brand/posts/week-05-voice-carousel/02-controls.png
      The explanation, for the people who do. The same four labels, this time
      with what each one actually controls, closing on the value from card one
      so the pair ties back together.

  brand/posts/week-05-shipped.png
      Spare single: the week as a dated shipping list, newest first, with the
      draft-voice line lit.

Card one carries a small page number and card two carries the lockup, which is
how the August carousels in brand/posts/ are signed.

Both cards are editorial and text-first, so they read as different pieces from
the radar sweep (week 1), the field of gig cards (week 2), the pack of racing
trails (week 3) and the timestamped rail down the day (week 4).

Run:  .venv/bin/python tools/make_post.py

Each week this file gets rewritten with a NEW visual idea rather than a new seed
of the same one — the point is a fresh piece, not a recolour. Git history keeps
the previous weeks' generators.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts"
CAR = OUT / "week-05-draft-voice"
CAR.mkdir(parents=True, exist_ok=True)

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
    identical every week. Carousels carry it on the last card only.
    """
    f_url = font(24, "Semibold", ARIAL_B)
    mk, gap, t = 36, 11, "nabbly.co"
    x0 = (S - (mk + gap + d.textlength(t, font=f_url))) / 2
    y = S * 0.949
    mark = nabbly_mark(mk)
    img.paste(mark, (int(x0), int(y - mk / 2)), mark)
    d.text((x0 + mk + gap, y), t, font=f_url, fill=(190, 140, 92), anchor="lm")


def page_number(d, n, total):
    """How the August carousels number their inner cards."""
    d.text((S / 2, S * 0.941), f"{n} / {total}", font=font(24, "Semibold", ARIAL_B),
           fill=(104, 111, 122), anchor="mm")


# ===========================================================================
# Card 1 — the announcement cover
#
# Built to the format the August covers already use: the mark glowing at the
# top, a white line over an amber line, one grey line under, and the lockup.
# ===========================================================================
COVER = [("Introducing", BODY), ("Draft Voice.", (214, 152, 88))]
COVER_SUB = "Your replies, the way you write them."
# The tier line lives in the caption, not on the card.


def card_cover():
    img = Image.new("RGB", (S, S), BG)

    # The bloom behind the mark, then the mark itself.
    cx, cy, r = S // 2, 350, 106
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse([cx - r, cy - r, cx + r, cy + r], fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img = Image.composite(Image.new("RGB", (S, S), (146, 84, 26)), img, glow)

    mk = 148
    mark = nabbly_mark(mk)
    img.paste(mark, (cx - mk // 2, cy - mk // 2), mark)

    d = ImageDraw.Draw(img)
    f_h = font(58, "Semibold")
    f_sub = font(27, "Regular", ARIAL)

    for i, (text, colour) in enumerate(COVER):
        d.text((S * 0.5, 728 + i * 68), text, font=f_h, fill=colour, anchor="mm")
    d.text((S * 0.5, 871), COVER_SUB, font=f_sub, fill=(126, 133, 143),
           anchor="mm")

    signature(img, d)
    return img, CAR / "01-introducing.png"


# ===========================================================================
# Card 2 — the draft, and the settings behind it
# ===========================================================================
GIG = "Brand identity for a healthcare startup"
META = "Design / creative  ·  posted 4 minutes ago"

DRAFT = [
    [("Hi Maya, I can take this on.", BODY)],
    [("I've spent ", BODY), ("ten years on brand identity", HOT), (",", BODY)],
    [("and healthcare brands are most of it.", BODY)],
    [("Happy to send two directions this week.", BODY)],
]
SIGN = "Alex"

CLAIM = "Alex set four things, once."

# Two columns, because the split between the control and the value Alex typed
# is what the block is for, and a dim label beside a lighter value shows it
# without spending any amber. The draft's lit clause stays the only warm thing
# on the card; an amber value column was tried and read as too much orange.
SETTINGS = [
    ("Length", "Standard"),
    ("Include", "ten years on brand identity"),
    ("Avoid", "hourly rates"),
    ("Signature", "Alex"),
]


def card_draft():
    img = ground([M - 190, 300, S - M + 60, 580])
    img = hairlines(img, (240, 678))
    d = ImageDraw.Draw(img)

    f_gig = font(33, "Semibold")
    f_meta = font(25, "Regular", ARIAL)
    f_body = font(40, "Regular", ARIAL)
    f_claim = font(29, "Semibold")
    f_lbl = font(23, "Semibold")
    f_val = font(23, "Regular", ARIAL)

    # The gig being replied to, so the draft has something to be a reply to.
    d.text((M, 152), GIG, font=f_gig, fill=(139, 146, 157), anchor="lm")
    d.text((M, 196), META, font=f_meta, fill=DIM, anchor="lm")

    # The draft. Runs, so the configured clause carries the accent mid-line.
    y = 318
    for line in DRAFT:
        runs(d, M, y, line, f_body)
        y += 65
    d.text((M, y + 27), SIGN, font=f_body, fill=BODY, anchor="lm")

    # Below the rule: what the feature is, then the settings behind the draft.
    d.text((M, 722), CLAIM, font=f_claim, fill=(198, 203, 211), anchor="lm")
    ry = 786
    for label, value in SETTINGS:
        d.text((M, ry), label, font=f_lbl, fill=(99, 106, 116), anchor="lm")
        d.text((M + 132, ry), value, font=f_val, fill=GREY, anchor="lm")
        ry += 40

    signature(img, d)
    return img, CAR / "02-in-action.png"


# ===========================================================================
# Card 2 — what each of the four settings actually controls
# ===========================================================================
CONTROLS_TITLE = "Four settings, set once."

CONTROLS = [
    ("Length", "Brief, Standard or Detailed"),
    ("Include", "one line it always works in"),
    ("Avoid", "what it never brings up"),
    ("Signature", "how you sign off"),
]

# Closes on the value from card one, so the pair ties back together.
TIE = [
    [("Alex set Include to ", GREY), ("ten years on brand identity", HOT),
     (".", GREY)],
    [("Every draft says it.", GREY)],
]


def card_controls():
    img = ground([M - 190, 320, S - M + 60, 560], strength=100)
    img = hairlines(img, (272, 790))
    d = ImageDraw.Draw(img)

    f_ttl = font(44, "Semibold")
    f_lbl = font(28, "Semibold")
    f_val = font(35, "Regular", ARIAL)
    f_tie = font(26, "Regular", ARIAL)

    d.text((M, 206), CONTROLS_TITLE, font=f_ttl, fill=BODY, anchor="lm")

    ry = 375
    for label, value in CONTROLS:
        d.text((M, ry), label, font=f_lbl, fill=(103, 110, 121), anchor="lm")
        d.text((M + 186, ry), value, font=f_val, fill=GREY, anchor="lm")
        ry += 100

    ty = 848
    for line in TIE:
        runs(d, M, ty, line, f_tie)
        ty += 42

    signature(img, d)
    return img, CAR / "02-controls.png"


# ===========================================================================
# Spare single — the week as a shipping list
# ===========================================================================
SHIPPED_TITLE = "New on Nabbly this week"

# Newest first, so the lit line sits high in the frame. Every one of these is a
# real dated change; check git before editing the dates.
SHIPPED = [
    ("Aug 18", "You set how every draft reads", True),
    ("Aug 17", "The board works on a phone", False),
    ("Aug 17", "Alerts back off instead of nagging", False),
    ("Aug 16", "Sign in with Google", False),
    ("Aug 14", "Draft my reply, on every gig", False),
]

SHIPPED_CLOSER = "All of it is live now."


def single_shipped():
    img = ground([M - 190, 300, S - M + 60, 500], strength=100)
    img = hairlines(img, (272, 848))
    d = ImageDraw.Draw(img)

    f_ttl = font(44, "Semibold")
    f_date = font(25, "Semibold")
    f_item = font(35, "Regular", ARIAL)
    f_note = font(26, "Regular", ARIAL)

    d.text((M, 206), SHIPPED_TITLE, font=f_ttl, fill=BODY, anchor="lm")

    # The dates stay uniform so the one amber line is the only emphasis.
    ry = 375
    for date, item, lit in SHIPPED:
        d.text((M, ry), date, font=f_date, fill=(99, 106, 116), anchor="lm")
        d.text((M + 150, ry), item, font=f_item,
               fill=HOT if lit else GREY, anchor="lm")
        ry += 100

    d.text((M, 898), SHIPPED_CLOSER, font=f_note, fill=(130, 137, 148),
           anchor="lm")

    signature(img, d)
    return img, OUT / "week-05-shipped.png"


if __name__ == "__main__":
    for render in (card_cover, card_draft, single_shipped):
        im, path = render()
        im.save(path, "PNG", optimize=True)
        print("wrote", path, im.size)

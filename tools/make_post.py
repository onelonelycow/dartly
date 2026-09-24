"""
make_post.py — the weekly social image for @nabbly.co.

  brand/posts/week-08-place-the-bid.png
      The bid panel from a gig's draft page, drawn as it appears: the gig, the
      client's budget and the bids so far as Freelancer reports them, the
      member's own bids left for the month, price and days to deliver, and
      one button. The headline says what the page now does; the panel shows
      it with the real numbers a bid needs.

Editorial and text-first, in the spirit of weeks 4, 6 and 7 — the content on
the canvas is what a member would actually read, not a shape standing in for
the idea. Structurally new: the first week built around a control rather than
a list or a pair. The single accent is the Place bid button; the headline's
second line is amber pulled well back so it points at the button rather than
competing with it.

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
# Week 8 — draft the reply, then place the bid
#
# The panel is the one on the draft page, set at poster scale. Every number in
# it is the kind the page reads live before it draws the form: the client's
# budget, how many bids are already in, how many the member has left. The
# price is pre-filled with the budget floor the way the real form does it.
# ===========================================================================
HEAD = [("Draft the reply,", BODY), ("then place the bid.", HOT)]

GIG = "Landing page rewrite for a B2B analytics tool"
PILLS = ["Copywriting", "Fixed price", "posted 3 min ago"]

PANEL_H = "Bid on Freelancer"
PANEL_WHO = "as maya_writes"
LIVE_1 = "Client's budget $250 to $500 USD  \u00b7  9 bids so far"
LIVE_2 = "41 bids left on your account this month"

FIELDS = [("Your price (USD)", "250"), ("Days to deliver", "5")]
BUTTON = "Place bid"
HINT = "Sends the draft above as your proposal. You can retract it here afterwards."

PANEL = (18, 20, 25)       # a shade up from the ground, like the app's panel
INPUT = (12, 14, 18)       # the input wells sit back into the ground
LINE = (255, 255, 255, 30)


def rounded_layer(box, radius, fill=None, outline=None, width=1):
    """A rounded rectangle drawn at 3x and downscaled so the corners are clean."""
    layer = Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [v * SS for v in box], radius=radius * SS, fill=fill, outline=outline,
        width=width * SS)
    return layer.resize((S, S), Image.LANCZOS)


def over(img, layer):
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def week_eight():
    # The bloom sits behind the panel's lower half, under the button, so the
    # warmth gathers where the eye is meant to land.
    img = ground([M - 160, 574, S - M + 160, 914], strength=112)

    f_head = font(54, "Semibold")
    f_gig = font(33, "Semibold")
    f_pill = font(20, "Regular", ARIAL)
    f_ph = font(27, "Semibold")
    f_who = font(21, "Regular", ARIAL)
    f_live = font(23, "Regular", ARIAL)
    f_lab = font(20, "Regular", ARIAL)
    f_val = font(28, "Semibold")
    f_btn = font(24, "Semibold")
    f_hint = font(20, "Regular", ARIAL)

    # The panel. Padding inside it is generous so the numbers have air.
    px0, py0, px1, py1 = M, 332, S - M, 886
    pad = 44
    img = over(img, rounded_layer((px0, py0, px1, py1), 22, fill=PANEL + (255,),
                                  outline=LINE, width=1))
    d = ImageDraw.Draw(img)

    # Headline: two lines, the second in the pulled-back amber.
    d.text((M, 164), HEAD[0][0], font=f_head, fill=HEAD[0][1], anchor="lm")
    d.text((M, 230), HEAD[1][0], font=f_head, fill=HEAD[1][1], anchor="lm")

    # The gig, as it reads at the top of the draft page.
    x, y = px0 + pad, py0 + pad + 16
    d.text((x, y), GIG, font=f_gig, fill=(214, 218, 225), anchor="lm")

    # Pills under it: outline only, so they read as labels and not buttons.
    y += 56
    cx = x
    for text in PILLS:
        w = d.textlength(text, font=f_pill)
        box = (cx, y - 17, cx + w + 28, y + 17)
        img = over(img, rounded_layer(box, 17, outline=(255, 255, 255, 34), width=1))
        d = ImageDraw.Draw(img)
        d.text((cx + 14, y), text, font=f_pill, fill=GREY, anchor="lm")
        cx += w + 28 + 12

    # Rule between the gig and the bid.
    y += 52
    d.line([(px0 + pad, y), (px1 - pad, y)], fill=(34, 37, 43), width=1)

    # The bid panel proper.
    y += 54
    d.text((x, y), PANEL_H, font=f_ph, fill=(228, 231, 236), anchor="lm")
    wx = x + d.textlength(PANEL_H, font=f_ph) + 14
    d.text((wx, y), PANEL_WHO, font=f_who, fill=DIM, anchor="lm")

    # The live numbers. Two lines rather than one long one, so each stays legible.
    y += 48
    d.text((x, y), LIVE_1, font=f_live, fill=(176, 182, 192), anchor="lm")
    y += 36
    d.text((x, y), LIVE_2, font=f_live, fill=(176, 182, 192), anchor="lm")

    # Price, days, button, on one row. The wells are dark and the button is the
    # only filled amber on the canvas.
    y += 60
    well_w, well_h, gap = 196, 62, 22
    cx = x
    for label, val in FIELDS:
        d.text((cx, y), label, font=f_lab, fill=DIM, anchor="lm")
        box = (cx, y + 20, cx + well_w, y + 20 + well_h)
        img = over(img, rounded_layer(box, 12, fill=INPUT + (255,),
                                      outline=(255, 255, 255, 38), width=1))
        d = ImageDraw.Draw(img)
        d.text((cx + 18, y + 20 + well_h / 2), val, font=f_val,
               fill=(228, 231, 236), anchor="lm")
        cx += well_w + gap
    bw = d.textlength(BUTTON, font=f_btn) + 56
    box = (cx, y + 20, cx + bw, y + 20 + well_h)
    img = over(img, rounded_layer(box, 12, fill=AMBER + (255,)))
    d = ImageDraw.Draw(img)
    d.text((cx + bw / 2, y + 20 + well_h / 2), BUTTON, font=f_btn,
           fill=(27, 18, 5), anchor="mm")

    # The line under the form, as the page says it.
    y += 20 + well_h + 40
    d.text((x, y), HINT, font=f_hint, fill=DIM, anchor="lm")

    signature(img, d)
    return img, OUT / "week-08-place-the-bid.png"


if __name__ == "__main__":
    for render in (week_eight,):
        im, path = render()
        im.save(path, "PNG", optimize=True)
        print("wrote", path, im.size)

"""
make_nextnw_post.py — the co-branded square for the Nabbly x NextNW partnership.

Same 1080x1080 format and the same restraint as the weekly posts, but built on
the shared ground from site/nextnw.html: Nabbly's near-black pulled a few
degrees green (#0E1613) so NextNW's forest sits on it without looking pasted on.

Written for the whole audience, not for NextNW. Someone scrolling past has
never heard of them, so the headline states the partnership plainly and the
sub line says what it amounts to. The full name is used in the headline where
the marks above show the short one, so the abbreviation explains itself and the
sentence carries more weight.

Two variants come out of the same layout, differing only in that sub line:

  nextnw-collab.png       "Every member now gets Nabbly Pro."
      The scale of the deal. Impressive, but it hands something to a closed
      group that a passing reader cannot have.

  nextnw-collab-open.png  "Every gig, the moment it drops. Free to join."
      Same proof, open door. The partnership is the credibility, and the line
      underneath is the brand's own tagline followed by the one fact a stranger
      needs. Nothing in the frame is reserved for members. Signs off at
      nabbly.co rather than the partnership page, because the job of this one
      is a signup rather than a read.

Run:  .venv/bin/python tools/make_nextnw_post.py
Out:  brand/posts/nextnw-collab.png, brand/posts/nextnw-collab-open.png
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts"
OUT.mkdir(parents=True, exist_ok=True)

S = 1080

# Nabbly
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)
# Next Northwest, sampled from nextnw.org via site/nextnw.html
NW_GREEN  = (84, 185, 90)
# the shared ground
BG   = (14, 22, 19)
INK  = (242, 245, 243)

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


DISC_Y = 0.395
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S


def field(cx, cy, r, colour, peak):
    d = ((xx - cx) / r) ** 2 + ((yy - cy) / r) ** 2
    return (np.exp(-d * 1.35) * peak)[..., None] * np.array(colour, np.float32)


def render(head1, head2, sub, url, out_name):
    # -----------------------------------------------------------------------
    # 1. The ground: two discs rather than one wash. Tight enough to read as
    #    two separate lights, close enough that they overlap in the middle.
    #    That overlap is the whole idea of the piece, and it fills the upper
    #    half so the marks are not marooned in empty space. Peaks stay low so
    #    the ground is still near-black like every other post. Green needs
    #    more than amber to read at all on a green-shifted ground.
    # -----------------------------------------------------------------------
    canvas = np.zeros((S, S, 3), np.float32)
    canvas[:] = BG
    canvas += field(0.330, DISC_Y, 0.235, AMBER, 0.165)
    canvas += field(0.670, DISC_Y, 0.235, NW_GREEN, 0.215)
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img, "RGBA")

    # -----------------------------------------------------------------------
    # 2. The two marks, each at the centre of its own disc with its name under
    #    it, so the overlap does the work a divider would. Their glyph is used
    #    unaltered — their exact white, background removed — the same treatment
    #    the site header gives it. Neither logo is subordinate.
    # -----------------------------------------------------------------------
    MARK = 84
    f_lk = font(34, "Semibold")

    nw = Image.open(ROOT / "site" / "nextnw-icon.png").convert("RGBA")
    nw_h = 78      # their glyph has no square container, so it is set a shade
    nw_w = round(nw.width * nw_h / nw.height)      # smaller to match optically
    nw = nw.resize((nw_w, nw_h), Image.LANCZOS)

    LX, RX = S * 0.330, S * 0.670
    MARK_Y = S * (DISC_Y - 0.026)   # sits a touch high, name balances under it
    NAME_Y = S * (DISC_Y + 0.062)

    mark = nabbly_mark(MARK)
    img.paste(mark, (int(LX - MARK / 2), int(MARK_Y - MARK / 2)), mark)
    d.text((LX, NAME_Y), "Nabbly", font=f_lk, fill=INK, anchor="mm")

    img.paste(nw, (int(RX - nw_w / 2), int(MARK_Y - nw_h / 2)), nw)
    d.text((RX, NAME_Y), "NextNW", font=f_lk, fill=INK, anchor="mm")

    # -----------------------------------------------------------------------
    # 3. Type
    # -----------------------------------------------------------------------
    f_h = font(56, "Semibold")
    f_sub = font(25, "Regular", ARIAL)
    f_url = font(23, "Semibold", ARIAL_B)
    SOFT_AMBER = (214, 152, 88)

    # Signed, stated plainly. The accent stays Nabbly amber — green already
    # owns half the field behind the marks, and giving it the headline too
    # tipped the whole square green.
    d.text((S * 0.5, S * 0.715), head1, font=f_h,
           fill=(228, 234, 230), anchor="mm")
    d.text((S * 0.5, S * 0.780), head2, font=f_h,
           fill=SOFT_AMBER, anchor="mm")
    d.text((S * 0.5, S * 0.842), sub, font=f_sub, fill=(150, 170, 159),
           anchor="mm")

    # nothing meaningful should come within 5% of an edge; shout if a longer
    # wording ever pushes a headline out past that
    for line in (head1, head2):
        if d.textlength(line, font=f_h) > S * 0.90:
            raise SystemExit(f"headline too wide for the frame: {line!r}")

    # Sign-off lockup, the same signature the weekly posts carry
    MK, G2 = 34, 11
    tw = d.textlength(url, font=f_url)
    x0 = (S - (MK + G2 + tw)) / 2
    y = S * 0.932
    sig = nabbly_mark(MK)
    img.paste(sig, (int(x0), int(y - MK / 2)), sig)
    d.text((x0 + MK + G2, y), url, font=f_url, fill=(190, 150, 108), anchor="lm")

    path = OUT / out_name
    img.save(path, "PNG", optimize=True)
    print("wrote", path, img.size)


TAGLINE = "Every gig, the moment it drops. Free to join."

# The chosen headline. Plain past tense states it as accomplished fact without
# needing "officially" to prop it up, and the full name reads more substantial
# than the abbreviation the marks above already carry.
#
# Wordings that were considered and passed over, kept here so any of them is a
# one-line change rather than a rewrite:
#   "Officially partnered"  / "with Next Northwest."
#   "Nabbly is officially"  / "partnered with NextNW."
HEAD1, HEAD2 = "Nabbly has partnered", "with Next Northwest."

# The public cut. Nothing in the frame is reserved for members, and it signs
# off at the front door because its job is a signup.
render(HEAD1, HEAD2, TAGLINE, "nabbly.co", "nextnw-collab-open.png")

# The members cut, for whatever NextNW sends its own membership. Same square,
# but the sub line names the perk and the link goes to the partnership page.
render(HEAD1, HEAD2, "Every member now gets Nabbly Pro.", "nabbly.co/nextnw",
       "nextnw-collab.png")

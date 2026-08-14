"""
make_carousel.py — the monthly "what shipped" carousel for @nabbly.co.

A changelog is a bad single square and a good carousel: a list has no focal
point, but give each item its own slide and each one gets a picture that
carries it. Six 1080x1080 slides, posted in order.

Split across two posts rather than one, because four features is a long swipe
and the two halves argue different things:

  1-personal/  the board learns you — ranking by rating, then by resume
  2-access/    less locked          — free drafts, inbox forwarding, home screen

FEEL.md 7 forbids advertising sources: no board names, no source counts. A
"forty sources" slide was built and cut for exactly that reason. Provenance is
plumbing; what the reader gets is the post.

Slide 1 carries the usual signature because it is the one that shows in the
grid; slide 6 carries it because it is the call to action. The slides between
get a quiet counter instead, so the signature does not repeat six times.

Every claim here was read off the commits it describes, not remembered.

Run:  .venv/bin/python tools/make_carousel.py
Out:  brand/posts/aug-carousel-{1-personal,2-access}/*.png
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts"

S = 1080
SS = 3
W = S * SS

BG      = (11, 13, 16)
AMBER   = (232, 147, 58)
AMBER_L = (247, 181, 105)
SOFT_AMBER = (214, 152, 88)
CARD    = (19, 21, 25, 255)
EDGE    = (255, 255, 255, 15)
BAR_HI  = (108, 114, 123, 132)
BAR_LO  = (108, 114, 123, 76)

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


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


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


def slide(art, head, body, out_dir, out_name, step=None, sign=False, mark_px=None):
    """
    art  — callable(layer_draw, glow_draw, layer) drawing into the supersampled
           canvas, or None for a type-only slide
    head — one or two lines; the second is set in amber
    body — up to two descriptive lines, set small and muted
    """
    img = Image.new("RGB", (W, W), BG).convert("RGBA")
    if art:
        layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        art(ImageDraw.Draw(layer), ImageDraw.Draw(glow), layer)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=24 * SS))
        img = Image.alpha_composite(img, glow)
        img = Image.alpha_composite(img, layer)
    img = img.convert("RGB").resize((S, S), Image.LANCZOS)
    d = ImageDraw.Draw(img)

    f_h = font(54, "Semibold")
    f_b = font(25, "Regular", ARIAL)
    f_u = font(24, "Semibold", ARIAL_B)
    f_c = font(20, "Semibold", ARIAL_B)

    if mark_px:          # the bookend slides carry the mark as their artwork
        m = nabbly_mark(mark_px)
        img.paste(m, (int((S - mark_px) / 2), int(S * 0.325 - mark_px / 2)), m)

    hy = 0.672 if len(head) > 1 else 0.700
    d.text((S * 0.5, S * hy), head[0], font=f_h, fill=(226, 229, 234), anchor="mm")
    if len(head) > 1:
        d.text((S * 0.5, S * (hy + 0.064)), head[1], font=f_h, fill=SOFT_AMBER,
               anchor="mm")

    by = (hy + 0.064 * (len(head) - 1)) + 0.070
    for n, line in enumerate(body):
        d.text((S * 0.5, S * (by + n * 0.046)), line, font=f_b,
               fill=(132, 139, 149), anchor="mm")

    if sign:
        MK, GAP = 36, 11
        t = "nabbly.co"
        tw = d.textlength(t, font=f_u)
        x0 = (S - (MK + GAP + tw)) / 2
        y = S * 0.940
        m = nabbly_mark(MK)
        img.paste(m, (int(x0), int(y - MK / 2)), m)
        d.text((x0 + MK + GAP, y), t, font=f_u, fill=(190, 140, 92), anchor="lm")
    elif step:
        d.text((S * 0.5, S * 0.940), step, font=f_c, fill=(92, 98, 108), anchor="mm")

    (OUT / out_dir).mkdir(parents=True, exist_ok=True)
    path = OUT / out_dir / out_name
    img.save(path, "PNG", optimize=True)
    print("wrote", path)


def halo(gd, cy=0.325, r=0.135, a=88):
    gd.ellipse([W * (0.5 - r), W * (cy - r), W * (0.5 + r), W * (cy + r)],
               fill=(232, 147, 58, a))


def row(ld, x0, x1, y0, h, hot=False, bar2=True):
    """One gig row: a pip, a long bar and a short one. The feed's basic unit."""
    fill = tuple(int(c) for c in lerp(BG, AMBER, 0.17)) + (255,) if hot else CARD
    edge = (247, 181, 105, 205) if hot else EDGE
    ew = max(1, int((1.8 if hot else 1.0) * SS))
    ld.rounded_rectangle([x0, y0, x1, y0 + h], radius=h * 0.26, fill=fill,
                         outline=edge, width=ew)
    pr = h * 0.115
    px, py = x0 + h * 0.42, y0 + h / 2
    ld.ellipse([px - pr, py - pr, px + pr, py + pr],
               fill=(250, 214, 170, 245) if hot else (92, 98, 107, 150))
    bx = x0 + h * 0.85
    ld.rounded_rectangle([bx, y0 + h * 0.30, bx + (x1 - x0) * 0.42, y0 + h * 0.40],
                         radius=h * 0.05,
                         fill=(252, 232, 208, 235) if hot else BAR_HI)
    if bar2:
        ld.rounded_rectangle([bx, y0 + h * 0.56, bx + (x1 - x0) * 0.25,
                              y0 + h * 0.645], radius=h * 0.05,
                             fill=(238, 187, 130, 165) if hot else BAR_LO)


# --- 02 ranking learns -----------------------------------------------------
def art_learns(ld, gd, _):
    X0, X1 = W * 0.215, W * 0.785
    top, h, gap = W * 0.150, W * 0.058, W * 0.023
    for k in range(1, 4):                    # the warmth it left behind
        y = top + k * (h + gap)
        gd.rounded_rectangle([X0, y, X1, y + h], radius=h * 0.26,
                             fill=(232, 147, 58, int(46 * (1 - (k - 1) / 3.2))))
    for r in range(6):
        row(ld, X0, X1, top + r * (h + gap), h, hot=(r == 0))
    gd.rounded_rectangle([X0 - h * 0.5, top - h * 0.5, X1 + h * 0.5, top + h * 1.5],
                         radius=h, fill=(232, 147, 58, 52))


# --- 03 scored against your resume -----------------------------------------
def art_resume(ld, gd, _):
    # the resume on the left, a gig on the right, and the overlap lit between
    RX0, RX1 = W * 0.155, W * 0.415
    RY0, RY1 = W * 0.140, W * 0.520
    ld.rounded_rectangle([RX0, RY0, RX1, RY1], radius=W * 0.018, fill=CARD,
                         outline=EDGE, width=max(1, int(1.0 * SS)))
    hit_rows = {2, 5, 8}
    ys = []
    for i in range(11):
        y = RY0 + W * 0.045 + i * W * 0.030
        wfrac = 0.74 if i % 3 else 0.52
        hot = i in hit_rows
        ld.rounded_rectangle([RX0 + W * 0.028, y,
                              RX0 + W * 0.028 + (RX1 - RX0 - W * 0.056) * wfrac,
                              y + W * 0.0105], radius=W * 0.005,
                             fill=(247, 200, 148, 225) if hot else BAR_LO)
        if hot:
            ys.append(y + W * 0.005)

    GX0, GX1 = W * 0.585, W * 0.845
    gh = W * 0.058
    gy = W * 0.290
    row(ld, GX0, GX1, gy, gh, hot=True)
    row(ld, GX0, GX1, gy - gh - W * 0.023, gh)
    row(ld, GX0, GX1, gy + gh + W * 0.023, gh)
    gd.rounded_rectangle([GX0 - gh * 0.5, gy - gh * 0.5, GX1 + gh * 0.5,
                          gy + gh * 1.5], radius=gh, fill=(232, 147, 58, 58))

    # the connectors, thin and warm, fanning into the one row that matched
    for y in ys:
        steps = 200
        for s_i in range(steps + 1):
            t = s_i / steps
            x = RX1 + (GX0 - RX1) * t
            yy = y + (gy + gh / 2 - y) * (t * t * (3 - 2 * t))   # smoothstep
            a = int(150 * math.sin(math.pi * t) ** 0.6)
            r = 1.3 * SS
            ld.ellipse([x - r, yy - r, x + r, yy + r], fill=(238, 176, 112, a))


# --- 04 the draft came out from behind Pro ---------------------------------
def art_draft(ld, gd, _):
    X0, X1 = W * 0.180, W * 0.820
    Y0, Y1 = W * 0.150, W * 0.520
    gd.rounded_rectangle([X0, Y0, X1, Y1], radius=W * 0.02, fill=(232, 147, 58, 44))
    ld.rounded_rectangle([X0, Y0, X1, Y1], radius=W * 0.02,
                         fill=tuple(int(c) for c in lerp(BG, AMBER, 0.07)) + (255,),
                         outline=(247, 181, 105, 150), width=max(1, int(1.6 * SS)))
    # the quote rule that marks it as written text
    ld.rounded_rectangle([X0 + W * 0.040, Y0 + W * 0.048,
                          X0 + W * 0.040 + W * 0.006, Y1 - W * 0.048],
                         radius=W * 0.003, fill=(238, 176, 112, 210))
    tx = X0 + W * 0.072
    widths = [0.80, 0.92, 0.86, 0.64, 0.88, 0.42]
    for i, wf in enumerate(widths):
        y = Y0 + W * 0.058 + i * W * 0.052
        first = i < 2
        ld.rounded_rectangle([tx, y, tx + (X1 - tx - W * 0.055) * wf, y + W * 0.0135],
                             radius=W * 0.006,
                             fill=(246, 238, 228, 232) if first else (206, 198, 190, 150))


# --- inbox forwarding: one email in, gigs out ------------------------------
def art_forward(ld, gd, _):
    """A forwarded email above, the gigs it was split into below."""
    X0, X1 = W * 0.230, W * 0.770
    EY0, EH = W * 0.145, W * 0.115
    ld.rounded_rectangle([X0, EY0, X1, EY0 + EH], radius=W * 0.014, fill=CARD,
                         outline=EDGE, width=max(1, int(1.0 * SS)))
    # sender, subject, and an excerpt fading out
    ld.rounded_rectangle([X0 + W * 0.030, EY0 + W * 0.022,
                          X0 + W * 0.030 + W * 0.090, EY0 + W * 0.0325],
                         radius=W * 0.005, fill=BAR_HI)
    ld.rounded_rectangle([X0 + W * 0.030, EY0 + W * 0.048,
                          X0 + W * 0.030 + W * 0.200, EY0 + W * 0.0595],
                         radius=W * 0.005, fill=(198, 205, 214, 190))
    for i, wf in enumerate((0.62, 0.40)):
        y = EY0 + W * 0.074 + i * W * 0.019
        ld.rounded_rectangle([X0 + W * 0.030, y,
                              X0 + W * 0.030 + (X1 - X0 - W * 0.06) * wf,
                              y + W * 0.0085], radius=W * 0.004,
                             fill=(108, 114, 123, int(70 - i * 26)))

    # the split: three short amber feeds fanning down into the rows
    gy0 = EY0 + EH + W * 0.052
    h = W * 0.052
    for k in range(3):
        y = gy0 + k * (h + W * 0.020)
        row(ld, X0, X1, y, h, hot=(k == 0))
    gd.rounded_rectangle([X0 - h * 0.5, gy0 - h * 0.5, X1 + h * 0.5,
                          gy0 + h * 1.5], radius=h, fill=(232, 147, 58, 54))
    for k in range(3):
        x = X0 + (X1 - X0) * (0.30 + 0.20 * k)
        steps = 120
        for s_i in range(steps + 1):
            t = s_i / steps
            yy = EY0 + EH + (gy0 - EY0 - EH) * t
            a = int(120 * math.sin(math.pi * t) ** 0.7)
            r_ = 1.2 * SS
            ld.ellipse([x - r_, yy - r_, x + r_, yy + r_], fill=(238, 176, 112, a))


# --- the home screen. A grid of dim app tiles with the real mark lit among
#     them, which is exactly what installing it looks like.
def art_home(ld, gd, layer):
    COLS, ROWS = 4, 3
    ico = W * 0.085
    gx, gy = W * 0.048, W * 0.038
    x0 = (W - (COLS * ico + (COLS - 1) * gx)) / 2
    y0 = W * 0.155
    pitch = ico + gy + W * 0.014
    HOT_C, HOT_R = 1, 1                   # off centre, on a thirds intersection
    for r in range(ROWS):
        for c in range(COLS):
            x, y = x0 + c * (ico + gx), y0 + r * pitch
            if (c, r) == (HOT_C, HOT_R):
                gd.rounded_rectangle([x - ico * 0.45, y - ico * 0.45,
                                      x + ico * 1.45, y + ico * 1.45],
                                     radius=ico, fill=(232, 147, 58, 78))
                m = nabbly_mark(int(ico))
                layer.paste(m, (int(x), int(y)), m)
                lab, lw_ = (238, 214, 186, 225), ico * 0.60
            else:
                ld.rounded_rectangle([x, y, x + ico, y + ico], radius=ico * 0.23,
                                     fill=(23, 26, 31, 255), outline=EDGE,
                                     width=max(1, int(1.0 * SS)))
                lab = (108, 114, 123, 96)
                lw_ = ico * (0.44 + 0.22 * (0.5 + 0.5 * math.sin(r * 3.1 + c * 1.7)))
            ly = y + ico + ico * 0.17      # the name under each icon, as a bar
            ld.rounded_rectangle([x + (ico - lw_) / 2, ly,
                                  x + (ico - lw_) / 2 + lw_, ly + ico * 0.06],
                                 radius=ico * 0.03, fill=lab)


CLOSE = (["Every gig,", "the moment it drops."], ["Free to join."])

# ---------------------------------------------------------------------------
# Post one — the feed learns you. Both slides are about ranking, so they earn
# a post of their own rather than being two of four in a long swipe.
# ---------------------------------------------------------------------------
P1 = "aug-carousel-1-personal"
slide(lambda ld, gd, l: halo(gd), ["The board", "learns from you."],
      ["Two changes to how gigs get ranked."],
      P1, "01-cover.png", sign=True, mark_px=150)
slide(art_learns, ["Rate one gig.", "The board shifts."],
      ["Good match or bad, the ranking takes it.",
       "On every page now, not just the dashboard."],
      P1, "02-learns.png", step="2 / 4")
slide(art_resume, ["It scores gigs", "against your resume."],
      ["Gigs rank on real overlap with what you",
       "actually do. Your resume is never stored."],
      P1, "03-resume.png", step="3 / 4")
slide(lambda ld, gd, l: halo(gd), *CLOSE, P1, "04-close.png",
      sign=True, mark_px=150)

# ---------------------------------------------------------------------------
# Post two — more of it, and less of it locked.
# ---------------------------------------------------------------------------
P2 = "aug-carousel-2-access"
slide(lambda ld, gd, l: halo(gd), ["Three upgrades.", "All in the free tier."],
      ["Shipped in August."],
      P2, "01-cover.png", sign=True, mark_px=150)
slide(art_draft, ["The draft is free now."],
      ["The opening reply used to sit behind Pro.",
       "Everyone gets one."],
      P2, "02-draft.png", step="2 / 5")
slide(art_forward, ["Turn your inbox", "into your board."],
      ["Forward the newsletters you already get.",
       "Nabbly splits them into gigs. Free tier."],
      P2, "03-forwarding.png", step="3 / 5")
slide(art_home, ["It lives on", "your home screen."],
      ["Add nabbly.co to your phone and it opens",
       "straight to your board. No app store."],
      P2, "04-home.png", step="4 / 5")
slide(lambda ld, gd, l: halo(gd), *CLOSE, P2, "05-close.png",
      sign=True, mark_px=150)

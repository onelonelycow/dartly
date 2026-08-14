"""
make_post_options.py — four candidate squares for one week's post.

Throwaway comparison tool, not the weekly generator. It renders the same
1080x1080 format four different ways so a direction can be picked by looking
rather than by describing. Once one wins it gets folded into tools/make_post.py
as that week's real generator and this file can be deleted or rewritten.

  a-learns.png    the match-feedback loop: rate a gig, the feed reorders
  b-homescreen.png  the web app manifest: Nabbly on the phone home screen
  c-roundup.png   a quiet changelog of what shipped this month
  d-speed.png     the comet pack, with depth added to the field

Run:  .venv/bin/python tools/make_post_options.py
Out:  brand/posts/week-03-options/*.png
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts" / "week-03-options"
OUT.mkdir(parents=True, exist_ok=True)

S = 1080
SS = 3
W = S * SS

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


SOFT_AMBER = (214, 152, 88)


def finish(art, head1, head2, sub, out_name, extra=None):
    """Downsample the art, then set every piece of type at final scale."""
    img = art.resize((S, S), Image.LANCZOS)
    d = ImageDraw.Draw(img)

    f_h = font(58, "Semibold")
    f_sub = font(27, "Regular", ARIAL)
    f_url = font(24, "Semibold", ARIAL_B)

    if head1:
        d.text((S * 0.5, S * 0.782), head1, font=f_h, fill=(226, 229, 234),
               anchor="mm")
        d.text((S * 0.5, S * 0.845), head2, font=f_h, fill=SOFT_AMBER, anchor="mm")
    if sub:
        d.text((S * 0.5, S * 0.905), sub, font=f_sub, fill=(126, 133, 143),
               anchor="mm")
    if extra:
        extra(img, d)

    MK, GAP = 36, 11
    t = "nabbly.co"
    tw = d.textlength(t, font=f_url)
    x0 = (S - (MK + GAP + tw)) / 2
    y = S * 0.949
    mark = nabbly_mark(MK)
    img.paste(mark, (int(x0), int(y - MK / 2)), mark)
    d.text((x0 + MK + GAP, y), t, font=f_url, fill=(190, 140, 92), anchor="lm")

    path = OUT / out_name
    img.save(path, "PNG", optimize=True)
    print("wrote", path)


# ---------------------------------------------------------------------------
# A — the ranking learns. A column of rows with one lit amber at the top and a
#     soft vertical streak under it, so it reads as having just climbed there.
# ---------------------------------------------------------------------------
def opt_learns():
    img = Image.new("RGB", (W, W), BG).convert("RGBA")
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)

    X0, X1 = W * 0.215, W * 0.785
    ROWS = 6
    top, row_h, gap = W * 0.150, W * 0.058, W * 0.023

    # the streak the promoted row left behind it, drawn first so it sits under
    for k in range(1, 4):
        y = top + k * (row_h + gap)
        a = int(46 * (1 - (k - 1) / 3.2))
        gd.rounded_rectangle([X0, y, X1, y + row_h], radius=row_h * 0.26,
                             fill=(232, 147, 58, a))

    for r in range(ROWS):
        y0 = top + r * (row_h + gap)
        y1 = y0 + row_h
        hot = (r == 0)

        if hot:
            fill = tuple(int(c) for c in lerp(BG, AMBER, 0.17)) + (255,)
            edge, ew = (247, 181, 105, 205), max(1, int(1.8 * SS))
        else:
            fill = (19, 21, 25, 255)
            edge, ew = (255, 255, 255, 15), max(1, int(1.0 * SS))
        ld.rounded_rectangle([X0, y0, X1, y1], radius=row_h * 0.26, fill=fill,
                             outline=edge, width=ew)

        # a rank pip on the left, then two bars standing in for the posting
        pr = row_h * 0.115
        px = X0 + row_h * 0.42
        pc = (250, 214, 170, 245) if hot else (92, 98, 107, 150)
        ld.ellipse([px - pr, (y0 + y1) / 2 - pr, px + pr, (y0 + y1) / 2 + pr],
                   fill=pc)

        bx = X0 + row_h * 0.85
        b1 = (252, 232, 208, 235) if hot else (108, 114, 123, 130)
        b2 = (238, 187, 130, 165) if hot else (108, 114, 123, 74)
        ld.rounded_rectangle([bx, y0 + row_h * 0.30, bx + (X1 - X0) * 0.42,
                              y0 + row_h * 0.30 + row_h * 0.10],
                             radius=row_h * 0.05, fill=b1)
        ld.rounded_rectangle([bx, y0 + row_h * 0.56, bx + (X1 - X0) * 0.25,
                              y0 + row_h * 0.56 + row_h * 0.085],
                             radius=row_h * 0.05, fill=b2)

    # one quiet bloom behind the row that matters, nothing else
    gd.rounded_rectangle([X0 - row_h * 0.5, top - row_h * 0.5,
                          X1 + row_h * 0.5, top + row_h * 1.5],
                         radius=row_h, fill=(232, 147, 58, 58))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=24 * SS))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, layer).convert("RGB")
    finish(img, "It learns what you", "actually want.",
           "Rate a match and the feed reorders.", "a-learns.png")


# ---------------------------------------------------------------------------
# B — the home screen. A grid of dim app tiles with the real mark lit among
#     them, which is exactly what installing it looks like.
# ---------------------------------------------------------------------------
def opt_homescreen():
    img = Image.new("RGB", (W, W), BG).convert("RGBA")
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)

    COLS, ROWS = 4, 3
    ico = W * 0.118
    gx, gy = W * 0.062, W * 0.055
    grid_w = COLS * ico + (COLS - 1) * gx
    x0 = (W - grid_w) / 2
    y0 = W * 0.155
    HOT_C, HOT_R = 1, 1          # off-centre, on a thirds intersection

    for r in range(ROWS):
        for c in range(COLS):
            x = x0 + c * (ico + gx)
            y = y0 + r * (ico + gy + W * 0.020)
            hot = (c == HOT_C and r == HOT_R)

            if hot:
                gd.rounded_rectangle([x - ico * 0.45, y - ico * 0.45,
                                      x + ico * 1.45, y + ico * 1.45],
                                     radius=ico, fill=(232, 147, 58, 82))
                m = nabbly_mark(int(ico))
                layer.paste(m, (int(x), int(y)), m)
                lab = (238, 214, 186, 225)
                lw_ = ico * 0.60
            else:
                ld.rounded_rectangle([x, y, x + ico, y + ico],
                                     radius=ico * 0.23, fill=(23, 26, 31, 255),
                                     outline=(255, 255, 255, 14),
                                     width=max(1, int(1.0 * SS)))
                lab = (108, 114, 123, 96)
                lw_ = ico * (0.44 + 0.22 * (0.5 + 0.5 * math.sin(r * 3.1 + c * 1.7)))

            # the little name under every icon, as a bar rather than as type
            ly = y + ico + ico * 0.16
            ld.rounded_rectangle([x + (ico - lw_) / 2, ly,
                                  x + (ico - lw_) / 2 + lw_, ly + ico * 0.055],
                                 radius=ico * 0.03, fill=lab)

    glow = glow.filter(ImageFilter.GaussianBlur(radius=26 * SS))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, layer).convert("RGB")
    finish(img, "Now on your", "home screen.",
           "Add to Home Screen. No app store.", "b-homescreen.png")


# ---------------------------------------------------------------------------
# C — the roundup. Type led, so the headline runs at the top and the list sits
#     under a hairline. Set entirely at final scale.
# ---------------------------------------------------------------------------
def opt_roundup():
    img = Image.new("RGB", (W, W), BG)

    def extra(im, d):
        f_h = font(58, "Semibold")
        f_it = font(31, "Regular", ARIAL)
        d.text((S * 0.5, S * 0.300), "What shipped", font=f_h,
               fill=(226, 229, 234), anchor="mm")
        d.text((S * 0.5, S * 0.365), "this month.", font=f_h, fill=SOFT_AMBER,
               anchor="mm")
        d.line([(S * 0.30, S * 0.452), (S * 0.70, S * 0.452)],
               fill=(58, 63, 71), width=1)

        items = ["Ranking that learns from your ratings",
                 "Add it to your home screen",
                 "40 sources, and counting"]
        # left aligned as a block, but the block is centred on the widest line
        widest = max(d.textlength(i, font=f_it) for i in items)
        bx = (S - (widest + 30)) / 2
        for n, it in enumerate(items):
            y = S * (0.545 + n * 0.088)
            d.ellipse([bx, y - 5, bx + 10, y + 5], fill=(200, 141, 82))
            d.text((bx + 30, y), it, font=f_it, fill=(176, 184, 194), anchor="lm")

    finish(img, None, None, None, "c-roundup.png", extra=extra)


# ---------------------------------------------------------------------------
# D — the comet pack, with depth. Each trail gets its own weight so the field
#     has near and far in it instead of reading as a flat rake, and the leader
#     picks up an anamorphic streak through its head.
# ---------------------------------------------------------------------------
def opt_speed():
    img = Image.new("RGB", (W, W), BG).convert("RGBA")
    trails = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    td_ = ImageDraw.Draw(trails)
    glow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    flare = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flare)

    BAND_Y0, BAND_Y1 = W * 0.150, W * 0.595
    N, HOT = 16, 6
    row_gap = (BAND_Y1 - BAND_Y0) / (N - 1)

    for i in range(N):
        hot = (i == HOT)
        y = BAND_Y0 + i * row_gap + math.sin(i * 5.3) * row_gap * 0.16
        dep = 0.5 + 0.5 * math.sin(i * 4.7 + 2.3)      # 0 far, 1 near

        if hot:
            head_x = W * 0.790
        else:
            head_x = W * (0.42 + 0.24 * (0.5 + 0.5 * math.sin(i * 2.7 + 1.1)))

        # nearer trails are longer as well as brighter, which is most of what
        # sells the depth
        tail_x = W * (0.11 - 0.05 * dep) + math.sin(i * 3.9) * W * 0.015
        span = head_x - tail_x
        drift = math.sin(i * 1.7) * 5.0 * SS
        phase = i * 2.1

        steps = 460
        for s_i in range(steps + 1):
            t = s_i / steps
            x = tail_x + span * t
            yy = y + drift * math.sin(phase + t * 1.9)
            fade = t ** 1.7

            if hot:
                col = tuple(int(c) for c in lerp(AMBER, AMBER_L, t)) + (int(242 * fade),)
                r = (1.1 + 2.1 * fade) * SS
            else:
                col = (114, 121, 131, int((58 + 92 * dep) * fade))
                r = ((0.7 + 0.7 * dep) + (0.8 + 0.9 * dep) * fade) * SS

            td_.ellipse([x - r, yy - r, x + r, yy + r], fill=col)

        hy = y + drift * math.sin(phase + 1.9)
        if hot:
            hr = 5.2 * SS
            gd.ellipse([head_x - hr * 8, hy - hr * 8, head_x + hr * 8, hy + hr * 8],
                       fill=(232, 147, 58, 70))
            gd.ellipse([head_x - hr * 3.4, hy - hr * 3.4,
                        head_x + hr * 3.4, hy + hr * 3.4], fill=(240, 168, 92, 96))
            # the anamorphic streak: wide, shallow, and faint
            fd.ellipse([head_x - hr * 15, hy - hr * 0.62,
                        head_x + hr * 15, hy + hr * 0.62], fill=(250, 196, 138, 120))
            td_.ellipse([head_x - hr, hy - hr, head_x + hr, hy + hr],
                        fill=(253, 235, 210, 255))
        else:
            hr = (1.5 + 1.4 * dep) * SS
            td_.ellipse([head_x - hr, hy - hr, head_x + hr, hy + hr],
                        fill=(146, 153, 163, int(90 + 80 * dep)))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=30 * SS))
    flare = flare.filter(ImageFilter.GaussianBlur(radius=7 * SS))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, flare)
    img = Image.alpha_composite(img, trails).convert("RGB")
    finish(img, "Every gig,", "the moment it drops.",
           "The fastest reply usually wins.", "d-speed.png")


opt_learns()
opt_homescreen()
opt_roundup()
opt_speed()

"""
make_demo_video.py — the product demo, typeset rather than screen-grabbed.

WHY NOT A SCREEN RECORDING. The browser tooling here caps its captures well
below 1080 and will not hand the raw frames to disk, so a real recording would
have to be upscaled and would land soft. Worse, the live board carries two
things the brand rules keep out of marketing: the gig counts and the named
sources on every card. Framing around them mid-recording is fiddly; not drawing
them is exact.

Everything on screen is real. The gig, its tags, its age and every word of the
reply were captured from board.nabbly.co signed in as a Pro account with the
Draft Voice settings filled in. Nothing is invented copy. What is recreated is
the typesetting, in the same Pillow code that draws the weekly cards, so the
demo and the posts look like one piece of work.

The story is the wait. Before today the page blocked for 27.5s on the model
call; it now returns instantly and fills in. That is why the middle beat exists
rather than cutting straight to the finished reply.

Run:  .venv/bin/python tools/make_demo_video.py
Out:  brand/posts/demo/draft-my-reply.mp4   (1080x1080, ~14s)
"""
import sys
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_post as mp                                    # noqa: E402

OUT = mp.OUT / "demo"
OUT.mkdir(parents=True, exist_ok=True)

S, M, FPS = mp.S, mp.M, 30

# --- Real content, captured from board.nabbly.co -----------------------------
GIG = "Modern Minimalist Website Build"
TAGS = "Design / creative · Small budget   ·   Posted 2h ago"

# The clause that came from the Include setting is the only thing lit.
HOT_SPAN = "Ten years doing brand identity work"
REPLY = [
    "Monochrome-only is the part that trips most people up, they lean on imagery to create hierarchy and then have nothing to fall back on once color's off the table. Ten years doing brand identity work, mostly SaaS and healthcare, so typography-led systems that still feel warm in black and white is familiar territory.",
    "For the CMS side, markdown workflow so you can publish without touching code is straightforward to set up, I'd lean toward something like that over a heavier CMS given how lightweight you want this.",
    "Two things I'd want to know: do you have type preferences already, or is that open? And roughly how many pages beyond the blog are we talking?",
    "Alex",
]

# --- Beats, in frames -------------------------------------------------------
# The reply is TYPED, not faded in. A fade says "here is some text"; typing
# says "this is being written for you right now", which is the actual claim.
CARD_IN, WAIT_IN, TYPE_IN = 0, 22, 66

# NOT TYPING, AND NOT WORD BY WORD EITHER. A caret marching character by
# character puts the whole frame's attention on one moving point. A word
# cascade fixed that but still had a leading edge travelling through the text,
# which is motion the reader has to track rather than read. Paragraphs fade in
# whole instead: each arrives as a block, the eye gets a beat to read it, then
# the next lands. That is how someone actually consumes a reply.
#
# Total reveal is (paragraphs - 1) * PARA_STEP + PARA_DUR frames. STEP is the
# gap between paragraphs arriving and does most of the pacing; DUR is how long
# one paragraph takes to come up and should stay shorter than STEP, or the
# blocks smear into each other.
PARA_STEP = 42           # frames between paragraphs starting
PARA_DUR = 30            # frames for one paragraph to fade up

# --- Phase plan, after the cascade ------------------------------------------
# The reply finishing is not the end any more. The camera then punches into the
# three places the profile settings actually landed — the Include clause, the
# paragraph the Avoid setting kept clean, the Signature — each held with a chip
# naming the setting, and the video closes on the reply being sent. Zoom crops
# come from a 2x master render so pushed-in type stays crisp instead of
# upscaling 1080 pixels.
HOLD_A = 26              # rest on the finished reply before the first zoom
Z_IN = 22                # frames: full frame -> first target
Z_HOLD = 40              # frames held on each target, chip visible
Z_MOVE = 20              # frames gliding between consecutive targets
Z_OUT = 18               # frames: last target -> full frame
SEND_SLIDE = 40          # frames: the reply lifts off the top of the frame
SENT_HOLD = 44           # frames: the ping ring and the word Sent.
WORDMARK = 86            # frames: Sent. clears and the mark spells itself

# What each zoom is about: the setting name and the value the user typed.
CHIPS = [
    ("Include", "ten years on brand identity"),
    ("Avoid", "hourly rates · not one mention"),
    ("Signature", "just Alex"),
]


def wrap(d, text, font, width, hot=HOT_SPAN):
    """Wrap to `width`, keeping the lit clause coloured across a line break."""
    marked, i = [], 0
    while (j := text.find(hot, i)) != -1:
        marked.append((text[i:j], mp.GREY))
        marked.append((hot, mp.HOT))
        i = j + len(hot)
    marked.append((text[i:], mp.GREY))

    tokens = [(w, c) for chunk, c in marked for w in chunk.split(" ") if w]
    lines, cur, cur_w = [], [], 0.0
    space = d.textlength(" ", font=font)
    for word, colour in tokens:
        w = d.textlength(word, font=font)
        lead = 0.0 if (not cur or word[0] in TIGHT) else space
        if cur and cur_w + lead + w > width:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur.append((word, colour))
        cur_w += w + (lead if len(cur) > 1 else 0)
    if cur:
        lines.append(cur)
    return lines


TIGHT = ",.;:!?)"          # never take a leading space


def draw_line(d, x, y, line, font, opacities):
    """
    Draw one wrapped line with a per-word fade and return the x it ended at.

    `line` is [(word, colour)]; `opacities` is a same-length list of 0..1, one
    per word, so several words can be mid-fade in the same frame while earlier
    ones sit solid and later ones are not drawn at all.
    """
    space = d.textlength(" ", font=font)
    for k, (word, colour) in enumerate(line):
        if k and word[0] not in TIGHT:
            x += space
        o = opacities[k]
        if o > 0:
            d.text((x, y), word, font=font, fill=fade(colour, o), anchor="lm")
        x += d.textlength(word, font=font)
    return x


def word_count(line):
    return len(line)


def fade(colour, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(mp.BG[i] + (colour[i] - mp.BG[i]) * k) for i in range(3))


def ease(a, b, f):
    if f <= a:
        return 0.0
    if f >= b:
        return 1.0
    t = (f - a) / (b - a)
    return t * t * (3 - 2 * t)


def ground(W, H, box, strength=96):
    img = Image.new("RGB", (W, H), mp.BG)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse(box, fill=strength)
    glow = glow.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(170))
    return Image.composite(Image.new("RGB", (W, H), (92, 56, 22)), img, glow)


def rule(img, W, y):
    ss = 3
    layer = Image.new("RGBA", (W * ss, img.height * ss), (0, 0, 0, 0))
    ImageDraw.Draw(layer).line([(M * ss, y * ss), ((W - M) * ss, y * ss)],
                               fill=(255, 255, 255, 26), width=ss)
    return Image.alpha_composite(
        img.convert("RGBA"),
        layer.resize((W, img.height), Image.LANCZOS)).convert("RGB")


def sign(img, d, W, y):
    """The same lockup as the cards, placed for whichever canvas this is."""
    f_url = mp.font(24, "Semibold", mp.ARIAL_B)
    mk, gap, t = 36, 11, "nabbly.co"
    x0 = (W - (mk + gap + d.textlength(t, font=f_url))) / 2
    mark = mp.nabbly_mark(mk)
    img.paste(mark, (int(x0), int(y - mk / 2)), mark)
    d.text((x0 + mk + gap, y), t, font=f_url, fill=(190, 140, 92), anchor="lm")


def draw_master(L, k=2):
    """
    The finished reply, drawn once at k-times resolution, plus a box for every
    word. The zoom beats crop this instead of the native frame so a 2x push-in
    still lands on real pixels. Boxes come back in master coordinates as
    (para_index, colour, x0, y0, x1, y1).
    """
    W, H = L["W"] * k, L["H"] * k
    f_gig = mp.font(L["f"][0] * k, "Semibold")
    f_tag = mp.font(L["f"][1] * k, "Regular", mp.ARIAL)
    f_body = mp.font(L["f"][2] * k, "Regular", mp.ARIAL)

    img = rule(ground(W, H, tuple(v * k for v in L["glow"])), W, L["rule_y"] * k)
    d = ImageDraw.Draw(img)
    d.text((M * k, L["gig"] * k), GIG, font=f_gig, fill=mp.BODY, anchor="lm")
    d.text((M * k, L["tags"] * k), TAGS, font=f_tag, fill=mp.DIM, anchor="lm")

    paras = [wrap(d, p, f_body, W - 2 * M * k) for p in REPLY]
    space = d.textlength(" ", font=f_body)
    half = L["f"][2] * k * 0.62
    boxes, y = [], L["body"] * k
    for pi, para in enumerate(paras):
        for line in para:
            x = M * k
            for wi, (word, colour) in enumerate(line):
                if wi and word[0] not in TIGHT:
                    x += space
                ww = d.textlength(word, font=f_body)
                d.text((x, y), word, font=f_body, fill=colour, anchor="lm")
                boxes.append((pi, colour, x, y - half, x + ww, y + half))
                x += ww
            y += L["lead"] * k
        y += L["gap"] * k

    # the lockup, scaled to match
    f_url = mp.font(24 * k, "Semibold", mp.ARIAL_B)
    mk, gap, t = 36 * k, 11 * k, "nabbly.co"
    x0 = (W - (mk + gap + d.textlength(t, font=f_url))) / 2
    mark = mp.nabbly_mark(mk)
    img.paste(mark, (int(x0), int(L["mark"] * k - mk / 2)), mark)
    d.text((x0 + mk + gap, L["mark"] * k), t, font=f_url,
           fill=(190, 140, 92), anchor="lm")
    return img, boxes


def union(boxes):
    """Bounding box of word boxes, which carry (para, colour) before coords."""
    return (min(b[2] for b in boxes), min(b[3] for b in boxes),
            max(b[4] for b in boxes), max(b[5] for b in boxes))


def frame_rect(content, W, H, mW, mH):
    """
    A W:H-shaped crop window that actually punches in on the content.

    Sized from the content's WIDTH, not its height: these targets are lines of
    text, wide and short, and a height-based fit of a full-width line is nearly
    the whole frame, which reads as no zoom at all. The floor of 0.42 * master
    width caps the push-in around 2.4x, so a single short word like the
    signature does not become a screen-filling close-up of four letters.
    """
    cx = (content[0] + content[2]) / 2
    cy = (content[1] + content[3]) / 2
    cw = max((content[2] - content[0]) * 1.12,
             (content[3] - content[1]) * (W / H) * 1.12,
             mW * 0.34)
    ch = cw * H / W
    cw, ch = min(cw, mW), min(ch, mH)
    x0 = max(0, min(cx - cw / 2, mW - cw))
    y0 = max(0, min(cy - ch / 2, mH - ch))
    return (x0, y0, x0 + cw, y0 + ch)


def lerp_rect(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def draw_chip(img, W, H, label, value, alpha):
    """
    The setting, named on screen while the camera holds: a small rounded panel,
    label in amber, value beside it. Drawn on an overlay so it can fade as one.
    """
    if alpha <= 0:
        return img
    f_lbl = mp.font(30, "Semibold")
    f_val = mp.font(30, "Regular", mp.ARIAL)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lw = probe.textlength(label, font=f_lbl)
    vw = probe.textlength(value, font=f_val)
    pad_x, gap, ch = 34, 18, 78
    cw = lw + vw + gap + 2 * pad_x
    x0, y0 = (W - cw) / 2, H * 0.86 - ch / 2

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=ch / 2,
                        fill=(15, 17, 21, int(252 * alpha)),
                        outline=(*mp.AMBER, int(150 * alpha)), width=2)
    d.text((x0 + pad_x, y0 + ch / 2), label, font=f_lbl,
           fill=(*mp.HOT, int(255 * alpha)), anchor="lm")
    d.text((x0 + pad_x + lw + gap, y0 + ch / 2), value, font=f_val,
           fill=(219, 223, 229, int(255 * alpha)), anchor="lm")
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# Square reads in feed; the tall cut is for Reels, where the app puts its own
# controls over roughly the bottom sixth and the caption over the top, so the
# type sits well inside both.
LAYOUTS = [
    dict(name="draft-my-reply-square.mp4", W=1080, H=1080,
         gig=196, tags=240, rule_y=274, body=372,
         f=(38, 24, 27), lead=39, gap=19, mark=1025,
         glow=(M - 190, 250, 1080 - M + 60, 560)),
    dict(name="draft-my-reply-vertical.mp4", W=1080, H=1920,
         gig=350, tags=402, rule_y=446, body=548,
         f=(46, 28, 32), lead=46, gap=24, mark=1470,
         glow=(M - 190, 430, 1080 - M + 60, 860)),
]


def render(L):
    W, H = L["W"], L["H"]
    f_gig = mp.font(L["f"][0], "Semibold")
    f_tag = mp.font(L["f"][1], "Regular", mp.ARIAL)
    f_body = mp.font(L["f"][2], "Regular", mp.ARIAL)

    base = rule(ground(W, H, L["glow"]), W, L["rule_y"])
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    paras = [wrap(probe, p, f_body, W - 2 * M) for p in REPLY]

    reveal_out = TYPE_IN + (len(paras) - 1) * PARA_STEP + PARA_DUR
    end = reveal_out + HOLD_A

    w = iio.get_writer(OUT / L["name"], fps=FPS, codec="libx264", quality=9,
                       macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    for f in range(end):
        img = base.copy()
        d = ImageDraw.Draw(img)

        k = ease(CARD_IN, CARD_IN + 16, f)
        d.text((M, L["gig"]), GIG, font=f_gig, fill=fade(mp.BODY, k), anchor="lm")
        d.text((M, L["tags"]), TAGS, font=f_tag, fill=fade(mp.DIM, k), anchor="lm")

        if WAIT_IN <= f < TYPE_IN:
            # The page comes back instantly and says so. This beat is the fix.
            dots = "." * (1 + (f - WAIT_IN) // 8 % 3)
            d.text((M, L["body"]), "Writing your reply" + dots, font=f_body,
                   fill=fade(mp.DIM, ease(WAIT_IN, WAIT_IN + 10, f)), anchor="lm")

        if f >= TYPE_IN:
            y = L["body"]
            for pi, para in enumerate(paras):
                a = ease(TYPE_IN + pi * PARA_STEP,
                         TYPE_IN + pi * PARA_STEP + PARA_DUR, f)
                for line in para:
                    if a > 0:
                        draw_line(d, M, y, line, f_body, [a] * len(line))
                    y += L["lead"]
                y += L["gap"]

        sign(img, d, W, L["mark"])
        w.append_data(np.asarray(img))

    # ----- Phase B: three punch-ins, one per setting -------------------------
    K = 2
    master, boxes = draw_master(L, K)
    mW, mH = master.size

    hot = [b for b in boxes if b[1] == mp.HOT]
    para_last = max(b[0] for b in boxes)
    sig = [b for b in boxes if b[0] == para_last]
    avoid = [b for b in boxes if b[0] == 1]
    targets = [frame_rect(union(r), W, H, mW, mH)
               for r in (hot, avoid, sig)]
    full = (0.0, 0.0, float(mW), float(mH))

    def crop_frame(rect, chip=None, chip_alpha=0.0, content=None):
        r = tuple(int(round(v)) for v in rect)
        img = master.crop(r).resize((W, H), Image.LANCZOS)
        if content is not None and chip_alpha > 0:
            # The emphasis itself: everything but the target sinks into a dim
            # layer while a soft-edged window over the setting's own words
            # stays at full brightness. The dim rides the chip's alpha so the
            # spotlight and the label arrive and leave together.
            sx = W / (r[2] - r[0])
            sy = H / (r[3] - r[1])
            cx0 = (content[0] - r[0]) * sx - 20
            cy0 = (content[1] - r[1]) * sy - 16
            cx1 = (content[2] - r[0]) * sx + 20
            cy1 = (content[3] - r[1]) * sy + 16
            hole = Image.new("L", (W, H), 0)
            ImageDraw.Draw(hole).rounded_rectangle(
                [cx0, cy0, cx1, cy1], radius=26, fill=255)
            hole = hole.filter(
                __import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(18))
            dim_a = Image.new("L", (W, H), int(198 * chip_alpha))
            # inside the hole the dim strength drops to zero
            dim_a.paste(0, (0, 0), hole)
            img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img,
                                  dim_a)
        if chip:
            img = draw_chip(img, W, H, chip[0], chip[1], chip_alpha)
        return img

    for bi, (rect, chip) in enumerate(zip(targets, CHIPS)):
        prev = full if bi == 0 else targets[bi - 1]
        steps = Z_IN if bi == 0 else Z_MOVE
        for f in range(steps):
            t = ease(0, steps, f + 1)
            w.append_data(np.asarray(crop_frame(lerp_rect(prev, rect, t))))
        content = union((hot, avoid, sig)[bi])
        for f in range(Z_HOLD):
            a = ease(0, 8, f) * (1 - ease(Z_HOLD - 6, Z_HOLD, f))
            w.append_data(np.asarray(crop_frame(rect, chip, a, content)))
    for f in range(Z_OUT):
        t = ease(0, Z_OUT, f + 1)
        w.append_data(np.asarray(crop_frame(lerp_rect(targets[-1], full, t))))

    # ----- Phase C: sent ----------------------------------------------------
    native = master.resize((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), mp.BG)
    for f in range(SEND_SLIDE):
        t = ease(0, SEND_SLIDE, f + 1)
        img = bg.copy()
        sc = 1 - 0.08 * t
        sw, sh = int(W * sc), int(H * sc)
        moved = native.resize((sw, sh), Image.LANCZOS)
        img.paste(moved, ((W - sw) // 2, int((1 - t) * (H - sh) // 2 - t * H * 1.05)))
        w.append_data(np.asarray(img))

    # The mark, its ping ring expanding once, and the word Sent. The ring is
    # the logo's own motif, so the ending is the brand doing the sending.
    mk = 132
    mark = mp.nabbly_mark(mk)
    f_sent = mp.font(54, "Semibold")
    cx, cy = W // 2, int(H * 0.44)

    def ring_layer(img, f):
        ring = ease(0, 26, f)
        if not 0 < ring < 1:
            return img
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        r = mk * 0.55 + ring * 190
        ImageDraw.Draw(layer).ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(*mp.AMBER, int(170 * (1 - ring))), width=5)
        return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    for f in range(SENT_HOLD):
        img = ring_layer(bg.copy(), f)
        img.paste(mark, (cx - mk // 2, cy - mk // 2), mark)
        d2 = ImageDraw.Draw(img)
        # Sent. lands with the ring rather than trailing it, so the mark is
        # never sitting alone in an empty frame waiting for its own caption.
        d2.text((cx, cy + mk // 2 + 74), "Sent.", font=f_sent,
                fill=fade((226, 229, 234), ease(0, 10, f)), anchor="mm")
        w.append_data(np.asarray(img))

    # ----- Phase D: the mark spells itself ----------------------------------
    # The mark IS the N — same stroke as the wordmark's first letter — so the
    # close is "abbly" walking out from behind it while Sent. clears and the
    # static lockup drops away. Letters are drawn BEFORE the mark is pasted, so
    # the mark occludes them and they genuinely emerge from under it rather
    # than fading in beside it.
    f_word = mp.font(96, "Bold")
    probe2 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    letters = "abbly"
    wgap = 9           # tight to the tile: the mark IS the N
    tw = probe2.textlength(letters, font=f_word)
    x_final = (W - (mk + wgap + tw)) / 2          # mark's resting left edge
    x_start = (W - mk) / 2                         # where it sits now
    text_x = x_final + mk + wgap
    # The word arrives whole. Walking it out letter by letter made the ending
    # busy and pulled the eye left to right chasing each one; fading the
    # wordmark up as a single object lets it land with some weight instead.
    WORD_IN, WORD_DUR = 12, 24
    # The domain follows a beat later, in the same amber the lockup has used all
    # the way through, so the last thing on screen is where to go.
    URL_IN, URL_DUR = 34, 20
    f_url_end = mp.font(34, "Semibold", mp.ARIAL_B)

    for f in range(WORDMARK):
        img = bg.copy()
        sent_a = 1 - ease(0, 12, f)
        if sent_a > 0:
            ImageDraw.Draw(img).text(
                (cx, cy + mk // 2 + 74), "Sent.", font=f_sent,
                fill=fade((226, 229, 234), sent_a), anchor="mm")

        glide = ease(6, 30, f)
        mx = x_start + (x_final - x_start) * glide

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        a = ease(WORD_IN, WORD_IN + WORD_DUR, f)
        if a > 0:
            dl.text((text_x, cy), letters, font=f_word,
                    fill=(236, 238, 241, int(255 * a)), anchor="lm")
        u = ease(URL_IN, URL_IN + URL_DUR, f)
        if u > 0:
            dl.text((W / 2, cy + mk // 2 + 62), "nabbly.co", font=f_url_end,
                    fill=(190, 140, 92, int(255 * u)), anchor="mm")
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        img.paste(mark, (int(mx), cy - mk // 2), mark)
        w.append_data(np.asarray(img))

    w.close()
    total = (end + Z_IN + 2 * Z_MOVE + 3 * Z_HOLD + Z_OUT
             + SEND_SLIDE + SENT_HOLD + WORDMARK)
    print(f"wrote {OUT / L['name']}  {W}x{H}  {total / FPS:.1f}s  "
          f"cascade {(reveal_out - TYPE_IN) / FPS:.1f}s + 3 zooms + send + wordmark")


if __name__ == "__main__":
    for L in LAYOUTS:
        render(L)

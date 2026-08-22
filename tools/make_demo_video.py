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
GIG = "Luxury Skincare Packaging Design"
TAGS = "Design / creative   ·   Medium budget   ·   Posted 1h ago"

# The clause that came from the Include setting is the only thing lit.
HOT_SPAN = "ten years doing brand identity work"
REPLY = [
    "Three-SKU glass line with a carton that has to hold its own next to it, "
    "that's a fun constraint. I've spent " + HOT_SPAN + ", mostly SaaS and "
    "healthcare, so I'm used to translating something technical or clinical "
    "into visuals that feel considered rather than cold.",

    "My approach: nail the color and material story first with a small palette "
    "test against your glass and finish choices, then build the carton system "
    "so serum, moisturizer, and eye cream read as a family but aren't "
    "identical twins.",

    "Quick question: do you have printer specs and dielines ready to share "
    "now, or should I help spec those too?",
]

# --- Beats, in frames --------------------------------------------------------
CARD_IN, WAIT_IN, REPLY_IN, HOLD, END = 0, 46, 128, 356, 420
PARA_STEP = 62          # each paragraph starts this many frames after the last


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


def draw_line(d, x, y, line, font):
    space = d.textlength(" ", font=font)
    for k, (word, colour) in enumerate(line):
        if k and word[0] not in TIGHT:
            x += space
        d.text((x, y), word, font=font, fill=colour, anchor="lm")
        x += d.textlength(word, font=font)


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


# Square reads in feed; the tall cut is for Reels, where the app puts its own
# controls over roughly the bottom sixth and the caption over the top, so the
# type sits well inside both.
LAYOUTS = [
    dict(name="draft-my-reply-square.mp4", W=1080, H=1080,
         gig=218, tags=262, rule_y=296, body=430,
         f=(38, 24, 30), lead=44, gap=22, mark=1025,
         glow=(M - 190, 250, 1080 - M + 60, 560)),
    dict(name="draft-my-reply-vertical.mp4", W=1080, H=1920,
         gig=384, tags=436, rule_y=480, body=612,
         f=(46, 28, 34), lead=50, gap=26, mark=1414,
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

    w = iio.get_writer(OUT / L["name"], fps=FPS, codec="libx264", quality=9,
                       macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    for f in range(END):
        img = base.copy()
        d = ImageDraw.Draw(img)

        k = ease(CARD_IN, CARD_IN + 20, f)
        d.text((M, L["gig"]), GIG, font=f_gig, fill=fade(mp.BODY, k), anchor="lm")
        d.text((M, L["tags"]), TAGS, font=f_tag, fill=fade(mp.DIM, k), anchor="lm")

        if WAIT_IN <= f < REPLY_IN:
            # The page comes back instantly and says so. This beat is the fix.
            dots = "." * (1 + (f - WAIT_IN) // 9 % 3)
            kk = ease(WAIT_IN, WAIT_IN + 12, f)
            d.text((M, L["body"]), "Writing your reply" + dots, font=f_body,
                   fill=fade(mp.DIM, kk), anchor="lm")

        if f >= REPLY_IN:
            y = L["body"]
            for i, lines in enumerate(paras):
                a = REPLY_IN + i * PARA_STEP
                kk = ease(a, a + 26, f)
                for line in lines:
                    if kk > 0:
                        draw_line(d, M, y, [(t, fade(c, kk)) for t, c in line],
                                  f_body)
                    y += L["lead"]
                y += L["gap"]

        sign(img, d, W, L["mark"])
        w.append_data(np.asarray(img))
    w.close()
    last_y = y if f >= REPLY_IN else 0
    print(f"wrote {OUT / L['name']}  {W}x{H}  {END / FPS:.1f}s  "
          f"text ends y={last_y} of {H}")


if __name__ == "__main__":
    for L in LAYOUTS:
        render(L)

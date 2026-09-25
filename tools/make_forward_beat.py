"""
make_forward_beat.py — the beat that shows the thing no public board can do.

The demo covers the loop anyone can picture: a gig is posted, you are told, you
reply. Forwarding is the half nobody else has, and it is invisible in every cut
we have. A newsletter goes to an inbox, not a board — so a crawler cannot see
it, and neither can a competitor. The person who receives it can forward it,
and then it is on their board and on nobody else's.

COPY IS LIFTED FROM THE SITE, NOT WRITTEN HERE. nabbly.co already carries this
exact example — Study Hall's "Opportunities of the Week" split into three gigs.
Reusing it verbatim keeps the video and the front page telling one story, and
it is copy that has already been through a founder pass.

THE ADDRESS IS THE REAL SHAPE. inbox.py derives it as `gigs+<10 hex>@nabbly.co`,
a hash of the account's email so it is stable without storing another secret
and does not leak who it belongs to. The tag shown here is inbox.py's own
docstring example, not a live one: putting a working address on a video means
publishing an inbox anyone can post into.

Run:  .venv/bin/python tools/make_forward_beat.py [WxH]
Out:  brand/posts/demo/forward-beat.png   (stills; animation comes after review)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_post as mp                                    # noqa: E402

OUT = ROOT / "brand" / "posts" / "demo"
W, H = 1920, 1080

SENDER_INITIALS = "SH"
SENDER = "Study Hall"
SUBJECT = "Opportunities of the Week"
BODY = ("A few things crossed our desk this week that are a fit for you. "
        "Wired's looking for a freelance science reporter, $1/word, pitches "
        "due Friday. Also heard from a production house after a documentary "
        "editor for a 6-week remote contract, and a nonprofit is hunting for "
        "someone to handle a full brand refresh…")

# inbox.py's docstring example. Deliberately not a live address.
ADDRESS = "gigs+3f9a2b1c04@nabbly.co"

SPLIT = [
    ("Freelance science reporter — Wired", "$1/word · pitch by Friday"),
    ("Documentary editor — 6-week contract", "Remote · Video"),
    ("Brand designer for a nonprofit rebrand", "Project rate · Design"),
]


def wrap(d, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# Beats, in frames. The card lands, the address it was sent to lights, then
# the gigs peel off it one at a time — the split is the claim, so it gets the
# time rather than the headline does.
FADE, ADDR_AT, ROW_STEP, ROW_DUR, TAIL = 18, 26, 22, 16, 40


def _a(f, start, dur):
    """Opacity of something that begins at `start` and takes `dur` frames."""
    if f <= start:
        return 0.0
    t = min(1.0, (f - start) / dur)
    return t * t * (3 - 2 * t)


def render(f=None):
    """
    One frame. `f` is the frame index, or None for the finished still.

    Each group is drawn on its own transparent layer and composited at that
    beat's opacity, rather than fading colours toward the background. Lerping
    text toward the ground goes muddy halfway through and turns the amber
    brown; an alpha composite keeps every colour true at every opacity.
    """
    LX, LW = 190, 720
    RX = LX + LW + 150
    img = Image.new("RGB", (W, H), mp.BG)

    f_lbl = mp.font(21, "Semibold")
    f_name = mp.font(32, "Semibold")
    f_sub = mp.font(27, "Regular", mp.ARIAL)
    f_body = mp.font(23, "Regular", mp.ARIAL)
    f_addr = mp.font(25, "Semibold")
    f_title = mp.font(29, "Semibold")
    f_meta = mp.font(22, "Regular", mp.ARIAL)

    def layer():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        return im, ImageDraw.Draw(im)

    def put(im, alpha):
        if alpha <= 0:
            return
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        img.alpha_composite(im) if img.mode == "RGBA" else img.paste(im, (0, 0), im)

    def panel(w, h, radius):
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle(
            [0, 0, w * 2 - 1, h * 2 - 1], radius=radius * 2,
            fill=(21, 24, 29, 255), outline=(47, 52, 61, 255), width=4)
        return im.resize((w, h), Image.LANCZOS)

    a = (lambda *_: 1.0) if f is None else _a

    # ---- the claim ---------------------------------------------------------
    im, d = layer()
    d.text((LX, 170), "The gigs no public board carries.",
           font=mp.font(52, "Semibold"), fill=mp.BODY)
    d.text((LX, 232), "Forward the newsletter once. Every gig inside it lands "
                      "on your board, and nobody else's.",
           font=mp.font(26, "Regular", mp.ARIAL), fill=mp.GREY)
    put(im, a(f, 0, FADE))

    # ---- the newsletter, as it lands in a mailbox --------------------------
    im, d = layer()
    im.paste(panel(LW, 470, 26), (LX, 300), panel(LW, 470, 26))
    d = ImageDraw.Draw(im)
    av = 60
    d.ellipse([LX + 36, 336, LX + 36 + av, 336 + av], fill=(44, 49, 58, 255))
    d.text((LX + 36 + av / 2, 336 + av / 2), SENDER_INITIALS,
           font=mp.font(24, "Semibold"), fill=mp.GREY, anchor="mm")
    d.text((LX + 118, 344), SENDER, font=f_name, fill=mp.BODY)
    d.text((LX + 118, 382), SUBJECT, font=f_sub, fill=mp.GREY)
    y = 448
    for line in wrap(d, BODY, f_body, LW - 76)[:5]:
        d.text((LX + 38, y), line, font=f_body, fill=mp.DIM)
        y += 33
    put(im, a(f, FADE // 2, FADE))

    # ---- the address it was sent to ----------------------------------------
    im, d = layer()
    d.line([(LX + 38, 640), (LX + LW - 38, 640)], fill=(47, 52, 61, 255), width=1)
    d.text((LX + 38, 664), "FORWARDED TO", font=mp.font(19, "Semibold"), fill=mp.DIM)
    d.text((LX + 38, 696), ADDRESS, font=f_addr, fill=mp.HOT)
    put(im, a(f, ADDR_AT, FADE))

    # ---- the hinge, and what it became -------------------------------------
    im, d = layer()
    d.text((LX + LW + 60, 520), "\u2192", font=mp.font(46, "Regular", mp.ARIAL),
           fill=(90, 96, 106))
    d.text((RX, 300), "NABBLY SPLITS IT INTO", font=f_lbl, fill=mp.DIM)
    put(im, a(f, ADDR_AT + FADE, FADE))

    # ---- the gigs, one at a time -------------------------------------------
    first_row = ADDR_AT + FADE + 10
    y = 356
    for i, (title, meta) in enumerate(SPLIT):
        im, d = layer()
        im.paste(panel(700, 116, 18), (RX, y), panel(700, 116, 18))
        d = ImageDraw.Draw(im)
        d.text((RX + 30, y + 30), title, font=f_title, fill=mp.BODY)
        d.text((RX + 30, y + 70), meta, font=f_meta, fill=mp.GREY)
        put(im, a(f, first_row + i * ROW_STEP, ROW_DUR))
        y += 140

    return img


def total_frames():
    """How long the whole beat runs, including the hold at the end."""
    return ADDR_AT + FADE + 10 + (len(SPLIT) - 1) * ROW_STEP + ROW_DUR + TAIL


if __name__ == "__main__":
    # make_forward_beat.py [WxH] [--still]
    argv = sys.argv[1:]
    still = "--still" in argv
    if still:
        argv.remove("--still")
    size = next((a for a in argv if "x" in a
                 and all(p.isdigit() for p in a.split("x", 1))), None)
    if size:
        W, H = (int(v) for v in size.split("x"))

    if still:
        out = OUT / "forward-beat.png"
        render().save(out, "PNG", optimize=True)
        print(f"wrote {out}  {W}x{H}")
    else:
        import imageio.v2 as iio
        import numpy as np
        out = OUT / "forward-beat.mp4"
        n = total_frames()
        w = iio.get_writer(out, fps=30, codec="libx264", quality=9,
                           macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
        for f in range(n):
            w.append_data(np.asarray(render(f)))
        w.close()
        print(f"wrote {out}  {W}x{H}  {n} frames  {n / 30:.1f}s")

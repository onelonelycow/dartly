"""
make_video.py — the weekly card, in motion.

Instagram and X take MP4, not GIF, so frames are drawn with Pillow and encoded
through imageio-ffmpeg (which ships its own ffmpeg binary). imageio-ffmpeg is a
LOCAL tool only and is deliberately absent from requirements.txt: Render builds
from that file and memory is the binding constraint there, so a video encoder
has no business in the deployed image.

This one animates card 2 of the Draft Voice post. The card fills itself in the
order a person would read it: the gig, then the reply typing out with the
configured clause landing in amber, then the four settings that produced it.
Nothing moves that would not move on the page — no slides, no wipes — because
the stills are restrained and the video should match them.

Run:  .venv/bin/python tools/make_video.py
Out:  brand/posts/week-05-draft-voice/02-in-action.mp4  (1080x1080, ~7.5s)
"""
import sys
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_post as mp                                    # noqa: E402

FPS = 30
S = mp.S
M = mp.M

# Beats, in frames. Each is the frame the phase starts on.
HEAD_IN, TYPE_IN, TYPE_OUT = 0, 16, 106
SIGN_IN, CLAIM_IN, ROWS_IN, END = 112, 132, 150, 226


def lerp(colour, k):
    """Fade a colour up from the background, so type can appear without alpha."""
    k = max(0.0, min(1.0, k))
    return tuple(int(mp.BG[i] + (colour[i] - mp.BG[i]) * k) for i in range(3))


def ease(a, b, f):
    """0 to 1 across frames a..b, smoothed at both ends."""
    if f <= a:
        return 0.0
    if f >= b:
        return 1.0
    t = (f - a) / (b - a)
    return t * t * (3 - 2 * t)


# The reply, flattened to characters so it can be revealed a few at a time.
CHARS = sum(len(t) for line in mp.DRAFT for t, _ in line)


def draft_upto(n):
    """The first n characters of the reply, still split into coloured runs."""
    out, budget = [], n
    for line in mp.DRAFT:
        segs = []
        for text, colour in line:
            if budget <= 0:
                break
            segs.append((text[:budget], colour))
            budget -= len(text)
        out.append(segs)
    return out


def frame(f, base, fonts):
    f_gig, f_meta, f_body, f_claim, f_lbl, f_val = fonts
    img = base.copy()
    d = ImageDraw.Draw(img)

    k = ease(HEAD_IN, HEAD_IN + 14, f)
    d.text((M, 152), mp.GIG, font=f_gig, fill=lerp((139, 146, 157), k), anchor="lm")
    d.text((M, 196), mp.META, font=f_meta, fill=lerp(mp.DIM, k), anchor="lm")

    # The reply types itself. The caret rides the last revealed character and
    # blinks only while it is waiting, which is the one moving part in the frame.
    shown = int(CHARS * ease(TYPE_IN, TYPE_OUT, f))
    y, end_x, end_y = 318, M, 318
    for segs in draft_upto(shown):
        x = M
        if segs:
            x = mp.runs(d, M, y, segs, f_body)
            end_x, end_y = x, y
        y += 65
    if TYPE_IN <= f < SIGN_IN and (f < TYPE_OUT or (f // 8) % 2 == 0):
        d.line([(end_x + 4, end_y - 20), (end_x + 4, end_y + 18)],
               fill=mp.HOT, width=3)

    if f >= SIGN_IN:
        d.text((M, 605), mp.SIGN, font=f_body,
               fill=lerp(mp.BODY, ease(SIGN_IN, SIGN_IN + 12, f)), anchor="lm")

    if f >= CLAIM_IN:
        d.text((M, 722), mp.CLAIM, font=f_claim,
               fill=lerp((198, 203, 211), ease(CLAIM_IN, CLAIM_IN + 12, f)),
               anchor="lm")

    ry = 786
    for i, (label, value) in enumerate(mp.SETTINGS):
        a = ROWS_IN + i * 9
        k = ease(a, a + 12, f)
        if k > 0:
            d.text((M, ry), label, font=f_lbl, fill=lerp((99, 106, 116), k),
                   anchor="lm")
            d.text((M + 132, ry), value, font=f_val, fill=lerp(mp.GREY, k),
                   anchor="lm")
        ry += 40

    mp.signature(img, d)
    return img


def main():
    base = mp.hairlines(mp.ground([M - 190, 300, S - M + 60, 580]), (240, 678))
    fonts = (mp.font(33, "Semibold"), mp.font(25, "Regular", mp.ARIAL),
             mp.font(40, "Regular", mp.ARIAL), mp.font(29, "Semibold"),
             mp.font(23, "Semibold"), mp.font(23, "Regular", mp.ARIAL))

    out = mp.CAR / "02-in-action.mp4"
    # yuv420p is what Instagram and X will accept; imageio does not default to it.
    w = iio.get_writer(out, fps=FPS, codec="libx264", quality=9,
                       macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    for f in range(END):
        w.append_data(np.asarray(frame(f, base, fonts)))
    w.close()
    print("wrote", out, f"{END / FPS:.1f}s")


if __name__ == "__main__":
    main()

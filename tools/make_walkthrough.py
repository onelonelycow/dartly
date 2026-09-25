"""
make_walkthrough.py — the real site, end to end, as one vertical video.

Two halves, joined by a fade:

  1. REAL FRAMES from board.nabbly.co, captured by capture_demo.py at
     1080x1920. Actual pixels, actual gigs, actual timestamps. Someone lands on
     the board, types a search, scrolls the results and stops on a fresh gig
     with the cursor over "Draft my reply".

  2. THE REPLY, from make_demo_video.py's vertical cut. This half is typeset
     rather than screen-grabbed because /draft is behind sign-in and the
     capture browser has no session: signing in would mean handling
     credentials. Every word of it is real, captured from the live board while
     signed in as Pro.

The cut between them is the honest seam. The first half proves the gigs are
real and fresh; the second shows what the product does with one.

Run:  .venv/bin/python tools/make_walkthrough.py <frames_dir>
Out:  brand/posts/demo/walkthrough.mp4
"""
import json
import sys
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "posts" / "demo"
# 9:16 by default, the social cut. Pass WxH for the landscape product demo —
# the reply half is picked to match, since a portrait reply letterboxed into a
# wide frame would undo the point of rendering one per aspect.
W, H, FPS = 1080, 1920, 30

# The capture is paced for a machine, not an eye. Every hold is stretched so
# the viewer can actually read a card before the page moves under them.
PACE = 1.25
FADE = 14                      # frames of cross-fade at the seam


def main(frames_dir: Path):
    shots = sorted(frames_dir.glob("[0-9]*.png"))
    holds = json.loads((frames_dir / "holds.json").read_text())
    assert len(shots) == len(holds), f"{len(shots)} shots vs {len(holds)} holds"

    # Frames are captured at 2x so the search-bar push-in crops real pixels.
    zoom = json.loads((frames_dir / "zoom.json").read_text())
    mW, mH = zoom["master"]
    z_lo, z_hi = zoom["shots"]
    sr = zoom["search_rect"]

    # A W:H window around the search bar, with room above and below so the
    # board's own frame still reads and the push-in does not feel like a
    # different screenshot. Sized off the bar's width, since it is wide and short.
    # Centred on the SEARCH ROW the capture measured — input plus its Search
    # button — not on the page. The board grew a left rail on 2026-08-23 and
    # the search bar is no longer centred in the viewport, so a page-centred
    # window framed the sidebar instead of the thing being typed into.
    scx, scy = (sr[0] + sr[2]) / 2, (sr[1] + sr[3]) / 2
    zw = min(mW, (sr[2] - sr[0]) * 1.22)
    zh = zw * H / W
    # Centred on the row in 9:16, where the window is narrow enough to hold
    # just the search. A 16:9 window is much wider than the row, so centring it
    # reaches past the row's left edge and swallows the filter rail — the demo
    # showed a column of half-cut category labels. Wide frames start at the
    # row instead, with a small pad, so the rail stays out of shot.
    if W > H:
        zx = max(0, min(sr[0] - zw * 0.04, mW - zw))
    else:
        zx = max(0, min(scx - zw / 2, mW - zw))
    zy = max(0, min(scy - zh / 2, mH - zh))
    near = (zx, zy, zx + zw, zy + zh)
    far = (0.0, 0.0, float(mW), float(mH))

    def blend(a, b, t):
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))

    def smooth(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    wide = W > H
    demo = OUT / ("draft-my-reply-wide.mp4" if wide
                  else "draft-my-reply-vertical.mp4")
    assert demo.exists(), f"missing {demo}; run make_demo_video.py first"

    out = OUT / ("walkthrough-wide.mp4" if wide else "walkthrough.mp4")
    w = iio.get_writer(out, fps=FPS, codec="libx264", quality=9,
                       macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])

    last = None
    n = 0
    # The push-in eases in over the first shots of the typing run and eases out
    # over the last, so the query is typed while the bar owns the frame.
    IN_SHOTS, OUT_SHOTS = 2.0, 1.5
    for si, (path, hold) in enumerate(zip(shots, holds)):
        src = Image.open(path).convert("RGB")
        reps = max(1, round(hold * PACE))
        for r in range(reps):
            # fractional shot position, so the ease is smooth across holds
            pos = si + (r + 0.5) / reps
            if z_lo - IN_SHOTS <= pos <= z_hi + OUT_SHOTS:
                t = min(smooth((pos - (z_lo - IN_SHOTS)) / IN_SHOTS),
                        smooth((z_hi + OUT_SHOTS - pos) / OUT_SHOTS), 1.0)
            else:
                t = 0.0
            if t <= 0.001:
                img = src.resize((W, H), Image.LANCZOS)
            else:
                r4 = tuple(int(round(v)) for v in blend(far, near, t))
                img = src.crop(r4).resize((W, H), Image.LANCZOS)
            arr = np.asarray(img)
            w.append_data(arr)
            n += 1
            last = arr

    # Fade the real page out into the reply, so the seam reads as a cut rather
    # than a glitch.
    reader = iio.get_reader(demo)
    first_demo = None
    for i, frame in enumerate(reader):
        if frame.shape[0] != H or frame.shape[1] != W:
            frame = np.asarray(Image.fromarray(frame).resize((W, H), Image.LANCZOS))
        if i == 0:
            first_demo = frame
            for k in range(FADE):
                t = (k + 1) / (FADE + 1)
                w.append_data((last * (1 - t) + frame * t).astype(np.uint8))
                n += 1
        w.append_data(frame)
        n += 1
    reader.close()
    w.close()
    print(f"wrote {out}  {W}x{H}  {n} frames  {n / FPS:.1f}s")


if __name__ == "__main__":
    # make_walkthrough.py <frames_dir> [WxH]
    argv = sys.argv[1:]
    size = next((a for a in argv if "x" in a
                 and all(p.isdigit() for p in a.split("x", 1))), None)
    if size:
        argv.remove(size)
        W, H = (int(v) for v in size.split("x"))
    main(Path(argv[0]))

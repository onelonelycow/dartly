"""
make_demo_full.py — the whole demo, in the order the beat sheet argues for.

demo-full-wide.mp4 ends on the wordmark, because the reply cut it is built
from ends on the wordmark. That is right when the reply is the last thing and
wrong the moment anything follows it: the video would sign off, then keep
going. So the ending is lifted off, the two remaining beats are inserted, and
the ending is put back where an ending belongs.

    alert · board · search · the gig · the reply
    → the settings that shaped it
    → the gigs no public board carries
    → lockup

WHY THE SETTINGS COME AFTER THE REPLY. Shown first they are a feature tour,
asking someone to care about controls before they have seen anything worth
controlling. Shown after, they answer the question the reply just raised —
how did it know that. Same frames, different job. See brand/DEMO-BEATS.md.

THE SETTINGS ARE SLOWED DOWN, NOT RE-SHOT. The capture paces for a machine:
14 shots covering three separate ideas — what you do, the words that matter,
where alerts reach you — run 2.7s, which is a blur. The holds are stretched
rather than more frames grabbed, because the page did not change between them.

Run:  .venv/bin/python tools/make_demo_full.py <settings_frames_dir>
Out:  brand/posts/demo/demo-full.mp4
"""
import json
import sys
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_demo_video as dv                              # noqa: E402
import make_forward_beat as fb                            # noqa: E402

OUT = ROOT / "brand" / "posts" / "demo"
W, H, FPS = 1920, 1080, 30

# The settings capture is paced for a machine; three ideas need room to land.
SETTINGS_PACE = 3.2
SEAM = 14                       # cross-fade frames between sections


def _fade(w, a, b, n=SEAM):
    """Cross-fade one array into another, so a section change is not a jolt."""
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    for k in range(n):
        t = (k + 1) / (n + 1)
        w.append_data((a * (1 - t) + b * t).astype(np.uint8))
    return n


def settings_frames(d: Path):
    """The captured settings shots, stretched to something readable."""
    holds = json.loads((d / "holds.json").read_text())
    shots = sorted(d.glob("[0-9]*.png"))
    assert len(shots) == len(holds), f"{len(shots)} shots vs {len(holds)} holds"
    for path, hold in zip(shots, holds):
        im = Image.open(path).convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        arr = np.asarray(im)
        for _ in range(max(1, round(hold * SETTINGS_PACE))):
            yield arr


def main(settings_dir: Path):
    src = OUT / "demo-full-wide.mp4"
    assert src.exists(), f"missing {src}; run make_alert_open.py first"

    # STREAMED, NOT LOADED. 977 frames of 1080p is about 6GB as a list of
    # arrays, which is how the first version of this died. The source is read
    # twice instead — once for the body, once for the wordmark tail — and only
    # the single frames either side of a seam are ever held.
    total = iio.get_reader(src).count_frames()
    cut = total - dv.WORDMARK          # where the sign-off begins

    out = OUT / "demo-full.mp4"
    w = iio.get_writer(out, fps=FPS, codec="libx264", quality=9,
                       macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    n = 0
    last_body = None
    reader = iio.get_reader(src)
    for i, f in enumerate(reader):
        if i >= cut:
            break
        w.append_data(f)
        last_body = f
        n += 1
    reader.close()

    sett = list(settings_frames(settings_dir))
    n += _fade(w, last_body, sett[0])
    for f in sett:
        w.append_data(f)
        n += 1

    fwd = [np.asarray(fb.render(i)) for i in range(fb.total_frames())]
    n += _fade(w, sett[-1], fwd[0])
    for f in fwd:
        w.append_data(f)
        n += 1

    # the sign-off, read back out of the source rather than kept in memory
    reader = iio.get_reader(src)
    tail_first, tail_n = None, 0
    for i, f in enumerate(reader):
        if i < cut:
            continue
        if tail_first is None:
            tail_first = f
            n += _fade(w, fwd[-1], f)
        w.append_data(f)
        tail_n += 1
        n += 1
    reader.close()

    w.close()
    print(f"wrote {out}  {W}x{H}  {n} frames  {n / FPS:.1f}s")
    print(f"  reply+board {cut/FPS:.1f}s · settings {len(sett)/FPS:.1f}s "
          f"· forwarding {len(fwd)/FPS:.1f}s · lockup {tail_n/FPS:.1f}s")


if __name__ == "__main__":
    fb.W, fb.H = W, H
    main(Path(sys.argv[1]))

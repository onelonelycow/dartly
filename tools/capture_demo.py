"""
capture_demo.py — drive the real site and save real frames.

Playwright renders board.nabbly.co at full 1080x1920 and screenshots it, so the
walkthrough is actual pixels rather than a typeset recreation. Frames land in a
directory; make_walkthrough.py turns them into the MP4.

Typing and scrolling are captured a step at a time — a shot per character, a
shot per scroll increment — so the motion in the finished video is the real
page moving, not an animation drawn over a still.

WHAT THIS CANNOT REACH. /draft is behind sign-in and this browser has no
session, by design: signing in would mean handling credentials. So the capture
stops where a signed-out visitor stops. The drafting beat is filmed separately.

Run:  .venv/bin/python tools/capture_demo.py <out_dir>
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1080, 1920
DSF = 2                 # device scale factor: frames land at 2160x3840
SEARCH = "logo design"

# The two things the brand rules keep out of marketing, removed from the live
# page BEFORE the shutter rather than masked afterwards. Nothing else is
# touched, and the timestamps stay: "Posted 2h ago" is the whole argument.
#
#   .gr-posted   renders "Posted 2h ago · via Freelancer.com" as ONE text node
#                (g.posted_line), so CSS cannot hide half of it. Trimmed at the
#                separator instead, which keeps the age and drops the source.
#   a.gr-cat     "Everywhere · 49,780" — same trick, keeps the label.
#   .count       "1,143 gigs for “logo design”" and .at "Page 1 of 46": board
#                size, which we never lead on.
STRIP = """
document.querySelectorAll('.gr-posted').forEach(function (el) {
  el.textContent = el.textContent.split('\u00b7')[0].trim();
});
document.querySelectorAll('a.gr-cat').forEach(function (el) {
  el.textContent = el.textContent.split('\u00b7')[0].trim();
});
document.querySelectorAll('.count, .at').forEach(function (el) {
  el.style.visibility = 'hidden';
});
"""


def strip(pg):
    """
    Apply the strip pass once the DOM is actually there.

    Pressing Enter navigates, and evaluating into a context that is still being
    torn down raises "Execution context was destroyed". Waiting for a card to
    exist is the reliable signal that the new document is ready.
    """
    pg.wait_for_selector(".gr-posted", timeout=30000)
    for _ in range(3):
        try:
            pg.evaluate(STRIP)
            return
        except Exception:
            pg.wait_for_timeout(400)
    raise RuntimeError("strip pass never applied")


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    n = 0

    holds = []

    def shot(page, hold=1):
        """
        Save the view ONCE and record how many frames it should occupy.

        Writing `hold` identical PNGs meant 176 full-page screenshots of a
        1080x1920 viewport, which is minutes of disk for frames that are
        byte-identical. The assembler repeats them instead.
        """
        nonlocal n
        page.screenshot(path=out / f"{n:04d}.png")
        holds.append(hold)
        n += 1

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DSF)

        pg.goto("https://board.nabbly.co/", wait_until="networkidle", timeout=45000)
        pg.wait_for_timeout(400)
        strip(pg)
        shot(pg, 34)                                    # the board, cold open

        box = pg.locator("input[type='search'], input[name='q']").first
        box.click()
        # THE SEARCH BAR'S OWN RECTANGLE, in device pixels. The assembler pushes
        # in on exactly this while the query is typed, so the eye is on the box
        # rather than hunting the page for what changed. Recorded here because
        # only the live page knows where its own input actually sits.
        bb = box.bounding_box()
        zoom_from = n                                   # first shot of the push-in
        for ch in SEARCH:                               # a frame per keystroke
            box.type(ch, delay=0)
            shot(pg, 2)
        shot(pg, 10)
        zoom_to = n - 1                                 # last shot still pushed in

        pg.keyboard.press("Enter")
        pg.wait_for_load_state("networkidle", timeout=45000)
        pg.wait_for_timeout(300)
        strip(pg)
        shot(pg, 26)                                    # results

        for _ in range(18):                             # scroll the real page
            pg.mouse.wheel(0, 88)
            pg.wait_for_timeout(20)
            shot(pg, 1)
        shot(pg, 30)                                    # rest on a gig

        # THE VIDEO HAS TO DRAFT FOR THE GIG IT JUST FOUND. The card under the
        # cursor is read out here so the second half can be generated against
        # this exact posting instead of a different one, which is what made the
        # first cut show someone finding job X and replying to job Y.
        card = pg.locator(".gr-cardwrap").nth(3)
        card.scroll_into_view_if_needed()
        pg.wait_for_timeout(150)
        shot(pg, 12)

        # THE CLICKED CARD SAYS SO. Without this the cut to the reply looks like
        # it came from nowhere: eight near-identical cards are on screen and
        # nothing marks which one was picked. Brand amber, injected on the live
        # element so it renders with the page's own radius and shadow rather
        # than being drawn on afterwards.
        card.evaluate("""el => {
          el.style.transition = 'none';
          el.style.borderRadius = '16px';
          el.style.boxShadow =
            '0 0 0 3px rgba(232,147,58,.9), 0 0 46px rgba(232,147,58,.22)';
        }""")
        pg.wait_for_timeout(80)
        shot(pg, 10)                                    # the outline lands

        chosen = card.evaluate("""el => {
          const t = s => (el.querySelector(s)?.textContent || '').trim();
          return {
            title: t('.gr-title'),
            pills: Array.from(el.querySelectorAll('.gr-pill')).map(p => p.textContent.trim()),
            posted: t('.gr-posted'),
            body: t('.gr-full') || t('.gr-body'),
          };
        }""")
        (out / "gig.json").write_text(json.dumps(chosen, indent=2))
        print("chosen gig:", chosen["title"])

        card.locator("a.draftlink").hover()
        shot(pg, 26)                                    # cursor on the button

        b.close()
    (out / "holds.json").write_text(json.dumps(holds))
    (out / "zoom.json").write_text(json.dumps({
        "search_rect": [bb["x"] * DSF, bb["y"] * DSF,
                        (bb["x"] + bb["width"]) * DSF,
                        (bb["y"] + bb["height"]) * DSF],
        "shots": [zoom_from, zoom_to],
        "master": [W * DSF, H * DSF],
    }))
    print(f"captured {n} shots ({sum(holds)} frames) at {W}x{H} into {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/frames"))

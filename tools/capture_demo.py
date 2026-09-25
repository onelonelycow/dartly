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

ROOT = Path(__file__).resolve().parent.parent

from playwright.sync_api import sync_playwright

# The social cuts are 9:16, so that stays the default. A product demo for a
# site or an email is 16:9, and the board is a different layout at that width
# — past 1440 the dashboard lays its cards out two across — so the landscape
# capture is not a crop of this one, it is a different page. Pass WxH to pick.
W, H = 1080, 1920
DSF = 2                 # device scale factor: frames land at 2x the viewport
SEARCH = "GTM"

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


# ---------------------------------------------------------------------------
# REDACTION, BEFORE THE SHUTTER RATHER THAN AFTER.
#
# The settings page is the best unfilmed argument the product has — what you
# do, the words that matter, the budget floor, and the channels an alert can
# reach you on. It also carries things that must never be on a public video,
# and blurring them in post is not good enough: the pixels would still have
# existed, in a file, on a machine, before someone drew a box over them.
#
# So the page is edited in the DOM first and photographed second. What goes:
#
#   .pane-acct        the whole Account tab, REMOVED rather than hidden. It
#                     holds the private forwarding address — a live inbox that
#                     anyone reading it off a frame could post gigs into — plus
#                     the account email and plan. The tabs are CSS radios, so
#                     every pane is in the document whether or not it is on
#                     screen; deleting it means a mis-aimed full-page shot
#                     cannot catch it either.
#   alert channels    a real phone number, and Discord/Slack/Telegram
#                     credentials. Anyone with that webhook can post into the
#                     channel. Replaced with plausible values so the settings
#                     still look configured rather than empty, because an empty
#                     form argues the opposite of the point.
#   any address       a belt-and-braces sweep for anything email-shaped left
#                     anywhere on the page, in case a field moves later.
#
# The number is a FULL, correctly formatted one rather than a stub: a
# half-number on screen reads as a bug in the product, which is the opposite
# of what a demo is for. 555-01xx is the range reserved for fiction precisely
# so it cannot ring anybody, and the area code is Seattle's, which suits the
# audience. It looks real and can never reach a person.
REDACT = """
document.querySelectorAll('.pane-acct').forEach(function (el) { el.remove(); });

var fake = {
  sms_to: '+1 206 555 0134',
  discord_webhook: 'https://hooks.slack.com/services/T000/B000/xxxxxxxx',
  telegram_token: '0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  telegram_chat: '100000000'
};
Object.keys(fake).forEach(function (id) {
  var el = document.getElementById(id);
  if (el) { el.value = fake[id]; el.setAttribute('value', fake[id]); }
});

// BOTH the property and the attribute. Setting el.value alone leaves the
// original in the serialised HTML — the input renders redacted while the real
// address is still sitting in the markup, which fails the whole point of
// editing before the shutter rather than blurring after.
var EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g;
document.querySelectorAll('input').forEach(function (el) {
  if (el.value && el.value.match(EMAIL)) {
    el.value = 'you@example.com';
    el.setAttribute('value', 'you@example.com');
  }
});
var walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
var node;
while ((node = walk.nextNode())) {
  if (node.nodeValue && node.nodeValue.match(EMAIL)) {
    node.nodeValue = node.nodeValue.replace(EMAIL, 'you@example.com');
  }
}
"""


def capture_settings(out: Path, auth: Path):
    """
    The settings tab, signed in, with everything private taken out first.

    Only ONE tab is ever opened: "Your feed", which is where the feed rules and
    the alert channels live. Account is never navigated to and is deleted from
    the page besides.

    READ-ONLY. This navigates, scrolls and photographs. It does not click save,
    upload, delete or sign out — the session belongs to the owner account and
    nothing here should be able to change it.
    """
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    holds, n = [], 0

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H},
                            device_scale_factor=DSF,
                            storage_state=str(auth))
        pg = ctx.new_page()
        # Straight to the one tab. `tab` is read by web/main.py and only
        # 'board' and 'acct' are honoured, so this deep-links past Account
        # rather than clicking through it.
        pg.goto("https://board.nabbly.co/profile?tab=board",
                wait_until="networkidle", timeout=45000)
        pg.wait_for_timeout(400)
        if pg.locator(".pane-board").count() == 0:
            b.close()
            raise SystemExit("not signed in — run tools/capture_login.py first")
        pg.evaluate(REDACT)

        def shot(hold=1):
            nonlocal n
            pg.screenshot(path=out / f"{n:04d}.png")
            holds.append(hold)
            n += 1

        shot(30)                                   # the settings, as they sit
        for _ in range(12):                        # down through the rules
            pg.mouse.wheel(0, 96)
            pg.wait_for_timeout(20)
            shot(1)
        shot(26)                                   # rest on the alert channels

        b.close()

    (out / "holds.json").write_text(json.dumps(holds))
    print(f"captured {n} settings shots ({sum(holds)} frames) into {out}")


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

        # THE JOURNEY CHANGED WITH THE SITE. The board was redesigned on
        # 2026-08-23: the dashboard lost its search bar entirely and grew a
        # category rail, and search now lives on /gigs. Opening on the
        # dashboard and NAVIGATING to Gigs is both what a visitor actually does
        # and the only route that still reaches a search box.
        # ONE PAGE FOR THE WHOLE SEARCH BEAT. The dashboard grew its own working
        # search box (form action="/", stays on the dashboard) — the founder's
        # "search within your feed" pass. The first cut established the
        # dashboard's search bar, then cut away to a DIFFERENT search box on
        # /gigs to actually type into, which read as a mistake: the thing you
        # were just shown is not the thing that moved. Typing into the same box
        # the establishing shot lingers on removes the cut entirely for this
        # beat — the video only switches pages when the story does (dashboard
        # to the full board, after a result is picked).
        pg.goto("https://board.nabbly.co/", wait_until="networkidle", timeout=45000)
        pg.wait_for_timeout(400)
        strip(pg)
        shot(pg, 30)                                    # the hero, cold open

        box = pg.locator("input[name='q']").first
        box.click()
        row = box.evaluate("""el => {
          const f = el.closest('form') || el.parentElement;
          const r = f.getBoundingClientRect();
          return {x: r.x, y: r.y, width: r.width, height: r.height};
        }""")
        zoom_from = n
        for ch in SEARCH:                               # a frame per keystroke
            box.type(ch, delay=0)
            shot(pg, 2)
        shot(pg, 10)
        zoom_to = n - 1

        pg.keyboard.press("Enter")
        pg.wait_for_load_state("networkidle", timeout=45000)
        pg.wait_for_timeout(300)
        strip(pg)
        shot(pg, 24)                                    # results, still on "/"

        # THE RESULTS ARE WHERE THE GIG GETS PICKED, so the scroll and the
        # choice both stay on "/". The cut to /gigs used to happen here, before
        # the card was chosen — and navigating there drops the query, so the
        # capture scrolled an UNFILTERED board and the matcher below never
        # found a title containing the search term. It fell through to its
        # positional default every time: a demo that types "go-to-market" and
        # then hands the reply cut a translation gig.
        #
        # The comment above this block already described the right order —
        # switch pages "after a result is picked". This is that order.
        for _ in range(14):                             # scroll the real page
            pg.mouse.wheel(0, 88)
            pg.wait_for_timeout(20)
            shot(pg, 1)
        shot(pg, 26)                                    # rest on a gig

        # THE CARD ALSO HAS TO BE WORTH REPLYING TO. Matching the search was
        # not enough on its own: "Go-To-Market (GTM) Specialist" is the top
        # title match for a GTM search and its whole posting is 95 characters
        # of boilerplate. The next beat claims the reply was written FROM the
        # posting, so a card with nothing in it quietly disproves the thing the
        # video exists to show. A body threshold picks the first result that
        # both matches and has something to answer.
        #
        # Tokens under three characters are ignored. "go to market" split into
        # "go"/"to"/"market", and "to" matches the "cto" inside "Director" —
        # which is how a Managing Director posting once qualified as a
        # go-to-market result.
        MIN_BODY = 250
        cards = pg.locator(".gr-cardwrap")
        count = cards.count()
        terms = [t.lower() for t in SEARCH.split() if len(t) >= 3]
        idx, first_match = 3, None
        for i in range(min(count, 12)):
            c = cards.nth(i)
            title = (c.locator(".gr-title").text_content() or "").lower()
            if not any(t in title for t in terms):
                continue
            if first_match is None:
                first_match = i
            body = c.evaluate("el => (el.querySelector('.gr-full') || "
                              "el.querySelector('.gr-body'))?.textContent || ''")
            if len(body.strip()) >= MIN_BODY:
                idx = i
                break
        else:
            idx = first_match if first_match is not None else idx
            print(f"  ! no match with a {MIN_BODY}+ char posting; "
                  f"using card {idx}", flush=True)
        card = cards.nth(idx)
        card.scroll_into_view_if_needed()
        pg.wait_for_timeout(150)
        shot(pg, 12)

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
        "search_rect": [row["x"] * DSF, row["y"] * DSF,
                        (row["x"] + row["width"]) * DSF,
                        (row["y"] + row["height"]) * DSF],
        "shots": [zoom_from, zoom_to],
        "master": [W * DSF, H * DSF],
    }))
    print(f"captured {n} shots ({sum(holds)} frames) at {W}x{H} into {out}")


if __name__ == "__main__":
    # capture_demo.py <out_dir> [WxH] [--settings]
    argv = sys.argv[1:]
    settings = "--settings" in argv
    if settings:
        argv.remove("--settings")
    size = next((a for a in argv if "x" in a
                 and all(p.isdigit() for p in a.split("x", 1))), None)
    if size:
        argv.remove(size)
        W, H = (int(v) for v in size.split("x"))
    target = Path(argv[0] if argv else "/tmp/frames")
    if settings:
        auth = ROOT / "auth.json"
        if not auth.exists():
            raise SystemExit(f"no {auth} — run tools/capture_login.py first")
        capture_settings(target, auth)
    else:
        main(target)

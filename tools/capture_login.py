"""
capture_login.py — sign in ONCE, by hand, so the capture can reach signed-in pages.

capture_demo.py deliberately has no session: the signed-out board is all a
crawler-shaped script should be able to see, and nothing here should ever hold
a password. But the pages that carry the actual argument — the settings, the
alert channels, the drafted reply — only exist behind sign-in.

So this opens a REAL browser window and gets out of the way. You sign in
yourself, with your own hands, on the real site. Nothing types credentials for
you and nothing reads them. When you are through, it saves the resulting
session to a file the capture can reuse.

WHAT THE FILE IS. auth.json is a live session cookie for whatever account you
signed into. It is a credential. Treat it like one:

  * it is written to the repo root and gitignored, never committed
  * delete it when the capture is done — `rm auth.json`
  * signing out in a browser does not necessarily kill it; if you want it dead,
    sign out from the account menu on the board itself

WHAT USES IT DOES NOT MAKE. capture_demo.py is read-only against a signed-in
session by design: it navigates, types in a search box, and hovers. It never
clicks save, delete, upload, or sign out. That guarantee matters more when the
session belongs to the owner account, which can see admin surfaces.

Run:  .venv/bin/python tools/capture_login.py
Out:  auth.json  (gitignored)
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "auth.json"
START = "https://board.nabbly.co/signin"

# The capture runs at this size, so sign in at it too: the board lays its
# dashboard out two-up past 1440 and a session saved at a different width is
# not a problem, but seeing the page you will be filming is worth the nothing
# it costs.
W, H = 1920, 1080


def main():
    print("Opening a browser. Sign in as yourself — email code or Google.")
    print("Nothing here types or reads your credentials.")
    print("When the board has loaded and you are signed in, come back and "
          "press Enter.\n")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context(viewport={"width": W, "height": H})
        pg = ctx.new_page()
        pg.goto(START, wait_until="networkidle", timeout=60000)

        input("  press Enter once you are signed in > ")

        # Confirm rather than trust: an account menu only renders for a real
        # session, so this catches "pressed Enter on the sign-in page".
        pg.goto("https://board.nabbly.co/profile", wait_until="networkidle",
                timeout=45000)
        signed_in = pg.locator(".pane-you").count() > 0
        if not signed_in:
            print("\n  /profile did not render its settings — that is the "
                  "signed-out page.\n  Nothing saved. Run this again and "
                  "complete the sign-in first.")
            b.close()
            return 1

        ctx.storage_state(path=str(OUT))
        b.close()

    print(f"\n  saved {OUT}")
    print("  This is a live session cookie. It is gitignored; delete it when "
          "the capture is done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

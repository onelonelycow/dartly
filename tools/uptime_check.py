"""
tools/uptime_check.py — does Nabbly actually work, from outside?

RUN THIS FROM SOMEWHERE THAT IS NOT NABBLY. ops_watch.py lives inside the app
process and watches the DATA — ingest stalling, a source going dark. It cannot
watch whether the app runs, because if the app does not run then neither does
it. That is not a gap in ops_watch; it is what "in-process" means.

That distinction has already cost a real outage. A module named watchdog.py
shadowed Streamlit's watchdog dependency, Streamlit died before executing
app.py, and every visitor got a grey skeleton loader — while /_stcore/health
answered 200 the entire time, because that endpoint is served by tornado and
never touches the script. An in-process monitor would have been dead alongside
it.

SO THIS CHECKS WHAT A VISITOR GETS, NOT WHAT THE SERVER ADMITS:

  * the app — opens a real Streamlit session over a websocket and waits for the
    script to finish. Anything less (HTTP 200, the HTML shell, the page title)
    is served without the script running and reports a dead app as healthy.
    The shell's <title> is literally "Streamlit" on a HEALTHY app; the browser
    rewrites it only once the script runs, so it is useless as a signal.
  * the board service — /health, which reports its own row count and how far
    its copy has drifted from the mirror. Zero rows is unhealthy however
    cheerfully the process is answering.
  * the static site — the pages outreach points at.

Exits non-zero if anything is wrong, which is what makes it usable as a cron:
a failing scheduled job emails whoever owns it, with no alerting to build.
"""
import asyncio
import json
import ssl
import sys
import time
import urllib.request

APP = "https://app.nabbly.co"
BOARD = "https://nabbly-board.onrender.com"
SITE = "https://nabbly.co"

RENDER_TIMEOUT_S = 90      # a cold Render instance can take a while to wake
MAX_DRIFT_S = 600          # the board syncs every 60s; 10 minutes is broken
ATTEMPTS = 3               # one blip is not an outage

# HOW LONG A DEPLOY IS ALLOWED TO TAKE BEFORE IT COUNTS AS A STUCK SERVICE.
#
# This was 45s x 3 attempts = 90s, written when a boot pull took ~50s. The
# board has grown since; full_sync() was measured at 73s for 65,348 rows on a
# laptop with a fast connection on 2026-08-19, and Render is slower than that.
# So the budget had quietly fallen below a normal boot, and every deploy that
# overlapped a scheduled run reported an outage that was not happening — twice
# in half an hour that day, both of them 90 seconds after a push.
#
# 6 x 45s = 270s. That is roughly three times a measured boot, which leaves
# room for the board to keep growing before this needs looking at again. A
# board that is genuinely stuck stays stuck, so the only thing a longer budget
# costs is finding out about it one cycle later.
BOOT_ATTEMPTS = 7
BOOT_WAIT_S = 45

# WATCHING THE GAP, SO THE BUDGET ABOVE CANNOT QUIETLY DRIFT UNDER A BOOT AGAIN.
#
# The budget has been wrong once already, and HOW it went wrong is the part
# worth fixing: it was correct when written, the board grew, and nothing was
# comparing the two. ROADMAP.md records the same shape of failure against the
# scaling ceiling. Raising the number fixes today and rebuilds the same trap.
#
# So the check now reports how much of its own budget a real boot used. This
# costs nothing to measure: the retry loop below is ALREADY waiting out boots
# and already knows how many rounds it waited, and that number was simply being
# discarded. Nothing extra is fetched, no rows are pulled from the mirror, and
# the board is never restarted to take a reading. The only boots measured are
# ones that were going to happen anyway, on a deploy.
#
# Two thresholds, because "getting close" and "about to break" deserve
# different answers:
#   NOTE — printed, run still passes. Early visibility, no inbox noise.
#   WARN — reported as a problem, so the job fails and mails. This is NOT an
#          outage and the message says so. It means the budget has nearly
#          fallen under a real boot and is about to start crying wolf on every
#          deploy, which is worth an email precisely BECAUSE it arrives before
#          the false alarms do.
BOOT_BUDGET_S = BOOT_WAIT_S * (BOOT_ATTEMPTS - 1)
BOOT_NOTE_FRACTION = 0.50
BOOT_WARN_FRACTION = 0.80


def _ssl_ctx():
    """
    certifi's roots when available, the system's otherwise.

    macOS python.org builds ship without a usable CA bundle, so every HTTPS
    call here failed with CERTIFICATE_VERIFY_FAILED and this check reported the
    whole site down while it was perfectly fine. A monitor that cries wolf on
    the machine you run it from is a monitor you stop running.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "nabbly-uptime/1"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as r:
        return r.status, r.read()


async def _render_once() -> tuple[float, int]:
    """Open a real session and run the script. Returns (seconds, deltas)."""
    import certifi
    import websockets
    from streamlit.proto.BackMsg_pb2 import BackMsg
    from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

    ctx = ssl.create_default_context(cafile=certifi.where())
    msg = BackMsg()
    # NOT A BARE VISIT ANY MORE. app.nabbly.co forwards a signed-out visitor
    # with no query string to the board now, so a bare render draws a meta
    # refresh and one line — two elements — and this check read that as the
    # app drawing nothing. It failed twice on 2026-09-02 for exactly that.
    #
    # ?nav=signin is a page the app still owns and still renders in full, so
    # the check keeps doing its actual job: proving Streamlit executed app.py
    # rather than serving a skeleton with a healthy /_stcore/health behind it.
    msg.rerun_script.query_string = "nav=signin"
    msg.rerun_script.page_script_hash = ""
    t0 = time.monotonic()
    url = APP.replace("https://", "wss://") + "/_stcore/stream"
    async with websockets.connect(url, subprotocols=["streamlit"], max_size=None,
                                  open_timeout=RENDER_TIMEOUT_S, ssl=ctx) as ws:
        await ws.send(msg.SerializeToString())
        deltas = 0
        while True:
            fm = ForwardMsg()
            fm.ParseFromString(await asyncio.wait_for(ws.recv(),
                                                      timeout=RENDER_TIMEOUT_S))
            kind = fm.WhichOneof("type")
            if kind == "delta":
                deltas += 1
            elif kind == "script_finished":
                name = ForwardMsg.ScriptFinishedStatus.Name(fm.script_finished)
                if name == "FINISHED_SUCCESSFULLY":
                    return time.monotonic() - t0, deltas
                raise RuntimeError(f"script finished as {name}")


def check_app() -> list[str]:
    last = ""
    for i in range(ATTEMPTS):
        try:
            secs, deltas = asyncio.run(_render_once())
            if deltas < 5:
                return [f"app rendered but produced only {deltas} elements — "
                        f"the script ran and drew almost nothing"]
            print(f"  app      OK   rendered in {secs:.1f}s, {deltas} elements")
            return []
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if i < ATTEMPTS - 1:
                time.sleep(10)
    return [f"app never rendered a page ({last}). HTTP may still answer 200 — "
            f"that endpoint does not run the script."]


def check_board() -> list[str]:
    """
    A DEPLOY IS NOT AN OUTAGE, and this is where that distinction lives.

    The board binds its port immediately and fills itself from the mirror
    behind that, which takes over a minute and is reported honestly as
    status="starting". The first version of this check saw ok=false and paged
    — on a completely normal deploy. A monitor that fires every time you ship
    is one you learn to ignore, and then it is worth nothing on the day it
    matters.

    So "starting" is retried rather than reported. A boot that is STILL going
    after every attempt is a real problem — that is a service stuck, not a
    service starting — and it does get reported.
    """
    data, last_err = None, ""
    # Wall clock, not attempts x BOOT_WAIT_S: the /health request itself takes
    # real time, and on a cold Render instance the first one can take most of a
    # minute. Counting sleeps alone would undercount a boot and report a
    # comfortable margin that is not there.
    started_at = time.monotonic()
    saw_boot = False
    for i in range(BOOT_ATTEMPTS):
        try:
            _, body = _get(f"{BOARD}/health")
            data = json.loads(body)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            data = None
        if data is not None and data.get("status") == "starting":
            saw_boot = True
        if data is not None and data.get("status") != "starting":
            break
        if i < BOOT_ATTEMPTS - 1:
            time.sleep(BOOT_WAIT_S)
    boot_took_s = time.monotonic() - started_at
    if data is None:
        return [f"board service unreachable: {last_err}"]

    problems = []
    rows = int(data.get("rows") or 0)
    drift = data.get("drift_s")
    if data.get("status") == "starting":
        return [f"board has been starting for over "
                f"{BOOT_WAIT_S * (BOOT_ATTEMPTS - 1)}s — the boot sync is stuck, "
                f"not slow: {json.dumps(data)}"]
    if not data.get("ok"):
        problems.append(f"board reports unhealthy: {json.dumps(data)}")
    if rows <= 0:
        problems.append("board is serving ZERO gigs — is DATABASE_URL set?")
    if drift is not None and drift > MAX_DRIFT_S:
        problems.append(f"board has not synced in {drift}s — its copy is going stale")
    # Only meaningful when a boot was actually caught in progress. On the runs
    # where the board was already up (most of them) there is nothing to measure
    # and nothing is said, which is what keeps this quiet.
    if saw_boot:
        used = boot_took_s / BOOT_BUDGET_S
        detail = (f"boot took {boot_took_s:.0f}s of a {BOOT_BUDGET_S}s budget "
                  f"({used:.0%}), with {rows:,} gigs to load")
        if used >= BOOT_WARN_FRACTION:
            problems.append(
                f"BUDGET, NOT AN OUTAGE: {detail}. The board is fine. Raise "
                f"BOOT_ATTEMPTS in tools/uptime_check.py before this drops "
                f"under a real boot and starts failing on every deploy.")
        elif used >= BOOT_NOTE_FRACTION:
            print(f"  board    NOTE {detail} — worth raising the budget soon")

    if not problems:
        # drift is null immediately after a boot, before the first sync lands,
        # and "Nones behind the mirror" is what that printed.
        behind = "not synced yet" if drift is None else f"{drift}s behind the mirror"
        print(f"  board    OK   {rows:,} gigs, {behind}")
    return problems


def check_site() -> list[str]:
    problems = []
    for path in ("/", "/freelance-writing-jobs/", "/faq.html"):
        try:
            status, body = _get(SITE + path)
            if status != 200:
                problems.append(f"{path} returned HTTP {status}")
            elif len(body) < 2000:
                problems.append(f"{path} returned only {len(body)} bytes")
        except Exception as e:
            problems.append(f"{path} unreachable: {type(e).__name__}: {e}")
    if not problems:
        print("  site     OK   homepage, a field page and the FAQ all serving")
    return problems


def main() -> int:
    print("Nabbly uptime check")
    problems = check_app() + check_board() + check_site()
    if not problems:
        print("\nEverything is up.")
        return 0
    print("\nPROBLEMS:")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""
refresh.py — free "live while in use" auto-refresh, and the alert trigger.

Starts ONE background daemon thread per server process that periodically fetches
new gigs, so the feed grows on its own while the app is being used. Paired with a
timed re-read on the dashboard, the numbers climb without anyone clicking.

It also fires the alerts. Without this, "every gig, the moment it drops" was only
true if you happened to be running watch.py on your own Mac — the live site
gathered gigs around the clock and never told anyone about them.

Free-tier reality: when the instance goes idle it sleeps and this pauses; on the
next wake it restarts from the bundled seed (persistence needs a paid always-on
plan). That's the tradeoff we chose for $0.
"""
import threading
import time

_INTERVAL_S = 120          # ~2 min between fetches
_FIRST_DELAY_S = 30        # let the app finish booting before the first pull
_ALERT_MIN_GAP_S = 900     # fallback gap if prefs can't be read (see _loop)
_started = False
_lock = threading.Lock()
_state = {"runs": 0, "last": None, "alerted": 0, "last_alert": None}


def _baseline():
    """
    Mark everything already on the board as old news, silently.

    The bundled seed ships ~1,500 gigs and none are flagged as alerted, so
    without this the very first pass would treat the whole board as brand new
    and fire one alert announcing thousands of gigs. That's wrong, and on SMS
    it costs real money. After this runs, only genuinely new arrivals can
    trigger anything.
    """
    import db
    try:
        db.mark_alerted([p["id"] for p in db.unalerted()])
    except Exception:
        pass


def _loop():
    import ingest
    import alerts
    time.sleep(_FIRST_DELAY_S)
    _baseline()
    last_alert = 0.0

    while True:
        try:
            ingest.run()
            _state["runs"] += 1
            _state["last"] = time.time()

            # Batch anything that landed since the last ping. The fetch runs
            # every 2 minutes, but pinging that often all day is how people end
            # up muting you, so the gap is the user's call now — read fresh
            # each loop so a change on the Alerts page takes effect without a
            # restart.
            try:
                gap = max(1, int(alerts.load_prefs().get("every_min") or 15)) * 60
            except Exception:
                gap = _ALERT_MIN_GAP_S
            if time.time() - last_alert >= gap:
                # desktop=False: the pop-up shells out to osascript, which only
                # exists on the owner's Mac. The server is Linux.
                n = alerts.notify_new(desktop=False)
                if n:
                    _state["alerted"] += n
                    _state["last_alert"] = time.time()
                last_alert = time.time()
        except Exception:
            pass  # a bad fetch or a dead webhook shouldn't kill the loop
        time.sleep(_INTERVAL_S)


def start():
    """Idempotent — safe to call on every Streamlit rerun; only one thread runs."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
        threading.Thread(target=_loop, daemon=True, name="nabbly-refresh").start()


def state() -> dict:
    return dict(_state)

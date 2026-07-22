"""
refresh.py — free "live while in use" auto-refresh.

Starts ONE background daemon thread per server process that periodically fetches
new gigs, so the feed grows on its own while the app is being used. Paired with a
timed re-read on the dashboard, the numbers climb without anyone clicking.

Free-tier reality: when the instance goes idle it sleeps and this pauses; on the
next wake it restarts from the bundled seed (persistence needs a paid always-on
plan). That's the tradeoff we chose for $0.
"""
import threading
import time

_INTERVAL_S = 120          # ~2 min between fetches
_FIRST_DELAY_S = 30        # let the app finish booting before the first pull
_started = False
_lock = threading.Lock()
_state = {"runs": 0, "last": None}


def _loop():
    import ingest
    time.sleep(_FIRST_DELAY_S)
    while True:
        try:
            ingest.run()
            _state["runs"] += 1
            _state["last"] = time.time()
        except Exception:
            pass  # a bad fetch shouldn't kill the loop
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

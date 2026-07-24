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


def _loop():
    import ingest
    import alerts
    import accounts
    import paths
    time.sleep(_FIRST_DELAY_S)
    # Old news is handled per person now: each account remembers the highest
    # gig id it has been alerted about, and a new account starts that marker at
    # the current top of the board. So there's no global "mark everything
    # alerted" step to run here any more — it would have written a flag nothing
    # on the server reads. (watch.py, the local single-user poller, still uses
    # the global path and does its own baselining.)
    paths.prune_scratch()
    # Re-tag the existing board once, so a classifier change reaches gigs that
    # are already stored (new ingests are classified correctly on the way in).
    # Cheap and idempotent: a second pass finds nothing to change.
    try:
        import db
        _state["reclassified"] = db.reclassify_all()
    except Exception:
        pass
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
                # Shortest gap anyone has asked for, so a user who wants alerts
                # every 5 minutes isn't held to someone else's hourly setting.
                gaps = []
                for _a in accounts.all_accounts():
                    paths.set_scope(paths.scope_for(_a["email"]))
                    gaps.append(max(1, int(alerts.load_prefs().get("every_min") or 15)))
                gap = (min(gaps) if gaps else 15) * 60
            except Exception:
                gap = _ALERT_MIN_GAP_S
            # Mirror traffic to the durable store each cycle. Cheap (one small
            # record per day) and it means a redeploy can't wipe the history.
            try:
                import analytics
                analytics.flush()
            except Exception:
                pass

            if time.time() - last_alert >= gap:
                # One pass per signed-in person, each against their own skills
                # and their own channels. notify_new() is the single-user path
                # and reads whichever profile the thread happens to be scoped
                # to, which in a background thread is nobody's.
                n = alerts.notify_everyone(desktop=False)
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

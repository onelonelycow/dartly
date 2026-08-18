"""
ops_watch.py — tells the owner when Nabbly quietly stops working.

NAMED ops_watch, NOT watchdog, AND IT MATTERS. This file was called
watchdog.py for one deploy and took the live app down: Streamlit's file
watcher does `from watchdog.observers import Observer`, a module in the app
directory shadows the installed package, and Streamlit died before running
app.py. Every visitor got a skeleton loader and a tab titled "Streamlit"
while /_stcore/health kept answering 200, because that endpoint never touches
the script. Do not rename this back, and think twice before adding any
top-level module that shares a name with a dependency.

THE GAP THIS CLOSES. Every failure mode below is currently silent. Ingest can
stop, the biggest source can die, the durable mirror can become unreachable,
and nothing says so — the log keeps printing healthy cycles because the OTHER
sources still work, the board slowly goes stale, and the first report comes
from a person mentioning the gigs look old. sources.health() has existed for
days and is read in exactly one place: the admin page. A dashboard nobody
opens is not monitoring.

WHAT IT WATCHES, and why each one is worth an email:

  * ingest stalled — no new gig in STALL_HOURS. The board's whole promise is
    "the moment it drops", so this is the failure that matters most.
  * a source gone dark — one that normally delivers has delivered nothing in
    DARK_HOURS. Himalayas alone is 41% of the board; losing it would not dent
    the cycle count but would hollow out the board.
  * the mirror unreachable — the app keeps serving from local disk and looks
    fine, right up until a deploy wipes that disk and takes everything with it.
  * repeated cycle failures — refresh.py already counts them; nobody reads it.

RULES IT FOLLOWS, because a noisy monitor gets muted and a muted monitor is
worse than none:

  * one email per incident, not per check. State lives in the durable KV store,
    NOT on disk — Render wipes the disk on deploy, and a watchdog that forgets
    on every deploy re-alerts on every deploy until it is turned off.
  * an issue that clears is recorded as cleared, so the next occurrence is a
    new incident and does get an email.
  * it never raises. A monitor that can break the thing it monitors is a
    liability, so every path is wrapped and failure means "no alert", never "no
    ingest".
"""
import os
import time
from datetime import datetime, timedelta, timezone

import store

# Where alerts go. Unset = the watchdog is off, which is the honest default for
# a fork or a local checkout: mailing a stranger's inbox on someone else's
# schedule is worse than staying quiet.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "").strip()

STALL_HOURS = 3        # no new gig at all — ingest runs every ~2 minutes
DARK_HOURS = 24        # a normally-productive source delivering nothing
DARK_MIN_PER_DAY = 20  # only watch sources big enough for silence to mean something
RECHECK_S = 1800       # how often check() is worth running
COOLDOWN_H = 12        # never re-send the same open incident inside this
COOLDOWN_MAX_H = 168   # ...and back off to at most weekly while it stays open

_SCOPE = "_ops"
_KEY = "watchdog"
_last_run = 0.0


def enabled() -> bool:
    return bool(OWNER_EMAIL) and store.enabled()


def _state() -> dict:
    try:
        return store.get(_SCOPE, _KEY) or {}
    except Exception:
        return {}


def _save(state: dict):
    try:
        store.put(_SCOPE, _KEY, state)
    except Exception:
        pass


def _mirror_counts():
    """(total live rows, newest fetched_at) from the durable mirror."""
    import board_store
    conn, ph = store._connect()
    try:
        board_store._ensure(conn)
        row = conn.execute(
            f"SELECT COUNT(*), MAX(fetched_at) FROM {board_store._TABLE} "
            f"WHERE is_demand = 1").fetchone()
        return int(row[0] or 0), (row[1] or "")
    finally:
        conn.close()


def _per_source(hours: int):
    """{source: rows fetched in the last `hours`} plus each source's total."""
    import board_store
    cut = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn, ph = store._connect()
    try:
        board_store._ensure(conn)
        rows = conn.execute(
            f"SELECT source, COUNT(*), "
            f"SUM(CASE WHEN fetched_at >= {ph} THEN 1 ELSE 0 END) "
            f"FROM {board_store._TABLE} GROUP BY source", (cut,)).fetchall()
        return {r[0]: (int(r[1] or 0), int(r[2] or 0)) for r in rows if r[0]}
    finally:
        conn.close()


def _expected_sources() -> set:
    """
    The source names we still actually ask for.

    Resolved through each feed spec's own `source` field because the enabled
    list is not the same as the names rows are stamped with: thirteen
    jobicy_* keys and six wwr_* keys all write rows as "jobicy" and
    "weworkremotely". Comparing the raw key list against the data would report
    nineteen dead sources that are all working perfectly.

    Empty on any failure, which the caller reads as "watch everything" — a
    missing config should not silently switch the monitor off.
    """
    try:
        import config
        out = set()
        for key in config.ENABLE_SOURCES:
            spec = config.RSS_SOURCES.get(key) or {}
            out.add(spec.get("source") or key)
        return out
    except Exception:
        return set()


def _age_hours(iso: str) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return None


def check() -> list[dict]:
    """
    Everything currently wrong. Each is {key, title, detail} — `key` identifies
    the INCIDENT so the same problem is not mailed twice.
    """
    out = []
    try:
        live, newest = _mirror_counts()
    except Exception as e:
        # The mirror being unreachable IS the alert. The app keeps serving from
        # local disk and looks fine until a deploy wipes it.
        return [{"key": "mirror-unreachable",
                 "title": "The durable mirror is unreachable",
                 "detail": f"{type(e).__name__}: {e}\n\n"
                           "Nabbly keeps serving from local disk while this is "
                           "true, and loses everything the next time it deploys."}]

    age = _age_hours(newest)
    if age is None:
        out.append({"key": "no-timestamp",
                    "title": "No readable timestamp on the newest gig",
                    "detail": f"MAX(fetched_at) came back as {newest!r}."})
    elif age > STALL_HOURS:
        out.append({"key": "ingest-stalled",
                    "title": f"No new gigs for {age:.0f} hours",
                    "detail": f"The newest gig on the board arrived {age:.1f} "
                              f"hours ago. Ingest runs every couple of minutes, "
                              f"so this means it has stopped, not that it is "
                              f"quiet.\n\nBoard: {live:,} live gigs."})

    try:
        by_src = _per_source(DARK_HOURS)
    except Exception:
        by_src = {}
    expected = _expected_sources()
    dark = [(s, tot) for s, (tot, recent) in by_src.items()
            # Only sources we still ASK for. A disabled source is supposed to
            # be silent, and alerting on it is how a monitor earns the reply
            # "it always says that" — reddit tripped this on the first run,
            # 10 days after it was switched off on purpose.
            if recent == 0 and tot >= DARK_MIN_PER_DAY * 7
            and (not expected or s in expected)]
    for src, tot in sorted(dark, key=lambda x: -x[1]):
        share = (tot / live * 100) if live else 0
        # "0% of the board" for a source holding 293 gigs reads as a rounding
        # bug and makes the whole alert easier to dismiss. Small shares get a
        # decimal; genuinely tiny ones say so in words.
        share_txt = (f"{share:.0f}%" if share >= 10 else
                     f"{share:.1f}%" if share >= 0.1 else "under 0.1%")
        out.append({
            "key": f"source-dark:{src}",
            "title": f"{src} has delivered nothing in {DARK_HOURS} hours",
            "detail": f"{src} holds {tot:,} gigs ({share_txt} of the board) and "
                      f"has added none since yesterday. The cycle count will "
                      f"still look healthy because the other sources are "
                      f"working."})
    return out


def run(force: bool = False) -> int:
    """
    Check, and email anything new. Returns how many alerts were sent.

    Safe to call from the fetch loop on every cycle — it rate-limits itself and
    never raises.
    """
    global _last_run
    if not enabled():
        return 0
    if not force and time.time() - _last_run < RECHECK_S:
        return 0
    _last_run = time.time()
    try:
        issues = check()
        state = _state()
        open_now = {i["key"] for i in issues}
        now = time.time()
        sent = 0

        for issue in issues:
            # BACKS OFF INSTEAD OF NAGGING. A flat 12-hour cooldown meant an
            # incident that stays true keeps arriving twice a day forever:
            # entcareers went dark for three days and that is six identical
            # emails about one thing nobody can fix twice. The first one is the
            # useful one; the tenth teaches you to filter the sender, which is
            # how a monitor stops working without anybody switching it off.
            #
            # So the gap doubles each time: 12h, 24h, 48h, 96h, then capped at
            # a week. Still audible if it drags on, no longer shouting. The
            # count resets when the incident clears, because a recurrence is
            # news again.
            prev = state.get(issue["key"]) or {}
            if not isinstance(prev, dict):        # pre-2026-08-18 state: a bare timestamp
                prev = {"at": float(prev or 0), "n": 1}
            wait = min(COOLDOWN_H * (2 ** max(0, prev.get("n", 1) - 1)),
                       COOLDOWN_MAX_H) * 3600
            if now - float(prev.get("at", 0)) < wait:
                continue          # already told them, and it is still true
            if _send(issue):
                state[issue["key"]] = {"at": now, "n": prev.get("n", 0) + 1}
                sent += 1

        # Forget anything that has cleared, so its next occurrence is a NEW
        # incident and does get an email rather than being suppressed by a
        # cooldown from last week.
        for key in [k for k in state if k not in open_now]:
            state.pop(key, None)
        _save(state)
        return sent
    except Exception:
        return 0          # a monitor must never break what it monitors


def _send(issue: dict) -> bool:
    try:
        import mailer
        if not mailer.enabled():
            return False
        subject = f"Nabbly: {issue['title']}"
        text = (f"{issue['title']}\n\n{issue['detail']}\n\n"
                f"— Nabbly watchdog, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
        html_body = (
            f'<div style="font-family:system-ui,-apple-system,sans-serif;'
            f'max-width:520px;color:#1a1d23;line-height:1.6">'
            f'<p style="font-weight:650;font-size:16px;margin:0 0 10px">'
            f'{issue["title"]}</p>'
            f'<p style="white-space:pre-wrap;margin:0 0 16px">{issue["detail"]}</p>'
            f'<p style="color:#6b7280;font-size:12px;margin:0">Nabbly watchdog · '
            f'{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC</p></div>')
        return bool(mailer.send(OWNER_EMAIL, subject, html_body, text))
    except Exception:
        return False


if __name__ == "__main__":
    # dotenv BEFORE store is re-read: store.py resolves DATABASE_URL at import
    # time, so loading the env after importing it leaves the connection
    # disabled and every check reports a healthy-looking empty board. Same trap
    # that made the field-page generator build from stale local data for weeks.
    import importlib

    from dotenv import load_dotenv
    load_dotenv()
    importlib.reload(store)
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "").strip()
    print(f"owner: {OWNER_EMAIL or '(unset — watchdog off)'}")
    print(f"store reachable: {store.enabled()}\n")
    issues = check()
    if not issues:
        print("nothing wrong.")
    for i in issues:
        print(f"  [{i['key']}] {i['title']}")
        for line in i["detail"].splitlines():
            if line.strip():
                print(f"      {line}")

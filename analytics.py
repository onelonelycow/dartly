"""
analytics.py — who showed up, what they did, and who raised their hand.

Two jobs:

  1. VISITS   — count sessions and which views people open, so you can answer
                "did anyone actually come, and did they look around?"
  2. SIGNUPS  — capture an email plus the one question that matters:
                would you pay for this?

Deliberately NOT a third-party script. Streamlit strips <script> tags from the
main page, so Google Analytics and friends can't run there without ugly hacks.
Doing it in Python is boring, reliable, cookie-free, and it can see things an
off-the-shelf tracker never could (which category was clicked, whether someone
generated a draft).

WHERE IT LIVES: its own SQLite file, separate from the gig database, so
reseeding the gigs never wipes your signups.

IMPORTANT — surviving redeploys: on Render's free tier the disk is wiped every
deploy, so this data resets. Two ways to make it permanent:
  • set DATA_DIR to a mounted persistent disk (see paths.py), or
  • set SIGNUP_WEBHOOK_URL and every signup is also POSTed there the moment it
    happens (a Zapier/Make catch hook, a Google Apps Script, a form endpoint).
The webhook is the belt-and-braces option: even if the disk vanishes, the email
already left the building.
"""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from paths import data_file

DB_PATH = data_file("nabbly_signals.db")

# Set this in Render → Environment to mirror every signup somewhere permanent.
WEBHOOK_URL = os.environ.get("SIGNUP_WEBHOOK_URL", "").strip()

# Visit ?admin=<key> to see the numbers. Override in Render → Environment.
ADMIN_KEY = os.environ.get("ADMIN_KEY", "nabbly-admin").strip()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init():
    """Create the two tables the first time we run. Safe to call every time."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT NOT NULL,
            session TEXT,
            event   TEXT NOT NULL,   -- 'session', 'view', 'click', 'signup'
            detail  TEXT             -- which view, which category, etc.
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signups (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            ts    TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pay   TEXT DEFAULT '',   -- 'yes' / 'maybe' / 'no'
            note  TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()


def track(event: str, detail: str = "", session: str = ""):
    """Record one thing that happened. Never allowed to break the page."""
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO events (ts, session, event, detail) VALUES (?,?,?,?)",
            (_now(), session, event, detail[:200]),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass  # analytics must never take the app down


# ---------------------------------------------------------------------------
# Where the traffic came from
# ---------------------------------------------------------------------------
# Referrers arrive as full URLs; we only keep the host, and only long enough to
# answer "is anyone actually coming from Reddit". No paths, no query strings,
# nothing that could identify a person.
_OWN_HOSTS = ("nabbly.co", "localhost", "127.0.0.1", "onrender.com")


def referrer_label(referer: str) -> str:
    """'https://www.reddit.com/r/forhire/x' -> 'reddit.com'. '' -> 'Direct'."""
    ref = (referer or "").strip()
    if not ref:
        return "Direct"
    try:
        from urllib.parse import urlparse
        host = (urlparse(ref).hostname or "").lower().lstrip("www.")
    except Exception:
        return "Other"
    if not host:
        return "Direct"
    if any(host.endswith(h) for h in _OWN_HOSTS):
        return "Direct"          # a click from one Nabbly page to another
    return host[:60]


def device_label(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if not ua:
        return "Unknown"
    if any(k in ua for k in ("iphone", "android", "ipod", "mobile")):
        return "Mobile"
    if "ipad" in ua or "tablet" in ua:
        return "Tablet"
    return "Desktop"


def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match((email or "").strip()))


def add_signup(email: str, note: str = "") -> tuple:
    """
    Save an email. Returns (ok, message).

    A repeat email is treated as success, not an error — someone typing their
    address twice should not be told off.
    """
    email = (email or "").strip().lower()
    if not valid_email(email):
        return False, "That doesn't look like an email address."
    try:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO signups (ts, email, note) VALUES (?,?,?)",
            (_now(), email, note[:500]),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False, "Couldn't save that just now. Try again in a moment."
    _mirror({"type": "signup", "email": email, "note": note, "at": _now()})
    return True, "You're on the list."


def set_pay_answer(email: str, answer: str):
    """Record the would-you-pay answer for someone who already left an email."""
    email = (email or "").strip().lower()
    try:
        conn = _connect()
        conn.execute("UPDATE signups SET pay = ? WHERE email = ?", (answer, email))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return
    _mirror({"type": "pay", "email": email, "pay": answer, "at": _now()})


def _mirror(payload: dict):
    """POST a copy somewhere permanent, if a webhook is configured."""
    if not WEBHOOK_URL:
        return
    try:
        import requests
        requests.post(WEBHOOK_URL, json=payload, timeout=6)
    except Exception:
        pass  # a dead webhook must never block a signup


def _count(conn, sql, *args):
    row = conn.execute(sql, args).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def stats() -> dict:
    """Everything the admin panel needs, in one trip."""
    out = {"sessions": 0, "sessions_24h": 0, "sessions_7d": 0, "views": [],
           "clicks": [], "signups": 0, "pay": {}, "started": ""}
    try:
        conn = _connect()
        day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
        week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")

        out["sessions"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events WHERE event='session'")
        out["sessions_24h"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts >= ?", day)
        out["sessions_7d"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts >= ?", week)
        out["views"] = [(r["detail"], r["n"]) for r in conn.execute(
            "SELECT detail, COUNT(*) n FROM events WHERE event='view' "
            "GROUP BY detail ORDER BY n DESC")]
        out["clicks"] = [(r["detail"], r["n"]) for r in conn.execute(
            "SELECT detail, COUNT(*) n FROM events WHERE event='click' "
            "GROUP BY detail ORDER BY n DESC LIMIT 15")]
        out["signups"] = _count(conn, "SELECT COUNT(*) FROM signups")
        out["pay"] = {r["pay"]: r["n"] for r in conn.execute(
            "SELECT pay, COUNT(*) n FROM signups WHERE pay != '' GROUP BY pay")}
        row = conn.execute("SELECT MIN(ts) t FROM events").fetchone()
        out["started"] = (row["t"] or "") if row else ""
        conn.close()
    except sqlite3.Error:
        pass
    return out


# ---------------------------------------------------------------------------
# Surviving a redeploy
# ---------------------------------------------------------------------------
# The events table lives on Render's disk, which is wiped on every deploy, so
# raw traffic history would reset each time you ship. Rather than write every
# page view straight to Supabase (a network round trip per view would slow the
# page down), we roll each day up into one small record and mirror that. Days
# are immutable once past, so re-sending today's rollup repeatedly is cheap and
# always correct.
_ANALYTICS_SCOPE = "_analytics"


def _day_bounds(day: str):
    return f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00"


def day_rollup(day: str) -> dict:
    """Everything that happened on one UTC day, as a small dict."""
    lo, hi = _day_bounds(day)
    out = {"sessions": 0, "views": {}, "clicks": {}, "refs": {}, "devices": {}}
    try:
        conn = _connect()
        out["sessions"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts BETWEEN ? AND ?", lo, hi)
        for key, ev in (("views", "view"), ("clicks", "click"),
                        ("refs", "ref"), ("devices", "device")):
            out[key] = {r["detail"]: r["n"] for r in conn.execute(
                "SELECT detail, COUNT(*) n FROM events WHERE event=? "
                "AND ts BETWEEN ? AND ? GROUP BY detail ORDER BY n DESC LIMIT 25",
                (ev, lo, hi))}
        conn.close()
    except sqlite3.Error:
        pass
    return out


def flush(days_back: int = 2) -> int:
    """
    Mirror recent days to the durable store. Returns how many days were sent.

    Covers a couple of days rather than just today so a deploy that happens
    right after midnight doesn't strand yesterday's numbers on the dead disk.
    """
    import store
    if not store.enabled():
        return 0
    sent = 0
    today = datetime.now(timezone.utc).date()
    for back in range(days_back):
        day = (today - timedelta(days=back)).isoformat()
        roll = day_rollup(day)
        if roll["sessions"] or roll["views"]:
            if store.put(_ANALYTICS_SCOPE, day, roll):
                sent += 1
    return sent


def history(days: int = 30) -> list:
    """
    [(day, rollup)] oldest-first, merging the durable store with today's live
    local numbers so the newest day is never stale.
    """
    import store
    saved = store.list_scope(_ANALYTICS_SCOPE) or {}
    today = datetime.now(timezone.utc).date()
    live = day_rollup(today.isoformat())
    if live["sessions"] or live["views"]:
        saved[today.isoformat()] = live
    cutoff = (today - timedelta(days=days)).isoformat()
    return sorted(((d, r) for d, r in saved.items() if d >= cutoff),
                  key=lambda x: x[0])


def traffic_summary(days: int = 30) -> dict:
    """Totals across the retained history — what the admin panel charts."""
    hist = history(days)
    refs, devices, daily = {}, {}, []
    total = 0
    for day, r in hist:
        total += r.get("sessions", 0)
        daily.append({"day": day, "sessions": r.get("sessions", 0)})
        for k, v in (r.get("refs") or {}).items():
            refs[k] = refs.get(k, 0) + v
        for k, v in (r.get("devices") or {}).items():
            devices[k] = devices.get(k, 0) + v
    return {
        "daily": daily,
        "total_sessions": total,
        "refs": sorted(refs.items(), key=lambda x: -x[1]),
        "devices": sorted(devices.items(), key=lambda x: -x[1]),
        "days_kept": len(daily),
    }


def signup_rows() -> list:
    """Every signup, newest first — for the admin table and CSV export."""
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT ts, email, pay, note FROM signups ORDER BY id DESC")]
        conn.close()
        return rows
    except sqlite3.Error:
        return []

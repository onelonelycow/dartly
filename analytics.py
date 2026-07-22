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

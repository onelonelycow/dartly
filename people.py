"""
people.py — the humans using Nabbly, and what they tell us.

Two tables, both keyed on email:

  people    who they are: the profile they filled in, plus whether they'd pay
  feedback  what they think: free text, optionally with a rating

WHY EMAIL AND NOT ACCOUNTS: real accounts (passwords, sessions, resets) are a
lot of machinery, and every field you add to a signup form loses you people.
At this stage the question is "who is showing up and would they pay", and an
email plus a profile answers it. Accounts can come later without changing what
is stored here — this table becomes the users table.

SURVIVING REDEPLOYS: Render's free tier wipes the disk on every deploy, so the
SQLite file below is temporary. Set SIGNUP_WEBHOOK_URL and every person and
every piece of feedback is also POSTed there the moment it arrives (a Zapier or
Make catch hook, a Google Apps Script writing to a Sheet). That way the copy
that matters lives somewhere you own. Treat the local database as a cache.
"""
import os
import re
import json
import sqlite3
from datetime import datetime, timezone

from paths import data_file

DB_PATH = data_file("nabbly_people.db")
WEBHOOK_URL = os.environ.get("SIGNUP_WEBHOOK_URL", "").strip()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")

# Profile fields we copy off the Profile page onto a person's record.
PROFILE_FIELDS = ("name", "headline", "skills", "rate_floor", "rate_unit",
                  "keywords", "portfolio", "bio", "country", "city")


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


def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match((email or "").strip()))


def init():
    """Create both tables. Safe to call on every run."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            email      TEXT PRIMARY KEY,
            created    TEXT NOT NULL,
            updated    TEXT,
            source     TEXT DEFAULT '',   -- where they signed up from
            pay        TEXT DEFAULT '',   -- 'yes' / 'maybe' / 'no'
            name       TEXT DEFAULT '',
            headline   TEXT DEFAULT '',
            skills     TEXT DEFAULT '',   -- JSON list, as saved on the profile
            rate_floor TEXT DEFAULT '',
            rate_unit  TEXT DEFAULT '',
            keywords   TEXT DEFAULT '',
            portfolio  TEXT DEFAULT '',
            bio        TEXT DEFAULT '',
            country    TEXT DEFAULT '',
            city       TEXT DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT NOT NULL,
            email   TEXT DEFAULT '',      -- blank if they didn't sign up
            rating  TEXT DEFAULT '',      -- 'good' / 'ok' / 'bad'
            message TEXT NOT NULL,
            page    TEXT DEFAULT ''       -- which view they were on
        )
        """
    )
    conn.commit()
    conn.close()


def _mirror(payload: dict):
    """Send a copy off-box so a redeploy can't lose it."""
    if not WEBHOOK_URL:
        return
    try:
        import requests
        requests.post(WEBHOOK_URL, json=payload, timeout=6)
    except Exception:
        pass  # a dead webhook must never block a signup


def add_person(email: str, source: str = "") -> tuple:
    """Create the record at signup. Repeat emails are fine, not an error."""
    email = (email or "").strip().lower()
    if not valid_email(email):
        return False, "That doesn't look like an email address."
    try:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO people (email, created, updated, source) "
            "VALUES (?,?,?,?)", (email, _now(), _now(), source[:60]))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False, "Couldn't save that just now. Try again in a moment."
    _mirror({"type": "signup", "email": email, "source": source, "at": _now()})
    return True, "You're on the list."


def set_pay(email: str, answer: str):
    """Record the would-you-pay answer."""
    email = (email or "").strip().lower()
    try:
        conn = _connect()
        conn.execute("UPDATE people SET pay = ?, updated = ? WHERE email = ?",
                     (answer, _now(), email))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return
    _mirror({"type": "pay", "email": email, "pay": answer, "at": _now()})


def attach_profile(email: str, prof: dict):
    """
    Copy the Profile page onto this person's record.

    Called whenever a signed-up visitor saves their profile, so the thing you
    get is not just an email but 'a logo designer in Portland who won't go
    below $60/hr'. That is the difference between a list and a market.
    """
    email = (email or "").strip().lower()
    if not valid_email(email):
        return
    vals = {}
    for f in PROFILE_FIELDS:
        v = prof.get(f, "")
        vals[f] = json.dumps(v) if isinstance(v, (list, dict)) else str(v or "")
    sets = ", ".join(f"{f} = ?" for f in PROFILE_FIELDS)
    try:
        conn = _connect()
        conn.execute("INSERT OR IGNORE INTO people (email, created, updated) VALUES (?,?,?)",
                     (email, _now(), _now()))
        conn.execute(f"UPDATE people SET {sets}, updated = ? WHERE email = ?",
                     [vals[f] for f in PROFILE_FIELDS] + [_now(), email])
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return
    _mirror({"type": "profile", "email": email, "at": _now(), **vals})


def add_feedback(message: str, email: str = "", rating: str = "", page: str = "") -> bool:
    """Store what someone told us. Email optional — never gate feedback on it."""
    message = (message or "").strip()
    if not message:
        return False
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO feedback (ts, email, rating, message, page) VALUES (?,?,?,?,?)",
            (_now(), (email or "").strip().lower(), rating, message[:4000], page[:40]))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False
    _mirror({"type": "feedback", "email": email, "rating": rating,
             "message": message[:4000], "page": page, "at": _now()})
    return True


def people_rows() -> list:
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM people ORDER BY created DESC")]
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def feedback_rows() -> list:
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT ts, email, rating, message, page FROM feedback ORDER BY id DESC")]
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def stats() -> dict:
    """Headline numbers for the admin panel."""
    out = {"people": 0, "with_profile": 0, "feedback": 0, "pay": {}, "ratings": {}}
    try:
        conn = _connect()
        one = lambda q: (conn.execute(q).fetchone() or [0])[0] or 0
        out["people"] = one("SELECT COUNT(*) FROM people")
        out["with_profile"] = one("SELECT COUNT(*) FROM people WHERE skills != '' OR headline != ''")
        out["feedback"] = one("SELECT COUNT(*) FROM feedback")
        out["pay"] = {r["pay"]: r["n"] for r in conn.execute(
            "SELECT pay, COUNT(*) n FROM people WHERE pay != '' GROUP BY pay")}
        out["ratings"] = {r["rating"]: r["n"] for r in conn.execute(
            "SELECT rating, COUNT(*) n FROM feedback WHERE rating != '' GROUP BY rating")}
        conn.close()
    except sqlite3.Error:
        pass
    return out

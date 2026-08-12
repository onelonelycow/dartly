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

import table_mirror
from paths import data_file

DB_PATH = data_file("nabbly_people.db")
WEBHOOK_URL = os.environ.get("SIGNUP_WEBHOOK_URL", "").strip()

# Durable mirror (store.py), separate from the write-only webhook above.
_PEOPLE_SCOPE = "_people"
_FEEDBACK_SCOPE = "_people_feedback"
_PEOPLE_COLS = ("email", "created", "updated", "source", "pay", "name",
                "headline", "skills", "rate_floor", "rate_unit", "keywords",
                "portfolio", "bio", "country", "city", "campaign")

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
            page    TEXT DEFAULT '',      -- which view they were on
            quotable INTEGER DEFAULT 0    -- 1 = they ticked "you can quote me"
        )
        """
    )
    # Which partner link brought them in, kept apart from `source` (which is
    # the in-app placement they signed up from, e.g. "dashboard"). A
    # collaboration is only measurable if the tag survives all the way to the
    # signup, not just the first page view.
    try:
        conn.execute("ALTER TABLE people ADD COLUMN campaign TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # Consent to be quoted, asked for explicitly. Feedback is written to report
    # a problem, not to be published, and the FAQ promises nothing is shared —
    # so a note is only quotable if its author said so at the time. Defaults to
    # 0, which means every note collected before this existed stays private.
    try:
        conn.execute("ALTER TABLE feedback ADD COLUMN quotable INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()

    # SIGNUP_WEBHOOK_URL below is write-only: it ships a copy off-box but
    # nothing ever reads it back, so on Render's ephemeral disk this table
    # returned empty after every deploy. That silently disables the
    # lapsed-payer email — lapsed_nudge builds its list from the people whose
    # `pay` answer was "yes", and an empty table means it finds nobody and
    # sends nothing, with no error anywhere. Same durable store accounts.py
    # uses, so the two halves of one identity survive together.
    table_mirror.rehydrate(
        _PEOPLE_SCOPE, conn, "people", _PEOPLE_COLS,
        "SELECT COUNT(*) FROM people")
    table_mirror.rehydrate(
        _FEEDBACK_SCOPE, conn, "feedback",
        ("ts", "email", "rating", "message", "page", "quotable"),
        "SELECT COUNT(*) FROM feedback")
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


def _mirror_person(email: str):
    """Push one person's row to the durable store (readable back at boot)."""
    email = (email or "").strip().lower()
    if not email:
        return
    try:
        conn = _connect()
        row = conn.execute(
            f"SELECT {', '.join(_PEOPLE_COLS)} FROM people WHERE email = ?",
            (email,)).fetchone()
        conn.close()
        if row:
            table_mirror.mirror_rows(_PEOPLE_SCOPE, email, [dict(row)])
    except sqlite3.Error:
        pass


def _mirror_feedback(email: str):
    """Push this person's feedback rows to the durable store."""
    key = (email or "").strip().lower() or "_anon"
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT ts, email, rating, message, page, quotable FROM feedback "
            "WHERE COALESCE(NULLIF(email,''),'_anon') = ?", (key,))]
        conn.close()
        table_mirror.mirror_rows(_FEEDBACK_SCOPE, key, rows)
    except sqlite3.Error:
        pass


def add_person(email: str, source: str = "", campaign: str = "") -> tuple:
    """Create the record at signup. Repeat emails are fine, not an error."""
    email = (email or "").strip().lower()
    if not valid_email(email):
        return False, "That doesn't look like an email address."
    try:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO people (email, created, updated, source, campaign) "
            "VALUES (?,?,?,?,?)",
            (email, _now(), _now(), source[:60], (campaign or "")[:40]))
        # A returning visitor who first arrived untagged and comes back through
        # a partner link should still be credited to that partner — but never
        # overwrite a tag we already have, or the last link they happened to
        # click would steal the attribution from the one that actually worked.
        if campaign:
            conn.execute(
                "UPDATE people SET campaign = ?, updated = ? "
                "WHERE email = ? AND COALESCE(campaign, '') = ''",
                (campaign[:40], _now(), email))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False, "Couldn't save that just now. Try again in a moment."
    _mirror({"type": "signup", "email": email, "source": source,
             "campaign": campaign, "at": _now()})
    _mirror_person(email)
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
    _mirror_person(email)


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
    _mirror_person(email)


def add_feedback(message: str, email: str = "", rating: str = "", page: str = "",
                 quotable: bool = False) -> bool:
    """Store what someone told us. Email optional — never gate feedback on it.

    `quotable` records an explicit yes to being quoted publicly. Absent that,
    a note is private: it was written to tell us something was broken.
    """
    message = (message or "").strip()
    if not message:
        return False
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO feedback (ts, email, rating, message, page, quotable) "
            "VALUES (?,?,?,?,?,?)",
            (_now(), (email or "").strip().lower(), rating, message[:4000],
             page[:40], 1 if quotable else 0))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False
    _mirror({"type": "feedback", "email": email, "rating": rating,
             "message": message[:4000], "page": page, "at": _now()})
    _mirror_feedback(email)
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
            "SELECT ts, email, rating, message, page, quotable FROM feedback ORDER BY id DESC")]
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

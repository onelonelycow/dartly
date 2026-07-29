"""
budget.py — how much AI drafting we're willing to pay for, per day.

Drafted replies cost real money per call. Sign-in only checks that an email
LOOKS like an email (people.valid_email is a regex, there's no confirmation
link), and every new account can start a self-serve Pro trial without a
payment method. So a script can mint plausible addresses, take a trial each,
and hold the "Draft my reply" button down — every click a live API charge with
nothing on the other side of it.

Three limits, in the order they matter:

  * DAILY_TOTAL — one counter for the whole app. This is the one that actually
    bounds the bill. However many accounts someone scripts, the day's spend
    cannot exceed this number of drafts.
  * DAILY_PER_ACCOUNT — stops a single account being the entire problem. Set
    well above what a person drafts by hand, so nobody real ever meets it.
  * A durable cache (see pitch.py) so a double-click or a page reload never
    pays twice for the same draft.

Crossing a cap is NOT an error. draft_pitch() already falls back to the free
template whenever the AI path can't run, so a capped request quietly returns
the template instead. Somebody hitting a limit gets a worse draft, never a
broken page.

Counts live in SQLite next to everything else, so they survive the restarts
that a purely in-memory counter would reset — which on Render (which restarts
on deploy, on OOM, and on idle-wake) would mean a cap that resets several
times a day and bounds nothing.
"""
import os
import sqlite3
from datetime import datetime, timezone

from paths import data_file

DB_PATH = data_file("budget.db")

# Overridable from Render's environment without a deploy, so a cap can be
# loosened the moment real usage justifies it (or clamped in a hurry).
DAILY_TOTAL = int(os.environ.get("AI_DAILY_TOTAL") or 400)
DAILY_PER_ACCOUNT = int(os.environ.get("AI_DAILY_PER_ACCOUNT") or 20)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_usage (
            day    TEXT NOT NULL,   -- UTC date, YYYY-MM-DD
            who    TEXT NOT NULL,   -- account scope, or '_all' for the global row
            n      INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (day, who)
        )
        """
    )
    conn.commit()
    conn.close()


def _init_cache(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_cache (
            k       TEXT PRIMARY KEY,   -- hash of gig + profile + resume
            text    TEXT NOT NULL,
            made    TEXT NOT NULL
        )
        """
    )


def cached_ai(key: str) -> str:
    """
    A draft we've already paid for, or ''.

    Shared across everyone on purpose: the key already hashes in the profile
    and resume, so two people only collide when the gig AND their details are
    identical — in which case the draft genuinely is the same one. Lives in
    SQLite rather than the module-level dict this replaced, which emptied on
    every restart, and Render restarts on deploy, on OOM and on idle-wake.
    """
    if not key:
        return ""
    try:
        init()
        conn = _connect()
        try:
            _init_cache(conn)
            row = conn.execute("SELECT text FROM ai_cache WHERE k=?",
                               (key,)).fetchone()
            return row["text"] if row else ""
        finally:
            conn.close()
    except Exception:
        return ""


def cache_ai(key: str, text: str):
    if not key or not text:
        return
    try:
        init()
        conn = _connect()
        try:
            _init_cache(conn)
            conn.execute(
                "INSERT INTO ai_cache (k, text, made) VALUES (?, ?, ?) "
                "ON CONFLICT(k) DO UPDATE SET text=excluded.text, made=excluded.made",
                (key, text, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def _count(conn, day: str, who: str) -> int:
    row = conn.execute("SELECT n FROM ai_usage WHERE day=? AND who=?",
                       (day, who)).fetchone()
    return int(row["n"]) if row else 0


def allow(who: str) -> tuple[bool, str]:
    """
    May we spend an API call on this person right now?

    Returns (allowed, reason). The reason is for logs, not for the reader —
    telling someone "the global cap is spent" invites them to work out what
    the cap is.
    """
    try:
        init()
        day = _today()
        conn = _connect()
        try:
            if _count(conn, day, "_all") >= DAILY_TOTAL:
                return False, "global daily cap reached"
            if who and _count(conn, day, who) >= DAILY_PER_ACCOUNT:
                return False, "per-account daily cap reached"
            return True, ""
        finally:
            conn.close()
    except Exception:
        # A broken ledger must not take drafting down with it. Failing OPEN is
        # the deliberate choice: the global cap exists to stop a runaway bill,
        # and a database error is not that — it would be worse to break the
        # feature for everyone because a counter file got locked.
        return True, "ledger unavailable"


def record(who: str, n: int = 1):
    """Count a call we actually made. Both the global row and this account."""
    try:
        init()
        day = _today()
        conn = _connect()
        try:
            for key in ("_all", who or "_anon"):
                conn.execute(
                    "INSERT INTO ai_usage (day, who, n) VALUES (?, ?, ?) "
                    "ON CONFLICT(day, who) DO UPDATE SET n = n + ?",
                    (day, key, n, n))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def today() -> dict:
    """What's been spent today — for the admin page."""
    try:
        init()
        day = _today()
        conn = _connect()
        try:
            total = _count(conn, day, "_all")
            accounts = conn.execute(
                "SELECT COUNT(*) FROM ai_usage WHERE day=? AND who != '_all'",
                (day,)).fetchone()[0]
            top = conn.execute(
                "SELECT who, n FROM ai_usage WHERE day=? AND who != '_all' "
                "ORDER BY n DESC LIMIT 5", (day,)).fetchall()
            return {"day": day, "drafts": total, "cap": DAILY_TOTAL,
                    "accounts": int(accounts),
                    "top": [(r["who"][:12], int(r["n"])) for r in top]}
        finally:
            conn.close()
    except Exception:
        return {"day": _today(), "drafts": 0, "cap": DAILY_TOTAL,
                "accounts": 0, "top": []}


def purge(keep_days: int = 14):
    """Drop old rows so the ledger stays small. Called from the refresh loop."""
    try:
        init()
        conn = _connect()
        try:
            conn.execute(
                "DELETE FROM ai_usage WHERE day < date('now', ?)",
                (f"-{int(keep_days)} days",))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

"""
activity.py — durable per-account usage counters: what someone has actually
DONE on Nabbly, not just what's on the board for them.

First use: the weekly digest wants a real "you clicked apply on N gigs this
week" number. analytics.py's events table exists already, but it's keyed by
an anonymous browser session, not an account — fine for admin traffic
numbers, wrong for "MY activity" in an email that has to still be true a week
from now on a different device. This is a separate, small, account-scoped
table for exactly that.

Counts what someone clicked "apply" on, not whether they were hired or even
finished the application — that's the honest limit of what a redirect link
can ever know, and the digest email says so plainly rather than implying more.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

from paths import data_file

DB_PATH = data_file("activity.db")


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
        CREATE TABLE IF NOT EXISTS apply_clicks (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            who    TEXT NOT NULL,     -- account scope (paths.scope_for(email))
            gig_id INTEGER NOT NULL,
            ts     TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_apply_who_ts ON apply_clicks(who, ts)")
    conn.commit()
    conn.close()


def log_apply(who: str, gig_id):
    """One outbound apply-link click, for one account. Never raises — a
    tracking write must never be the reason someone's apply click fails."""
    if not who:
        return
    try:
        init()
        conn = _connect()
        conn.execute(
            "INSERT INTO apply_clicks (who, gig_id, ts) VALUES (?, ?, ?)",
            (who, int(gig_id), datetime.now(timezone.utc).isoformat(timespec="seconds")))
        conn.commit()
        conn.close()
    except Exception:
        pass


def applied_count(who: str, days: int | None = None) -> int:
    """How many apply clicks this account has, optionally only the last
    `days` days (the digest wants "this week"; a future profile stat might
    want all-time, hence the parameter rather than two functions)."""
    if not who:
        return 0
    try:
        init()
        conn = _connect()
        if days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            n = conn.execute(
                "SELECT COUNT(*) FROM apply_clicks WHERE who=? AND ts>=?",
                (who, cutoff)).fetchone()[0]
        else:
            n = conn.execute(
                "SELECT COUNT(*) FROM apply_clicks WHERE who=?", (who,)).fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def purge(keep_days: int = 120):
    """Old click rows aren't useful to anyone once even an all-time count
    wouldn't reasonably include them; keeps the table from growing forever."""
    try:
        init()
        conn = _connect()
        conn.execute("DELETE FROM apply_clicks WHERE ts < ?",
                    ((datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat(),))
        conn.commit()
        conn.close()
    except Exception:
        pass

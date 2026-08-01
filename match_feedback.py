"""
match_feedback.py — was the match actually good?

Pro's whole pitch on a card is the score and the reasons under it: "73%
match — pays your rate, remote." Nabbly has never once found out if that
claim was right. A thumbs up/down right where the claim is made is the
cheapest possible way to ask, and it's the earliest warning system for a
skill, category or source that's quietly ranking wrong — long before
someone gets frustrated enough to churn or write in about it.

Same shape as outcomes.py on purpose: one small SQLite table, best-effort
writes, no new durability mechanism invented for a feature this size.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

from paths import data_file

DB_PATH = data_file("nabbly_match_feedback.db")


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
    """Create the table. Safe to call on every run."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            email    TEXT NOT NULL,
            gig_id   TEXT NOT NULL,
            job_type TEXT DEFAULT '',   -- snapshotted so a later re-tag can't
                                          -- quietly move a rating to a
                                          -- different category's tally
            source   TEXT DEFAULT '',
            rating   TEXT NOT NULL,     -- 'up' or 'down'
            ts       TEXT NOT NULL,
            UNIQUE(email, gig_id)
        )
        """
    )
    conn.commit()
    conn.close()


def my_ratings(email: str) -> dict:
    """{gig_id: 'up'|'down'} for this person, for the cards they've rated."""
    email = (email or "").strip().lower()
    if not email:
        return {}
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT gig_id, rating FROM ratings WHERE email = ?", (email,))
        out = {r["gig_id"]: r["rating"] for r in rows}
        conn.close()
        return out
    except sqlite3.Error:
        return {}


def rate(email: str, gig_id, rating: str, job_type: str = "", source: str = ""):
    """
    Set a rating. Setting the SAME rating again clears it — a second tap on
    the thumb you already pressed reads as "undo", not "rate it twice."
    Returns the new state: 'up', 'down', or None.
    """
    email = (email or "").strip().lower()
    gid = str(gig_id)
    if not email or not gid or rating not in ("up", "down"):
        return None
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT rating FROM ratings WHERE email = ? AND gig_id = ?",
            (email, gid)).fetchone()
        if row and row["rating"] == rating:
            conn.execute("DELETE FROM ratings WHERE email = ? AND gig_id = ?",
                         (email, gid))
            conn.commit()
            conn.close()
            return None
        conn.execute(
            "INSERT INTO ratings (email, gig_id, job_type, source, rating, ts) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(email, gig_id) DO UPDATE SET "
            "rating=excluded.rating, job_type=excluded.job_type, "
            "source=excluded.source, ts=excluded.ts",
            (email, gid, job_type, source, rating, _now()))
        conn.commit()
        conn.close()
        return rating
    except sqlite3.Error:
        return None


def worst_categories(days: int = 30, limit: int = 15) -> list[dict]:
    """
    Job types with the most down-votes, net of up-votes — where the ranking
    is quietly wrong often enough that it's worth a look, not just noise
    from one annoyed person.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT job_type, "
            "  SUM(CASE WHEN rating='down' THEN 1 ELSE 0 END) AS down_n, "
            "  SUM(CASE WHEN rating='up' THEN 1 ELSE 0 END) AS up_n "
            "FROM ratings WHERE ts >= ? AND job_type != '' "
            "GROUP BY job_type "
            "HAVING down_n > 0 "
            "ORDER BY (down_n - up_n) DESC, down_n DESC LIMIT ?",
            (since, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []

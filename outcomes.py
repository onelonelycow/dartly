"""
outcomes.py — the moment the board actually worked for someone.

Everything else in this app is upstream of one question: did you get the
gig? Right now Nabbly never finds out — a freelancer applies and either
Nabbly hears nothing back, forever, or the site quietly assumes it helped.
This is the one place that closes the loop: a single tap, "I got this one,"
turns a browse into a result.

Two things fall out of the same table:
  - a person's own count, worth showing them (it's the whole reason to come
    back and tap it)
  - a sitewide total — gigs landed, dollars landed — which is a far
    stronger trust signal on the front page than "16,000 gigs" ever was,
    once there's enough of it to show.

Same shape as people.py on purpose: one small SQLite table, best-effort
writes that degrade to "nothing recorded" rather than a broken page, no
new durability mechanism invented for a feature this size.
"""
import sqlite3
from datetime import datetime, timezone

from paths import data_file

DB_PATH = data_file("nabbly_outcomes.db")


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
        CREATE TABLE IF NOT EXISTS outcomes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            email   TEXT NOT NULL,
            gig_id  TEXT NOT NULL,
            amount  INTEGER DEFAULT 0,   -- the gig's parsed budget, snapshotted
                                          -- at the moment of the tap: the post
                                          -- can be re-tagged or archived later,
                                          -- and a win shouldn't quietly change
                                          -- value or disappear from the total
                                          -- because of that.
            ts      TEXT NOT NULL,
            UNIQUE(email, gig_id)
        )
        """
    )
    conn.commit()
    conn.close()


def has_won(email: str, gig_id) -> bool:
    email = (email or "").strip().lower()
    if not email:
        return False
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT 1 FROM outcomes WHERE email = ? AND gig_id = ?",
            (email, str(gig_id))).fetchone()
        conn.close()
        return row is not None
    except sqlite3.Error:
        return False


def toggle(email: str, gig_id, amount: int = 0) -> bool:
    """Flip won state for this person+gig. Returns True if now marked won."""
    email = (email or "").strip().lower()
    gid = str(gig_id)
    if not email or not gid:
        return False
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT 1 FROM outcomes WHERE email = ? AND gig_id = ?",
            (email, gid)).fetchone()
        if row:
            conn.execute("DELETE FROM outcomes WHERE email = ? AND gig_id = ?",
                         (email, gid))
            conn.commit()
            conn.close()
            return False
        conn.execute(
            "INSERT INTO outcomes (email, gig_id, amount, ts) VALUES (?,?,?,?)",
            (email, gid, max(0, int(amount or 0)), _now()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error:
        return False


def my_wins(email: str) -> list:
    """This person's wins, newest first."""
    email = (email or "").strip().lower()
    if not email:
        return []
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT gig_id, amount, ts FROM outcomes WHERE email = ? "
            "ORDER BY id DESC", (email,))]
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def my_count(email: str) -> int:
    return len(my_wins(email))


def site_stats() -> dict:
    """Sitewide totals — gigs landed, dollars landed, across everyone."""
    out = {"wins": 0, "total_amount": 0}
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(amount), 0) total FROM outcomes"
        ).fetchone()
        conn.close()
        out["wins"] = row["n"] or 0
        out["total_amount"] = row["total"] or 0
    except sqlite3.Error:
        pass
    return out

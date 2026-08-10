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

import table_mirror
from paths import data_file

DB_PATH = data_file("nabbly_match_feedback.db")
# Namespace inside store.py's shared key-value table, one row per person.
_MIRROR_SCOPE = "_match_feedback"


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
    # Ratings are what my_category_bias() ranks on, so losing them doesn't
    # just clear the thumbs — it silently turns personalisation back into a
    # generic feed while the app still claims to be learning.
    table_mirror.rehydrate(
        _MIRROR_SCOPE, conn, "ratings",
        ("email", "gig_id", "job_type", "source", "rating", "ts"),
        "SELECT COUNT(*) FROM ratings")
    conn.close()


def _all_rows(email: str) -> list:
    """Every stored rating for one person, as plain dicts (for the mirror)."""
    email = (email or "").strip().lower()
    if not email:
        return []
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT email, gig_id, job_type, source, rating, ts "
            "FROM ratings WHERE email = ?", (email,))]
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def _mirror(email: str):
    """Push this person's whole rating history to the durable store."""
    table_mirror.mirror_rows(_MIRROR_SCOPE, email, _all_rows(email))


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
            _mirror(email)          # an undo has to reach the mirror too
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
        _mirror(email)
        return rating
    except sqlite3.Error:
        return None


def my_category_bias(email: str) -> dict[str, int]:
    """
    {job_type: point adjustment} from this person's OWN up/down history —
    the loop worst_categories() was supposed to close but never did. That
    function tells the founder a category's ranking wrong for people in
    general; this tells the ranking it's wrong for THIS person specifically,
    which is the whole reason the thumbs live right next to the score.

    Net votes (up minus down) per category, scaled modestly and capped —
    this nudges rank, it doesn't override it. Someone who's downvoted every
    "Marketing" gig they've seen shouldn't need to keep re-teaching that on
    every visit; someone who's upvoted "Development / tech" every time
    should see more of it float up. Two or fewer net votes doesn't move
    anything — that's noise, not a preference yet.
    """
    email = (email or "").strip().lower()
    if not email:
        return {}
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT job_type, "
            "  SUM(CASE WHEN rating='up' THEN 1 ELSE -1 END) AS net "
            "FROM ratings WHERE email = ? AND job_type != '' "
            "GROUP BY job_type", (email,)).fetchall()
        conn.close()
        out = {}
        for row in rows:
            net = row["net"]
            if abs(net) <= 2:
                continue
            # +/-4 points per net vote past the noise floor, capped at +/-20
            # — enough to move a borderline gig a few ranks, not enough to
            # override a real skill/budget mismatch on its own.
            out[row["job_type"]] = max(-20, min(20, net * 4))
        return out
    except sqlite3.Error:
        return {}


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

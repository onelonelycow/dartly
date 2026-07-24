"""
db.py — stores demand posts in a single local file (demand_radar.db).

SQLite is a database that lives in one file. No server, no setup.
"""
import sqlite3
from datetime import datetime, timezone

from paths import data_file

DB_PATH = data_file("demand_radar.db")


def connect():
    # timeout lets a reader wait briefly if the background fetcher is mid-write.
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")  # concurrent reads during writes
    except sqlite3.OperationalError:
        pass
    return conn


def init_db():
    """Create the posts table the first time we run."""
    conn = connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,      -- 'craigslist' or 'reddit'
            source_id   TEXT NOT NULL,      -- the original post id (for dedup)
            url         TEXT,
            title       TEXT,
            body        TEXT,
            posted_at   TEXT,               -- when the person posted it
            fetched_at  TEXT,               -- when we pulled it
            is_demand   INTEGER,            -- 1 = looks like a real request for help
            job_type    TEXT,
            size_tier   TEXT,               -- 'Small', 'Medium', 'Large'
            urgency     TEXT,               -- 'Urgent' or ''
            is_new      INTEGER DEFAULT 0,  -- 1 = arrived in the latest fetch
            alerted     INTEGER DEFAULT 0,  -- 1 = we've already sent an alert for it
            owner       TEXT DEFAULT '',    -- '' = public board; else one person's
            UNIQUE(source, source_id)
        )
        """
    )
    # Safe migration for databases created before these columns existed.
    for col in ("is_new", "alerted"):
        try:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN owner TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def _owner_clause(owner: str | None) -> tuple[str, list]:
    """
    Which rows this viewer is allowed to see.

    Everything scraped from a public board has an empty owner and is visible to
    all. Anything forwarded in by email belongs to the person who forwarded it —
    those newsletters are often paid subscriptions, so they stay on that one
    board and nobody else's.
    """
    if owner:
        return "(COALESCE(owner, '') = '' OR owner = ?)", [owner]
    return "COALESCE(owner, '') = ''", []


def upsert_post(post: dict) -> bool:
    """Insert a post. Returns True if it was new, False if we'd already seen it."""
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO posts
                (source, source_id, url, title, body, posted_at, fetched_at,
                 is_demand, job_type, size_tier, urgency, is_new, alerted, owner)
            VALUES
                (:source, :source_id, :url, :title, :body, :posted_at, :fetched_at,
                 :is_demand, :job_type, :size_tier, :urgency, 1, 0, :owner)
            """,
            # Everything except the inbox arrives without an owner, i.e. public.
            {"owner": "",
             "fetched_at": datetime.now(timezone.utc).isoformat(),
             **post},
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already have this post (same source + source_id) — skip it.
        return False
    finally:
        conn.close()


def reclassify_all() -> int:
    """
    Re-run the classifier over every stored post, updating any whose tags moved.

    upsert_post() never touches a row it has already seen, so a classifier
    improvement would otherwise only reach new gigs while the existing board
    kept its old (often wrong) tags. This re-tags what's already stored. Only
    changed rows are written, so a second run is a cheap no-op.
    """
    import classify
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, title, body, source, job_type, size_tier, urgency FROM posts"
        ).fetchall()
        changed = 0
        for r in rows:
            t = classify.classify(r["title"], r["body"], r["source"])
            if (t["job_type"] != r["job_type"] or t["size_tier"] != r["size_tier"]
                    or t["urgency"] != r["urgency"]):
                conn.execute(
                    "UPDATE posts SET job_type=?, size_tier=?, urgency=? WHERE id=?",
                    (t["job_type"], t["size_tier"], t["urgency"], r["id"]))
                changed += 1
        conn.commit()
        return changed
    finally:
        conn.close()


def all_posts(demand_only: bool = True, owner: str | None = None):
    """
    Return the posts this viewer can see, newest first.

    Pass someone's storage scope as `owner` to include the gigs they forwarded
    in by email alongside the public board. Leave it off and you get the public
    board only.
    """
    conn = connect()
    clause, params = _owner_clause(owner)
    where = f"WHERE {clause}" + (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(posted_at, fetched_at) DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def owned_posts(owner: str, demand_only: bool = True):
    """Just the gigs one person forwarded in — none of the public board."""
    if not owner:
        return []
    conn = connect()
    where = "WHERE owner = ?" + (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(posted_at, fetched_at) DESC",
        [owner],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def max_post_id() -> int:
    """
    Highest id on the whole table, private rows included.

    Alert watermarks compare against this. If it only counted the public board,
    a forwarded gig with a higher id would sit permanently above the marker and
    re-alert on every cycle.
    """
    conn = connect()
    n = conn.execute("SELECT COALESCE(MAX(id), 0) FROM posts").fetchone()[0]
    conn.close()
    return int(n)


def count(owner: str | None = None) -> int:
    conn = connect()
    clause, params = _owner_clause(owner)
    n = conn.execute(
        f"SELECT COUNT(*) FROM posts WHERE is_demand = 1 AND {clause}", params
    ).fetchone()[0]
    conn.close()
    return n


def ensure_seeded():
    """If the working DB is missing or empty, populate it from the bundled
    seed.db. Lets a fresh deploy have gigs instantly without fetching live data
    during the build (which is slow/fragile on small hosts)."""
    import shutil
    from pathlib import Path
    seed = Path(__file__).parent / "seed.db"
    try:
        if not seed.exists() or seed.resolve() == DB_PATH.resolve():
            return
        empty = True
        if DB_PATH.exists():
            init_db()          # ensure schema, safe if it already exists
            empty = count() == 0
        if empty:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(seed, DB_PATH)
        # The bundled seed was captured before newer columns (e.g. owner)
        # existed, so migrate whatever we just landed up to the current schema.
        # Without this a fresh deploy would query a column the copied file
        # doesn't have yet, and every board read would crash until the first
        # background fetch happened to run init_db().
        init_db()
    except Exception:
        pass


def reset_new_flags():
    """Clear the 'new' flag on all posts (call before a fresh fetch)."""
    conn = connect()
    conn.execute("UPDATE posts SET is_new = 0")
    conn.commit()
    conn.close()


def unalerted(owner: str | None = None):
    """Demand posts we haven't sent an alert for yet (newest first)."""
    conn = connect()
    clause, params = _owner_clause(owner)
    rows = conn.execute(
        f"SELECT * FROM posts WHERE is_demand = 1 AND alerted = 0 AND {clause} "
        "ORDER BY COALESCE(posted_at, fetched_at) DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alerted(ids):
    if not ids:
        return
    conn = connect()
    conn.executemany("UPDATE posts SET alerted = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

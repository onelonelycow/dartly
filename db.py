"""
db.py — stores demand posts in a single local file (demand_radar.db).

SQLite is a database that lives in one file. No server, no setup.
"""
import sqlite3

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
    conn.commit()
    conn.close()


def upsert_post(post: dict) -> bool:
    """Insert a post. Returns True if it was new, False if we'd already seen it."""
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO posts
                (source, source_id, url, title, body, posted_at, fetched_at,
                 is_demand, job_type, size_tier, urgency, is_new, alerted)
            VALUES
                (:source, :source_id, :url, :title, :body, :posted_at, :fetched_at,
                 :is_demand, :job_type, :size_tier, :urgency, 1, 0)
            """,
            post,
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already have this post (same source + source_id) — skip it.
        return False
    finally:
        conn.close()


def all_posts(demand_only: bool = True):
    """Return every stored post, newest first."""
    conn = connect()
    where = "WHERE is_demand = 1" if demand_only else ""
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(posted_at, fetched_at) DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count() -> int:
    conn = connect()
    n = conn.execute("SELECT COUNT(*) FROM posts WHERE is_demand = 1").fetchone()[0]
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
    except Exception:
        pass


def reset_new_flags():
    """Clear the 'new' flag on all posts (call before a fresh fetch)."""
    conn = connect()
    conn.execute("UPDATE posts SET is_new = 0")
    conn.commit()
    conn.close()


def unalerted():
    """Demand posts we haven't sent an alert for yet (newest first)."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM posts WHERE is_demand = 1 AND alerted = 0 "
        "ORDER BY COALESCE(posted_at, fetched_at) DESC"
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

"""
board_store.py — the gig board's durable backup in Supabase.

Same idea as store.py, but for the board (the posts table) rather than per-user
KV. Render's free tier wipes the disk on every deploy and every ~15-minute idle
spin-down, so the board rebuilds from the 1,558-row seed each time and slowly
climbs back. This mirrors gigs to Supabase as they're ingested and pulls them
back on boot, so the board accumulates and *sticks* instead of resetting.

THE ONE RULE THAT KEEPS IT FAST: reads never come from here. The app reads the
local SQLite board on every page load; this is written on ingest (in the
background fetch loop) and read exactly once, at boot. It is a backup, never the
hot path.

DEGRADES CLEANLY: with no DATABASE_URL set, enabled() is False and every call is
a no-op — identical to how the app ran before Supabase. Every operation is
wrapped so a slow or unreachable database can never block or crash a fetch; the
worst case is a batch of gigs isn't mirrored and is re-mirrored next cycle.

It reuses store.py's connection + DSN handling, so the SQLite-or-Postgres
placeholder juggling lives in one place. Point DATABASE_URL at a sqlite file and
this runs identically to how it runs against Supabase, which is how it's tested.
"""
import store

_TABLE = "nabbly_posts"
CAP = 15000          # rehydrate the newest N; keeps boot quick and storage bounded

# Everything except the local autoincrement id, which is meaningless across
# instances — rows are keyed on (source, source_id), the same natural key the
# local table dedupes on.
_COLS = ("source", "source_id", "url", "title", "body", "posted_at",
         "fetched_at", "is_demand", "job_type", "size_tier", "urgency", "owner")
_DEFAULTS = {"is_demand": 1, "owner": ""}


def enabled() -> bool:
    return store.enabled()


def _ensure(conn):
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
                source     text NOT NULL,
                source_id  text NOT NULL,
                url        text,
                title      text,
                body       text,
                posted_at  text,
                fetched_at text,
                is_demand  integer,
                job_type   text,
                size_tier  text,
                urgency    text,
                owner      text DEFAULT '',
                PRIMARY KEY (source, source_id)
            )""")


def _row(rec: dict) -> tuple:
    return tuple(rec.get(c, _DEFAULTS.get(c, "")) for c in _COLS)


def push(records) -> int:
    """
    Mirror a batch of gigs. Best-effort; returns how many were sent (0 on any
    failure or when disabled). Safe to call with the whole new-this-cycle batch.
    """
    records = [r for r in (records or []) if r.get("source") and r.get("source_id")]
    if not enabled() or not records:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cols = ", ".join(_COLS)
            marks = ", ".join([ph] * len(_COLS))
            sets = ", ".join(f"{c}=excluded.{c}" for c in _COLS
                             if c not in ("source", "source_id"))
            sql = (f"INSERT INTO {_TABLE} ({cols}) VALUES ({marks}) "
                   f"ON CONFLICT (source, source_id) DO UPDATE SET {sets}")
            with conn:                       # commits on clean exit (both drivers)
                conn.cursor().executemany(sql, [_row(r) for r in records])
            return len(records)
        finally:
            conn.close()
    except Exception:
        return 0


def pull(cap: int = CAP) -> list[dict]:
    """The newest `cap` mirrored gigs as dicts. Empty on any failure/disabled."""
    if not enabled():
        return []
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cur = conn.execute(
                f"SELECT {', '.join(_COLS)} FROM {_TABLE} "
                f"ORDER BY COALESCE(posted_at, fetched_at) DESC LIMIT {int(cap)}")
            return [dict(zip(_COLS, r)) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def count() -> int:
    """How many gigs are in the mirror (for the admin page). -1 if unreachable."""
    if not enabled():
        return -1
    try:
        conn, _ = store._connect()
        try:
            _ensure(conn)
            return int(conn.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0])
        finally:
            conn.close()
    except Exception:
        return -1


def mark_archived(pairs) -> int:
    """
    Record in the mirror that these (source, source_id) gigs are off the board.

    THIS IS WHY DEAD GIGS KEPT COMING BACK. The mirror only ever heard about
    gigs at ingest, where everything is is_demand=1 by definition. Archival —
    sweep_dead_links() finding a 404, archive_stale() ageing a post out — was
    written to the LOCAL sqlite file only, and Render's free tier has no
    persistent disk, so that file is destroyed on every restart. Each OOM
    restart therefore rehydrated the newest 15,000 mirrored gigs with their
    original is_demand=1, resurrecting postings we had already proven dead;
    the sweeper then had to rediscover them six per cycle. A founder watching
    the board saw an April listing reappear at the top of "Fresh off the
    boards" minutes after a crash and reasonably concluded the fix never
    worked. The fix has to outlive the disk, which means it lives here.
    """
    pairs = [(s, sid) for s, sid in (pairs or []) if s and sid]
    if not enabled() or not pairs:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            sql = (f"UPDATE {_TABLE} SET is_demand = 0 "
                   f"WHERE source = {ph} AND source_id = {ph}")
            with conn:
                conn.cursor().executemany(sql, pairs)
            return len(pairs)
        except Exception:
            return 0
        finally:
            conn.close()
    except Exception:
        return 0

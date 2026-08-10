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
# Rehydrate the newest N. This has to stay comfortably ahead of the real board
# or the mirror quietly becomes lossy in a way nothing reports: gigs past the
# cap never come back, and because they're gone their source_ids stop blocking
# re-ingest, so old postings can reappear later as brand new. At 15,000 against
# a ~25,600-gig board that was already happening to the oldest 10,000.
CAP = 40000

# Everything except the local autoincrement id, which is meaningless across
# instances — rows are keyed on (source, source_id), the same natural key the
# local table dedupes on.
#
# A column missing from this tuple is a column that silently does not survive a
# redeploy. That is not theoretical: apply_email, page_checked and link_checked
# were all absent here, so every gig lost its extracted apply-to address on each
# deploy and the two backfill sweeps restarted from zero at a few pages a cycle,
# never catching up. Add a column to posts, add it here too.
_COLS = ("source", "source_id", "url", "title", "body", "posted_at",
         "fetched_at", "is_demand", "job_type", "size_tier", "urgency", "owner",
         "apply_email", "page_checked", "link_checked")
# page_checked/link_checked default to NULL, not 0 or "": db.py asks for work
# with `WHERE page_checked IS NULL`, so a 0 would mark every restored gig as
# already swept, and an "" would fail outright against an integer column in
# Postgres — taking the whole executemany, and the batch, down with it.
_DEFAULTS = {"is_demand": 1, "owner": "",
             "page_checked": None, "link_checked": None}

# db.upsert_many() restores exactly these columns, so it reads them from here
# rather than keeping a second copy that can drift out of sync (it did).
COLS = _COLS
DEFAULTS = _DEFAULTS


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
                apply_email text,
                page_checked integer,
                link_checked integer,
                PRIMARY KEY (source, source_id)
            )""")
    _migrate(conn)


# Columns added after the mirror table was first created. CREATE TABLE IF NOT
# EXISTS above is a no-op against the table already live in Supabase, so new
# columns only ever arrive through here.
_ADDED = (("apply_email", "text"),
          ("page_checked", "integer"),
          ("link_checked", "integer"))


def _migrate(conn):
    """
    Add any missing columns to an already-created mirror table.

    Asks what the table has before altering it rather than firing ALTERs and
    catching the failures: psycopg runs in a transaction, and one failed
    statement aborts it, so a redundant "column already exists" would poison the
    connection and make the INSERT that follows fail — push() would swallow that
    and return 0, mirroring nothing, silently. SELECT ... LIMIT 0 gets the
    column names off the cursor description on both drivers.
    """
    try:
        cur = conn.execute(f"SELECT * FROM {_TABLE} LIMIT 0")
        have = {d[0] for d in (cur.description or ())}
    except Exception:
        return
    added = False
    for col, decl in _ADDED:
        if col not in have:
            conn.execute(f"ALTER TABLE {_TABLE} ADD COLUMN {col} {decl}")
            added = True
    if added:
        # pull()/count() never commit, so without this the DDL rolls back on
        # close and every boot re-runs the migration.
        conn.commit()


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

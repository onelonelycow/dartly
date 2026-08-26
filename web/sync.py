"""
web/sync.py — keeps the board service's own copy of the board current.

WHY A SEPARATE COPY. Render gives every service its own filesystem, so the
board service cannot read the Streamlit app's SQLite file. Supabase is the one
store both can reach, but querying it per request costs ~50ms against SQLite's
0.03ms. So the board service does what the Streamlit app already does and has
done reliably for weeks: pull from the durable mirror into a local SQLite file
and serve every request from that.

THE COST OF THAT CHOICE IS DRIFT, and drift is bounded here rather than
hand-waved:

  * every REFRESH_S (default 60s) it pulls only gigs mirrored since the last
    watermark — usually a handful of rows, not 48,000;
  * every RECONCILE_S (default 900s) it pulls the (source, source_id,
    is_demand) triples for the whole board and applies archival locally.

The second pass is not optional. mark_archived() flips is_demand without
touching fetched_at, so an incremental pull can see gigs ARRIVE but never see
them LEAVE. Without reconciliation a dead gig would sit on this copy forever,
which is precisely the bug the durable mirror was built to kill.

Read-only with respect to the mirror. Nothing here ever writes to Supabase.
"""
import os
import re
import sqlite3
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import board_store  # noqa: E402
import lang as _lang  # noqa: E402
import location as _location  # noqa: E402
import migrate as _migrate_mod  # noqa: E402  (web/migrate.py)

# Facts about a POST that the board filters on, derived from its own text and
# stored here rather than computed per request.
#
# This is the same lesson as yesterday's outage, applied before it can happen
# again: the Streamlit app called location.tag() per row, per render, for every
# visitor — 53,000 title+body concatenations and a dozen regexes each, on every
# board load. Derived once at sync and written to a column, filtering by
# "remote" becomes an indexed WHERE instead of work.
_DERIVED = ("is_remote", "is_onsite", "restrict_cc", "lang_code", "city_lock",
            "dup_key", "is_worldwide")

# The same key app.py's _build_feed dedupes on: the title's distinct words of
# more than two letters, sorted. Sorted so word order doesn't matter, so
# "Senior Frontend Engineer" and "Frontend Engineer, Senior" collapse.
_WORDS = re.compile(r"[a-z0-9]+")


def _dup_key(title: str) -> str:
    return " ".join(sorted({w for w in _WORDS.findall(str(title).lower())
                            if len(w) > 2}))


def _derive(rec: dict) -> tuple:
    title = (rec.get("title") or "")
    body = (rec.get("body") or "")
    t = _location.tag({"title": title, "body": body})
    return (1 if t["remote"] else 0,
            1 if t["onsite"] else 0,
            t["restrict"] or "",
            _lang.detect(title, body) or "en",
            _location.city_lock({"title": title}) or "",
            _dup_key(title),
            # Stored separately from is_remote even though is_remote already
            # covers it: location.label() distinguishes "Worldwide" from
            # "Remote", and collapsing them would downgrade the pill on every
            # explicitly-worldwide posting.
            1 if t["worldwide"] else 0)

BOARD_DB = os.environ.get("NABBLY_BOARD_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "board.db")
REFRESH_S = int(os.environ.get("NABBLY_REFRESH_S") or 60)
RECONCILE_S = int(os.environ.get("NABBLY_RECONCILE_S") or 900)
# RETENTION, RUN WHERE THE DATA ACTUALLY LIVES.
#
# db.archive_stale() sweeps the ingest machine's local SQLite and mirrors the
# result. That machine is redeployed with an empty disk, so the sweep finds
# nothing, reports zero, and the mirror keeps every gig it has ever seen. The
# board boots from the mirror, so the tail lands here: 85,056 rows and a 232s
# boot against Render's 270s limit, which had to be swept by hand.
#
# This service is the one that suffers and the one that is always running, so
# it does the sweeping. Once a day is plenty for a 14-day window.
SWEEP_S = int(os.environ.get("NABBLY_SWEEP_S") or 86400)

_COLS = board_store.COLS
_state = {"rows": 0, "last_sync": 0.0, "last_reconcile": 0.0,
          "watermark": "", "adds": 0, "archived": 0, "errors": 0,
          "hidden_dupes": 0, "note": "",
          # Retention against the mirror. last_sweep starts at 0 so the first
          # pass runs shortly after boot rather than a day later.
          "last_sweep": 0.0, "swept": 0, "sweep_note": ""}
_lock = threading.Lock()
_started = False


def state() -> dict:
    d = dict(_state)
    d["drift_s"] = int(time.time() - d["last_sync"]) if d["last_sync"] else None
    return d


def _connect_rw():
    conn = sqlite3.connect(BOARD_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")     # readers never block on the writer
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn):
    cols = ", ".join(
        f"{c} INTEGER" if c in ("is_demand", "page_checked", "link_checked",
                                "llm_checked", "rare")
        else f"{c} TEXT" for c in _COLS)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {cols}, sort_at TEXT,
            is_remote INTEGER, is_onsite INTEGER, restrict_cc TEXT,
            lang_code TEXT, city_lock TEXT, dup_key TEXT, is_primary INTEGER,
            is_worldwide INTEGER,
            UNIQUE (source, source_id))""")
    # An older board.db predates the derived columns; add them rather than
    # forcing a full re-pull.
    have = {r[1] for r in conn.execute("PRAGMA table_info(posts)")}
    for c in _DERIVED + ("is_primary",):
        if c not in have:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {c} "
                         f"{'INTEGER' if c.startswith('is_') else 'TEXT'}")
    conn.commit()


def _upsert(conn, rows) -> int:
    """Insert or update mirrored rows, keeping sort_at in step."""
    if not rows:
        return 0
    cols = list(_COLS) + ["sort_at"] + list(_DERIVED)
    marks = ", ".join("?" * len(cols))
    sets = ", ".join(f"{c}=excluded.{c}" for c in cols
                     if c not in ("source", "source_id"))
    sql = (f"INSERT INTO posts ({', '.join(cols)}) VALUES ({marks}) "
           f"ON CONFLICT (source, source_id) DO UPDATE SET {sets}")
    payload = []
    for r in rows:
        vals = [r.get(c) for c in _COLS]
        posted = (r.get("posted_at") or "").strip()
        payload.append(tuple(vals)
                       + ((posted or r.get("fetched_at") or ""),)
                       + _derive(r))
    with conn:
        conn.executemany(sql, payload)
    return len(payload)


def mark_primaries(conn) -> int:
    """
    One row per duplicate title stays visible; the rest are hidden.

    THIS IS PARITY WITH THE STREAMLIT BOARD, not a new idea. app.py's
    _build_feed drops duplicates on exactly this key before rendering, so the
    old board never showed the same posting twice. The SQL board had no
    equivalent and showed all of them: measured 6,274 duplicate rows, 12.5% of
    the board, with "Sales Development Representative" appearing 42 times. The
    same role really is syndicated across several feeds, so this is dedupe, not
    data loss — the row is still there, still blocking re-ingest by its own
    source_id.

    Newest wins, matching drop_duplicates(keep="first") on a newest-first
    frame. Rows with no usable title words keep is_primary = 1 rather than
    collapsing into one giant "" group.
    """
    with conn:
        conn.execute("UPDATE posts SET is_primary = 1 "
                     "WHERE COALESCE(dup_key, '') = ''")
        conn.execute("""UPDATE posts SET is_primary = 0
                        WHERE COALESCE(dup_key, '') != ''""")
        conn.execute("""UPDATE posts SET is_primary = 1 WHERE id IN (
                            SELECT id FROM (
                                SELECT id, ROW_NUMBER() OVER (
                                    PARTITION BY dup_key
                                    ORDER BY sort_at DESC, id DESC) rn
                                FROM posts WHERE COALESCE(dup_key,'') != ''
                            ) WHERE rn = 1)""")
    return conn.execute(
        "SELECT COUNT(*) FROM posts WHERE is_demand=1 AND is_primary=0").fetchone()[0]


def _invalidate_schema():
    """
    Tell the query layer the board file's schema just changed.

    migrate() can ADD posts_fts and the derived columns, and queries caches
    "does this file have FTS / this column" per file. Without this, a process
    that answered a request before the first migrate would keep serving the
    pre-migrate answer — search silently on the slow LIKE path, location
    filters silently skipped.
    """
    try:
        import queries
        queries.clear_schema_cache()
    except Exception:
        pass


def _watermark(conn) -> str:
    row = conn.execute(
        "SELECT COALESCE(MAX(fetched_at), '') FROM posts").fetchone()
    return row[0] or ""


def full_sync() -> int:
    """
    Pull the whole board, in pages. Boot, or an empty local file.

    PAGED, NOT CAPPED. board_store.pull() returns the newest CAP rows and
    stops; measured 2026-08-13 that left 10,206 live gigs — a fifth of the
    board — off every boot, with nothing reporting it. iter_all() walks the
    lot, and writing each page as it arrives keeps peak memory flat instead of
    holding 50,000 rows and their bodies at once.

    demand_only: archived gigs are never rendered, and reconcile() learns about
    archival from the far cheaper flags query.
    """
    n = 0
    conn = _connect_rw()
    try:
        _ensure_schema(conn)
        for page in board_store.iter_all(demand_only=True):
            n += _upsert(conn, page)
        _state["rows"] = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        _state["watermark"] = _watermark(conn)
        _state["hidden_dupes"] = mark_primaries(conn)
    finally:
        conn.close()
    if not n:
        return 0
    _migrate_mod.migrate(BOARD_DB, verbose=False)   # indexes + FTS
    _invalidate_schema()
    _state["last_sync"] = time.time()
    return n


def incremental() -> int:
    """Only what has been mirrored since our watermark."""
    conn = _connect_rw()
    try:
        _ensure_schema(conn)
        mark = _watermark(conn)
        if not mark:
            return 0
        rows = board_store.pull_since(mark)
        n = _upsert(conn, rows)
        if n:
            _state["rows"] = conn.execute(
                "SELECT COUNT(*) FROM posts").fetchone()[0]
            _state["watermark"] = _watermark(conn)
            _state["adds"] += n
            _state["hidden_dupes"] = mark_primaries(conn)
    finally:
        conn.close()
    if n:
        # New rows need to reach the search index or they are invisible to
        # search while visible on the board, which reads as broken.
        _migrate_mod.migrate(BOARD_DB, verbose=False)
        _invalidate_schema()
    _state["last_sync"] = time.time()
    return n


def reconcile() -> int:
    """
    Apply archival. See the module docstring for why this cannot be skipped.
    """
    # Paged: capped, this could not see an archived gig past the cap, so it
    # would stay on the board copy forever — the exact bug this function is
    # here to prevent.
    dead, tags = [], []
    for page in board_store.iter_flags():
        for row in page:
            # Tolerates the three-column shape too, so a board running ahead of
            # a mirror that has not been migrated yet reconciles archival rather
            # than throwing and reconciling nothing.
            s_, sid, d = row[0], row[1], row[2]
            job, rare = (row[3], row[4]) if len(row) >= 5 else (None, None)
            if not d:
                dead.append((s_, sid))
            if job is not None or rare is not None:
                tags.append((job, rare, s_, sid))
    if not dead and not tags:
        _state["last_reconcile"] = time.time()
        return 0
    conn = _connect_rw()
    try:
        _ensure_schema(conn)
        # Counted with a query, not cur.rowcount: sqlite3 reports the LAST
        # statement's row count after an executemany, so a reconcile that
        # retired hundreds of gigs would report whatever the final UPDATE
        # happened to touch — usually zero. A monitoring number that reads 0
        # while the work is happening is worse than no number.
        # What this copy currently believes, so only real differences are
        # written. Two small columns keyed on the natural key.
        have = {(r[0], r[1]): (r[2], r[3]) for r in conn.execute(
            "SELECT source, source_id, job_type, rare FROM posts")}
        changed = []
        for job, rare, s_, sid in tags:
            cur = have.get((s_, sid))
            if cur is None:
                continue                      # not on this copy yet
            job = cur[0] if job is None else job
            rare = cur[1] if rare is None else rare
            if (job, rare) != cur:
                changed.append((job, rare, s_, sid))

        before = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand = 0").fetchone()[0]
        with conn:
            if dead:
                conn.executemany(
                    "UPDATE posts SET is_demand = 0 WHERE source = ? AND source_id = ? "
                    "AND is_demand != 0", dead)
            # Differences are worked out in Python against what this copy
            # already holds, rather than in a WHERE clause clever enough to be
            # wrong. This runs on a timer over the whole board, so writing every
            # row each pass would rewrite 49,000 rows a minute to change none of
            # them; writing only what differs is usually a handful.
            if changed:
                conn.executemany(
                    "UPDATE posts SET job_type = ?, rare = ? "
                    "WHERE source = ? AND source_id = ?", changed)
        n = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand = 0").fetchone()[0] - before
        _state["archived"] += n
        _state["retagged"] = _state.get("retagged", 0) + len(changed)
    finally:
        conn.close()
    _state["last_reconcile"] = time.time()
    return n


def sweep_mirror() -> int:
    """
    Age gigs past the retention window out of the mirror. Never raises.

    The stamp moves even when the sweep refuses or fails, deliberately: a
    mirror that is unreachable or a floor that trips would otherwise retry on
    every pass of the loop, which is a failing network call every REFRESH_S
    instead of once a day. The reason is kept on _state and surfaced by
    /health, so a refusal is visible rather than silent.
    """
    _state["last_sweep"] = time.time()
    try:
        import board_store
        import queries
        out = board_store.archive_stale_mirror(queries.STALE_DAYS)
        _state["swept"] = out.get("archived", 0)
        _state["sweep_note"] = out.get("note", "")
        return _state["swept"]
    except Exception as e:
        _state["sweep_note"] = f"{type(e).__name__}: {e}"
        return 0


def _loop():
    while True:
        try:
            incremental()
            if time.time() - _state["last_reconcile"] > RECONCILE_S:
                reconcile()
            if time.time() - _state["last_sweep"] > SWEEP_S:
                sweep_mirror()
            _state["note"] = ""
        except Exception as e:
            _state["errors"] += 1
            _state["note"] = f"{type(e).__name__}: {e}"
        time.sleep(REFRESH_S)


def start(block_on_boot: bool = False):
    """
    Idempotent. Boots the local copy, then keeps it current in the background.

    DEFAULTS TO NOT BLOCKING, AND THAT CHANGED FOR A REASON. The boot pull used
    to be synchronous, on the argument that serving an empty board while it ran
    would show visitors a broken page — true, and correct while the pull took
    eleven seconds against a capped 40,000 rows. Paging the whole board took it
    to ~50 seconds, and I did not revisit the decision that depended on the
    cost. Render scans for an open port after starting the process, found none
    because uvicorn had not bound yet, and failed the deploy:

        Started server process
        Waiting for application startup.
        ==> No open ports detected, continuing to scan...

    Binding first and syncing behind it is also the RIGHT shape, not just the
    one that deploys. /health already reports unhealthy on an empty board, so
    Render keeps routing to the old instance until this one has data — the
    health check does the waiting instead of the startup hook, which is what a
    health check is for.
    """
    global _started
    with _lock:
        if _started:
            return
        _started = True
    if block_on_boot:
        conn = _connect_rw()
        try:
            _ensure_schema(conn)
            have = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        finally:
            conn.close()
        if have:
            _state["rows"] = have
            incremental()
        else:
            full_sync()
        reconcile()
    threading.Thread(target=_loop, daemon=True, name="board-sync").start()


def start_background():
    """
    Bind the port now, fill the board behind it.

    The first thing the loop does is rehydrate, so the only difference from the
    old blocking path is WHEN the process starts answering — immediately,
    unhealthy, instead of in a minute, healthy.
    """
    global _started
    with _lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_boot_then_loop, daemon=True, name="board-sync").start()


def _boot_then_loop():
    try:
        conn = _connect_rw()
        try:
            _ensure_schema(conn)
            have = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        finally:
            conn.close()
        if have:
            _state["rows"] = have
            incremental()
        else:
            full_sync()
        reconcile()
    except Exception as e:
        _state["errors"] += 1
        _state["note"] = f"boot sync failed: {type(e).__name__}: {e}"[:200]
    _loop()


if __name__ == "__main__":
    t = time.time()
    print(f"board db: {BOARD_DB}")
    print(f"mirror enabled: {board_store.enabled()}  count: {board_store.count():,}")
    start()
    s = state()
    print(f"  rows local: {s['rows']:,}")
    print(f"  watermark:  {s['watermark']}")
    print(f"  archived:   {s['archived']:,}")
    print(f"  boot took:  {time.time()-t:.1f}s")

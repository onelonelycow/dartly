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
_DERIVED = ("is_remote", "is_onsite", "restrict_cc", "lang_code", "city_lock")


def _derive(rec: dict) -> tuple:
    title = (rec.get("title") or "")
    body = (rec.get("body") or "")
    t = _location.tag({"title": title, "body": body})
    return (1 if t["remote"] else 0,
            1 if t["onsite"] else 0,
            t["restrict"] or "",
            _lang.detect(title, body) or "en",
            _location.city_lock({"title": title}) or "")

BOARD_DB = os.environ.get("NABBLY_BOARD_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "board.db")
REFRESH_S = int(os.environ.get("NABBLY_REFRESH_S") or 60)
RECONCILE_S = int(os.environ.get("NABBLY_RECONCILE_S") or 900)

_COLS = board_store.COLS
_state = {"rows": 0, "last_sync": 0.0, "last_reconcile": 0.0,
          "watermark": "", "adds": 0, "archived": 0, "errors": 0, "note": ""}
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
        f"{c} INTEGER" if c in ("is_demand", "page_checked", "link_checked")
        else f"{c} TEXT" for c in _COLS)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {cols}, sort_at TEXT,
            is_remote INTEGER, is_onsite INTEGER, restrict_cc TEXT,
            lang_code TEXT, city_lock TEXT,
            UNIQUE (source, source_id))""")
    # An older board.db predates the derived columns; add them rather than
    # forcing a full re-pull.
    have = {r[1] for r in conn.execute("PRAGMA table_info(posts)")}
    for c in _DERIVED:
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


def _watermark(conn) -> str:
    row = conn.execute(
        "SELECT COALESCE(MAX(fetched_at), '') FROM posts").fetchone()
    return row[0] or ""


def full_sync() -> int:
    """Pull the whole board. Boot, or an empty local file."""
    rows = board_store.pull()
    if not rows:
        return 0
    conn = _connect_rw()
    try:
        _ensure_schema(conn)
        n = _upsert(conn, rows)
        _state["rows"] = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        _state["watermark"] = _watermark(conn)
    finally:
        conn.close()
    _migrate_mod.migrate(BOARD_DB, verbose=False)   # indexes + FTS
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
    finally:
        conn.close()
    if n:
        # New rows need to reach the search index or they are invisible to
        # search while visible on the board, which reads as broken.
        _migrate_mod.migrate(BOARD_DB, verbose=False)
    _state["last_sync"] = time.time()
    return n


def reconcile() -> int:
    """
    Apply archival. See the module docstring for why this cannot be skipped.
    """
    flags = board_store.pull_flags()
    if not flags:
        return 0
    dead = [(s, sid) for s, sid, d in flags if not d]
    if not dead:
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
        before = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand = 0").fetchone()[0]
        with conn:
            conn.executemany(
                "UPDATE posts SET is_demand = 0 WHERE source = ? AND source_id = ? "
                "AND is_demand != 0", dead)
        n = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand = 0").fetchone()[0] - before
        _state["archived"] += n
    finally:
        conn.close()
    _state["last_reconcile"] = time.time()
    return n


def _loop():
    while True:
        try:
            incremental()
            if time.time() - _state["last_reconcile"] > RECONCILE_S:
                reconcile()
            _state["note"] = ""
        except Exception as e:
            _state["errors"] += 1
            _state["note"] = f"{type(e).__name__}: {e}"
        time.sleep(REFRESH_S)


def start(block_on_boot: bool = True):
    """
    Idempotent. Boots the local copy, then keeps it current in the background.

    The boot pull is synchronous on purpose: serving an empty board while the
    first pull runs would show visitors a broken page, and the pull takes
    seconds, not minutes.
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

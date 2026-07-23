"""
store.py — the copy of the data that survives a redeploy.

THE PROBLEM: Render's free tier wipes the instance's disk on every deploy. The
gig database doesn't care, it's rebuilt from the sources each time. But a
person's profile, their alert channels, their saved drafts, and their account
(which trial day they're on, whether they've upgraded) live in files on that
disk. Wipe it and a tester who signed in yesterday comes back to an empty
profile and a reset trial, which reads as "this product is broken."

THE FIX: a durable key-value mirror in Supabase (a hosted Postgres). It is a
BACKUP, not the working store. The app still reads and writes the local files,
which are fast and already battle-tested; every write is also copied here, and
when the disk has been wiped, a missing file is pulled back from here and
rewritten locally. Nothing about the existing logic changes; this just catches
what the wipe would have dropped.

DEGRADES CLEANLY: with no DATABASE_URL set, enabled() is False and every call
here is a no-op, so the app behaves exactly as it did before Supabase existed.
Every operation is wrapped so a slow or unreachable database can never block or
crash a page; the worst case is that one write doesn't get mirrored and is
re-mirrored on the next save.

WHY IT'S TESTABLE WITHOUT SUPABASE: the one SQL statement it relies on,
INSERT ... ON CONFLICT DO UPDATE, is written the same way in SQLite and
Postgres. Point DATABASE_URL at a sqlite file and the logic runs identically to
how it will run against Supabase, which is how this was verified before a real
Supabase project existed.
"""
import json
import os
import threading

DB_URL = os.environ.get("DATABASE_URL", "").strip()
_TIMEOUT_S = 8
_lock = threading.Lock()
_ready = False


def _is_pg(url: str) -> bool:
    return url.startswith(("postgres://", "postgresql://"))


def enabled() -> bool:
    return bool(DB_URL)


def _pg_dsn(url: str) -> str:
    # Supabase requires TLS; add it if the URL doesn't already ask for it.
    if "sslmode=" in url:
        return url
    return url + ("&" if "?" in url else "?") + "sslmode=require"


def _connect():
    """Returns (connection, placeholder). Placeholder differs by driver."""
    if _is_pg(DB_URL):
        import psycopg
        return psycopg.connect(_pg_dsn(DB_URL), connect_timeout=_TIMEOUT_S), "%s"
    import sqlite3
    path = DB_URL.replace("sqlite:///", "").replace("sqlite://", "")
    return sqlite3.connect(path, timeout=_TIMEOUT_S), "?"


def _run(sql: str, params=(), fetch: bool = False):
    """One statement, committed, connection closed. Params are positional."""
    conn, ph = _connect()
    if ph == "?":
        sql = sql.replace("%s", "?")
    try:
        with conn:                       # commits on clean exit (both drivers)
            cur = conn.execute(sql, params)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def _init():
    global _ready
    if _ready or not enabled():
        return
    with _lock:
        if _ready:
            return
        _run("""CREATE TABLE IF NOT EXISTS nabbly_kv (
                    scope   text NOT NULL,
                    name    text NOT NULL,
                    data    text NOT NULL,
                    updated double precision NOT NULL,
                    PRIMARY KEY (scope, name)
                )""")
        _ready = True


# ---------------------------------------------------------------------------
# Public API — all best-effort, all silent on failure.
# ---------------------------------------------------------------------------
def put(scope: str, name: str, obj) -> bool:
    """Mirror one JSON value. Returns True if it reached the database."""
    if not enabled():
        return False
    try:
        _init()
        import time as _t
        # time.monotonic() would be wrong here (relative), but a wall clock is
        # only used to break ties between two writers; approximate is fine.
        stamp = _t.time()
        _run("INSERT INTO nabbly_kv (scope, name, data, updated) "
             "VALUES (%s, %s, %s, %s) "
             "ON CONFLICT (scope, name) DO UPDATE SET "
             "data = excluded.data, updated = excluded.updated",
             (scope, name, json.dumps(obj), stamp))
        return True
    except Exception:
        return False


def get(scope: str, name: str):
    """The mirrored value, or None if absent or the database is unreachable."""
    if not enabled():
        return None
    try:
        _init()
        rows = _run("SELECT data FROM nabbly_kv WHERE scope=%s AND name=%s",
                    (scope, name), fetch=True)
        if rows:
            return json.loads(rows[0][0])
    except Exception:
        pass
    return None


def list_scope(scope: str) -> dict:
    """Every {name: value} stored under one scope (e.g. all accounts)."""
    if not enabled():
        return {}
    try:
        _init()
        rows = _run("SELECT name, data FROM nabbly_kv WHERE scope=%s",
                    (scope,), fetch=True)
        return {r[0]: json.loads(r[1]) for r in rows}
    except Exception:
        return {}


def delete(scope: str, name: str):
    if not enabled():
        return
    try:
        _init()
        _run("DELETE FROM nabbly_kv WHERE scope=%s AND name=%s", (scope, name))
    except Exception:
        pass


def healthy() -> bool:
    """For the admin page: is the durable mirror actually reachable right now?"""
    if not enabled():
        return False
    try:
        _init()
        _run("SELECT 1", fetch=True)
        return True
    except Exception:
        return False

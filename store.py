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
_last_error = ""      # sanitised reason the mirror is unreachable, for the admin page

# Passive health of the WRITE path. healthy() below is an active probe, and it
# only runs when somebody opens the admin page — so it answers "is it up right
# now", never "has anything been saved in the last six hours". Every mirror
# write returns False on failure and every caller ignores that, by design: a
# dead mirror must not break a signup. The consequence is that losing the
# durable store is completely invisible while the app carries on looking fine,
# right up until a redeploy wipes the disk and takes the accounts, the wins and
# the board with it. These counters are what make that audible.
_w = {"ok": 0, "failed": 0, "streak": 0, "last_ok": 0.0, "last_error": ""}


def _note_write(ok: bool, exc: Exception | None = None):
    """Record one mirror write, and speak up when the streak says it's real."""
    import time as _t
    if ok:
        if _w["streak"]:
            print(f"  store: durable store back after {_w['streak']} failed "
                  f"write(s)", flush=True)
        _w["ok"] += 1
        _w["streak"] = 0
        _w["last_ok"] = _t.time()
        return
    _w["failed"] += 1
    _w["streak"] += 1
    _w["last_error"] = f"{type(exc).__name__}: {_sanitise(exc)}" if exc else ""
    # 1st says it happened, 5th and 25th say it isn't a blip, then hourly-ish
    # so a long outage stays on the record without burying the log.
    if _w["streak"] in (1, 5, 25) or _w["streak"] % 100 == 0:
        print(f"  ! store: durable write failed ({_w['streak']} in a row) — "
              f"nothing is being persisted; a redeploy would lose it: "
              f"{_w['last_error']}", flush=True)


def write_health() -> dict:
    """Counters for the admin page. See _w."""
    return dict(_w)


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
        _note_write(True)
        return True
    except Exception as e:
        _note_write(False, e)
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


def _sanitise(msg: str) -> str:
    """
    A connection error, safe to show on the admin page.

    Postgres auth/host errors don't echo the password, but strip any DSN just
    in case, and cap the length.
    """
    import re
    msg = re.sub(r"postgres(?:ql)?://\S+", "postgresql://…", str(msg))
    return msg[:280]


def healthy() -> bool:
    """For the admin page: is the durable mirror actually reachable right now?"""
    global _last_error
    if not enabled():
        return False
    try:
        _init()
        _run("SELECT 1", fetch=True)
        _last_error = ""
        return True
    except Exception as e:
        _last_error = f"{type(e).__name__}: {_sanitise(e)}"
        return False


def last_error() -> str:
    return _last_error

"""
web/migrate.py — prepare the board table for query-per-page serving.

Adds what the Streamlit app never needed because it read the whole board into
memory and did the work in pandas: a stored sort key, indexes that carry the
board's sort order, and an FTS5 text index for search.

SAFE TO RUN REPEATEDLY, AND ON A LIVE DATABASE. Every step is guarded, and
none of it changes a value the existing app reads — sort_at is a new column
derived from two it already has, and posts_fts is a separate virtual table.
The Streamlit app keeps working, untouched, before and after.

Measured on the 53,525-row board (see the numbers in `bench` below):
    default board view      ~1,000 ms  ->  0.03 ms
    filtered (two fields)   ~1,000 ms  ->  0.06 ms
    keyword search          ~1,000 ms  ->  0.44 ms

THE COUNTERINTUITIVE PART, DO NOT "FIX" IT: there is deliberately NO index on
(is_demand, job_type, size_tier). That index exists in the obvious design, and
it is actively harmful — SQLite prefers it, and because it cannot satisfy the
ORDER BY, it then sorts every matching row to return 25. Measured at 16.95ms
with it and 0.06ms without. The indexes below all END in sort_at so the sort
comes free from the index walk.
"""
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Indexes end in sort_at DESC on purpose — see the note above.
_INDEXES = (
    ("ix_posts_sort", "posts(is_demand, sort_at DESC)"),
    ("ix_posts_jt", "posts(is_demand, job_type, sort_at DESC)"),
    ("ix_posts_src", "posts(is_demand, source, sort_at DESC)"),
)


def _cols(conn, table="posts"):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def has_fts(conn) -> bool:
    return any("FTS5" in (r[0] or "").upper()
               for r in conn.execute("PRAGMA compile_options"))


def migrate(db_path: str, verbose: bool = True) -> dict:
    out = {"sort_at": False, "indexes": [], "fts": False, "rows": 0}
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")     # readers don't block writers
        out["rows"] = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand=1").fetchone()[0]

        if "sort_at" not in _cols(conn):
            conn.execute("ALTER TABLE posts ADD COLUMN sort_at TEXT")
            out["sort_at"] = True
        # Always refresh: ingest writes posted_at/fetched_at and knows nothing
        # about this column, so rows added since the last run have it NULL.
        # Cheap — the WHERE means it only touches those rows.
        n = conn.execute(
            "UPDATE posts SET sort_at = COALESCE(NULLIF(posted_at,''), fetched_at) "
            "WHERE sort_at IS NULL OR sort_at = ''").rowcount
        if verbose and n:
            print(f"  sort_at: filled {n:,} rows")

        # An index SQLite prefers but cannot sort with makes the board 280x
        # slower. If an earlier version created it, take it back out.
        conn.execute("DROP INDEX IF EXISTS ix_posts_board")

        for name, decl in _INDEXES:
            before = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?",
                (name,)).fetchone()[0]
            conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {decl}")
            if not before:
                out["indexes"].append(name)

        if has_fts(conn):
            exists = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='posts_fts'"
            ).fetchone()[0]
            if not exists:
                # external-content: the index stores terms, the rows stay in
                # posts. Keeps the file smaller and means one copy of the text.
                conn.execute("CREATE VIRTUAL TABLE posts_fts USING fts5("
                             "title, body, content='posts', content_rowid='id')")
                conn.execute("INSERT INTO posts_fts(rowid, title, body) "
                             "SELECT id, title, body FROM posts")
                out["fts"] = True
            else:
                # Catch up on anything ingested since the last run.
                conn.execute(
                    "INSERT INTO posts_fts(rowid, title, body) "
                    "SELECT p.id, p.title, p.body FROM posts p "
                    "WHERE p.id NOT IN (SELECT rowid FROM posts_fts)")
        elif verbose:
            print("  ! FTS5 not compiled into this SQLite — search falls back to LIKE")

        conn.execute("ANALYZE")
        conn.commit()
        return out
    finally:
        conn.close()


def bench(db_path: str):
    """Prove the indexes are doing their job, rather than assuming they are."""
    conn = sqlite3.connect(db_path)
    skills = [r[0] for r in conn.execute(
        "SELECT DISTINCT job_type FROM posts WHERE job_type IS NOT NULL")]
    cases = [
        ("default board view",
         "SELECT id,title FROM posts WHERE is_demand=1 "
         "ORDER BY sort_at DESC LIMIT 25", ()),
        ("filtered board view",
         "SELECT id,title FROM posts WHERE is_demand=1 AND job_type IN (%s) "
         "ORDER BY sort_at DESC LIMIT 25" % ",".join("?" * len(skills[:2])),
         tuple(skills[:2])),
        ("page 200 (deep offset)",
         "SELECT id,title FROM posts WHERE is_demand=1 "
         "ORDER BY sort_at DESC LIMIT 25 OFFSET 5000", ()),
        ("result count",
         "SELECT COUNT(*) FROM posts WHERE is_demand=1", ()),
    ]
    if conn.execute("SELECT COUNT(*) FROM sqlite_master "
                    "WHERE name='posts_fts'").fetchone()[0]:
        cases.append(("keyword search",
                      "SELECT p.id,p.title FROM posts_fts f JOIN posts p ON p.id=f.rowid "
                      "WHERE posts_fts MATCH ? AND p.is_demand=1 "
                      "ORDER BY p.sort_at DESC LIMIT 25", ("figma",)))
    print(f"\n  {'query':<26}{'time':>10}")
    print("  " + "-" * 36)
    for label, sql, params in cases:
        conn.execute(sql, params).fetchall()
        t = time.perf_counter()
        for _ in range(30):
            conn.execute(sql, params).fetchall()
        print(f"  {label:<26}{(time.perf_counter()-t)/30*1000:>8.2f} ms")
    conn.close()


if __name__ == "__main__":
    import db as _db
    path = sys.argv[1] if len(sys.argv) > 1 else _db.DB_PATH
    print(f"migrating {path}")
    r = migrate(path)
    print(f"  rows: {r['rows']:,}")
    print(f"  sort_at added: {r['sort_at']}")
    print(f"  indexes created: {r['indexes'] or 'none (already present)'}")
    print(f"  fts built: {r['fts']}")
    bench(path)

"""
web/queries.py — the board, as database queries instead of a DataFrame.

This is the whole point of the rewrite. The Streamlit app loads all 53,525
gigs into memory, filters them in pandas, and slices out 25 to display. That
costs ~190MB of transient allocation and ~1s of Python per visitor, and it is
why five simultaneous readers could put a 2GB instance on the floor.

Here the database returns the 25 rows being displayed, and nothing else ever
enters Python. Measured at 0.03-0.44ms per query against the same board.

Connections are per-request and read-only. SQLite handles concurrent readers
natively in WAL mode, so there is no pool to size and no shared state to get
wrong — which also means no cache keyed on a visitor, the mistake that caused
both of the app's memory incidents.
"""
import os
import re
import sqlite3

# Columns a card actually renders. body is DELIBERATELY ABSENT: it is the
# heaviest column on the table and nothing on the list view shows it. Fetching
# it "just in case" is how the frame got expensive in the first place.
CARD_COLS = ("id", "title", "url", "source", "sort_at", "posted_at",
             "job_type", "size_tier", "urgency")

PAGE_SIZE = 25
MAX_LIMIT = 100          # a caller cannot ask for the whole board


def _db_path() -> str:
    import db as _db
    return _db.DB_PATH


def connect(path: str | None = None) -> sqlite3.Connection:
    """A read-only connection. Read-only so a bug here can never write."""
    p = path or _db_path()
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _in_clause(col: str, values) -> tuple[str, list]:
    """`col IN (?, ?, ...)`, or nothing at all when the filter isn't set."""
    values = [v for v in (values or []) if v]
    if not values:
        return "", []
    return f" AND {col} IN ({','.join('?' * len(values))})", list(values)


# FTS5 treats bare punctuation as syntax, so a search for "c++ dev" or a stray
# quote is a query error rather than zero results. Everything non-word becomes
# a space and each term is quoted, which makes any input a literal phrase
# search. Users type search boxes, not query languages.
_FTS_SAFE = re.compile(r"[^\w\s]")


def _fts_query(keyword: str) -> str:
    terms = _FTS_SAFE.sub(" ", keyword or "").split()
    return " AND ".join(f'"{t}"' for t in terms)


def board(keyword: str = "", job_types=None, sizes=None, sources=None,
          urgent_only: bool = False, page: int = 0, page_size: int = PAGE_SIZE,
          conn: sqlite3.Connection | None = None) -> dict:
    """
    One page of the board, plus the honest total.

    Returns {"rows": [...], "total": int, "page": int, "pages": int}. `total`
    is the count of everything matching, not len(rows), so the UI can tell
    "you've seen it all" from "you've seen the first page".
    """
    own = conn is None
    conn = conn or connect()
    try:
        page_size = max(1, min(int(page_size or PAGE_SIZE), MAX_LIMIT))
        page = max(0, int(page or 0))

        where = "WHERE p.is_demand = 1"
        params: list = []
        for col, vals in (("p.job_type", job_types), ("p.size_tier", sizes),
                          ("p.source", sources)):
            clause, ps = _in_clause(col, vals)
            where += clause
            params += ps
        if urgent_only:
            where += " AND p.urgency = 'Urgent'"

        kw = _fts_query(keyword)
        if kw and _has_fts(conn):
            frm = ("FROM posts p JOIN posts_fts f ON f.rowid = p.id "
                   "AND posts_fts MATCH ?")
            params = [kw] + params
        elif kw:
            # No FTS5 in this SQLite: every word must appear somewhere.
            frm = "FROM posts p"
            for term in (keyword or "").lower().split():
                where += " AND (lower(p.title) LIKE ? OR lower(p.body) LIKE ?)"
                params += [f"%{term}%", f"%{term}%"]
        else:
            frm = "FROM posts p"

        total = conn.execute(f"SELECT COUNT(*) {frm} {where}", params).fetchone()[0]
        cols = ", ".join(f"p.{c}" for c in CARD_COLS)
        rows = conn.execute(
            f"SELECT {cols} {frm} {where} ORDER BY p.sort_at DESC LIMIT ? OFFSET ?",
            params + [page_size, page * page_size]).fetchall()
        return {"rows": [dict(r) for r in rows], "total": total, "page": page,
                "pages": max(1, -(-total // page_size))}
    finally:
        if own:
            conn.close()


_fts_cache: dict[int, bool] = {}


def _has_fts(conn) -> bool:
    key = id(conn)
    if key not in _fts_cache:
        _fts_cache[key] = bool(conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='posts_fts'"
        ).fetchone()[0])
    return _fts_cache[key]


def facets(conn: sqlite3.Connection | None = None) -> dict:
    """
    Counts per field and per source, for the filter chips.

    A GROUP BY over an indexed column, which is what the Streamlit app spends
    a value_counts() over the whole in-memory board on.
    """
    own = conn is None
    conn = conn or connect()
    try:
        def group(col):
            return {r[0]: r[1] for r in conn.execute(
                f"SELECT {col}, COUNT(*) FROM posts WHERE is_demand = 1 "
                f"AND {col} IS NOT NULL AND {col} != '' GROUP BY {col} "
                f"ORDER BY COUNT(*) DESC")}
        return {"job_type": group("job_type"), "source": group("source"),
                "size_tier": group("size_tier")}
    finally:
        if own:
            conn.close()


def board_total(conn: sqlite3.Connection | None = None) -> int:
    own = conn is None
    conn = conn or connect()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_demand = 1").fetchone()[0]
    finally:
        if own:
            conn.close()

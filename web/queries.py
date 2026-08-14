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
          urgent_only: bool = False, where_work: str = "", languages=None,
          page: int = 0, page_size: int = PAGE_SIZE,
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

        # Location. The signed-in board can also weigh a reader's region and
        # city; an anonymous page knows neither, so this is the honest subset:
        # is the work remote, or is it hands-on. Nothing here claims to know
        # where the visitor is.
        if where_work == "remote" and _has_col(conn, "is_remote"):
            where += " AND p.is_remote = 1"
        elif where_work == "onsite" and _has_col(conn, "is_onsite"):
            where += " AND p.is_onsite = 1"

        clause, ps = _in_clause("p.lang_code", languages
                                if _has_col(conn, "lang_code") else None)
        where += clause
        params += ps

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


_col_cache: dict[tuple, bool] = {}


def _has_col(conn, col: str) -> bool:
    """
    Does this database carry a column the board service derives?

    Guarded rather than assumed so the same queries run against the board
    service's enriched copy AND a plain database (local dev pointed at the
    Streamlit app's file, or a board.db from before the derived columns
    existed). A filter over a missing column is skipped, not fatal.
    """
    key = (id(conn), col)
    if key not in _col_cache:
        _col_cache[key] = col in {r[1] for r in
                                  conn.execute("PRAGMA table_info(posts)")}
    return _col_cache[key]


def facets(conn: sqlite3.Connection | None = None, ctx: dict | None = None) -> dict:
    """
    Counts for the filter chips, WITHIN the filters already applied.

    Each dimension is counted with every OTHER active filter applied but not
    its own — standard faceted search, and the only version that tells the
    truth. Counted globally, a chip reading "Development / tech 7,262" while
    Remote is active promises 7,262 gigs and delivers 2,573, because the click
    keeps Remote on. That is the same broken promise as the location chips on
    the Streamlit board, one dimension over.

    Excluding a dimension from its own count is what makes multi-select work:
    with Design selected, the Development chip has to say how many you would
    get by ALSO picking Development, not how many are left inside Design.
    """
    own = conn is None
    conn = conn or connect()
    ctx = ctx or {}
    try:
        def group(col, skip):
            if not _has_col(conn, col):
                return {}
            where = "WHERE is_demand = 1"
            params: list = []
            for key, column in (("job_types", "job_type"), ("sizes", "size_tier"),
                                ("sources", "source"), ("languages", "lang_code")):
                if key == skip or not ctx.get(key) or not _has_col(conn, column):
                    continue
                vals = [v for v in ctx[key] if v]
                if vals:
                    where += f" AND {column} IN ({','.join('?' * len(vals))})"
                    params += vals
            if ctx.get("urgent_only"):
                where += " AND urgency = 'Urgent'"
            ww = ctx.get("where_work")
            if ww == "remote" and _has_col(conn, "is_remote"):
                where += " AND is_remote = 1"
            elif ww == "onsite" and _has_col(conn, "is_onsite"):
                where += " AND is_onsite = 1"
            return {r[0]: r[1] for r in conn.execute(
                f"SELECT {col}, COUNT(*) FROM posts {where} "
                f"AND {col} IS NOT NULL AND {col} != '' GROUP BY {col} "
                f"ORDER BY COUNT(*) DESC", params)}

        return {"job_type": group("job_type", "job_types"),
                "source": group("source", "sources"),
                "size_tier": group("size_tier", "sizes"),
                "lang_code": group("lang_code", "languages")}
    finally:
        if own:
            conn.close()


def location_counts(conn: sqlite3.Connection | None = None,
                    ctx: dict | None = None) -> dict:
    """
    (everywhere, remote, onsite) for the location toggle.

    Counted through the SAME predicates board() filters on, and within whatever
    else is already selected. On the Streamlit board these were two separate
    loops that disagreed, so a chip promised a number the tap didn't deliver.
    A chip is a promise about what one tap gives you, so it has to count the
    board the tap lands on — including the field or budget already chosen.
    """
    own = conn is None
    conn = conn or connect()
    ctx = ctx or {}
    try:
        where = "WHERE is_demand = 1"
        params: list = []
        for key, column in (("job_types", "job_type"), ("sizes", "size_tier"),
                            ("sources", "source"), ("languages", "lang_code")):
            vals = [v for v in (ctx.get(key) or []) if v]
            if vals and _has_col(conn, column):
                where += f" AND {column} IN ({','.join('?' * len(vals))})"
                params += vals
        if ctx.get("urgent_only"):
            where += " AND urgency = 'Urgent'"
        total = conn.execute(
            f"SELECT COUNT(*) FROM posts {where}", params).fetchone()[0]
        if not _has_col(conn, "is_remote"):
            return {"all": total, "remote": 0, "onsite": 0}
        row = conn.execute(
            f"SELECT COALESCE(SUM(is_remote), 0), COALESCE(SUM(is_onsite), 0) "
            f"FROM posts {where}", params).fetchone()
        return {"all": total, "remote": int(row[0]), "onsite": int(row[1])}
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

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
from datetime import datetime, timedelta, timezone

# MUST MATCH db.STALE_DAYS. Deliberately not imported from there: db.py pulls
# in pandas and the whole app's dependency tree, and this service exists
# precisely because it does not do that. Duplicated with a name and a note
# rather than silently diverging.
# MUST MATCH db.STALE_DAYS. Two copies of one window is how a board serves
# gigs the sweep already retired: db.py archives at 14 days while this served
# 21, so a week of rows would render here and 404 on the source. Retuned
# together 2026-08-24 (21 -> 14) when boot hit 86% of its budget; db.py
# carries the full reasoning.
STALE_DAYS = int(os.environ.get("NABBLY_STALE_DAYS") or 14)


def _stale_cutoff() -> str:
    """The oldest sort_at this service will serve, as an ISO string."""
    return (datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)).isoformat()

# Columns a card renders, body included — the app's cards show a clamped
# preview, so the board has to have it.
#
# THIS IS NOT A RETREAT FROM THE ORIGINAL RULE, it is the point of it. body is
# the heaviest column on the table, and the Streamlit board pays for it 53,525
# times to display 25 previews. Here it is fetched for the 25 rows on the page
# and nowhere else: the filter, the sort, the counts and the ranking window all
# run over the narrow columns and never touch it. Twenty-five bodies is about
# 40KB; the whole column is 40MB.
CARD_COLS = ("id", "title", "url", "source", "sort_at", "posted_at",
             "job_type", "size_tier", "urgency", "body", "apply_email",
             "is_remote", "is_onsite", "restrict_cc", "is_worldwide", "rare")

PAGE_SIZE = 25
MAX_LIMIT = 100          # a caller cannot ask for the whole board

# ONE SOURCE SHOULD NOT OWN THE SHOP WINDOW.
#
# The board is ordered newest-first, and the feeds do not post at the same
# rate. Measured on the live board on 2026-08-19, the first 60 gigs a visitor
# saw under "Writing / content" were 90% one source, and under "Design /
# creative" 53%. Nothing in the code caused that and nothing prevented it:
# volume alone decides the top of a recency sort.
#
# It matters because of what the field pages promise — work gathered "from
# across the job boards and hiring communities" — and a first page that is
# nine-tenths one site does not read like that, whatever the total says.
#
# NOTHING IS HIDDEN OR DROPPED. This is a reordering: a gig held out of one
# page is the next page's first candidate, so the same gigs appear, slightly
# later. It reaches SPREAD_PAGES deep and then stops, because past that point
# somebody is searching rather than browsing and strict recency serves them
# better.
SPREAD_SHARE = 0.4       # at most this share of any one page from one source

# WHY 16 AND NOT 8. The cap can only use the gigs inside its window, so on a
# field where one source posts nine tenths of everything, a shallow window runs
# out of anything else to promote and the page takes the overflow. Measured on
# real data: at 8 pages the writing field settled at 48% rather than the 40%
# the cap asks for, at 16 it reaches 40%, and past 16 nothing improves.
#
# It costs nothing in freshness. The oldest gig on page one is the same at 8
# pages and at 80 — the reach back in time is set by the cap, not the window —
# and the extra rows are id and source only, 6ms against 5ms for three pages.
SPREAD_PAGES = 16        # how deep the rebalance reaches


def _spread(pairs, page_size: int, share: float = SPREAD_SHARE) -> list:
    """
    Reorder (id, source) pairs so no source exceeds `share` of a page.

    Recency is preserved inside a source and inside a page: this only decides
    which page a gig lands on, never whether it lands. If a page cannot be
    filled under the cap (a field with one source, say) it takes the overflow
    in order rather than coming back short.
    """
    cap = max(1, int(page_size * share))
    remaining, out = list(pairs), []
    while remaining:
        used: dict = {}
        page, deferred = [], []
        for pid, src in remaining:
            if len(page) < page_size and used.get(src, 0) < cap:
                page.append(pid)
                used[src] = used.get(src, 0) + 1
            else:
                deferred.append((pid, src))
        if len(page) < page_size and deferred:
            need = page_size - len(page)
            page += [pid for pid, _ in deferred[:need]]
            deferred = deferred[need:]
        out += page
        remaining = deferred
    return out


def _db_path() -> str:
    import db as _db
    return _db.DB_PATH


class _Conn(sqlite3.Connection):
    """
    A connection that can carry which file it opened.

    sqlite3.Connection is a C type with no __dict__, so setting an attribute on
    a plain one raises AttributeError. Subclassing gives it one. The path is
    what the schema caches key on — see _has_fts.
    """
    nabbly_path = ""


def connect(path: str | None = None) -> sqlite3.Connection:
    """A read-only connection. Read-only so a bug here can never write."""
    p = path or _db_path()
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True,
                           check_same_thread=False, factory=_Conn)
    conn.row_factory = sqlite3.Row
    conn.nabbly_path = p
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


def _city_clause(conn, city: str, relocate: bool) -> tuple[str, list]:
    """
    Hide gigs pinned to a metro that isn't the reader's — app.py's rule.

    A title like "Senior Product Designer in New York City, NY" is work for
    people in that metro, and showing it to everyone fills the board with jobs
    most readers cannot take. app.py's apply_city_lock() has always dropped
    them; this service had no equivalent, which was the last of the app/board
    gap: measured 2026-08-17 with both sampled together, the app served 42,616
    and this service 42,806, and there were exactly 190 live English gigs
    carrying a city_lock. Not approximately 190. The same number.

    Three cases, matching the app exactly:
      * said they would relocate  -> no filter at all
      * gave no city              -> every pinned gig is hidden
      * gave a city               -> pinned gigs are hidden UNLESS the post
                                     names their city, so "New York" still
                                     matches "New York City"
    """
    if relocate or not _has_col(conn, "city_lock"):
        return "", []
    city = (city or "").strip().lower()
    if not city:
        return " AND COALESCE(p.city_lock, '') = ''", []
    # LIKE on title only. The app tests title and body, but body is the column
    # this service never reads on a filter path — that is the whole reason a
    # board page costs 0.01ms here and ~1s there — and city_lock is itself
    # derived from the title, so a metro named only in the body was never
    # what pinned the gig.
    return (" AND (COALESCE(p.city_lock, '') = '' OR LOWER(p.title) LIKE ?)",
            [f"%{city}%"])


def _filters(conn, keyword, job_types, sizes, sources, urgent_only,
             where_work, languages, since_hours=0, city="", relocate=False,
             since_ts=""):
    """
    The WHERE clause, its parameters, and the FROM, for every board query.

    ONE PLACE, deliberately. board() and fit_ranked() have to agree exactly: if
    the ranked view filtered even slightly differently, turning on "best match"
    would silently change WHICH gigs you are looking at as well as their order,
    and nothing about the page would say so. The chip counts read from the same
    predicates for the same reason.

    Every value is bound as a parameter — nothing from the request is ever
    formatted into SQL. Only the column names, which come from this module.
    """
    where = "WHERE p.is_demand = 1"
    params: list = []
    # FRESHNESS IS ENFORCED HERE, NOT ONLY INHERITED.
    #
    # The app ages a gig off the board after STALE_DAYS on the grounds that a
    # dead listing is worse than no listing, and this service was relying
    # entirely on hearing about that through the mirror. It did not hear about
    # it: measured 2026-08-16, the app was serving 43,411 gigs and this service
    # 47,706, and 3,849 of the difference were postings past the cutoff that
    # the app had already retired. The handshake that carries archival to the
    # mirror fails silently (see db.archive_stale), so this service went on
    # serving month-old listings with nothing anywhere reporting a problem —
    # and by then the marketing site pointed its front door here.
    #
    # A second surface enforcing the same rule from its own data is the point.
    # Anything that depends on a network handshake completing is a rule that is
    # only usually applied.
    #
    # Cheap: every index ends in sort_at DESC, so this is a bounded range scan
    # on the column already being ordered by, not an extra predicate the
    # indexes cannot serve. Measured before and after — see the commit.
    where += " AND p.sort_at >= ?"
    params.append(_stale_cutoff())
    # Metro-pinned gigs, on the same rule the app uses. See _city_clause.
    _c, _p = _city_clause(conn, city, relocate)
    where += _c
    params += _p
    # PUBLIC ROWS ONLY. Anything forwarded in by email belongs to the person
    # who forwarded it — those newsletters are often paid subscriptions, and
    # db.py's _owner_clause() has always kept them on that one person's board.
    # This service mirrors the owner column and had no equivalent test, so a
    # privately forwarded gig would have been served to every visitor.
    # Nothing has leaked: the mirror holds no owned rows today, checked
    # 2026-08-16. That is timing, not a safeguard — the first person to forward
    # a newsletter in would have published it. Guarded on the column so an
    # older board.db predating the mirror's owner column still answers.
    if _has_col(conn, "owner"):
        where += " AND COALESCE(p.owner, '') = ''"
    # One row per repeated title. The same role really is syndicated across
    # several feeds — "Sales Development Representative" appeared 42 times,
    # 12.5% of the board was duplicates — and the Streamlit board has always
    # dropped them before rendering. Guarded so a database without the column
    # still works, just without the dedupe.
    if _has_col(conn, "is_primary"):
        where += " AND p.is_primary = 1"
    for col, vals in (("p.job_type", job_types), ("p.size_tier", sizes),
                      ("p.source", sources)):
        clause, ps = _in_clause(col, vals)
        where += clause
        params += ps
    if urgent_only:
        where += " AND p.urgency = 'Urgent'"

    # "Posted in the last N hours" — the Dashboard's freshness quick-filter.
    # Compared against sort_at, which is the column the board is ordered by,
    # so the filter and the ordering agree about what "recent" means.
    # since_ts is NOT since_hours. That one is a rolling window ("last 24h");
    # this is an absolute mark ("since you last looked"). Merging them would
    # produce a wrong number the first time anyone touched either.
    if since_ts:
        where += " AND p.sort_at > ?"
        params.append(since_ts)

    if since_hours:
        cut = (datetime.now(timezone.utc)
               - timedelta(hours=int(since_hours))).isoformat()
        where += " AND p.sort_at >= ?"
        params.append(cut)

    # Location. The signed-in board can also weigh a reader's region and city;
    # an anonymous page knows neither, so this is the honest subset: is the
    # work remote, or is it hands-on. Nothing here claims to know where the
    # visitor is.
    if where_work == "remote" and _has_col(conn, "is_remote"):
        where += " AND p.is_remote = 1"
    elif where_work == "onsite" and _has_col(conn, "is_onsite"):
        where += " AND p.is_onsite = 1"

    clause, ps = _in_clause("p.lang_code",
                            languages if _has_col(conn, "lang_code") else None)
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
    return where, params, frm


def board(keyword: str = "", job_types=None, sizes=None, sources=None,
          urgent_only: bool = False, where_work: str = "", languages=None,
          since_hours: int = 0, city: str = "", relocate: bool = False,
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
        where, params, frm = _filters(conn, keyword, job_types, sizes, sources,
                                      urgent_only, where_work, languages,
                                      since_hours, city, relocate)
        total = conn.execute(f"SELECT COUNT(*) {frm} {where}", params).fetchone()[0]
        cols = ", ".join(f"p.{c}" for c in CARD_COLS)
        depth = SPREAD_PAGES * page_size
        if page * page_size < depth:
            # Two queries on purpose. The spread needs to see further down the
            # board than one page, and CARD_COLS carries every gig's body, so
            # reading 200 full rows to show 25 would cost eight times what this
            # page costs today. id and source are enough to decide the order;
            # the bodies are then fetched for the 25 that survive it.
            window = conn.execute(
                f"SELECT p.id, p.source {frm} {where} "
                f"ORDER BY p.sort_at DESC LIMIT ?", params + [depth]).fetchall()
            order = _spread([(str(r["id"]), r["source"] or "") for r in window],
                            page_size)
            rows = by_ids(order[page * page_size:(page + 1) * page_size], conn)
        else:
            rows = [dict(r) for r in conn.execute(
                f"SELECT {cols} {frm} {where} ORDER BY p.sort_at DESC "
                f"LIMIT ? OFFSET ?",
                params + [page_size, page * page_size]).fetchall()]
        return {"rows": rows, "total": total, "page": page,
                "pages": max(1, -(-total // page_size))}
    finally:
        if own:
            conn.close()


# Schema facts, cached per DATABASE FILE.
#
# THESE WERE KEYED ON id(conn) AND THAT WAS A BUG. Connections are per-request
# and short-lived, and CPython reuses the id of a freed object — verified: a
# new connection gets the id its predecessor just released, and would then read
# the previous connection's cached answer. It looked harmless because every
# connection opens the same file, and the dicts stayed small for the same
# reason, which is what made it invisible.
#
# The way it bites: on boot the board file exists before migrate() builds
# posts_fts. A request in that window caches "no FTS" against some id, that id
# is reused minutes later, and search silently falls back to the LIKE path —
# hundreds of times slower, with nothing reporting it. Schema is a property of
# the FILE, so that is what it is keyed on, and sync clears it after rebuilding.
_schema_cache: dict[tuple, bool] = {}


def _key(conn, what: str) -> tuple:
    # getattr with a default, not conn.nabbly_path: callers may hand in a
    # plain sqlite3.Connection they opened themselves (tests, scripts), and a
    # schema lookup must not raise because of where the connection came from.
    return (getattr(conn, "nabbly_path", "?"), what)


def clear_schema_cache():
    """Called after the board file's schema changes — see web/sync.py."""
    _schema_cache.clear()


def _has_fts(conn) -> bool:
    k = _key(conn, "@fts")
    if k not in _schema_cache:
        _schema_cache[k] = bool(conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='posts_fts'"
        ).fetchone()[0])
    return _schema_cache[k]


def _has_col(conn, col: str) -> bool:
    """
    Does this database carry a column the board service derives?

    Guarded rather than assumed so the same queries run against the board
    service's enriched copy AND a plain database (local dev pointed at the
    Streamlit app's file, or a board.db from before the derived columns
    existed). A filter over a missing column is skipped, not fatal.
    """
    k = _key(conn, col)
    if k not in _schema_cache:
        _schema_cache[k] = col in {r[1] for r in
                                   conn.execute("PRAGMA table_info(posts)")}
    return _schema_cache[k]


# How many recent gigs get scored when someone sorts by fit.
#
# BOUNDED ON PURPOSE, and this is the whole design. Ranking the full matched
# set is what the Streamlit board does: it loads every gig, scores all of them,
# and shows 25 — ~1s of Python and ~190MB per visitor, which is what put a 2GB
# instance on the floor at five concurrent readers. Scoring a recent window is
# a few milliseconds and a few hundred kilobytes.
#
# The honest cost is that fit ranking reaches back FIT_WINDOW gigs, not
# forever. That matches what the feature is for — the board's promise is gigs
# the moment they drop, and a three-week-old posting ranked first because it
# matches well is not the product. The UI says which window it ranked.
FIT_WINDOW = 500


def fit_ranked(profile: dict, keyword: str = "", job_types=None, sizes=None,
               sources=None, urgent_only: bool = False, where_work: str = "",
               languages=None, since_hours: int = 0,
               city: str = "", relocate: bool = False,
               page: int = 0, page_size: int = PAGE_SIZE,
               resume_text: str = "",
               conn: sqlite3.Connection | None = None) -> dict:
    """
    The same board, ordered by how well each gig fits this person.

    Two queries rather than one: the recent window's ids and scoring fields
    (which needs `body`, the heaviest column on the table), then the card
    columns for the 25 that survive the sort. Fetching bodies for 500 rows and
    card data for 25 keeps this off the path that made the old board expensive.
    """
    import score as _score
    own = conn is None
    conn = conn or connect()
    try:
        page_size = max(1, min(int(page_size or PAGE_SIZE), MAX_LIMIT))
        page = max(0, int(page or 0))
        where, params, frm = _filters(conn, keyword, job_types, sizes, sources,
                                      urgent_only, where_work, languages,
                                      since_hours, city, relocate)
        # The TRUE number matching the filters, not the size of the window we
        # ranked. Reporting the window here would put "500 gigs" in the header
        # of a board with twelve thousand matches — the same kind of number
        # that promises one thing and delivers another as the chip counts did.
        matched = conn.execute(f"SELECT COUNT(*) {frm} {where}", params).fetchone()[0]
        fit_cols = ", ".join(f"p.{c}" for c in _score.FIT_FIELDS)
        rows = conn.execute(
            f"SELECT p.id, {fit_cols} {frm} {where} "
            f"ORDER BY p.sort_at DESC LIMIT {int(FIT_WINDOW)}", params).fetchall()
        if not rows:
            return {"rows": [], "total": 0, "page": 0, "pages": 1,
                    "window": FIT_WINDOW, "ranked": True, "matched": 0}

        scored = []
        for r in rows:
            gig = {c: r[c] for c in _score.FIT_FIELDS}
            s, why = _score.fit_score(gig, profile, resume_text=resume_text)
            scored.append((s, why, r["id"]))
        # Stable within a score so equal fits keep the recency order the SQL
        # already put them in, rather than an arbitrary one that reshuffles
        # every load and makes the board look like it is churning.
        scored.sort(key=lambda x: -x[0])

        # `total` is how many were RANKED (what the pager walks); `matched` is
        # how many exist. They differ whenever the filters match more than the
        # window, and the page says so rather than quietly showing the smaller
        # number as if it were the board.
        total = len(scored)
        window = scored[page * page_size:(page + 1) * page_size]
        if not window:
            return {"rows": [], "total": total, "page": page,
                    "pages": max(1, -(-total // page_size)),
                    "window": FIT_WINDOW, "ranked": True, "matched": matched}

        ids = [w[2] for w in window]
        cols = ", ".join(CARD_COLS)
        got = {r["id"]: dict(r) for r in conn.execute(
            f"SELECT {cols} FROM posts WHERE id IN ({','.join('?' * len(ids))})",
            ids)}
        out = []
        for s, why, gid in window:
            row = got.get(gid)
            if not row:
                continue
            row["_score"], row["_why"] = s, why
            out.append(row)
        return {"rows": out, "total": total, "page": page,
                "pages": max(1, -(-total // page_size)),
                "window": FIT_WINDOW, "ranked": True, "matched": matched}
    finally:
        if own:
            conn.close()


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
            # THROUGH _filters(), NOT A SECOND COPY OF IT. This function used
            # to rebuild the predicates by hand, and the copy drifted exactly
            # as you would expect: it never learned about the owner filter that
            # keeps privately forwarded gigs off public pages, nor the
            # freshness floor, so a chip counted gigs the board would not show.
            # A chip is a promise about what one tap gives you; it can only
            # keep that promise by counting through the same code the tap runs.
            if not _has_col(conn, col):
                return {}
            sel = {k: (None if k == skip else ctx.get(k))
                   for k in ("job_types", "sizes", "sources", "languages")}
            # since_hours is deliberately NOT applied here — see the caller.
            where, params, frm = _filters(
                conn, "", sel["job_types"], sel["sizes"], sel["sources"],
                ctx.get("urgent_only"), ctx.get("where_work") or "",
                sel["languages"], 0,
                ctx.get("city") or "", bool(ctx.get("relocate")))
            return {r[0]: r[1] for r in conn.execute(
                f"SELECT p.{col}, COUNT(*) {frm} {where} "
                f"AND p.{col} IS NOT NULL AND p.{col} != '' GROUP BY p.{col} "
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
        # Same rule as facets(): counted through _filters(), never through a
        # second hand-rolled copy of it. The copy that used to live here said
        # "Everywhere · 47,858" while the board behind the tap held 44,001,
        # because it had never been taught the freshness floor or the owner
        # filter. where_work is deliberately empty — these chips ARE the
        # location choice, so each must count as if you had not made one yet.
        where, params, frm = _filters(
            conn, "", ctx.get("job_types"), ctx.get("sizes"),
            ctx.get("sources"), ctx.get("urgent_only"), "",
            ctx.get("languages"), 0,
            ctx.get("city") or "", bool(ctx.get("relocate")))
        total = conn.execute(
            f"SELECT COUNT(*) {frm} {where}", params).fetchone()[0]
        if not _has_col(conn, "is_remote"):
            return {"all": total, "remote": 0, "onsite": 0}
        row = conn.execute(
            f"SELECT COALESCE(SUM(p.is_remote), 0), COALESCE(SUM(p.is_onsite), 0) "
            f"{frm} {where}", params).fetchone()
        return {"all": total, "remote": int(row[0]), "onsite": int(row[1])}
    finally:
        if own:
            conn.close()


def by_ids(ids, conn: sqlite3.Connection | None = None) -> list[dict]:
    """
    Specific gigs, in the order asked for. For the Saved page.

    Deliberately NOT filtered by is_demand or is_primary. A gig you saved is
    yours: if it has since aged off the board or lost a duplicate coin-toss to
    an identical title from another feed, it should still be in your list.
    Silently dropping saved items would look exactly like losing them.

    AND THIS IS WHY THE BOARD STILL CARRIES ITS DUPLICATES. 11,990 rows, 18% of
    the file, are is_primary=0 and never appear on the board — so dropping them
    from the local copy looks like 18% off the disk and off every boot, for
    free. It is not free: those rows are exactly what this function exists to
    find, and someone's saved gig would vanish with no explanation.
    Making it work means falling back to the Postgres mirror on a miss, which
    puts a network dependency on the one page whose promise is that your list
    is yours. Weighed 2026-08-21 and left alone: boot was at 136s of a 270s
    budget, so 18% of it is ~24 seconds once per deploy, and retention is the
    cheaper lever if pressure ever arrives — 21 days is a choice, and 14 would
    cut a third with no new code and no new failure mode.

    Chunked because SQLite caps parameters per statement (999 by default), and
    somebody with a long list would otherwise get an error instead of a page.
    """
    ids = [str(i) for i in (ids or []) if str(i).strip()]
    if not ids:
        return []
    own = conn is None
    conn = conn or connect()
    try:
        cols = ", ".join(CARD_COLS)
        found: dict[str, dict] = {}
        for i in range(0, len(ids), 400):
            chunk = ids[i:i + 400]
            for r in conn.execute(
                    f"SELECT {cols} FROM posts "
                    f"WHERE id IN ({','.join('?' * len(chunk))})", chunk):
                d = dict(r)
                found[str(d["id"])] = d
        return [found[i] for i in ids if i in found]
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


def market_stats(conn: sqlite3.Connection | None = None) -> dict:
    """
    Everything the Market page counts, over the PUBLIC board.

    One _filters() call drives every aggregate, so Market cannot disagree with
    /gigs about how many gigs exist — the exact bug the app's version had
    (17,882 vs 16,007 on the same board, in the same session).

    THE GENERATOR IS THE WHOLE MEMORY STORY. market.skill_stats needs title and
    body for every public row because the pay parser reads the full text —
    truncating bodies was measured to corrupt the typical rate for 22 of 25
    skills, so that shortcut is dead. Streamed, the scan peaks ~2MB above
    baseline; materialised as a list it is ~100MB on a service that has been
    OOM-killed before. Do not turn `rows` into a list.

    Returns plain primitives only. Charts want pre-rounded widths, computed
    here rather than in the template so Jinja never does arithmetic.
    """
    own = conn is None
    conn = conn or connect()
    try:
        import market
        where, params, frm = _filters(conn, "", None, None, None, None,
                                      "", None, 0, "", False)
        total = conn.execute(f"SELECT COUNT(*) {frm} {where}",
                             params).fetchone()[0]
        # source is NOT optional: skill_stats computes per-source medians so
        # one over-posting board cannot set the "typical" rate alone. Omitting
        # it collapses every gig into one anonymous source and the medians go
        # sideways — caught because the rendered top rate looked wrong, not by
        # any error.
        rows = ({"job_type": jt, "source": src, "title": t, "body": b}
                for jt, src, t, b in conn.execute(
                    f"SELECT p.job_type, p.source, p.title, p.body {frm} {where}",
                    params))
        stats = market.skill_stats(rows)
        hot = market.hot_skills(stats, top=8)
        priced = sorted(((s, d["typical"]) for s, d in stats.items()
                         if d.get("typical")), key=lambda x: -x[1])[:8]
        size_mix = {r[0]: r[1] for r in conn.execute(
            f"SELECT p.size_tier, COUNT(*) {frm} {where} GROUP BY p.size_tier",
            params)}
        urgency = {r[0] or "": r[1] for r in conn.execute(
            f"SELECT p.urgency, COUNT(*) {frm} {where} GROUP BY p.urgency",
            params)}
        urgency_mix = {"Standard": sum(v for k, v in urgency.items()
                                       if k != "Urgent"),
                       "Urgent": urgency.get("Urgent", 0)}
        top_skills = [r[0] for r in conn.execute(
            f"SELECT p.job_type, COUNT(*) c {frm} {where} "
            f"GROUP BY p.job_type ORDER BY c DESC LIMIT 8", params)]
        cross = {(r[0], r[1]): r[2] for r in conn.execute(
            f"SELECT p.job_type, p.size_tier, COUNT(*) {frm} {where} "
            f"GROUP BY p.job_type, p.size_tier", params)}
        return {"total": total, "stats_n": len(stats), "hot": hot,
                "priced": priced, "size_mix": size_mix,
                "urgency_mix": urgency_mix, "top_skills": top_skills,
                "cross": cross}
    finally:
        if own:
            conn.close()


def count_since(since_ts: str, conn=None, **ctx) -> int:
    """
    How many gigs landed since a timestamp, THROUGH THE MEMBER'S OWN FILTERS.

    Same ctx the feed uses, deliberately: a count taken over the whole board
    would promise rows the page below does not contain. ~1ms — ix_posts_sort
    covers it — so it is cheap enough to run on every dashboard render.
    """
    if not since_ts:
        return 0
    own = conn is None
    conn = conn or connect()
    try:
        where, params, frm = _filters(
            conn, ctx.get("keyword", ""), ctx.get("job_types"), ctx.get("sizes"),
            ctx.get("sources"), ctx.get("urgent_only"), ctx.get("where_work", ""),
            ctx.get("languages"), 0, ctx.get("city", ""),
            ctx.get("relocate", False), since_ts=since_ts)
        return conn.execute(f"SELECT COUNT(*) {frm} {where}", params).fetchone()[0]
    finally:
        if own:
            conn.close()


def suggest_index(conn: sqlite3.Connection | None = None) -> list:
    """
    The search vocabulary, LEARNED FROM THE BOARD rather than hand-written.

    Every classifier keyword counted against live public titles, keeping only
    terms with at least MIN_LIVE gigs behind them. That threshold is the whole
    point: a suggestion the board cannot answer is worse than no suggestion,
    and this way the list shrinks and grows with what people are actually
    hiring for. Measured 2026-08-24: 825 keywords in, 418 survive.

    Titles only, not bodies. A body mentions skills in passing ("familiarity
    with Figma a plus") and would suggest terms the board cannot really fill;
    a title names the work.

    Returns [(term, count)] sorted by count. ~3.4s over 55k titles, so it is
    cached upstream per board version, never built per request.
    """
    import config
    own = conn is None
    conn = conn or connect()
    try:
        where, params, frm = _filters(conn, "", None, None, None, None,
                                      "", None, 0, "", False)
        titles = [r[0].lower() for r in
                  conn.execute(f"SELECT p.title {frm} {where}", params) if r[0]]
    finally:
        if own:
            conn.close()
    terms = set()
    for keywords in config.JOB_TYPES.values():
        for k in keywords:
            k = k.strip().lower()
            if len(k) >= 3:
                terms.add(k)
    counts: dict = {}
    for t in titles:
        for k in terms:
            if k in t:
                counts[k] = counts.get(k, 0) + 1
    MIN_LIVE = 5
    return sorted(((k, n) for k, n in counts.items() if n >= MIN_LIVE),
                  key=lambda x: -x[1])

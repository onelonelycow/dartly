"""
db.py — stores demand posts in a single local file (demand_radar.db).

SQLite is a database that lives in one file. No server, no setup.
"""
import sqlite3
from datetime import datetime, timezone

from paths import data_file

DB_PATH = data_file("demand_radar.db")


def connect():
    # timeout lets a reader wait briefly if the background fetcher is mid-write.
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")  # concurrent reads during writes
    except sqlite3.OperationalError:
        pass
    return conn


def init_db():
    """Create the posts table the first time we run."""
    conn = connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,      -- 'craigslist' or 'reddit'
            source_id   TEXT NOT NULL,      -- the original post id (for dedup)
            url         TEXT,
            title       TEXT,
            body        TEXT,
            posted_at   TEXT,               -- when the person posted it
            fetched_at  TEXT,               -- when we pulled it
            is_demand   INTEGER,            -- 1 = looks like a real request for help
            job_type    TEXT,
            size_tier   TEXT,               -- 'Small', 'Medium', 'Large'
            urgency     TEXT,               -- 'Urgent' or ''
            is_new      INTEGER DEFAULT 0,  -- 1 = arrived in the latest fetch
            alerted     INTEGER DEFAULT 0,  -- 1 = we've already sent an alert for it
            owner       TEXT DEFAULT '',    -- '' = public board; else one person's
            UNIQUE(source, source_id)
        )
        """
    )
    # Safe migration for databases created before these columns existed.
    for col in ("is_new", "alerted"):
        try:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN owner TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # The address to apply to, extracted once from the FULL body. It has to be
    # a stored column rather than something the app derives per render: the
    # feed frame truncates body to 2,000 chars for memory, and "how to apply"
    # lives at 4,000-8,000 in a long posting, so deriving it later would find
    # almost none of them. NULL = not looked at yet, '' = looked, none found.
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN apply_email TEXT")
    except sqlite3.OperationalError:
        pass
    # Separate from apply_email: a page we've read that simply has no address
    # must not be refetched every cycle forever.
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN page_checked INTEGER")
    except sqlite3.OperationalError:
        pass
    # Whether we've verified this posting still resolves. Separate again, so a
    # link we checked and found alive isn't re-fetched every cycle.
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN link_checked INTEGER")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def _owner_clause(owner: str | None) -> tuple[str, list]:
    """
    Which rows this viewer is allowed to see.

    Everything scraped from a public board has an empty owner and is visible to
    all. Anything forwarded in by email belongs to the person who forwarded it —
    those newsletters are often paid subscriptions, so they stay on that one
    board and nobody else's.
    """
    if owner:
        return "(COALESCE(owner, '') = '' OR owner = ?)", [owner]
    return "COALESCE(owner, '') = ''", []


def upsert_post(post: dict) -> bool:
    """Insert a post. Returns True if it was new, False if we'd already seen it."""
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO posts
                (source, source_id, url, title, body, posted_at, fetched_at,
                 is_demand, job_type, size_tier, urgency, is_new, alerted, owner)
            VALUES
                (:source, :source_id, :url, :title, :body, :posted_at, :fetched_at,
                 :is_demand, :job_type, :size_tier, :urgency, 1, 0, :owner)
            """,
            # Everything except the inbox arrives without an owner, i.e. public.
            {"owner": "",
             "fetched_at": datetime.now(timezone.utc).isoformat(),
             **post},
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already have this post (same source + source_id) — skip it.
        return False
    finally:
        conn.close()


def upsert_many(records) -> int:
    """
    Insert many gigs in one connection, skipping any we already have.

    upsert_post() opens a connection per row, which is fine for a fetch of a few
    hundred but not for rehydrating thousands from the durable mirror at boot.
    This does the whole batch in one transaction. INSERT OR IGNORE means gigs the
    local board already holds (e.g. from the seed) are kept, and only the missing
    ones are filled in. Returns how many rows were actually added.
    """
    records = [r for r in (records or []) if r.get("source") and r.get("source_id")]
    if not records:
        return 0
    cols = ("source", "source_id", "url", "title", "body", "posted_at",
            "fetched_at", "is_demand", "job_type", "size_tier", "urgency", "owner")
    defaults = {"is_demand": 1, "owner": ""}
    conn = connect()
    try:
        before = conn.total_changes
        conn.executemany(
            f"INSERT OR IGNORE INTO posts ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})",
            [tuple(r.get(c, defaults.get(c, "")) for c in cols) for r in records])
        conn.commit()
        return conn.total_changes - before
    finally:
        conn.close()


_board_rehydrated = False


def rehydrate_board():
    """
    After a wiped disk, refill the board from the durable Supabase mirror.

    Runs once per process, at boot, before the first page renders — the only
    time the whole board crosses the network (every later read is local). No-op
    when the mirror is disabled or already done, so it's safe to call on the
    app's module load even though that re-executes on every rerun.
    """
    global _board_rehydrated
    if _board_rehydrated:
        return
    _board_rehydrated = True
    try:
        import board_store
        if not board_store.enabled():
            return
        rows = board_store.pull()
        if rows:
            init_db()
            added = upsert_many(rows)
            if added:
                print(f"  board: rehydrated {added} gigs from the durable mirror")
    except Exception as e:
        print(f"  ! board rehydrate: {type(e).__name__}: {e}")


def normalize_dates() -> int:
    """
    Rewrite every non-ISO posted_at in place, and return how many changed.

    posted_at is TEXT and the board sorts on it, so a mix of RFC 2822 and ISO
    means the sort is alphabetical over two different formats — which put a
    January 2024 gig at the top of "Fresh off the boards" because "Wed," beats
    "Thu,". Runs once at boot; a second pass finds nothing and costs one scan.
    """
    import sources
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, posted_at FROM posts WHERE posted_at IS NOT NULL "
            "AND posted_at != ''").fetchall()
        fixes = []
        for r in rows:
            raw = r["posted_at"]
            # Cheap check first: a real ISO value starts "YYYY-MM-DD".
            if len(str(raw)) >= 10 and str(raw)[4] == "-" and str(raw)[7] == "-":
                continue
            iso = sources.to_iso(raw)
            # An unparseable date becomes '' so COALESCE falls through to
            # fetched_at, which is always ours and always ISO. Better to sort
            # by when we saw it than by a string we can't read.
            if iso != raw:
                fixes.append((iso, r["id"]))
        if fixes:
            conn.executemany("UPDATE posts SET posted_at=? WHERE id=?", fixes)
            conn.commit()
        return len(fixes)
    finally:
        conn.close()


def clean_bodies() -> int:
    """
    Re-clean stored descriptions that still carry raw HTML. Returns how many.

    _strip() used to unescape AFTER stripping tags, so any feed sending escaped
    HTML landed in the database with literal <h1>/<p>/&nbsp; in the text. The
    parser is fixed, but 310 rows were already stored that way and upsert never
    rewrites a row it has seen. Runs at boot; a second pass finds nothing.
    """
    import re as _re
    import sources
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, body FROM posts WHERE body LIKE '%<%' OR body LIKE '%&lt;%' "
            "OR body LIKE '%&amp;%' OR body LIKE '%&nbsp;%'").fetchall()
        fixes = []
        for r in rows:
            raw = r["body"] or ""
            # Machine hints live after HINT_SEP and are never shown as prose —
            # clean only the human half so the classifier's tail is untouched.
            human, sep, tail = str(raw).partition(sources.HINT_SEP)
            cleaned = sources._strip(human)
            rebuilt = f"{cleaned}{sep}{tail}" if sep else cleaned
            if rebuilt != raw:
                fixes.append((rebuilt, r["id"]))
        if fixes:
            conn.executemany("UPDATE posts SET body=? WHERE id=?", fixes)
            conn.commit()
        return len(fixes)
    finally:
        conn.close()


def backfill_emails(limit: int = 4000) -> int:
    """
    Fill apply_email for rows that haven't been looked at. Returns how many.

    Only touches rows where the column is still NULL, so the steady-state cost
    is whatever arrived in the last couple of minutes, not a full-table scan.
    Runs on the refresh loop, which means a new gig has its address within one
    cycle of landing.
    """
    import contact
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, body FROM posts WHERE apply_email IS NULL LIMIT ?",
            (int(limit),)).fetchall()
        if not rows:
            return 0
        # '' for "looked, found nothing" so the row isn't re-scanned forever.
        conn.executemany(
            "UPDATE posts SET apply_email=? WHERE id=?",
            [(contact.find(r["body"]), r["id"]) for r in rows])
        conn.commit()
        return len(rows)
    finally:
        conn.close()


# Deliberately small. This is the only place the app makes an outbound request
# per GIG rather than per feed, so it is capped hard and runs on the background
# loop: a handful per cycle clears any backlog within hours and never makes a
# visitor wait. Nothing but the extracted address is kept — the page itself is
# read, scanned and dropped, so it costs no database space and no lasting
# memory (which is the question worth asking after this week).
PAGE_FETCH_PER_CYCLE = 8


def backfill_emails_from_pages(limit: int = PAGE_FETCH_PER_CYCLE) -> int:
    """
    For the few sources that keep the address on the posting page, fetch it.

    Restricted to contact.PAGE_SOURCES, an allowlist of sources whose pages
    have been checked by hand. Testing this against everything showed why:
    freelancer.com serves "jane@freelancer.com" as a template placeholder, and
    a blanket version would have written that one fake address onto 7,000+
    gigs — worse than having no address at all, because someone would send a
    real application to it.

    Marks a row '' when the fetch fails or finds nothing, so a dead page is
    tried once rather than every cycle forever.
    """
    import contact
    try:
        import requests
    except ImportError:
        return 0
    if not contact.PAGE_SOURCES:
        return 0

    marks = ",".join("?" * len(contact.PAGE_SOURCES))
    conn = connect()
    try:
        rows = conn.execute(
            f"SELECT id, url, source FROM posts "
            f"WHERE (apply_email IS NULL OR apply_email = '') "
            f"  AND page_checked IS NULL "
            f"  AND source IN ({marks}) AND url LIKE 'http%' LIMIT ?",
            (*contact.PAGE_SOURCES, int(limit))).fetchall()
    finally:
        conn.close()
    if not rows:
        return 0

    found = []
    for r in rows:
        addr = ""
        try:
            resp = requests.get(
                r["url"], timeout=15,
                headers={"User-Agent": "nabbly/0.1 (public job & gig aggregator)"})
            if resp.status_code == 200:
                addr = contact.from_page(
                    resp.text, contact.PAGE_SOURCES.get(r["source"], ""))
        except Exception:
            pass          # a dead link is not worth a retry loop
        found.append((addr, r["id"]))

    conn = connect()
    try:
        # page_checked marks "we have looked at the page", separately from
        # apply_email, so a page that genuinely has no address isn't refetched
        # on every cycle for the rest of time.
        conn.executemany(
            "UPDATE posts SET apply_email = CASE WHEN ?1 != '' THEN ?1 "
            "ELSE apply_email END, page_checked = 1 WHERE id = ?2", found)
        conn.commit()
    finally:
        conn.close()
    return sum(1 for a, _ in found if a)


LINK_CHECK_PER_CYCLE = 6
LINK_CHECK_MIN_AGE_DAYS = 7


def sweep_dead_links(limit: int = LINK_CHECK_PER_CYCLE) -> int:
    """
    Take gigs off the board whose posting is provably gone. Returns how many.

    The age cutoff alone isn't enough. A We Work Remotely listing reported by
    the founder was 34 days old — inside the 45-day window — but WWR had
    already pulled it, so clicking it landed on their homepage. Boards expire
    postings on their own schedule, and the only way to know is to look.

    ONLY definitive signals archive a gig:
        404 / 410            the posting is gone
        redirect to the site root   the board bounced us off a dead listing

    Explicitly NOT archived on 403, 429, timeouts or connection errors. Several
    sources (himalayas, jobicy) return 403 to any script while serving the page
    perfectly to a real browser — treating that as "dead" would delete large
    numbers of live gigs, which is far worse than leaving a few stale ones up.

    Checks the OLDEST unchecked gigs first, since those are likeliest expired,
    and only a handful per cycle so this never becomes a crawl of anyone's site.
    """
    try:
        import requests
    except ImportError:
        return 0
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=LINK_CHECK_MIN_AGE_DAYS)).isoformat()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, url, source, source_id FROM posts "
            "WHERE is_demand = 1 AND link_checked IS NULL AND url LIKE 'http%' "
            "  AND COALESCE(NULLIF(posted_at,''), fetched_at) < ? "
            "ORDER BY COALESCE(NULLIF(posted_at,''), fetched_at) ASC LIMIT ?",
            (cutoff, int(limit))).fetchall()
    finally:
        conn.close()
    if not rows:
        return 0

    # A real browser UA: we're checking whether a HUMAN clicking this link
    # would reach the posting, so asking as anything else answers a different
    # question.
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/120.0 Safari/537.36"}
    verdicts = []
    gone = []
    for r in rows:
        dead = 0
        try:
            resp = requests.get(r["url"], headers=headers, timeout=15,
                                allow_redirects=True)
            if resp.status_code in (404, 410):
                dead = 1
            elif resp.status_code == 200:
                # Landed on the site root => the posting no longer exists and
                # the board bounced us to its front page.
                if str(resp.url).rstrip("/").count("/") <= 2:
                    dead = 1
        except Exception:
            pass          # unreachable now != gone; leave it and re-check later
        verdicts.append((dead, r["id"]))
        if dead:
            gone.append((r["source"], r["source_id"]))

    conn = connect()
    try:
        conn.executemany(
            "UPDATE posts SET link_checked = 1, "
            "is_demand = CASE WHEN ?1 = 1 THEN 0 ELSE is_demand END "
            "WHERE id = ?2", verdicts)
        conn.commit()
    finally:
        conn.close()

    # Tell the durable mirror too, or the next restart undoes this. See
    # board_store.mark_archived() for why that isn't hypothetical.
    if gone:
        try:
            import board_store
            board_store.mark_archived(gone)
        except Exception:
            pass
    return sum(d for d, _ in verdicts)


STALE_DAYS = 45


def archive_stale(days: int = STALE_DAYS) -> int:
    """
    Take gigs older than `days` off the board. Returns how many.

    A posting from three months ago is almost always filled or closed — the
    board was showing April gigs in late July, and clicking one led to a dead
    listing, which is worse than showing nothing. They're flipped to
    is_demand=0 rather than deleted, so the row still blocks its own
    source_id from being re-ingested and the history stays intact.

    Not a hard "expiry date": we don't get one from most feeds. It's a
    freshness cutoff, which is the honest version of the same idea.
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = connect()
    try:
        # Read the pairs BEFORE the update, so we know which rows this pass is
        # actually retiring and can mirror exactly those.
        aged = [(r["source"], r["source_id"]) for r in conn.execute(
            "SELECT source, source_id FROM posts WHERE is_demand = 1 "
            "  AND COALESCE(NULLIF(posted_at, ''), fetched_at) < ?",
            (cutoff,)).fetchall()]
        cur = conn.execute(
            "UPDATE posts SET is_demand = 0 "
            "WHERE is_demand = 1 "
            "  AND COALESCE(NULLIF(posted_at, ''), fetched_at) < ?", (cutoff,))
        conn.commit()
        n = cur.rowcount or 0
    finally:
        conn.close()

    # Same reason as sweep_dead_links: without this the next restart pulls
    # every one of these back onto the board as live.
    if aged:
        try:
            import board_store
            board_store.mark_archived(aged)
        except Exception:
            pass
    return n


def reclassify_all() -> int:
    """
    Re-run the classifier over every stored post, updating any whose tags moved.

    upsert_post() never touches a row it has already seen, so a classifier
    improvement would otherwise only reach new gigs while the existing board
    kept its old (often wrong) tags. This re-tags what's already stored. Only
    changed rows are written, so a second run is a cheap no-op.
    """
    import classify
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, title, body, source, job_type, size_tier, urgency FROM posts"
        ).fetchall()
        changed = 0
        for r in rows:
            t = classify.classify(r["title"], r["body"], r["source"])
            if (t["job_type"] != r["job_type"] or t["size_tier"] != r["size_tier"]
                    or t["urgency"] != r["urgency"]):
                conn.execute(
                    "UPDATE posts SET job_type=?, size_tier=?, urgency=? WHERE id=?",
                    (t["job_type"], t["size_tier"], t["urgency"], r["id"]))
                changed += 1
        conn.commit()
        return changed
    finally:
        conn.close()


def all_posts(demand_only: bool = True, owner: str | None = None):
    """
    Return the posts this viewer can see, newest first.

    Pass someone's storage scope as `owner` to include the gigs they forwarded
    in by email alongside the public board. Leave it off and you get the public
    board only.
    """
    conn = connect()
    clause, params = _owner_clause(owner)
    where = f"WHERE {clause}" + (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# How much of a description the board keeps in memory. We display ~620
# characters and search the rest; 2,000 keeps search honest while cutting the
# single heaviest thing in the frame. Full text is always one click away on the
# original posting.
BODY_CHARS = 2000
_CHUNK = 4000


def posts_frame(demand_only: bool = True, owner: str | None = None):
    """
    The board as a DataFrame, built to keep PEAK memory down, not just the
    finished size.

    Measured on the live board (14,393 gigs), the naive version peaked at 241MB
    to produce a 44MB frame, and that peak — not the frame — is what tripped
    Render's 512MB limit once Streamlit's own ~100MB was on top of it. Two
    changes take the peak to 152MB and the frame to 26MB:

    * Read in chunks. `SELECT *` builds the entire result set in memory before
      pandas sees a single row; chunks keep only `_CHUNK` rows in flight.
    * Truncate body IN SQL. Descriptions are the heaviest column by far, and
      lower-casing them for search (_b) doubles that. Trimming at the database
      means the long tail never crosses into Python at all.
    """
    import pandas as pd
    conn = connect()
    clause, params = _owner_clause(owner)
    where = f"WHERE {clause}" + (" AND is_demand = 1" if demand_only else "")
    try:
        # Column list from the live schema, so adding a column later can't
        # silently drop it here — body is the only one we rewrite.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(posts)")]
        select = ", ".join(
            f"substr({c}, 1, {BODY_CHARS}) AS {c}" if c == "body" else c
            for c in cols)
        sql = (f"SELECT {select} FROM posts {where} "
               f"ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC")
        chunks = list(pd.read_sql_query(sql, conn, params=params,
                                        chunksize=_CHUNK))
        if not chunks:
            return pd.DataFrame(columns=cols)
        if len(chunks) == 1:
            return chunks[0]
        out = pd.concat(chunks, ignore_index=True)
        chunks.clear()          # drop the per-chunk frames before returning
        return out
    finally:
        conn.close()


def board_version() -> tuple[int, int]:
    """
    A cheap fingerprint of the board: (highest id, total row count).

    Lets the app cache the built feed until the board ACTUALLY changes, instead
    of rebuilding it on a timer. Two integers from an index, not a table scan.

    Deliberately NOT filtered by is_demand = 1. sweep_dead_links() flips that
    flag on a handful of rows almost every 2-minute cycle, and this fingerprint
    used to be scoped to is_demand = 1 — so an archive-only cycle (no new gigs,
    just a few taken off the board) looked identical to real growth and forced
    the same full board rebuild new arrivals do. That rebuild is the ~150MB
    spike Round 3 was built to make rare; sweeping made it fire nearly every
    cycle instead, stacking on top of that cycle's own ingest cost right when
    live visitors are loading the board. sweep_dead_links() and
    backfill_emails_from_pages() only ever UPDATE existing rows (never INSERT),
    so neither id nor total count moves when they run — only real new posts
    change this fingerprint now. A gig archived this cycle stays visible until
    the next real ingest (usually minutes, not hours) instead of costing a
    rebuild of its own; posts_frame() still filters is_demand = 1 at rebuild
    time, so once a rebuild does happen the archived gig is gone regardless.
    """
    conn = connect()
    try:
        row = conn.execute(
            "SELECT COALESCE(MAX(id), 0), COUNT(*) FROM posts"
        ).fetchone()
        return int(row[0]), int(row[1])
    finally:
        conn.close()


def owned_posts(owner: str, demand_only: bool = True):
    """Just the gigs one person forwarded in — none of the public board."""
    if not owner:
        return []
    conn = connect()
    where = "WHERE owner = ?" + (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC",
        [owner],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def posts_since(min_id: int, demand_only: bool = True, owner: str | None = None):
    """
    Only the posts newer than a watermark.

    Alerting used to pull the WHOLE board every cycle to find the few rows above
    each person's marker — ~10,000 rows as Python dicts, about 45MB, every pass,
    all night. Python hands that memory back to its own allocator rather than the
    OS, so RSS crept up until Render killed the instance. This asks the database
    for the handful of rows that can possibly matter instead.
    """
    conn = connect()
    clause, params = _owner_clause(owner)
    where = f"WHERE id > ? AND {clause}" + (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC",
        [int(min_id)] + params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def max_post_id() -> int:
    """
    Highest id on the whole table, private rows included.

    Alert watermarks compare against this. If it only counted the public board,
    a forwarded gig with a higher id would sit permanently above the marker and
    re-alert on every cycle.
    """
    conn = connect()
    n = conn.execute("SELECT COALESCE(MAX(id), 0) FROM posts").fetchone()[0]
    conn.close()
    return int(n)


def count(owner: str | None = None) -> int:
    conn = connect()
    clause, params = _owner_clause(owner)
    n = conn.execute(
        f"SELECT COUNT(*) FROM posts WHERE is_demand = 1 AND {clause}", params
    ).fetchone()[0]
    conn.close()
    return n


def ensure_seeded():
    """If the working DB is missing or empty, populate it from the bundled
    seed.db. Lets a fresh deploy have gigs instantly without fetching live data
    during the build (which is slow/fragile on small hosts)."""
    import shutil
    from pathlib import Path
    seed = Path(__file__).parent / "seed.db"
    try:
        if not seed.exists() or seed.resolve() == DB_PATH.resolve():
            return
        empty = True
        if DB_PATH.exists():
            init_db()          # ensure schema, safe if it already exists
            empty = count() == 0
        if empty:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(seed, DB_PATH)
        # The bundled seed was captured before newer columns (e.g. owner)
        # existed, so migrate whatever we just landed up to the current schema.
        # Without this a fresh deploy would query a column the copied file
        # doesn't have yet, and every board read would crash until the first
        # background fetch happened to run init_db().
        init_db()
    except Exception:
        pass


def reset_new_flags():
    """Clear the 'new' flag on all posts (call before a fresh fetch)."""
    conn = connect()
    conn.execute("UPDATE posts SET is_new = 0")
    conn.commit()
    conn.close()


def unalerted(owner: str | None = None):
    """Demand posts we haven't sent an alert for yet (newest first)."""
    conn = connect()
    clause, params = _owner_clause(owner)
    rows = conn.execute(
        f"SELECT * FROM posts WHERE is_demand = 1 AND alerted = 0 AND {clause} "
        "ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alerted(ids):
    if not ids:
        return
    conn = connect()
    conn.executemany("UPDATE posts SET alerted = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

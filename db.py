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
    # Read the column list off the mirror instead of repeating it. These two
    # lists have to agree exactly — the mirror decides what gets saved, this
    # decides what comes back — and when they were two hand-kept copies they
    # drifted: the mirror later gained columns this side still dropped on the
    # floor. Lazy import for the same reason rehydrate_board() uses one.
    import board_store
    cols, defaults = board_store.COLS, board_store.DEFAULTS
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


def rehydrate_board() -> bool:
    """
    After a wiped disk, refill the board from the durable Supabase mirror.
    Returns True once the board is genuinely populated (or the mirror is off).

    THE FLAG IS SET ON SUCCESS, NOT ON ENTRY. It used to be set on the first
    line, before the network call, so a single failed pull — a blip, a cold
    Supabase, the 8s connect timeout under load — permanently gave up for the
    life of that process. Render's disk is wiped on every deploy, so the board
    at that moment is the bundled seed: 1,569 posts from 19-24 June. Visitors
    got a board of June listings that never filled in, with the 2-minute
    fetcher trickling new gigs on top, and nothing anywhere said why.

    Now a failure leaves the flag down and the caller retries. The work is
    idempotent (upsert_many is INSERT OR IGNORE), so a retry costs a pull and
    changes nothing if it turns out the board was already fine.
    """
    global _board_rehydrated
    if _board_rehydrated:
        return True
    try:
        import board_store
        if not board_store.enabled():
            _board_rehydrated = True      # nothing to wait for; this is terminal
            return True
        # PAGED, NOT CAPPED — the same fix the board service already got, which
        # never reached this path. board_store.pull() returns the newest CAP
        # (40,000) rows and stops, so every boot silently rebuilt the app's
        # board from a truncated copy of the mirror. Measured 2026-08-16: the
        # app showed 30,670 gigs where the board service showed 50,295, from
        # the same mirror, at the same moment. Roughly 20,000 gigs the app had
        # ingested were simply not there.
        #
        # It is worse than a display gap. An archived row exists to block its
        # own source_id from being re-ingested, so a gig dropped past the cap
        # can come back later as a brand new posting.
        #
        # Deliberately NOT demand_only: archived rows are exactly the ones
        # doing that blocking, and they carry no body, so they are cheap.
        # Each page is written and dropped, which also keeps peak memory flat
        # instead of holding one 60,000-row list with every body attached.
        init_db()
        want = board_store.count()
        added = pulled = 0
        for page in board_store.iter_all():
            pulled += len(page)
            added += upsert_many(page)
        if not pulled:
            # Reachable but empty is not success. Either the mirror is genuinely
            # bare (a brand new deployment) or the read failed quietly, and
            # retrying is right in both cases.
            print("  ! board rehydrate: mirror returned no rows, will retry",
                  flush=True)
            return False
        # iter_all() swallows a mid-page failure and just stops, which arrives
        # here looking identical to a clean finish. Without this check a
        # half-restored board would be marked done and never retried — the
        # truncation bug above, reintroduced by the fix for it.
        if want > 0 and pulled < want:
            print(f"  ! board rehydrate: mirror holds {want:,} rows but only "
                  f"{pulled:,} came back, will retry", flush=True)
            return False
        _board_rehydrated = True
        print(f"  board: rehydrated {added:,} gigs from the durable mirror "
              f"({pulled:,} pulled)", flush=True)
        return True
    except Exception as e:
        print(f"  ! board rehydrate failed, will retry: "
              f"{type(e).__name__}: {e}", flush=True)
        return False


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
            f"SELECT id, url, source, source_id FROM posts "
            f"WHERE (apply_email IS NULL OR apply_email = '') "
            f"  AND page_checked IS NULL "
            f"  AND source IN ({marks}) AND url LIKE 'http%' LIMIT ?",
            (*contact.PAGE_SOURCES, int(limit))).fetchall()
    finally:
        conn.close()
    if not rows:
        return 0

    found, keys = [], []
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
        keys.append((addr or None, 1, None, r["source"], r["source_id"]))

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
    # AND TELL THE MIRROR. Without this the work above lives only on Render's
    # disk, which is wiped on every deploy — so the sweep re-fetched the same
    # pages forever and the board never accumulated a single address. See
    # board_store.push_sweep for the numbers.
    try:
        import board_store
        board_store.push_sweep(keys)
    except Exception:
        pass          # mirroring must never break the sweep
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
            "is_demand = CASE WHEN ?1 = 1 THEN 0 ELSE is_demand END, "
            # Same as archive_stale: a dead link is off the board for good, so
            # its body is dead weight. Guarded on the verdict so a live gig
            # that merely got checked keeps everything.
            "body = CASE WHEN ?1 = 1 THEN '' ELSE body END "
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


# How long a gig stays on the board. This, not any row cap, is what decides how
# big the board gets: intake times retention. At ~1,200 new gigs a day, 45 days
# meant the board was converging on ~54,000 rows, and it was already at 33,000
# and climbing. 21 days settles it around ~25,000.
#
# THAT ~25,000 IS NO LONGER WHAT HAPPENS, because intake is not 1,200 any more.
# Measured 2026-08-22 over seven full days: ~2,919 new gigs a day, so 21 days
# converges on ~61,000 and the board was holding 65,347. Nobody was wrong;
# sources were added since the note above. The board IS at steady state, so it
# is not climbing, but at roughly 2.5x what this paragraph predicts.
#
# WHAT BREAKS FIRST IF IT GROWS AGAIN IS BOOT, not memory and not page speed.
# Page queries are 21ms and flat (indexed, 25 rows a page). Memory sits near
# 250MB of 536MB and barely tracks row count. Boot was ~136s of a 270s budget,
# and its row-dependent part is hauling the ~237MB file from the mirror; the
# local write of 65,000 rows is 0.7s and irrelevant.
#
# SO THE LEVER IS THIS CONSTANT, and 14 days would cut about a third with no new
# code. Do NOT reach for a row cap instead: a cap makes what is on the board
# depend on arrival order rather than freshness, so it would start dropping good
# recent gigs because older ones got there first.
#
# AND WATCH INTAKE, NOT BOARD SIZE. Every source added raises the steady state
# permanently. That is the trigger to retune this number.
#
# 21 rather than 45 because freelance work moves faster than salaried hiring. A
# six-week-old gig is nearly always filled, and a dead listing is worse than no
# listing (see archive_stale). The board is a marketing number; the part a
# member actually feels is whether the links they click are still alive.
STALE_DAYS = 21


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
        # body is dropped, not kept. An archived row exists to block its own
        # source_id from being re-ingested and to keep the history; it is never
        # displayed, because every board read filters is_demand = 1. Its body
        # averages 1,640 bytes and is 93% of what a row weighs, so keeping it
        # meant the archive tail grew forever and had to be hauled back over
        # the network at every boot for nothing.
        cur = conn.execute(
            "UPDATE posts SET is_demand = 0, body = '' "
            "WHERE is_demand = 1 "
            "  AND COALESCE(NULLIF(posted_at, ''), fetched_at) < ?", (cutoff,))
        conn.commit()
        n = cur.rowcount or 0
    finally:
        conn.close()

    # Same reason as sweep_dead_links: without this the next restart pulls
    # every one of these back onto the board as live.
    #
    # THE RETURN VALUE IS CHECKED NOW. It was discarded inside a bare `except
    # Exception: pass`, so a mirror write that never happened looked exactly
    # like one that did. The local rows were already committed as archived, so
    # nothing would ever retry them, and the board service — reading archival
    # from the mirror — kept serving gigs this function had retired. Measured
    # 2026-08-16: 3,849 of them, while the marketing site pointed its front
    # door at that service.
    if aged:
        try:
            import board_store
            pushed = board_store.mark_archived(aged)
            if pushed < len(aged):
                print(f"  ! archive_stale: retired {len(aged):,} gigs locally "
                      f"but only {pushed:,} reached the mirror. The board "
                      f"service will keep showing the difference until a later "
                      f"pass succeeds.", flush=True)
        except Exception as e:
            print(f"  ! archive_stale: mirror archival raised, {len(aged):,} "
                  f"gigs are retired locally only: "
                  f"{type(e).__name__}: {e}", flush=True)
    return n


def archive_not_openings() -> int:
    """
    Take postings that are not openings off the board. Returns how many.

    Talent pools, spontaneous applications, "future opportunities" and outright
    test rows. A member who opens "Expression of Interest - Account Executive"
    finds a body that says it is not a live vacancy, so the board told them
    something untrue. config.NOT_AN_OPENING carries the phrase list, the
    measured traps and the reasoning; classify.py stops new ones at the door.
    This is the one-off for what is already here.

    Modelled on archive_stale above, including the two things that function
    learned the hard way: read the pairs BEFORE the update, and check what the
    mirror actually accepted. Skipping the mirror is not a small bug here —
    archival written only to local sqlite is wiped on the next deploy and every
    row returns to the board as live.

    THE BODY DOES NOT SURVIVE, despite this function leaving it alone.
    compact_archived() runs on every boot and drops the body of every
    is_demand = 0 row, so a row archived here keeps its title, source and url
    and loses its text at the next restart. An earlier version of this
    docstring promised a one-UPDATE undo; that undo does not exist, and review
    caught the comment making a claim the codebase breaks two functions down.
    Undo means re-fetching from the source. Fine for what these rows are.
    """
    import classify
    conn = connect()
    try:
        hits = [(r["source"], r["source_id"], r["id"])
                for r in conn.execute(
                    "SELECT id, source, source_id, title FROM posts "
                    "WHERE is_demand = 1").fetchall()
                if classify._is_not_an_opening((r["title"] or "").lower())]
        if not hits:
            return 0
        ids = [h[2] for h in hits]
        # Chunked because SQLite caps host parameters per statement at 999.
        n = 0
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            cur = conn.execute(
                f"UPDATE posts SET is_demand = 0 WHERE id IN "
                f"({','.join('?' * len(chunk))})", chunk)
            n += cur.rowcount or 0
        conn.commit()
    finally:
        conn.close()

    pairs = [(h[0], h[1]) for h in hits]
    try:
        import board_store
        pushed = board_store.mark_archived(pairs)
        if pushed < len(pairs):
            print(f"  ! archive_not_openings: retired {len(pairs):,} locally "
                  f"but only {pushed:,} reached the mirror. The board service "
                  f"will keep showing the difference until a later pass "
                  f"succeeds.", flush=True)
    except Exception as e:
        print(f"  ! archive_not_openings: mirror archival raised, "
              f"{len(pairs):,} are retired locally only: "
              f"{type(e).__name__}: {e}", flush=True)
    return n


def fix_text_encoding() -> int:
    """
    Repair stored titles and bodies carrying mojibake or unresolved entities.
    Returns how many rows changed.

    "Forces armÃ©es canadiennes" and "Alexander &amp; Bebout" were live on
    member-facing cards: five fetchers assembled titles straight from API
    fields and skipped the cleaning that existed. ingest.py now runs
    sources.clean_stored() as a choke point for new arrivals; this repairs
    what those paths already stored, with the SAME function, so the two
    cannot disagree about what clean means.

    A SQL marker prefilter keeps the scan cheap, and clean_stored is a no-op
    on legitimate accents — "INOVAÇÃO" and "română" are real Portuguese and
    Romanian, and the mojibake regex only fires on byte-pair shapes real text
    does not produce. Verified by reading the rows that move.

    Corrected rows are re-pushed through board_store.push(), an upsert on
    (source, source_id) — without that the mirror keeps the broken copy and
    every deploy resurrects it, the exact failure mark_archived exists for.
    """
    import sources
    conn = connect()
    try:
        cand = conn.execute(
            "SELECT id FROM posts WHERE "
            "title LIKE '%Ã%' OR title LIKE '%â%' OR title LIKE '%Â%' "
            "OR title LIKE '%&%;%' "
            "OR body LIKE '%Ã%' OR body LIKE '%â%' OR body LIKE '%&amp;%'"
        ).fetchall()
        changed_ids = []
        for (pid,) in cand:
            r = conn.execute("SELECT title, body FROM posts WHERE id=?",
                             (pid,)).fetchone()
            nt = sources.clean_stored(r["title"] or "")
            nb = sources.clean_stored(r["body"] or "")
            if nt != (r["title"] or "") or nb != (r["body"] or ""):
                conn.execute("UPDATE posts SET title=?, body=? WHERE id=?",
                             (nt, nb, pid))
                changed_ids.append(pid)
        conn.commit()
        if not changed_ids:
            return 0
        # Full records for the mirror upsert, in chunks under the param cap.
        fixed = []
        for i in range(0, len(changed_ids), 900):
            chunk = changed_ids[i:i + 900]
            rows = conn.execute(
                f"SELECT * FROM posts WHERE id IN "
                f"({','.join('?' * len(chunk))})", chunk).fetchall()
            fixed.extend(dict(r) for r in rows)
    finally:
        conn.close()
    try:
        import board_store
        pushed = board_store.push(fixed)
        if pushed < len(fixed):
            print(f"  ! fix_text_encoding: repaired {len(fixed):,} locally but "
                  f"only {pushed:,} reached the mirror; the rest revert at the "
                  f"next deploy until a later pass succeeds.", flush=True)
    except Exception as e:
        print(f"  ! fix_text_encoding: mirror push raised, {len(fixed):,} "
              f"repairs are local only: {type(e).__name__}: {e}", flush=True)
    return len(fixed)


def compact_archived() -> int:
    """
    Drop the body from gigs that were archived before we started doing it.

    archive_stale() and sweep_dead_links() only ever touch rows that are still
    live, so everything retired before this change kept its text. Without a
    pass like this the old tail is never reclaimed — it just sits there being
    pulled over the network at every boot.

    Effectively a one-time job that reports 0 forever after, so it's safe to
    leave on the daily cycle rather than making it a migration someone has to
    remember to run.
    """
    conn = connect()
    try:
        cur = conn.execute(
            "UPDATE posts SET body = '' WHERE is_demand = 0 AND body != ''")
        conn.commit()
        n = cur.rowcount or 0
    finally:
        conn.close()
    if n:
        try:
            import board_store
            board_store.compact_archived()
        except Exception:
            pass
    return n


def archive_source(source: str) -> int:
    """
    Take every live gig from one source off the board. Returns how many.

    For dropping a source entirely (e.g. one that turned out to require a
    paid subscription to apply) — same is_demand=0-not-delete pattern as
    archive_stale, and same board_store mirror, for the same reason: skip
    the mirror and the next Render restart resurrects them straight back
    onto the live board.
    """
    conn = connect()
    try:
        aged = [(r["source"], r["source_id"]) for r in conn.execute(
            "SELECT source, source_id FROM posts WHERE is_demand = 1 AND source = ?",
            (source,)).fetchall()]
        cur = conn.execute(
            "UPDATE posts SET is_demand = 0, body = '' "   # see archive_stale
            "WHERE is_demand = 1 AND source = ?",
            (source,))
        conn.commit()
        n = cur.rowcount or 0
    finally:
        conn.close()

    if aged:
        try:
            import board_store
            board_store.mark_archived(aged)
        except Exception:
            pass
    return n


def backfill_freelancer_descriptions() -> int:
    """
    Refill already-stored Freelancer rows with the real description.

    fetch_freelancer() used to read preview_description, Freelancer's own
    truncated summary — sometimes cut off mid-sentence ("...confirming the
    integrity of three footings at"), which made "Show more" reveal nothing
    for a short posting because there was nothing fuller stored to reveal.
    The fetcher now reads the full description; this one-off UPDATEs the
    rows that were already saved with the old short text before the fix
    shipped. Only touches rows still live and still on Freelancer's own
    active-projects feed — it can't backfill a project that's since closed.
    """
    import sources
    fresh = {r["source_id"]: r["body"] for r in sources.fetch_freelancer()}
    if not fresh:
        return 0
    conn = connect()
    try:
        n = 0
        for source_id, body in fresh.items():
            cur = conn.execute(
                "UPDATE posts SET body=? WHERE source='freelancer' "
                "AND source_id=? AND is_demand=1 AND body != ?",
                (body, source_id, body))
            n += cur.rowcount or 0
        conn.commit()
    finally:
        conn.close()
    return n


def _classifier_fingerprint() -> str:
    """
    A short hash of everything that decides how a gig gets tagged.

    Covers classify.py's own source and the keyword vocabulary in config, so
    editing either one changes the fingerprint and earns a full re-tag. Editing
    neither does not.
    """
    import hashlib
    from pathlib import Path
    h = hashlib.sha256()
    try:
        h.update(Path(__file__).with_name("classify.py").read_bytes())
    except OSError:
        pass
    try:
        import config
        h.update(repr(sorted(config.JOB_TYPES.items())).encode())
    except Exception:
        pass
    return h.hexdigest()[:16]


def _last_reclassify() -> str:
    """The fingerprint of the classifier that last re-tagged the whole board."""
    try:
        import store
        if store.enabled():
            return (store.get("_classifier", "reclassified_at") or {}).get("fp", "")
    except Exception:
        pass
    try:
        return data_file("classifier.stamp").read_text().strip()
    except OSError:
        return ""


def _mark_reclassified(fp: str):
    """Durable, because Render wipes the disk and this must survive a deploy."""
    try:
        import store
        if store.enabled() and store.put("_classifier", "reclassified_at", {"fp": fp}):
            return
    except Exception:
        pass
    try:
        data_file("classifier.stamp").write_text(fp)
    except OSError:
        pass


def reclassify_all(force: bool = False) -> int:
    """
    Re-run the classifier over every stored post, updating any whose tags moved.

    SKIPPED UNLESS THE CLASSIFIER CHANGED. This is the single most expensive
    thing at boot: 82 seconds over a 25,600-gig board, and Render restarts on
    every deploy with a board nearer 40,000. It is CPU-bound Python, so the GIL
    hands the whole process to it and page renders queue behind it. Measured
    live: a board that rendered in 5s while idle took 32s during this.
    The docstring used to say a second run was "a cheap no-op". That was true
    of the writes and false of the work — it re-classified every row to
    discover it had nothing to write. Now a fingerprint of classify.py plus the
    keyword vocabulary decides: unchanged means skip in microseconds, changed
    means run once and stamp it. The stamp lives in the durable store because
    the local disk does not survive the deploy that would have changed it.

    upsert_post() never touches a row it has already seen, so a classifier
    improvement would otherwise only reach new gigs while the existing board
    kept its old (often wrong) tags. This re-tags what's already stored. Only
    changed rows are written, so a second run is a cheap no-op.

    STREAMED IN CHUNKS, not fetchall()'d. The naive version materialised every
    row — full, untruncated body text included — before the loop started:
    measured at 57MB peak on a 19,831-gig board, and it grows linearly as the
    board does. That lands on the WORST possible path: this runs at every
    process boot, right after board_store.pull() does its own full-board read,
    before the app has served a single request, under Render's 512MB ceiling.
    It's the same mistake posts_frame was already rewritten to fix — see its
    docstring for the profiling that prompted that one.

    Bodies are NOT truncated here the way posts_frame truncates them. The
    classifier reads the description to tag a gig, so trimming it would change
    what the board says a gig IS, not just how much text is held in memory.
    Streaming gets the memory back without touching the result.
    """
    fp = _classifier_fingerprint()
    if not force and fp == _last_reclassify():
        return 0
    import classify
    conn = connect()
    try:
        cur = conn.execute(
            "SELECT id, title, body, source, job_type, size_tier, urgency FROM posts")
        # Only the rows that actually changed are held, and each is four short
        # strings rather than a full description. A repeat run finds nothing and
        # so holds nothing — the idempotence this function already promised.
        pending = []
        while True:
            rows = cur.fetchmany(2000)
            if not rows:
                break
            for r in rows:
                t = classify.classify(r["title"], r["body"], r["source"])
                if (t["job_type"] != r["job_type"] or t["size_tier"] != r["size_tier"]
                        or t["urgency"] != r["urgency"]):
                    pending.append((t["job_type"], t["size_tier"], t["urgency"],
                                    r["id"]))
        # Applied after the read cursor is exhausted, never during it: SQLite
        # gives no guarantees about a SELECT still being stepped through while
        # the same table is being written.
        if pending:
            conn.executemany(
                "UPDATE posts SET job_type=?, size_tier=?, urgency=? WHERE id=?",
                pending)
        conn.commit()
        # Stamped only after the pass completed. A crash or a killed process
        # part-way leaves the stamp untouched, so the next boot does the work
        # again rather than recording a re-tag that never finished.
        _mark_reclassified(fp)
        return len(pending)
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
        #
        # Every TEXT column is COALESCEd to '' because a SQL NULL arrives in
        # pandas as NaN, and NaN is a FLOAT that is also TRUTHY. That combination
        # defeats the `(x or "").strip()` guard used all over the app: the `or`
        # sees something truthy, passes the float straight through, and .strip()
        # raises "'float' object has no attribute 'strip'". apply_email is NULL
        # on most gigs, so this crashed the whole board with a traceback the
        # moment one of those rows reached a card.
        #
        # Done in SQL rather than a pandas fillna() on purpose: fillna copies
        # the frame, and this function exists to hold peak memory down. SQLite
        # substitutes the empty string for free, before a single row crosses
        # into Python.
        rows = list(conn.execute("PRAGMA table_info(posts)"))
        cols = [r["name"] for r in rows]
        _texty = {r["name"] for r in rows if (r["type"] or "").upper() == "TEXT"}
        select = ", ".join(
            f"substr(COALESCE(body, ''), 1, {BODY_CHARS}) AS body" if c == "body"
            else (f"COALESCE({c}, '') AS {c}" if c in _texty else c)
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


def posts_recent(days: int, demand_only: bool = True):
    """
    Only the posts from the last `days` days — the SQL-side filter, not a
    full-table load. Same reasoning as posts_since: the weekly digest runs
    once per account, and pulling the whole ~17,000-row board into Python on
    every one of those passes is exactly the pattern that caused the OOM
    restarts earlier (~45MB per pass, never handed back to the OS). This asks
    the database for one week's rows once, and every account's digest is
    filtered from that single set in Python.
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = connect()
    where = "WHERE COALESCE(NULLIF(posted_at, ''), fetched_at) >= ?" + \
            (" AND is_demand = 1" if demand_only else "")
    rows = conn.execute(
        f"SELECT * FROM posts {where} "
        f"ORDER BY COALESCE(NULLIF(posted_at, ''), fetched_at) DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def post_by_id(gig_id) -> dict | None:
    """One post, for the outbound-click redirect route (app.py's ?nav=out) —
    it only knows a gig id from the URL, not the row itself."""
    conn = connect()
    row = conn.execute("SELECT * FROM posts WHERE id=?", (gig_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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

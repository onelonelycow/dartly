"""
board_store.py — the gig board's durable backup in Supabase.

Same idea as store.py, but for the board (the posts table) rather than per-user
KV. Render's free tier wipes the disk on every deploy and every ~15-minute idle
spin-down, so the board rebuilds from the 1,558-row seed each time and slowly
climbs back. This mirrors gigs to Supabase as they're ingested and pulls them
back on boot, so the board accumulates and *sticks* instead of resetting.

THE ONE RULE THAT KEEPS IT FAST: reads never come from here. The app reads the
local SQLite board on every page load; this is written on ingest (in the
background fetch loop) and read exactly once, at boot. It is a backup, never the
hot path.

DEGRADES CLEANLY: with no DATABASE_URL set, enabled() is False and every call is
a no-op — identical to how the app ran before Supabase. Every operation is
wrapped so a slow or unreachable database can never block or crash a fetch; the
worst case is a batch of gigs isn't mirrored and is re-mirrored next cycle.

It reuses store.py's connection + DSN handling, so the SQLite-or-Postgres
placeholder juggling lives in one place. Point DATABASE_URL at a sqlite file and
this runs identically to how it runs against Supabase, which is how it's tested.
"""
import os
import store

_TABLE = "nabbly_posts"
# Rehydrate the newest N. This has to stay comfortably ahead of the real board
# or the mirror quietly becomes lossy in a way nothing reports: gigs past the
# cap never come back, and because they're gone their source_ids stop blocking
# re-ingest, so old postings can reappear later as brand new. At 15,000 against
# a ~25,600-gig board that was already happening to the oldest 10,000.
CAP = 40000

# Everything except the local autoincrement id, which is meaningless across
# instances — rows are keyed on (source, source_id), the same natural key the
# local table dedupes on.
#
# posted_at MUST ARRIVE ISO. This table is text, so a mix of formats sorts
# alphabetically: 1,956 rows written before ingest normalised dates held RFC
# 2822 ("Wed, 29 Apr 2026 ...") and made MAX(posted_at) return an April string
# as the newest row on the board. Backfilled 2026-08-12; ingest has applied
# sources.to_iso() on the way in since July, so nothing new arrives broken.
# Deliberately not re-normalised here: that would make this module import
# sources, which drags in requests and feedparser, and the weekly CI job
# installs neither.
#
# A column missing from this tuple is a column that silently does not survive a
# redeploy. That is not theoretical: apply_email, page_checked and link_checked
# were all absent here, so every gig lost its extracted apply-to address on each
# deploy and the two backfill sweeps restarted from zero at a few pages a cycle,
# never catching up. Add a column to posts, add it here too.
_COLS = ("source", "source_id", "url", "title", "body", "posted_at",
         "fetched_at", "is_demand", "job_type", "size_tier", "urgency", "owner",
         "apply_email", "page_checked", "link_checked", "llm_checked",
         "archived_at")
# page_checked/link_checked default to NULL, not 0 or "": db.py asks for work
# with `WHERE page_checked IS NULL`, so a 0 would mark every restored gig as
# already swept, and an "" would fail outright against an integer column in
# Postgres — taking the whole executemany, and the batch, down with it.
_DEFAULTS = {"is_demand": 1, "owner": "",
             "page_checked": None, "link_checked": None, "llm_checked": None,
             "archived_at": None}

# db.upsert_many() restores exactly these columns, so it reads them from here
# rather than keeping a second copy that can drift out of sync (it did).
COLS = _COLS
DEFAULTS = _DEFAULTS


def enabled() -> bool:
    return store.enabled()


def _ensure(conn):
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
                source     text NOT NULL,
                source_id  text NOT NULL,
                url        text,
                title      text,
                body       text,
                posted_at  text,
                fetched_at text,
                is_demand  integer,
                job_type   text,
                size_tier  text,
                urgency    text,
                owner      text DEFAULT '',
                apply_email text,
                page_checked integer,
                link_checked integer,
                llm_checked integer,
                archived_at text,
                PRIMARY KEY (source, source_id)
            )""")
    _migrate(conn)


# Columns added after the mirror table was first created. CREATE TABLE IF NOT
# EXISTS above is a no-op against the table already live in Supabase, so new
# columns only ever arrive through here.
_ADDED = (("apply_email", "text"),
          ("page_checked", "integer"),
          ("link_checked", "integer"),
          ("llm_checked", "integer"),
          ("archived_at", "text"))


def _migrate(conn):
    """
    Add any missing columns to an already-created mirror table.

    Asks what the table has before altering it rather than firing ALTERs and
    catching the failures: psycopg runs in a transaction, and one failed
    statement aborts it, so a redundant "column already exists" would poison the
    connection and make the INSERT that follows fail — push() would swallow that
    and return 0, mirroring nothing, silently. SELECT ... LIMIT 0 gets the
    column names off the cursor description on both drivers.
    """
    try:
        cur = conn.execute(f"SELECT * FROM {_TABLE} LIMIT 0")
        have = {d[0] for d in (cur.description or ())}
    except Exception:
        return
    added = False
    for col, decl in _ADDED:
        if col not in have:
            conn.execute(f"ALTER TABLE {_TABLE} ADD COLUMN {col} {decl}")
            added = True
    if added:
        # pull()/count() never commit, so without this the DDL rolls back on
        # close and every boot re-runs the migration.
        conn.commit()


def _row(rec: dict) -> tuple:
    return tuple(rec.get(c, _DEFAULTS.get(c, "")) for c in _COLS)


def push(records) -> int:
    """
    Mirror a batch of gigs. Best-effort; returns how many were sent (0 on any
    failure or when disabled). Safe to call with the whole new-this-cycle batch.
    """
    records = [r for r in (records or []) if r.get("source") and r.get("source_id")]
    if not enabled() or not records:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cols = ", ".join(_COLS)
            marks = ", ".join([ph] * len(_COLS))
            sets = ", ".join(f"{c}=excluded.{c}" for c in _COLS
                             if c not in ("source", "source_id"))
            sql = (f"INSERT INTO {_TABLE} ({cols}) VALUES ({marks}) "
                   f"ON CONFLICT (source, source_id) DO UPDATE SET {sets}")
            with conn:                       # commits on clean exit (both drivers)
                conn.cursor().executemany(sql, [_row(r) for r in records])
            return len(records)
        finally:
            conn.close()
    except Exception:
        return 0


def push_tags(rows) -> int:
    """
    Mirror what a re-classification decided: job_type, size_tier, urgency.
    `rows` is [(job_type, size_tier, urgency, source, source_id)].

    WITHOUT THIS A CLASSIFIER FIX SURVIVES ONE PROCESS AND THEN UNDOES ITSELF.
    db.reclassify_all() UPDATEs the local SQLite file and nothing else, exactly
    as the sweeps did before push_sweep() existed — and this one is worse,
    because the re-tag is fingerprint-gated and the stamp is durable. The cycle:
    change the keywords, boot, re-tag locally, stamp the new fingerprint; next
    deploy wipes Render's disk, the board restores from the mirror's OLD tags,
    and reclassify_all sees a fingerprint it has already stamped and skips. The
    wrong tags are then permanent, and no later run will ever revisit them.

    The SEO generator reads the mirror too, so without this a re-tag never
    reaches the field pages at all, however many times the board re-tags itself.

    Assignment, not COALESCE, unlike push_sweep: a sweep that finds nothing must
    not blank an address it did not look for, but a classifier that returns
    "Other / general" has genuinely decided that, and an empty urgency is a real
    value meaning "not urgent" rather than an absence.
    """
    rows = [r for r in (rows or []) if r and r[-2] and r[-1]]
    if not enabled() or not rows:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            sql = (f"UPDATE {_TABLE} SET "
                   f"job_type = {ph}, size_tier = {ph}, urgency = {ph} "
                   f"WHERE source = {ph} AND source_id = {ph}")
            sent = 0
            # Chunked: a re-tag after a vocabulary change can move tens of
            # thousands of rows, and one executemany that size is a single
            # statement the pooler can time out on — losing every row rather
            # than the batch that failed.
            for i in range(0, len(rows), 2000):
                chunk = rows[i:i + 2000]
                with conn:
                    conn.cursor().executemany(sql, chunk)
                sent += len(chunk)
            return sent
        except Exception:
            return 0
        finally:
            conn.close()
    except Exception:
        return 0


def push_llm_result(rows) -> int:
    """
    Mirror one second-pass run: the field it decided, and the fact that it
    looked. `rows` is [(job_type_or_None, source, source_id)].

    COALESCE on job_type, unlike push_tags: None here does not mean "the
    classifier had no opinion to record", it means the model declined to place
    this gig, and the row must keep the "Other / general" it already has rather
    than be blanked.

    llm_checked is set unconditionally, and that is the whole point of mirroring
    this. Render wipes the local disk on every deploy and the board restores
    from here — so a mark that lived only in SQLite would be gone by morning and
    the entire unplaced backlog would be sent to the model again, and billed
    again, after every single deploy.
    """
    rows = [r for r in (rows or []) if r and r[-2] and r[-1]]
    if not enabled() or not rows:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            sql = (f"UPDATE {_TABLE} SET "
                   f"job_type = COALESCE({ph}, job_type), llm_checked = 1 "
                   f"WHERE source = {ph} AND source_id = {ph}")
            sent = 0
            for i in range(0, len(rows), 2000):
                chunk = rows[i:i + 2000]
                with conn:
                    conn.cursor().executemany(sql, chunk)
                sent += len(chunk)
            return sent
        except Exception:
            return 0
        finally:
            conn.close()
    except Exception:
        return 0


def compact_archived() -> int:
    """
    Mirror-side twin of db.compact_archived(): reclaim old archived bodies.

    Rows retired before mark_archived() started clearing body still carry their
    text here, and this is the copy that gets read back at boot, so leaving it
    would mean the local side got smaller while the boot cost stayed put.
    """
    if not enabled():
        return 0
    try:
        conn, _ = store._connect()
        try:
            _ensure(conn)
            with conn:
                cur = conn.execute(
                    f"UPDATE {_TABLE} SET body = '' "
                    f"WHERE is_demand = 0 AND COALESCE(body, '') != ''")
            return cur.rowcount or 0
        finally:
            conn.close()
    except Exception:
        return 0


def pull(cap: int = CAP) -> list[dict]:
    """The newest `cap` mirrored gigs as dicts. Empty on any failure/disabled."""
    if not enabled():
        return []
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cur = conn.execute(
                f"SELECT {', '.join(_COLS)} FROM {_TABLE} "
                f"ORDER BY COALESCE(posted_at, fetched_at) DESC LIMIT {int(cap)}")
            return [dict(zip(_COLS, r)) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def iter_all(batch: int = 10000, demand_only: bool = False):
    """
    Every mirrored gig, in pages, newest first. Yields lists of dicts.

    THE CAP IS A REAL LOSS, not a safety margin. pull() returns the newest CAP
    rows and stops: measured 2026-08-13, the mirror held 50,185 live gigs
    against a 40,000 cap, so 10,206 of them — a fifth of the board — did not
    come back on any boot, silently. Worse, a gig past the cap stops blocking
    re-ingest by its source_id, so it can reappear later as a brand new
    posting. That is the same lossiness the cap was raised from 15,000 to fix,
    just further out.

    Paging also holds peak memory down, which matters more here than the
    correctness fix: one 50,000-row list with every body attached is the same
    "load it all to use a bit of it" shape that took the app down. The caller
    writes each page and drops it.

    demand_only skips archived gigs. The board never shows them, and archival
    reaches a mirror-fed copy through pull_flags() instead, which carries three
    columns rather than whole rows.
    """
    if not enabled():
        return
    where = " WHERE is_demand = 1" if demand_only else ""
    offset = 0
    while True:
        try:
            conn, _ = store._connect()
            try:
                _ensure(conn)
                cur = conn.execute(
                    f"SELECT {', '.join(_COLS)} FROM {_TABLE}{where} "
                    f"ORDER BY COALESCE(posted_at, fetched_at) DESC "
                    f"LIMIT {int(batch)} OFFSET {int(offset)}")
                rows = [dict(zip(_COLS, r)) for r in cur.fetchall()]
            finally:
                conn.close()
        except Exception:
            return
        if not rows:
            return
        yield rows
        if len(rows) < batch:
            return
        offset += len(rows)


def pull_since(since: str, cap: int = CAP) -> list[dict]:
    """
    Only the gigs mirrored since `since` (an ISO fetched_at watermark).

    For the board service, which keeps its own local copy and refreshes it on a
    timer. Pulling all 48,000 rows every minute to collect the twenty that
    changed is the same "walk the whole board to answer a small question"
    mistake that cost the Streamlit app its memory twice — so it asks the
    database for the small answer instead.

    fetched_at, not posted_at: posted_at is when the CLIENT wrote the post,
    which can be older than when we saw it, so a backfilled gig would arrive
    with a timestamp behind the watermark and be missed forever.
    """
    if not enabled() or not since:
        return []
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cur = conn.execute(
                f"SELECT {', '.join(_COLS)} FROM {_TABLE} "
                f"WHERE fetched_at > {ph} "
                f"ORDER BY fetched_at ASC LIMIT {int(cap)}", (since,))
            return [dict(zip(_COLS, r)) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def iter_flags(batch: int = 20000):
    """
    Every gig's (source, source_id, is_demand), in pages.

    Paged for the same reason as iter_all: capped at CAP, reconciliation could
    not see an archived gig that had fallen past the cap, so it would stay on
    the board copy forever — which is exactly the bug reconciliation exists to
    prevent. Three small columns, so the pages can be large.
    """
    if not enabled():
        return
    offset = 0
    while True:
        try:
            conn, _ = store._connect()
            try:
                _ensure(conn)
                cur = conn.execute(
                    f"SELECT source, source_id, is_demand FROM {_TABLE} "
                    f"ORDER BY COALESCE(posted_at, fetched_at) DESC "
                    f"LIMIT {int(batch)} OFFSET {int(offset)}")
                rows = [(r[0], r[1], r[2]) for r in cur.fetchall()]
            finally:
                conn.close()
        except Exception:
            return
        if not rows:
            return
        yield rows
        if len(rows) < batch:
            return
        offset += len(rows)


def pull_flags(cap: int = CAP) -> list[tuple]:
    """
    Every gig's (source, source_id, is_demand) — the keys and nothing else.

    Archival is why this exists. mark_archived() flips is_demand without
    touching fetched_at, so an incremental pull keyed on that watermark can
    never see a gig LEAVE the board — it would sit on a mirror-fed copy
    forever, which is exactly the "dead gig reappears" class of bug the mirror
    was built to fix. Three small columns over the whole table is ~2MB and
    cheap enough to reconcile on a slow timer.
    """
    if not enabled():
        return []
    try:
        conn, _ = store._connect()
        try:
            _ensure(conn)
            cur = conn.execute(
                f"SELECT source, source_id, is_demand FROM {_TABLE} "
                f"ORDER BY COALESCE(posted_at, fetched_at) DESC LIMIT {int(cap)}")
            return [(r[0], r[1], r[2]) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def push_sweep(rows) -> int:
    """
    Mirror what the background sweeps learned: apply_email, page_checked,
    link_checked. `rows` is [(apply_email, page_checked, link_checked,
    source, source_id)] — pass None for a field this sweep didn't touch.

    THIS IS WHY THE APPLY ADDRESSES NEVER ACCUMULATED. The sweeps UPDATE the
    local SQLite file and nothing else, and Render's disk does not survive a
    deploy — so every deploy threw the addresses away and the sweep restarted
    from zero at six pages a cycle, forever. Measured 2026-08-14: the local
    database held 472 addresses and 23 page-checked rows; the mirror held
    ZERO of each, across 52,623 rows.

    Adding apply_email to _COLS fixed the schema half of this in August. It
    was only half: a column the mirror has but is never written to is exactly
    as empty as a column it does not have.

    COALESCE, not assignment: a sweep that found nothing must not blank an
    address an earlier one found.
    """
    rows = [r for r in (rows or []) if r and r[-2] and r[-1]]
    if not enabled() or not rows:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            sql = (f"UPDATE {_TABLE} SET "
                   f"apply_email  = COALESCE({ph}, apply_email), "
                   f"page_checked = COALESCE({ph}, page_checked), "
                   f"link_checked = COALESCE({ph}, link_checked) "
                   f"WHERE source = {ph} AND source_id = {ph}")
            with conn:
                conn.cursor().executemany(sql, rows)
            return len(rows)
        except Exception:
            return 0
        finally:
            conn.close()
    except Exception:
        return 0


def count() -> int:
    """How many gigs are in the mirror (for the admin page). -1 if unreachable."""
    if not enabled():
        return -1
    try:
        conn, _ = store._connect()
        try:
            _ensure(conn)
            return int(conn.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0])
        finally:
            conn.close()
    except Exception:
        return -1


# The retention floor. A sweep that would leave the board below this many
# live gigs is refused rather than run, because the only way to reach that
# number is a misconfigured window — NABBLY_STALE_DAYS set to 1, a clock skew,
# a cutoff computed in the wrong units. Retention is supposed to trim a tail,
# never empty a board, and the difference is worth one COUNT per day.
MIRROR_FLOOR = int(os.environ.get("NABBLY_MIRROR_FLOOR") or 5000)


def archive_stale_mirror(days: int, floor: int = MIRROR_FLOOR) -> dict:
    """
    Age gigs out of the MIRROR itself. Returns what happened, never raises.

    WHY THIS EXISTS AT ALL. db.archive_stale() sweeps the local SQLite file
    and then mirrors the result. That works on a machine that keeps its disk;
    it does nothing on one that does not. The ingest service is redeployed
    with an empty database, so the sweep runs against no rows, reports zero,
    and the mirror — which every reader actually boots from — keeps its full
    history forever. Retention was measured at 85,056 rows and a 232s boot
    against a 270s limit before it was swept by hand, and it drifts back the
    moment nobody is watching.

    So this does not sweep a copy and hope: it archives in the mirror, in one
    UPDATE, on whatever schedule the caller runs it. Same rule as
    db.archive_stale — is_demand=0 and the body dropped, never a DELETE, so
    the row still blocks its own source_id from being re-ingested.
    """
    out = {"ran": False, "archived": 0, "live_before": 0, "would_leave": 0,
           "note": ""}
    if not enabled():
        out["note"] = "mirror not configured"
        return out
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            cur = conn.cursor()
            # Count first, decide second. The floor check is worthless after
            # the UPDATE has already committed.
            cur.execute(f"SELECT COUNT(*) FROM {_TABLE} WHERE is_demand = 1")
            live = int(cur.fetchone()[0] or 0)
            cur.execute(
                f"SELECT COUNT(*) FROM {_TABLE} WHERE is_demand = 1 "
                f"  AND COALESCE(NULLIF(posted_at, ''), fetched_at) < {ph}",
                (cutoff,))
            aged = int(cur.fetchone()[0] or 0)
            out["live_before"], out["would_leave"] = live, live - aged
            if aged and (live - aged) < floor:
                out["note"] = (f"refused: would leave {live - aged:,} live, "
                               f"below the {floor:,} floor")
                print(f"  ! archive_stale_mirror {out['note']} "
                      f"(cutoff {days}d) — nothing was changed", flush=True)
                return out
            if not aged:
                out["ran"] = True
                return out
            cur.execute(
                # Stamped here as well as in db.archive_stale, because the two
                # paths retire rows independently: the mirror sweep can retire a
                # row this copy of the board never saw go. COALESCE so whichever
                # runs second does not overwrite the first date.
                f"UPDATE {_TABLE} SET is_demand = 0, body = '', "
                f"       archived_at = COALESCE(archived_at, {ph}) "
                f"WHERE is_demand = 1 "
                f"  AND COALESCE(NULLIF(posted_at, ''), fetched_at) < {ph}",
                (datetime.now(timezone.utc).isoformat(), cutoff))
            conn.commit()
            out["ran"], out["archived"] = True, int(cur.rowcount or 0)
            print(f"  archive_stale_mirror: retired {out['archived']:,} gigs "
                  f"past {days}d, {out['would_leave']:,} still live", flush=True)
        finally:
            conn.close()
    except Exception as e:
        out["note"] = f"{type(e).__name__}: {e}"
        print(f"  ! archive_stale_mirror failed: {out['note']}", flush=True)
    return out


def mark_archived(pairs) -> int:
    """
    Record in the mirror that these (source, source_id) gigs are off the board.

    THIS IS WHY DEAD GIGS KEPT COMING BACK. The mirror only ever heard about
    gigs at ingest, where everything is is_demand=1 by definition. Archival —
    sweep_dead_links() finding a 404, archive_stale() ageing a post out — was
    written to the LOCAL sqlite file only, and Render's free tier has no
    persistent disk, so that file is destroyed on every restart. Each OOM
    restart therefore rehydrated the newest 15,000 mirrored gigs with their
    original is_demand=1, resurrecting postings we had already proven dead;
    the sweeper then had to rediscover them six per cycle. A founder watching
    the board saw an April listing reappear at the top of "Fresh off the
    boards" minutes after a crash and reasonably concluded the fix never
    worked. The fix has to outlive the disk, which means it lives here.
    """
    pairs = [(s, sid) for s, sid in (pairs or []) if s and sid]
    if not enabled() or not pairs:
        return 0
    try:
        conn, ph = store._connect()
        try:
            _ensure(conn)
            # Drop the body here too, or the saving is local-only: the mirror
            # would keep every archived gig's text forever and hand it back at
            # the next boot, which is the one moment the whole board crosses
            # the network. The row still blocks re-ingest without it.
            sql = (f"UPDATE {_TABLE} SET is_demand = 0, body = '' "
                   f"WHERE source = {ph} AND source_id = {ph}")
            # CHUNKED, AND LOUD ON FAILURE. Both matter, and the old version
            # did neither.
            #
            # One executemany carried the whole set: a boot that aged out
            # thousands of gigs at once sent thousands of round trips inside a
            # single transaction, and if any part of it failed the entire
            # archival was lost — not deferred, lost, because the local UPDATE
            # had already committed. Chunking means a failure costs one batch
            # instead of all of them, and the count returned is what actually
            # landed rather than what was attempted.
            #
            # The silence was the worse half. This returned 0 on any exception
            # and the caller ignored the return value, so the local database
            # said "archived" while the mirror still said "live", the board
            # service went on serving month-old listings, and no log line
            # anywhere said so. Measured 2026-08-16: 3,849 gigs the app had
            # retired were still being served, and this is the write that was
            # supposed to prevent that.
            done = 0
            for i in range(0, len(pairs), 500):
                batch = pairs[i:i + 500]
                try:
                    with conn:
                        conn.cursor().executemany(sql, batch)
                    done += len(batch)
                except Exception as e:
                    print(f"  ! mirror archival FAILED for {len(batch)} gigs "
                          f"({i}..{i + len(batch)} of {len(pairs)}): "
                          f"{type(e).__name__}: {e}", flush=True)
            if done < len(pairs):
                print(f"  ! mirror archival incomplete: {done:,}/{len(pairs):,} "
                      f"landed. The board service will keep serving the rest "
                      f"as live until this succeeds.", flush=True)
            return done
        except Exception as e:
            print(f"  ! mirror archival could not start: "
                  f"{type(e).__name__}: {e}", flush=True)
            return 0
        finally:
            conn.close()
    except Exception as e:
        print(f"  ! mirror archival could not connect: "
              f"{type(e).__name__}: {e}", flush=True)
        return 0

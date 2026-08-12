"""
refresh.py — free "live while in use" auto-refresh, and the alert trigger.

Starts ONE background daemon thread per server process that periodically fetches
new gigs, so the feed grows on its own while the app is being used. Paired with a
timed re-read on the dashboard, the numbers climb without anyone clicking.

It also fires the alerts. Without this, "every gig, the moment it drops" was only
true if you happened to be running watch.py on your own Mac — the live site
gathered gigs around the clock and never told anyone about them.

Free-tier reality: when the instance goes idle it sleeps and this pauses; on the
next wake it restarts from the bundled seed (persistence needs a paid always-on
plan). That's the tradeoff we chose for $0.
"""
import threading
import time

_INTERVAL_S = 120          # ~2 min between fetches
_FIRST_DELAY_S = 30        # let the app finish booting before the first pull
_ALERT_MIN_GAP_S = 900     # fallback gap if prefs can't be read (see _loop)
_DIGEST_CHECK_S = 3600     # how often to check who's due for the weekly digest
_NUDGE_CHECK_S = 3600      # how often to check for a lapsed "yes I'd pay" trial
_ARCHIVE_CHECK_S = 86400   # how often to age gigs off the board
_GAP_RECHECK_S = 300       # how often to re-read everyone's alert interval
_started = False
_lock = threading.Lock()
_state = {"runs": 0, "last": None, "alerted": 0, "last_alert": None}


def _rss_mb() -> float:
    """Current resident memory, in MB. Linux reads /proc (what Render runs);
    the getrusage fallback on macOS reports peak rather than current, which is
    fine for a local sanity check and irrelevant in production."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return kb / (1024 * 1024) if kb > 10_000_000 else kb / 1024
    except Exception:
        return -1.0


def _loop(on_update=None):
    import db
    import ingest
    import alerts
    import accounts
    import paths
    # Top the board up from the durable mirror BEFORE the first fetch, but off
    # the request path — app.py used to do this synchronously at import, which
    # put a multi-thousand-row network read in front of the first page render.
    # Retry here rather than once: the board at this moment is the bundled
    # seed (June listings), and this window is precisely when a visitor would
    # see it. A few quick attempts cover a cold Supabase or a blip without
    # making anyone wait for the 2-minute loop to come round.
    try:
        for attempt in range(4):
            if db.rehydrate_board():
                break
            time.sleep(3 * (attempt + 1))      # 3s, 6s, 9s
    except Exception:
        pass
    time.sleep(_FIRST_DELAY_S)
    # Old news is handled per person now: each account remembers the highest
    # gig id it has been alerted about, and a new account starts that marker at
    # the current top of the board. So there's no global "mark everything
    # alerted" step to run here any more — it would have written a flag nothing
    # on the server reads. (watch.py, the local single-user poller, still uses
    # the global path and does its own baselining.)
    paths.prune_scratch()
    # Re-tag the existing board once, so a classifier change reaches gigs that
    # are already stored (new ingests are classified correctly on the way in).
    # Cheap and idempotent: a second pass finds nothing to change.
    try:
        # Dates BEFORE anything else reads the board: posted_at arrived from
        # feeds in RFC 2822 and the sort is a text sort, so until these are one
        # format "newest first" is really "weekday name, Z to A".
        _state["dates_fixed"] = db.normalize_dates()
        # First pass happens here, at boot, so a gig that's already 45+ days
        # old is off the board before the first visitor loads it. The RECURRING
        # pass is further down in the main loop (_ARCHIVE_CHECK_S) — this one
        # alone used to be the only call, which quietly worked on the free tier
        # because idle sleep and the OOM crashes restarted the process often
        # enough to keep re-triggering it. An always-on paid instance can run
        # for weeks without a restart, and without the loop call a gig that
        # crosses the cutoff mid-run would simply never age out.
        _state["archived"] = db.archive_stale()
        # Reclaims the text of gigs retired before archiving started dropping
        # it. Real work once, then reports 0 for the life of the deployment.
        _state["compacted"] = db.compact_archived()
        # Nodesk turned out to be a paid subscription, not a job board — pulled
        # from ENABLE_SOURCES already; this clears the ~43 rows it had already
        # placed on the board so they don't linger under a source we no longer
        # trust. One-off and idempotent: finds nothing to do once they're gone.
        _state["nodesk_removed"] = db.archive_source("nodesk")
        # fetch_freelancer() used to store Freelancer's own truncated preview
        # instead of the real description; this backfills the rows already on
        # the board with the full text now that the fetcher reads it.
        _state["freelancer_backfilled"] = db.backfill_freelancer_descriptions()
        _state["reclassified"] = db.reclassify_all()
    except Exception:
        pass
    # Everyone who signed up before the weekly digest existed has an empty
    # last_digest, which reads as "never sent" and would make the whole user
    # base due at once on the first pass. Start their clock now instead, so
    # the first digest anyone gets arrives on a normal weekly schedule rather
    # than as a surprise blast the moment this deploys. One-off and
    # idempotent: once stamped there's nothing left to find.
    try:
        import accounts as _accounts
        _state["digest_clock_started"] = _accounts.backfill_last_digest()
    except Exception:
        pass

    last_alert = 0.0
    # The alert gap is derived from every account's prefs file, so it is
    # recomputed on a clock rather than every tick — see where it's used.
    gap = None
    last_gap_calc = 0.0
    # NOT 0.0: `time.time() - 0.0 >= 3600` is true on the very first pass, so
    # a zero here means every deploy and every idle-wake restart fires a digest
    # sweep within seconds of booting instead of an hour in. Starting the clock
    # at "now" is what actually makes this an hourly check.
    last_digest_check = time.time()
    # Same reasoning as last_digest_check — starts the hourly clock at boot
    # rather than at zero.
    last_nudge_check = time.time()
    # Same reasoning: the boot-time call above already archived anything stale
    # as of right now, so the clock for the NEXT pass starts here, not at zero.
    last_archive_check = time.time()

    while True:
        try:
            # No-op once the board is genuinely filled. Until then this is the
            # thing standing between a visitor and a board of June seed data,
            # so it gets another go every cycle rather than being abandoned
            # after one failed pull at boot.
            db.rehydrate_board()
            result = ingest.run()
            _state["runs"] += 1
            _state["last"] = time.time()

            # Rebuild the cached public board HERE, in the background thread,
            # instead of leaving it to whichever visitor's rerun discovers the
            # cache is stale. That rebuild costs ~4s (a full board scan +
            # dedup + tagging) — fine to pay once every ~2 minutes in a thread
            # nobody's waiting on, not fine to hand to a real visitor as their
            # page-load time. Only when something actually changed: an empty
            # cycle (most of them, in a quiet window) would otherwise rebuild
            # an identical frame for nothing.
            if on_update and result.get("new"):
                try:
                    on_update()
                except Exception:
                    pass

            # One memory line per cycle, into Render's log stream. The OOM
            # restarts have now been "fixed" three times, and each diagnosis
            # was reconstructed after the fact from local reproductions. This
            # is the missing instrument: when (if) the next alert email
            # arrives, the log shows exactly what RSS was doing in the minutes
            # before, instead of us inferring it. ~720 short lines a day.
            _state["rss_mb"] = _rss_mb()
            print(f"  mem: {_state['rss_mb']:.0f}MB rss "
                  f"(cycle {_state['runs']})", flush=True)

            # Read anything people forwarded to their Nabbly address. Runs right
            # after the fetch so forwarded gigs are on the board before the
            # alert pass below decides who to ping. No-op unless the mailbox is
            # configured.
            try:
                import inbox
                if inbox.enabled():
                    got = inbox.poll()
                    _state["inbox_gigs"] = _state.get("inbox_gigs", 0) + got["gigs"]
                    _state["inbox_last"] = time.time()
            except Exception:
                pass

            # Batch anything that landed since the last ping. The fetch runs
            # every 2 minutes, but pinging that often all day is how people end
            # up muting you, so the gap is the user's call now — read fresh
            # each loop so a change on the Alerts page takes effect without a
            # restart.
            try:
                # Shortest gap anyone has asked for, so a user who wants alerts
                # every 5 minutes isn't held to someone else's hourly setting.
                #
                # Recomputed every _GAP_RECHECK_S rather than every tick. It
                # opens and parses one prefs file PER ACCOUNT, and the loop
                # ticks every 2 minutes — at a few hundred users that is
                # hundreds of file reads a minute, on the fetch thread, to
                # produce a number that changes when somebody edits a setting.
                # The cost was invisible with three accounts and grows with
                # every signup. A change now takes up to five minutes to take
                # effect instead of two, which is well inside the gap it sets.
                if time.time() - last_gap_calc >= _GAP_RECHECK_S or gap is None:
                    gaps = []
                    for _a in accounts.all_accounts():
                        paths.set_scope(paths.scope_for(_a["email"]))
                        gaps.append(max(1, int(alerts.load_prefs().get("every_min") or 15)))
                    gap = (min(gaps) if gaps else 15) * 60
                    last_gap_calc = time.time()
            except Exception:
                gap = _ALERT_MIN_GAP_S
            # Mirror traffic to the durable store each cycle. Cheap (one small
            # record per day) and it means a redeploy can't wipe the history.
            try:
                import analytics
                analytics.flush()
            except Exception:
                pass
            # Keep the AI spend ledger small — it only needs recent days.
            try:
                import budget
                budget.purge()
            except Exception:
                pass
            # Same reasoning for the apply-click log.
            try:
                import activity
                activity.purge()
            except Exception:
                pass
            # Pull the apply-to address out of anything that arrived this
            # cycle, so a new gig carries it within ~2 minutes of landing.
            try:
                db.backfill_emails()
                # A few posting-page fetches per cycle for the allowlisted
                # sources that keep the address off the feed.
                db.backfill_emails_from_pages()
                # Retire postings the source has already taken down. The age
                # cutoff alone missed a WWR gig that expired inside the window.
                _dead = db.sweep_dead_links()
                if _dead:
                    _state["dead_links"] = _state.get("dead_links", 0) + _dead
            except Exception:
                pass

            if time.time() - last_alert >= gap:
                # One pass per signed-in person, each against their own skills
                # and their own channels. notify_new() is the single-user path
                # and reads whichever profile the thread happens to be scoped
                # to, which in a background thread is nobody's.
                n = alerts.notify_everyone(desktop=False)
                if n:
                    _state["alerted"] += n
                    _state["last_alert"] = time.time()
                last_alert = time.time()

            # Hourly is plenty here — weekly_digest.run_all() only actually
            # sends to an account once accounts.last_digest is ~7 days old,
            # so checking every 2-minute cycle like alerts would just be
            # 30x more SQL for no earlier a send.
            if time.time() - last_digest_check >= _DIGEST_CHECK_S:
                try:
                    import weekly_digest
                    d = weekly_digest.run_all()
                    if d:
                        _state["digests_sent"] = _state.get("digests_sent", 0) + d
                except Exception:
                    pass
                last_digest_check = time.time()

            # Same hourly cadence as the digest check — this only ever sends
            # once per account, so there's no cost to checking often, but no
            # benefit to checking more than hourly either.
            if time.time() - last_nudge_check >= _NUDGE_CHECK_S:
                try:
                    import lapsed_nudge
                    nd = lapsed_nudge.run_all()
                    if nd:
                        _state["nudges_sent"] = _state.get("nudges_sent", 0) + nd
                except Exception:
                    pass
                last_nudge_check = time.time()

            # Daily is plenty — a freshness cutoff doesn't need a 2-minute clock,
            # and this is a full-table scan (see archive_stale) so it shouldn't
            # run any more often than the thing it's protecting against.
            if time.time() - last_archive_check >= _ARCHIVE_CHECK_S:
                try:
                    _state["archived"] = db.archive_stale()
                    _state["compacted"] = db.compact_archived()
                except Exception:
                    pass
                last_archive_check = time.time()
            _state["fails"] = 0          # a clean cycle clears the streak
        except Exception as e:
            # A bad fetch or a dead webhook still shouldn't kill the loop — but
            # it must not be silent either. This handler wraps the WHOLE cycle,
            # so anything that throws every time (a source changing shape, a
            # dependency break, a bad migration) turned into a loop that span
            # forever doing nothing: no gigs, no alerts, no output, and a
            # "runs" counter frozen where it stopped. The board just quietly
            # stopped being live, which is the one failure this product cannot
            # afford to hide.
            _state["fails"] = _state.get("fails", 0) + 1
            _state["last_error"] = f"{type(e).__name__}: {e}"[:300]
            _state["last_error_at"] = time.time()
            print(f"  ! refresh cycle failed ({_state['fails']} in a row): "
                  f"{_state['last_error']}", flush=True)
            if _state["fails"] in (3, 10) or _state["fails"] % 30 == 0:
                # Escalate at the points where "transient" stops being a
                # credible explanation, with the stack this time.
                import traceback
                print(f"  ! refresh has failed {_state['fails']} cycles in a row "
                      f"— the board is not updating", flush=True)
                traceback.print_exc()
        time.sleep(_INTERVAL_S)


def start(on_update=None):
    """
    Idempotent — safe to call on every Streamlit rerun; only one thread runs.

    on_update: called from the background thread after a cycle that actually
    added new gigs. Lets app.py hand in "go rebuild the cached board now"
    without refresh.py importing app.py back (app.py already imports this
    module to start it, so the reverse import would be circular).
    """
    global _started
    with _lock:
        if _started:
            return
        _started = True
        threading.Thread(target=_loop, args=(on_update,), daemon=True,
                         name="nabbly-refresh").start()


def state() -> dict:
    return dict(_state)

"""
weekly_digest.py — "this week, at a glance," the email touchpoint between
someone signing up and them actually opening the board again.

Distinct from alerts.py's instant/daily channels: those are opt-in, per-
channel, tied to plan (Free gets a daily roundup, Pro gets pinged the moment
a gig drops). This is a standing weekly email for every signed-up account,
Free and Pro alike — reusing the exact "Picked for you" ranking (score.py's
fit_score) the dashboard already shows, so the email never claims a match the
app itself wouldn't also make.

Cadence is per-account and durable (accounts.last_digest), not a fixed
weekday cron: each pass checks "has it been ~7 days since this account's last
digest," so a Render restart or a sleeping free instance can't cause a
missed week or a double-send — it just picks up wherever the timestamp says
it left off.
"""
from datetime import datetime, timedelta, timezone

DIGEST_EVERY_DAYS = 7

# WHEN IT ACTUALLY GOES OUT. "Seven days since the last one" is the trigger;
# it is not a time of day, and without a window the hour was whatever hour the
# very first send happened to land on, drifting by up to an hour a week. The
# founder's own was scheduled for 4:51 AM. A jobs email that arrives before
# anyone is at a desk is buried by the time they are. So an account that comes
# due overnight is HELD, and sent by the first hourly pass inside the window;
# after that its clock sits inside the window for good.
#
# 7-9 AM Pacific, the founder's call on 2026-09-11: morning for the US, early
# afternoon for Europe, evening for India. Two hours wide because the check
# runs hourly and _MAX_PER_RUN caps a single pass.
SEND_TZ = "America/Los_Angeles"
SEND_HOURS = (7, 9)          # local hours, [start, end)
_TOP_N = 10
# Ceiling on one pass, not on the day. Every existing account is "due" the
# first time this runs (last_digest starts empty), so without a cap the very
# first cycle after deploy tries to email the entire user base at once and
# runs straight into the mail provider's own daily limit. Whoever doesn't fit
# stays unstamped and is picked up on the next hourly check, so the backlog
# drains on its own rather than being dropped.
_MAX_PER_RUN = 40

# A thin profile (no keywords, no rate floor) leaves fit_score() with nothing
# to differentiate on, so its top matches often cluster on one prolific
# source or one company reposting several openings — a real digest sampled
# during testing put 7 of 10 slots on two employers, both via the same
# source. Capped here rather than in fit_score() itself: the score stays
# honest about what it actually knows: this only affects which of the
# already-scored gigs make the cut.
_MAX_PER_SOURCE = 3
_MAX_PER_TITLE_TAIL = 2


def _diverse_top(scored: list, n: int) -> list:
    """
    Best N by score, capped so no one source or company crowds out the rest.

    "Company" isn't a real field — titles just carry it as "Role — Company",
    inconsistently enough (checked against 2,000 real titles; plenty use
    " - " for something that isn't a company at all) that parsing it out in
    general was tried before and shelved. Matching on the exact trailing
    "— Company" substring sidesteps that: it never has to know what a
    company name IS, it just has to notice when two titles end in the exact
    same one, which carries none of the general parser's false-positive risk.

    One pass in score order; anything over a cap goes to `skipped` instead of
    being dropped, and gets used to top back up to `n` if the caps left the
    list short — a thin match pool should never show FEWER gigs than before,
    only a better-mixed ten when there's enough variety to mix.
    """
    by_source, by_tail, out, skipped = {}, {}, [], []
    for s, p in scored:
        src = p.get("source", "")
        tail = (p.get("title") or "").rsplit(" — ", 1)
        tail_key = tail[1].strip().lower() if len(tail) == 2 else None
        capped = (by_source.get(src, 0) >= _MAX_PER_SOURCE
                  or (tail_key and by_tail.get(tail_key, 0) >= _MAX_PER_TITLE_TAIL))
        if capped:
            skipped.append(p)
            continue
        out.append(p)
        by_source[src] = by_source.get(src, 0) + 1
        if tail_key:
            by_tail[tail_key] = by_tail.get(tail_key, 0) + 1
        if len(out) >= n:
            return out
    out.extend(skipped[:n - len(out)])
    return out


def _send_window_open(now=None) -> bool:
    """True inside SEND_HOURS local time. Loud, not silent, if the zone is missing."""
    now = now or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        local = now.astimezone(ZoneInfo(SEND_TZ))
    except Exception as e:
        # No zone database at all. Fall back to Pacific standard time as a
        # fixed offset -- an hour off for a third of the year, but the email
        # still lands in the morning rather than never. Printed every pass
        # on purpose: this is a misconfigured container, and it should nag.
        print(f"  weekly: no zone database ({type(e).__name__}); using UTC-8 "
              f"for the send window -- add tzdata", flush=True)
        local = now.astimezone(timezone(timedelta(hours=-8)))
    return SEND_HOURS[0] <= local.hour < SEND_HOURS[1]


def _due(acc: dict) -> bool:
    last = acc.get("last_digest")
    if not last:
        return True
    try:
        d = datetime.fromisoformat(last)
        if not d.tzinfo:
            d = d.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - d >= timedelta(days=DIGEST_EVERY_DAYS)


def _market(week: list[dict]) -> dict:
    """
    The part of the email that is still true a week after it is written.

    Computed ONCE per pass and shared by every recipient: it is the same board
    for all of them, and skill_stats over a week of posts is the expensive
    thing in here.
    """
    import db
    import market as market_mod

    stats = market_mod.skill_stats(week)
    hot = []
    for field, count in market_mod.hot_skills(stats, top=6):
        hot.append((field, count, (stats.get(field) or {}).get("typical")))
    return {
        "total": len(week),
        # COUNT(*), not a second week of rows in memory — see db.count_between.
        "prev_total": db.count_between(14, 7),
        "hot": hot,
        "urgent": sum(1 for p in week if p.get("urgency") == "Urgent"),
    }


# What "just landed" means. Anything older than this is very likely closed --
# a Freelancer bid period is 7 days and the median active project is ~1 hour
# old -- so the listings in a weekly email are the ones that arrived just
# before it was sent, never a week's backlog.
_FRESH_HOURS = 48
_SHOW = 5
# Added to fit_score (0-100) before ranking the picks. Large enough that a
# project beats a salaried role of similar fit, small enough that a poor-fit
# project does not beat a strong-fit contract. Unknown ('') is neutral: the
# ~55k rows stored before work_type existed must not be punished for it.
_WORK_TYPE_BOOST = {"project": 25, "contract": 15, "": 0, "fulltime": -25}


def _fresh_for(week: list[dict], skills: list[str], prof: dict) -> list[dict]:
    """The newest matches for this person, ranked the way the board ranks."""
    import score
    from datetime import datetime, timedelta, timezone as _tz
    from email.utils import parsedate_to_datetime

    cut = datetime.now(_tz.utc) - timedelta(hours=_FRESH_HOURS)

    def landed(p):
        """
        When this gig arrived, as a datetime.

        PARSED, NOT STRING-COMPARED. The first cut of this compared the raw
        column against an ISO cutoff, which silently means nothing the moment a
        row is not ISO -- and rows are not all ISO: the bundled seed carries
        RFC-2822 ("Tue, 16 Jun 2026 10:51:37 +0000"), which sorts before every
        ISO string and would have quietly excluded every such gig from "just
        landed" forever. Production is all ISO today (150,736 rows checked on
        2026-09-10, none unparseable), so this was invisible there -- exactly
        the kind of thing that stays invisible until a source changes format.
        Unparseable counts as old, never as fresh.
        """
        raw = str(p.get("posted_at") or p.get("fetched_at") or "").strip()
        if not raw:
            return None
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                d = parsedate_to_datetime(raw)
            except Exception:
                return None
        return d.replace(tzinfo=_tz.utc) if d.tzinfo is None else d

    matched = [p for p in week if not skills or p.get("job_type") in skills]
    fresh = [p for p in matched if (landed(p) or cut - timedelta(days=1)) >= cut]
    # A niche skill can go two days without a single match; widening beats
    # sending a section with nothing in it. Still ranked, still capped.
    pool = fresh if len(fresh) >= 3 else matched
    scored = []
    for p in pool:
        sc, _ = score.fit_score(p, prof)
        # PROJECT WORK OUTRANKS A SALARIED VACANCY, at equal fit. Rendered for
        # the founder's own profile on 2026-09-11, all five picks were
        # full-time roles -- a Director of Sales, two "(m/w/d)" German
        # postings -- in a weekly email from a product that sells freelance
        # and contract work. work_type is the structured field for exactly
        # this, and it arrives on every row since the same day; rows from
        # before carry '' and sit in the middle, so the ranking degrades to
        # fit-only on old data and sharpens as the board turns over.
        scored.append((sc + _WORK_TYPE_BOOST.get(p.get("work_type") or "", 0), p))
    scored.sort(key=lambda t: t[0], reverse=True)
    return _diverse_top(scored, _SHOW)


def run_all() -> int:
    """
    Send the weekly email to every account it is due for. Returns how many.

    ONE EMAIL, MARKET FIRST. This used to be a ranked list of the week's best
    matches, and alerts.py separately mailed a roundup of what had landed --
    two similar emails a week from one product. The founder's inbox called it,
    twice. Measured against 100 live Freelancer projects on 2026-09-10: the
    bid period is 7 days on 99 of them, the median age of a project still
    listed as active is 1.1 hours, and one under two hours old already carries
    ~30 bids. No weekly email can hand somebody a gig they can still win. What
    it CAN do is tell them what the market did, which is true whenever they
    read it -- so that leads, and the listings are only the freshest few at
    the moment of sending.

    Same cadence machinery as before: per-account and durable, so a restart
    can neither skip a week nor double-send.
    """
    import accounts
    import activity
    import db
    import mailer
    import paths
    import profile

    if not mailer.enabled():
        return 0
    # Held, not stamped: whoever is due stays due, and the first pass inside
    # the window picks them up. Nothing about the account changes here.
    if not _send_window_open():
        return 0

    due = [a for a in accounts.all_accounts()
           if not a.get("email_opt_out") and _due(a)]
    if not due:
        return 0

    week = db.posts_recent(DIGEST_EVERY_DAYS, demand_only=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not week:
        # A quiet data week is not a reason to bank seven digests that all
        # fire at once when gigs come back.
        for acc in due:
            accounts.set_last_digest(acc["email"], now)
        return 0

    market = _market(week)

    sent = 0
    for acc in due[:_MAX_PER_RUN]:
        scope = paths.scope_for(acc["email"])
        paths.set_scope(scope)
        prof = profile.load() or {}
        gigs = _fresh_for(week, prof.get("skills") or [], prof)
        try:
            is_pro = bool(accounts.status(acc).get("pro"))
        except Exception:
            is_pro = False
        mine = dict(market)
        mine["applied"] = activity.applied_count(scope, days=DIGEST_EVERY_DAYS)
        subject, html_body, text_body = mailer.weekly_email(
            prof.get("name", ""), mine, gigs,
            accounts.email_token(acc["token"]), is_pro=is_pro,
            # Only true when they actually told us something to match on. With
            # an empty profile _fresh_for returns the newest of everything, and
            # calling that "your matches" is a claim we cannot back.
            personalised=bool(prof.get("skills")))
        if mailer.send(acc["email"], subject, html_body, text_body):
            sent += 1
        else:
            # Do NOT stamp on a failed send: a rate limit would otherwise cost
            # this person their email for a full week, silently. Unstamped
            # means still due on the next hourly check, which self-heals.
            continue
        accounts.set_last_digest(acc["email"], now)
    return sent

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
_TOP_N = 10
# Ceiling on one pass, not on the day. Every existing account is "due" the
# first time this runs (last_digest starts empty), so without a cap the very
# first cycle after deploy tries to email the entire user base at once and
# runs straight into the mail provider's own daily limit. Whoever doesn't fit
# stays unstamped and is picked up on the next hourly check, so the backlog
# drains on its own rather than being dropped.
_MAX_PER_RUN = 40


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


def run_all() -> int:
    """Send the weekly digest to every account it's due for. Returns how many
    were sent. Mirrors alerts.notify_everyone()'s shape: fetch the shared
    window of posts ONCE, filter per-account in Python, never re-query per
    person."""
    import accounts
    import activity
    import db
    import mailer
    import paths
    import profile
    import score

    if not mailer.enabled():
        return 0

    due = [a for a in accounts.all_accounts()
          if not a.get("email_opt_out") and _due(a)]
    if not due:
        return 0

    week = db.posts_recent(DIGEST_EVERY_DAYS, demand_only=True)
    if not week:
        # Nobody's overdue for an email that would say "0 gigs this week" —
        # advance the marker anyway so a quiet data week doesn't queue up a
        # pile of digests that all fire the moment fresh gigs land.
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for acc in due:
            accounts.set_last_digest(acc["email"], now)
        return 0

    sent = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for acc in due[:_MAX_PER_RUN]:
        scope = paths.scope_for(acc["email"])
        paths.set_scope(scope)
        prof = profile.load()
        skills = prof.get("skills") or []
        matched = [p for p in week if not skills or p.get("job_type") in skills]
        if matched:
            # Same fit_score() the dashboard's "Picked for you" ranks by,
            # score AND reasons both attached to the row — the email should
            # never claim a match or a "why" the app itself wouldn't also show.
            scored = []
            for p in matched:
                s, why = score.fit_score(p, prof)
                scored.append((s, {**p, "_score": s, "_reasons": why}))
            scored.sort(key=lambda t: t[0], reverse=True)
            top = [p for _, p in scored[:_TOP_N]]
            stats = {"applied": activity.applied_count(scope, days=DIGEST_EVERY_DAYS),
                     "completeness": profile.completeness(prof)}
            subject, html_body, text_body = mailer.digest_email(
                prof.get("name", ""), top, len(matched), acc["token"], stats=stats)
            if mailer.send(acc["email"], subject, html_body, text_body):
                sent += 1
            else:
                # Do NOT stamp on a failed send. A rate limit or a transient
                # provider error would otherwise cost this person their digest
                # for a full week, silently — the marker says "sent" and the
                # next pass skips them. Leaving it unset means they're still
                # due on the next hourly check, which is self-healing.
                continue
        # Stamp on a real send, and on "nothing matched this week" — a quiet
        # week for one person's skills shouldn't bank a backlog that fires as
        # one big email the moment something finally matches.
        accounts.set_last_digest(acc["email"], now)
    return sent

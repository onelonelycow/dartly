"""
lapsed_nudge.py — the one email to someone who told us, in their own words,
that they'd pay for this, and then never got the chance to prove it.

people.set_pay() has captured a plain "would you pay for this: yes / maybe /
no" answer since day one, and until now nothing ever read it back — it only
ever surfaced in an admin funnel table. Someone who answered "yes", started
the 14-day trial, and let it lapse without upgrading is the warmest lead this
app has, sitting untouched. This sends one honest email and stops.

Mirrors weekly_digest.py's shape (same accounts.all_accounts() sweep, same
mailer.send(), same "don't stamp on a failed send" rule) but the "due" check
is simpler: no recurring clock, just three durable facts — said yes, trial
has actually expired, never sent this before (accounts.pay_nudge_sent). That
also means, unlike weekly_digest, no backfill-the-clock step is needed: an
unset pay_nudge_sent doesn't make everyone "due at once," because the other
two conditions already keep this list small and accurate from the first run.
"""
from datetime import datetime, timezone

_MAX_PER_RUN = 25  # naturally small — trial-taken AND pay="yes" both first


def run_all() -> int:
    """Email every account that said yes, had a trial that's since expired,
    and hasn't been sent this already. Returns how many were sent."""
    import accounts
    import mailer
    import paths
    import people
    import profile

    if not mailer.enabled():
        return 0

    pay_yes = {r["email"] for r in people.people_rows() if r.get("pay") == "yes"}
    if not pay_yes:
        return 0

    due = [a for a in accounts.all_accounts()
          if not a.get("email_opt_out")
          and not a.get("pay_nudge_sent")
          and a["email"] in pay_yes
          and accounts.status(a)["expired"]]
    if not due:
        return 0

    sent = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for acc in due[:_MAX_PER_RUN]:
        paths.set_scope(paths.scope_for(acc["email"]))
        name = profile.load().get("name", "")
        subject, html_body, text_body = mailer.lapsed_payer_email(
            name, acc["token"], accounts.email_token(acc["token"]))
        if mailer.send(acc["email"], subject, html_body, text_body):
            sent += 1
            accounts.set_pay_nudge_sent(acc["email"], now)
        # Do NOT stamp on a failed send — a transient provider error must
        # never permanently cost someone the one email this job ever sends.
    return sent

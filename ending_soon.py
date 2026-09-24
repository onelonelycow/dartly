"""
ending_soon.py -- the one email before a founding grant or trial runs out.

Founding members get 60 days of Pro from the day they sign up; a trial is
14. Until this existed the end was silent: the board dropped to Free on the
day and nobody had been told what was ending, what stayed, or where to keep
it. The first founding member's clock runs out on 2026-10-19.

Same shape as lapsed_nudge.py: an hourly sweep of accounts.all_accounts(),
mailer.send(), a durable once-only stamp (accounts.ending_soon_sent), and no
stamp on a failed send. Due when: Pro is on a clock (accounts.status gives
days_left), the clock is within LEAD_DAYS, nobody is paying already, the
address has not opted out, it has not been sent, and it is not the founder
or an internal account.

Sent in the same 7-9am Pacific window as the weekly, for the same reason.
"""
import os
from datetime import datetime, timezone

LEAD_DAYS = 3
_MAX_PER_RUN = 25

_INTERNAL = tuple(d.strip().lower() for d in (
    os.environ.get("NABBLY_INTERNAL_DOMAINS") or "onelonelycow.com").split(",") if d.strip())


def _internal(email: str) -> bool:
    import accounts
    e = (email or "").lower()
    return accounts.is_owner(e) or e.rsplit("@", 1)[-1] in _INTERNAL


def due(acc: dict, st: dict | None = None) -> bool:
    import accounts
    st = st or accounts.status(acc)
    return (bool(st.get("pro")) and st.get("days_left") is not None
            and 0 < int(st["days_left"]) <= LEAD_DAYS
            and not acc.get("stripe_subscription_id")
            and not acc.get("email_opt_out")
            and not acc.get("ending_soon_sent")
            and not _internal(acc.get("email", "")))


def run_all() -> int:
    """Email everyone whose Pro ends within LEAD_DAYS. Returns how many were sent."""
    import accounts
    import mailer
    import paths
    import profile
    import weekly_digest

    if not mailer.enabled() or not weekly_digest._send_window_open():
        return 0
    todo = []
    for acc in accounts.all_accounts():
        st = accounts.status(acc)
        if due(acc, st):
            todo.append((acc, st))
    sent = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for acc, st in todo[:_MAX_PER_RUN]:
        paths.set_scope(paths.scope_for(acc["email"]))
        name = (profile.load() or {}).get("name", "")
        ends = st.get("ends")
        ends_on = ends.strftime("%-d %B") if ends else "soon"
        subject, html_body, text_body = mailer.pro_ending_email(
            name, int(st["days_left"]), ends_on, bool(acc.get("founding")),
            accounts.email_token(acc["token"]))
        if mailer.send(acc["email"], subject, html_body, text_body):
            sent += 1
            accounts.set_ending_soon_sent(acc["email"], now)
            print(f"  ending-soon: sent to {acc['email']} ({st['days_left']}d left)", flush=True)
    return sent

"""
lastvisit.py — when this member last looked at their dashboard.

WHY NOT accounts.last_seen. That column exists and it is not this. Its only
writers are the sign-in paths and accounts.by_email(touch=True), and touch=True
is called from nowhere in the repo — webauth.account_for() deliberately uses
the default, because turning every board page load into an accounts write is
exactly what its docstring exists to prevent. For a member with a live cookie,
last_seen is their signup date. Using it would tell someone who was here
yesterday "41,000 new since your last visit", which is worse than saying
nothing (FEEL.md §7).

So this keeps its own stamp, on the same rails the profile already rides:
paths.read_user_json / write_user_json, meaning a local file plus the durable
mirror, healing across deploys.

THE WRITE IS THROTTLED, and that is not an optimisation. write_user_json does a
network round trip to Postgres, and without a throttle a member reloading their
dashboard five times in a minute would pay five of them AND watch the count
decay to zero as they read it. Thirty minutes means the number holds still
long enough to be read, and a session of browsing costs one write.
"""
from datetime import datetime, timezone

STAMP = "visit.json"
THROTTLE_S = 30 * 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read() -> str:
    """
    The mark to count from: the end of this member's PREVIOUS session.

    Not "the last time a page rendered". That version moved the mark on the
    first view, so a glance at the dashboard followed by a reload showed
    "612 new" and then nothing at all — the number evaporating as you looked
    at it. A session is what a person means by "last here", so the mark only
    advances once a gap has passed.
    """
    import paths
    try:
        return (paths.read_user_json(STAMP, {}) or {}).get("seen_at", "")
    except Exception:
        # A missing stamp is not an error: it means no "new since" line today.
        return ""


def touch() -> None:
    """
    Note that the member is here, and roll the mark forward between sessions.

    Called AFTER the count is taken. Two fields, doing different jobs:
      seen_at   the mark the count runs from — the end of the last session
      last_view the last time any dashboard rendered, updated every time

    When the gap since last_view exceeds THROTTLE_S the member has been away,
    so the old last_view BECOMES the new mark and counting starts there. Inside
    a session only last_view moves, which is why the number holds still while
    somebody reads it — and why a session of browsing costs one Postgres write
    rather than one per reload.
    """
    import paths
    try:
        cur = paths.read_user_json(STAMP, {}) or {}
        now = _now()
        last_view = cur.get("last_view", "")
        seen_at = cur.get("seen_at", "")
        gap = None
        if last_view:
            gap = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(last_view)).total_seconds()
        if gap is None:
            # First ever: mark from now, so the next visit counts from here.
            paths.write_user_json(STAMP, {"seen_at": now, "last_view": now})
        elif gap >= THROTTLE_S:
            paths.write_user_json(STAMP, {"seen_at": last_view, "last_view": now})
        # Inside the window: nothing to write. last_view is close enough, and
        # the saved round trip is the point.
    except Exception:
        pass

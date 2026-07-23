"""
accounts.py — who is using Nabbly right now, and what they're entitled to.

people.py answers "who signed up". This answers "who is looking at the screen",
which is a different question and the one that decides whose profile loads and
whether Pro features are unlocked.

WHY THIS EXISTS: every private file (profile, alert channels, drafts) used to
be a single copy shared by every visitor. One person's skills decided what the
next person saw on their dashboard, and the Alerts page showed whichever phone
number had been typed last. Fine for a demo with one user. Not fine the moment
you send the link to a tester.

HOW IDENTITY WORKS: no passwords. Someone types their email, we mint a random
token, and it rides in the URL (?u=...). Coming back on that link signs them
straight back in. This is deliberately light: it keeps the signup to one field,
and it is honest about its limits. A token in a URL can be forwarded, and
anyone holding it is that person. That is an acceptable trade for an invited
beta and not acceptable for a public launch with billing attached, at which
point this table already has the columns real accounts would need.

THE TRIAL: early testers get the full product for TRIAL_DAYS so they can judge
it at full strength, then drop to free unless upgraded. plan is the override:
'trial' obeys the clock, 'pro' is unlimited (a thank-you, or a paying user),
'free' is no trial at all.
"""
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import people
from paths import data_file

DB_PATH = data_file("nabbly_people.db")   # same file as people.py
TRIAL_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse(ts: str | None):
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init():
    """Create the table. Safe to call on every run."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            email         TEXT PRIMARY KEY,
            token         TEXT NOT NULL UNIQUE,
            created       TEXT NOT NULL,
            last_seen     TEXT,
            trial_start   TEXT,
            plan          TEXT DEFAULT 'trial',  -- trial | pro | free
            last_alert_id INTEGER DEFAULT 0,     -- highest gig id we've pinged them about
            visits        INTEGER DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_token ON accounts(token)")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Sign in / look up
# ---------------------------------------------------------------------------
def sign_in(email: str, source: str = "signin") -> tuple[dict | None, bool]:
    """
    Find or create the account for this email.

    Returns (account, is_new). Also records them in people.py, so a tester who
    signs in is captured in the same place as everyone else and mirrors to the
    Google Sheet like any other signup.
    """
    email = (email or "").strip().lower()
    if not people.valid_email(email):
        return None, False

    init()
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
    if row:
        conn.execute("UPDATE accounts SET last_seen=?, visits=visits+1 WHERE email=?",
                     (_now(), email))
        conn.commit()
        acc = dict(row)
        conn.close()
        return acc, False

    now = _now()
    token = secrets.token_urlsafe(18)
    # Start their alert marker at whatever is already on the board. Without
    # this, a new account's first alert pass sees several thousand existing
    # gigs as "new" and fires one enormous ping, which on SMS costs real money.
    # Joining today means hearing about gigs that land from today.
    try:
        import db as _db
        rows = _db.all_posts(demand_only=True)
        watermark = max((int(r["id"]) for r in rows), default=0)
    except Exception:
        watermark = 0
    conn.execute(
        "INSERT INTO accounts (email, token, created, last_seen, trial_start, "
        "plan, last_alert_id, visits) VALUES (?,?,?,?,?,'trial',?,1)",
        (email, token, now, now, now, watermark))
    conn.commit()
    acc = dict(conn.execute("SELECT * FROM accounts WHERE email=?",
                            (email,)).fetchone())
    conn.close()
    try:
        people.add_person(email, source=source)
    except Exception:
        pass          # a webhook hiccup must never block someone signing in
    return acc, True


def by_token(token: str) -> dict | None:
    """The account this URL token belongs to, or None."""
    token = (token or "").strip()
    if not token:
        return None
    init()
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE token=?", (token,)).fetchone()
    if row:
        conn.execute("UPDATE accounts SET last_seen=?, visits=visits+1 WHERE token=?",
                     (_now(), token))
        conn.commit()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Entitlement
# ---------------------------------------------------------------------------
def status(acc: dict | None) -> dict:
    """
    What this person can currently do.

    Anonymous visitors get the free view: they can browse the whole board and
    see what Pro adds, which is the point of a shop window.
    """
    if not acc:
        return {"signed_in": False, "pro": False, "plan": "anon",
                "days_left": 0, "expired": False, "email": ""}

    plan = (acc.get("plan") or "trial").lower()
    base = {"signed_in": True, "plan": plan, "email": acc.get("email", ""),
            "days_left": 0, "expired": False}

    if plan == "pro":
        return {**base, "pro": True}
    if plan == "free":
        return {**base, "pro": False}

    start = _parse(acc.get("trial_start"))
    if not start:
        return {**base, "pro": False, "expired": True}
    ends = start + timedelta(days=TRIAL_DAYS)
    left = ends - datetime.now(timezone.utc)
    days = max(0, -(-left.total_seconds() // 86400))   # round up; 0.1 days left is still "1"
    return {**base, "pro": left.total_seconds() > 0, "days_left": int(days),
            "expired": left.total_seconds() <= 0}


def set_plan(email: str, plan: str):
    """Grant Pro, drop to free, or restart a trial. Used from the admin page."""
    plan = (plan or "trial").lower()
    if plan not in ("trial", "pro", "free"):
        return
    init()
    conn = _connect()
    if plan == "trial":
        conn.execute("UPDATE accounts SET plan='trial', trial_start=? WHERE email=?",
                     (_now(), email.strip().lower()))
    else:
        conn.execute("UPDATE accounts SET plan=? WHERE email=?",
                     (plan, email.strip().lower()))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Alerting support
# ---------------------------------------------------------------------------
def set_last_alert_id(email: str, gig_id: int):
    """
    Remember the newest gig we've pinged this person about.

    Per person rather than one global "alerted" flag, because with more than
    one user a single flag means the first person's alert silences everyone
    else's.
    """
    init()
    conn = _connect()
    conn.execute("UPDATE accounts SET last_alert_id=? WHERE email=?",
                 (int(gig_id), email.strip().lower()))
    conn.commit()
    conn.close()


def all_accounts() -> list[dict]:
    init()
    conn = _connect()
    rows = conn.execute("SELECT * FROM accounts ORDER BY created").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats() -> dict:
    """Headline numbers for the admin page."""
    rows = all_accounts()
    live = [r for r in rows if status(r)["pro"]]
    return {
        "accounts": len(rows),
        "on_trial": sum(1 for r in rows if (r.get("plan") or "") == "trial"
                        and status(r)["pro"]),
        "expired": sum(1 for r in rows if status(r)["expired"]),
        "pro": sum(1 for r in rows if (r.get("plan") or "") == "pro"),
        "with_access": len(live),
        "returning": sum(1 for r in rows if (r.get("visits") or 0) > 1),
    }

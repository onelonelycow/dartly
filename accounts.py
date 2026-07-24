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

THE TRIAL: Pro is a lane people opt into, not one they're dropped into. Signing
in lands you on 'free'; you can then start a 14-day Pro trial whenever you want
to judge the product at full strength, once. plan is the override: 'free' is the
default and no trial, 'trial' obeys the clock from trial_start, 'pro' is
unlimited (a thank-you, or a paying user). Starting a trial is a deliberate
click (start_trial), so nobody feels forced down one path.
"""
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import people
import store
from paths import data_file

DB_PATH = data_file("nabbly_people.db")   # same file as people.py
TRIAL_DAYS = 14               # the opt-in trial anyone can start
FOUNDING_DAYS = 60           # ~2 months, the thank-you for the first backers
FOUNDING_LIMIT = 50          # how many of them get it

_ACCT_SCOPE = "_accounts"      # namespace for the durable mirror
_COLS = ("email", "token", "created", "last_seen", "trial_start", "pro_until",
         "founding", "plan", "last_alert_id", "visits")
_rehydrated = False


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
            pro_until     TEXT,                  -- time-boxed Pro ends here (trial or founding grant)
            founding      INTEGER DEFAULT 0,     -- 1 = one of the first FOUNDING_LIMIT members
            plan          TEXT DEFAULT 'free',   -- free | trial | pro
            last_alert_id INTEGER DEFAULT 0,     -- highest gig id we've pinged them about
            visits        INTEGER DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_token ON accounts(token)")
    # Safe migration for tables created before these columns existed.
    for col, decl in (("pro_until", "TEXT"), ("founding", "INTEGER DEFAULT 0")):
        try:
            conn.execute(f"ALTER TABLE accounts ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
    _rehydrate()


def _mirror(email: str):
    """
    Copy one account row to the durable store.

    Only the fields that must survive a wipe are worth mirroring; we skip the
    per-view visit bump so a busy tester doesn't cause a write on every page
    load, but token, trial_start, plan and last_alert_id all go through here so
    a redeploy can't reset someone's trial or make their alerts re-flood.
    """
    if not store.enabled():
        return
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE email=?",
                       (email.strip().lower(),)).fetchone()
    conn.close()
    if row:
        store.put(_ACCT_SCOPE, email.strip().lower(), dict(row))


def _rehydrate():
    """
    After a wiped disk, refill an empty accounts table from the durable store.

    Runs once per process, and only when the local table is empty, so a normal
    boot with data already on disk touches nothing.
    """
    global _rehydrated
    if _rehydrated or not store.enabled():
        return
    _rehydrated = True
    try:
        conn = _connect()
        empty = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
        if empty:
            saved = store.list_scope(_ACCT_SCOPE)
            # Built from _COLS so adding a column (pro_until, founding, …) can't
            # leave this INSERT out of sync with the tuple below it.
            cols = ", ".join(_COLS)
            marks = ", ".join("?" * len(_COLS))
            for row in saved.values():
                conn.execute(
                    f"INSERT OR IGNORE INTO accounts ({cols}) VALUES ({marks})",
                    tuple(row.get(c) for c in _COLS))
            conn.commit()
        conn.close()
    except Exception:
        pass


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
        watermark = _db.max_post_id()
    except Exception:
        watermark = 0
    # The first FOUNDING_LIMIT people to sign up get ~2 months of Pro as a
    # thank-you for taking the early chance — not because they asked, but as a
    # gift. Everyone after that lands on Free and can start the opt-in trial when
    # they choose. (The count is a snapshot; a rare simultaneous signup could put
    # us a hair over 50, which is fine — erring generous.)
    existing = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    founding = 1 if existing < FOUNDING_LIMIT else 0
    pro_until = (datetime.now(timezone.utc)
                 + timedelta(days=FOUNDING_DAYS)).isoformat(timespec="seconds") \
        if founding else ""
    conn.execute(
        "INSERT INTO accounts (email, token, created, last_seen, trial_start, "
        "pro_until, founding, plan, last_alert_id, visits) "
        "VALUES (?,?,?,?,'',?,?,'free',?,1)",
        (email, token, now, now, pro_until, founding, watermark))
    conn.commit()
    acc = dict(conn.execute("SELECT * FROM accounts WHERE email=?",
                            (email,)).fetchone())
    conn.close()
    _mirror(email)
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
                "days_left": 0, "expired": False, "email": "",
                "trialed": False, "can_trial": False, "founding": False}

    plan = (acc.get("plan") or "free").lower()
    founding = bool(acc.get("founding"))
    deadline = _pro_deadline(acc)            # when time-boxed Pro ends, or None
    trialed = deadline is not None           # has had some time-boxed Pro grant
    base = {"signed_in": True, "plan": plan, "email": acc.get("email", ""),
            "days_left": 0, "expired": False, "trialed": trialed,
            "founding": founding, "can_trial": False}

    if plan == "pro":                        # a manual/permanent grant
        return {**base, "pro": True}
    if deadline:                             # founding gift or an opted-in trial
        left = deadline - datetime.now(timezone.utc)
        if left.total_seconds() > 0:
            days = int(max(0, -(-left.total_seconds() // 86400)))   # round up
            return {**base, "pro": True, "days_left": days}
        return {**base, "pro": False, "expired": True}
    # Never had a grant → Free, and the opt-in trial is theirs to start.
    return {**base, "pro": False, "can_trial": True}


def _pro_deadline(acc: dict):
    """
    When this account's time-boxed Pro ends, or None if it never had any.

    Prefers pro_until (founding grants and new opt-in trials both write it);
    falls back to trial_start + TRIAL_DAYS for accounts created before pro_until
    existed, so an in-flight older trial keeps counting down correctly.
    """
    until = _parse(acc.get("pro_until"))
    if until:
        return until
    start = _parse(acc.get("trial_start"))
    if start:
        return start + timedelta(days=TRIAL_DAYS)
    return None


def start_trial(email: str) -> tuple[bool, str]:
    """
    Begin the 14-day Pro trial — only when the person chooses to.

    Signing in no longer starts this; Pro is opt-in. Guarded so it's used once:
    anyone already on Pro, mid-grant, or with an expired grant (founders
    included) is turned away here. The admin can still grant via set_plan.
    Returns (started, message).
    """
    email = (email or "").strip().lower()
    init()
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
    if not row:
        conn.close()
        return False, "Sign in first."
    acc = dict(row)
    if (acc.get("plan") or "") == "pro":
        conn.close()
        return False, "You're already on Pro."
    if _pro_deadline(acc) is not None:
        conn.close()
        return False, "You've already had your free Pro."
    until = (datetime.now(timezone.utc)
             + timedelta(days=TRIAL_DAYS)).isoformat(timespec="seconds")
    conn.execute("UPDATE accounts SET plan='trial', trial_start=?, pro_until=? "
                 "WHERE email=?", (_now(), until, email))
    conn.commit()
    conn.close()
    _mirror(email)
    return True, ""


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
    _mirror(email)


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
    _mirror(email)


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

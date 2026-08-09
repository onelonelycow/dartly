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
import hashlib
import hmac
import os
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

# Partner groups testing Nabbly under an in-kind agreement: their people get Pro
# free for the length of the test, unlocked by arriving on the partner's own
# link (?ref=<tag>). Keyed by the campaign tag so the same link that measures
# the collaboration also delivers what was promised on it — one thing to hand a
# partner, not a link plus a code.
#
# `days` is the test window, deliberately generous enough to cover a real
# working month or two rather than a weekend look.
PARTNER_GRANTS = {
    "nextnw": {"name": "Next Northwest", "days": 90},
}

_ACCT_SCOPE = "_accounts"      # namespace for the durable mirror
_COLS = ("email", "token", "created", "last_seen", "trial_start", "pro_until",
         "founding", "plan", "last_alert_id", "visits", "email_opt_out", "last_digest",
         "stripe_customer_id", "stripe_subscription_id")
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


class StoreUnavailable(RuntimeError):
    """
    The accounts database couldn't be reached on this render.

    Deliberately NOT the same thing as "no account matched". _resolve_account()
    pops the session token when a lookup comes back empty, on the reasoning
    that the token must be stale or forged — correct for a genuine miss, and
    exactly wrong for a database that was merely busy for a moment, which
    would sign a real person out for good. Callers distinguish the two by
    catching this; returning None for both is the bug this exists to prevent.
    """


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
            visits        INTEGER DEFAULT 0,
            email_opt_out INTEGER DEFAULT 0,     -- 1 = unsubscribed from all email
            last_digest   TEXT,                  -- when the weekly digest last sent them
            pay_nudge_sent TEXT,                 -- stamped once the lapsed-payer nudge sends
            stripe_customer_id     TEXT,
            stripe_subscription_id TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_accounts_token ON accounts(token)")
    # Safe migration for tables created before these columns existed.
    for col, decl in (("pro_until", "TEXT"), ("founding", "INTEGER DEFAULT 0"),
                      ("email_opt_out", "INTEGER DEFAULT 0"), ("last_digest", "TEXT"),
                      ("pay_nudge_sent", "TEXT"),
                      ("stripe_customer_id", "TEXT"), ("stripe_subscription_id", "TEXT")):
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
def sign_in(email: str, source: str = "signin",
            campaign: str = "") -> tuple[dict | None, bool]:
    """
    Find or create the account for this email.

    Returns (account, is_new). Also records them in people.py, so a tester who
    signs in is captured in the same place as everyone else and mirrors to the
    Google Sheet like any other signup.
    """
    email = (email or "").strip().lower()
    if not people.valid_email(email):
        return None, False

    try:
        return _sign_in_locked(email, source, campaign)
    except sqlite3.Error as e:
        # Same reasoning as by_token: a busy database is not a bad email
        # address, and the sign-in form must be able to tell the person to
        # try again rather than showing them a traceback.
        raise StoreUnavailable(str(e)) from e


def _sign_in_locked(email: str, source: str, campaign: str) -> tuple[dict | None, bool]:
    """The body of sign_in(), split out so one try/except covers all its SQL."""
    init()
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
    if row:
        conn.execute("UPDATE accounts SET last_seen=?, visits=visits+1 WHERE email=?",
                     (_now(), email))
        # An existing account arriving on a partner link still gets the offer.
        # Plenty of a partner's members will have looked at Nabbly before their
        # announcement went out, and telling those people "you signed up too
        # early, no Pro for you" is the opposite of what the collaboration is
        # for. Only ever extends: if they already have longer, theirs stands.
        grant = PARTNER_GRANTS.get((campaign or "").strip().lower())
        if grant:
            until = (datetime.now(timezone.utc)
                     + timedelta(days=grant["days"])).isoformat(timespec="seconds")
            have = _parse(row["pro_until"] if "pro_until" in row.keys() else None)
            if not have or have < _parse(until):
                conn.execute("UPDATE accounts SET pro_until=? WHERE email=?",
                             (until, email))
        conn.commit()
        acc = dict(conn.execute("SELECT * FROM accounts WHERE email=?",
                                (email,)).fetchone())
        conn.close()
        if grant:
            _mirror(email)
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
    # A partner's group gets Pro for the length of their test, and — importantly
    # — does NOT consume the founding-50 slots. Those were meant as a thank-you
    # to whoever found Nabbly on their own; a single partner announcement could
    # otherwise empty all fifty in an afternoon, spending the gesture on people
    # who were already being given Pro by the partner deal anyway.
    grant = PARTNER_GRANTS.get((campaign or "").strip().lower())
    if grant:
        founding = 0
        pro_until = (datetime.now(timezone.utc)
                     + timedelta(days=grant["days"])).isoformat(timespec="seconds")
    else:
        # The first FOUNDING_LIMIT people to sign up get ~2 months of Pro as a
        # thank-you for taking the early chance — not because they asked, but as
        # a gift. Everyone after that lands on Free and can start the opt-in
        # trial when they choose. (The count is a snapshot; a rare simultaneous
        # signup could put us a hair over 50, which is fine — erring generous.)
        existing = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        founding = 1 if existing < FOUNDING_LIMIT else 0
        pro_until = (datetime.now(timezone.utc)
                     + timedelta(days=FOUNDING_DAYS)).isoformat(timespec="seconds") \
            if founding else ""
    # last_digest starts at signup, not empty. Empty means "never sent", which
    # weekly_digest reads as due immediately — so a brand new account would get
    # a welcome email and then a full weekly digest within the hour. Starting
    # the clock here means their first digest lands a week after they join,
    # which is what "weekly" is supposed to mean.
    conn.execute(
        "INSERT INTO accounts (email, token, created, last_seen, trial_start, "
        "pro_until, founding, plan, last_alert_id, visits, last_digest) "
        "VALUES (?,?,?,?,'',?,?,'free',?,1,?)",
        (email, token, now, now, pro_until, founding, watermark, now))
    conn.commit()
    acc = dict(conn.execute("SELECT * FROM accounts WHERE email=?",
                            (email,)).fetchone())
    conn.close()
    _mirror(email)
    try:
        people.add_person(email, source=source, campaign=campaign)
    except Exception:
        pass          # a webhook hiccup must never block someone signing in
    try:
        import mailer
        subject, html_body, text_body = mailer.welcome_email(
            email, "", bool(founding), email_token(token))
        mailer.send(email, subject, html_body, text_body)
    except Exception:
        pass          # a mail-provider hiccup must never block someone signing in
    return acc, True


def by_token(token: str) -> dict | None:
    """
    The account this URL token belongs to, or None if no account matches.

    Raises StoreUnavailable if the database itself couldn't be read — see that
    class for why the caller must not treat the two outcomes the same way.
    This runs on EVERY rerun for every signed-in visitor (Streamlit re-executes
    the whole script on each click), so it is the single most-called write in
    the app and the first thing that touches SQLite on a page load.
    """
    token = (token or "").strip()
    if not token:
        return None
    conn = None
    try:
        init()
        conn = _connect()
        row = conn.execute("SELECT * FROM accounts WHERE token=?",
                           (token,)).fetchone()
        if row:
            conn.execute(
                "UPDATE accounts SET last_seen=?, visits=visits+1 WHERE token=?",
                (_now(), token))
            conn.commit()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise StoreUnavailable(str(e)) from e
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass


def _founding_rank(acc: dict) -> int | None:
    """
    This account's place in line among the first FOUNDING_LIMIT signups — #7,
    not just "founding". Computed from `created` order at read time rather
    than stored on the row, so it stays correct even after a wipe-and-
    rehydrate reorders when rows were last written.

    `rowid` BREAKS TIES, and it has to. `_now()` truncates to whole seconds,
    and the accounts table is keyed on email with no autoincrement id, so two
    people signing up in the same second got byte-identical `created` strings
    — and `created <= ?` alone then counted BOTH of them, handing the same
    number to two different people while skipping the next one entirely.
    That isn't hypothetical at launch: an announcement to a whole membership
    is exactly a burst of same-second signups. rowid is monotonic per insert,
    so (created, rowid) is a total order and every rank is unique.
    """
    if not acc.get("founding"):
        return None
    # Degrades to "no number" rather than taking the page down. status() calls
    # this, status() runs before anything paints, and it is NOT inside any
    # try/except — so a locked database here meant a founding member got a bare
    # traceback instead of a dashboard. by_token() and sign_in() were both
    # wrapped for exactly this; this function was added in the same change and
    # missed it. A missing badge is a rounding error next to a broken page.
    conn = None
    try:
        conn = _connect()
        row = conn.execute("SELECT rowid FROM accounts WHERE email=?",
                           (acc.get("email") or "",)).fetchone()
        if not row:
            return None
        n = conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE founding=1 AND "
            "(created < ?1 OR (created = ?1 AND rowid <= ?2))",
            (acc.get("created") or "", row[0])).fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
    return n or 1


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
                "trialed": False, "can_trial": False, "founding": False,
                "founding_rank": None}

    plan = (acc.get("plan") or "free").lower()
    founding = bool(acc.get("founding"))
    deadline = _pro_deadline(acc)            # when time-boxed Pro ends, or None
    trialed = deadline is not None           # has had some time-boxed Pro grant
    base = {"signed_in": True, "plan": plan, "email": acc.get("email", ""),
            "days_left": 0, "expired": False, "trialed": trialed,
            "founding": founding, "founding_rank": _founding_rank(acc),
            "can_trial": False,
            # A real Stripe subscription behind this account, vs. a manual/
            # founding/partner grant — plan_card uses this to tell a paying
            # member "you're on the $12/mo plan" instead of "on the house".
            "paid": bool(acc.get("stripe_subscription_id"))}

    # The founder's own account: Pro for life, not a 60-day clock. Checked
    # here rather than written once as plan='pro' in the database, so it
    # holds even if this row is ever recreated (a fresh sign-in token, a
    # schema reset) instead of depending on a value something else could
    # overwrite.
    if is_owner(acc.get("email")):
        return {**base, "plan": "pro", "pro": True}

    if plan == "pro":                        # a manual/permanent grant
        return {**base, "pro": True}
    if deadline:                             # founding gift or an opted-in trial
        left = deadline - datetime.now(timezone.utc)
        if left.total_seconds() > 0:
            days = int(max(0, -(-left.total_seconds() // 86400)))   # round up
            # `ends` is the REAL deadline, carried through so callers don't
            # have to reconstruct it from days_left. days_left rounds UP (59.2
            # days reads as 60), so `now + days_left` lands a day late — which
            # is exactly how the plan card came to promise "ends 30 September"
            # for a grant that actually stops on the 29th. Rounding up is right
            # for "how long have I got"; it is wrong for a date.
            return {**base, "pro": True, "days_left": days, "ends": deadline}
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


def downgrade(email: str) -> bool:
    """
    Move someone back to Free, at their own request.

    Clears pro_until and the founding flag as well as the plan, because
    status() reads the deadline first — leaving a live pro_until behind would
    keep handing them Pro after they asked to leave it, which is the kind of
    "we heard you and did nothing" bug people don't report, they just distrust.
    """
    email = (email or "").strip().lower()
    if not email:
        return False
    init()
    conn = _connect()
    conn.execute("UPDATE accounts SET plan='free', pro_until=NULL, founding=0 "
                 "WHERE email=?", (email,))
    conn.commit()
    conn.close()
    _mirror(email)
    return True


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


def set_stripe_ids(email: str, customer_id: str, subscription_id: str):
    """Record which Stripe customer/subscription paid for this account, so a
    future reconciliation pass has something to look up."""
    if not email:
        return
    init()
    conn = _connect()
    conn.execute(
        "UPDATE accounts SET stripe_customer_id=?, stripe_subscription_id=? "
        "WHERE email=?",
        (customer_id or None, subscription_id or None, email.strip().lower()))
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


# ---------------------------------------------------------------------------
# Email support (welcome + weekly digest)
# ---------------------------------------------------------------------------
def set_last_digest(email: str, when: str):
    """Stamp when the weekly digest last sent this person, so a restart can't
    make weekly_digest.py think a week has passed and re-send early."""
    init()
    conn = _connect()
    conn.execute("UPDATE accounts SET last_digest=? WHERE email=?",
                 (when, email.strip().lower()))
    conn.commit()
    conn.close()
    _mirror(email)


def set_pay_nudge_sent(email: str, when: str):
    """Stamp the moment the lapsed-payer nudge sends this account, so it can
    never fire twice for the same person — see lapsed_nudge.py."""
    init()
    conn = _connect()
    conn.execute("UPDATE accounts SET pay_nudge_sent=? WHERE email=?",
                 (when, email.strip().lower()))
    conn.commit()
    conn.close()
    _mirror(email)


def email_token(signin_token: str) -> str:
    """
    A per-account identifier safe to put in an email. NOT a way to sign in.

    Every link in the welcome email and the weekly digest used to carry the
    real sign-in token, because that token was the only per-account handle we
    had. That meant forwarding one interesting gig from a digest handed over
    the whole account, and any corporate link scanner that rewrites and logs
    URLs (Defender Safe Links and friends) captured a live credential.

    This is derived from the sign-in token by HMAC, so it identifies the
    account for the two things an email actually needs — unsubscribing, and
    attributing an apply click — while being useless for signing in:
    _resolve_account() only ever accepts the real token, and this cannot be
    reversed into one.

    Rotating someone's sign-in token rotates this with it, which is the
    behaviour you want: old email links stop resolving too.
    """
    if not signin_token:
        return ""
    key = (os.environ.get("AUTH_COOKIE_SECRET") or "nabbly-email-token").encode()
    return hmac.new(key, f"email:{signin_token}".encode(),
                    hashlib.sha256).hexdigest()[:32]


def by_email_token(tok: str) -> dict | None:
    """The account an email-link token belongs to, or None.

    Linear scan on purpose: this is a handful of accounts, it runs only on an
    unsubscribe or an apply click from an email, and storing the derived value
    would just be a second secret to keep in sync with the first.
    """
    tok = (tok or "").strip()
    if not tok:
        return None
    for acc in all_accounts():
        if secrets.compare_digest(email_token(acc.get("token", "")), tok):
            return acc
    return None


def backfill_last_digest() -> int:
    """
    Start the weekly-digest clock for accounts that predate the feature.

    last_digest was added to a table full of existing rows, so every one of
    them reads as "never sent" and weekly_digest._due() says yes to all of
    them at once. Stamping them with now means their first digest lands a
    normal week out instead of arriving as one unannounced blast the moment
    the feature deploys. Returns how many were stamped; idempotent, so the
    second call finds nothing.
    """
    init()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT email FROM accounts WHERE COALESCE(last_digest, '') = ''"
        ).fetchall()
        if not rows:
            return 0
        conn.execute("UPDATE accounts SET last_digest=? "
                     "WHERE COALESCE(last_digest, '') = ''", (_now(),))
        conn.commit()
        n = len(rows)
    finally:
        conn.close()
    for r in rows:
        _mirror(r["email"])
    return n


# ---------------------------------------------------------------------------
# Sign-in codes — proving the address is actually theirs
# ---------------------------------------------------------------------------
# sign_in() takes an email and hands back that account, with nothing in between.
# That was a deliberate trade while this was an invited beta of one, and it is
# the wrong trade the moment strangers are on it: typing someone else's address
# signed you in AS them, with their profile, their saved drafts and their
# uploaded resume. A code emailed to the address closes that, because only the
# person reading that inbox can finish the sign-in.
#
# Deliberate choices, each one load-bearing:
#   * The code is STORED HASHED. A leaked database read shouldn't hand over live
#     sign-in codes any more than it should hand over passwords.
#   * Short life, single use, small attempt budget. A 6-digit code is only 10^6
#     wide, so the thing that actually protects it is that guessing is capped
#     and it dies quickly.
#   * Issuing is rate-limited per address, so nobody can be mailbombed by
#     someone pounding "send me a code" with their address in the box.
CODE_TTL_MIN = 10          # how long a code stays good
CODE_MAX_ATTEMPTS = 5      # wrong guesses before a code is burned
CODE_MAX_PER_HOUR = 5      # codes we'll send one INBOX in an hour
# A ceiling across everyone, not per address. The per-address limit stops one
# person being mailbombed; this stops the whole mail quota being drained. That
# matters more than it looks: sign-in IS email now, so an exhausted quota does
# not merely stop codes — nobody can get into Nabbly at all until it resets.
# Set well above a real launch day (a 100-person group signing up inside an
# hour is ~200 emails counting welcomes) and well below anything a script
# would reach.
CODE_MAX_PER_HOUR_GLOBAL = 300
_GLOBAL_KEY = "_all"       # the bucket the global counter lives in


def _inbox_key(email: str) -> str:
    """
    Collapse the addresses that reach ONE inbox down to one rate-limit key.

    Limiting on the literal string was no limit at all: you+1@gmail.com,
    you+2@gmail.com and y.o.u@gmail.com are three different strings and one
    mailbox, so five-per-hour became five-per-variation and the mailbomb it
    was written to stop went straight through.

    Everything after a + is a tag and is dropped, which every major provider
    supports. Dots are only meaningless at Google, so they are stripped there
    and nowhere else — dots DO distinguish real mailboxes at other hosts, and
    over-collapsing would rate-limit two unrelated colleagues as one person.
    """
    email = (email or "").strip().lower()
    if "@" not in email:
        return email
    local, _, domain = email.partition("@")
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return f"{local}@{domain}"


def _code_hash(email: str, code: str) -> str:
    """Salted by the email so the same digits for two people don't collide,
    and so a stolen hash can't be replayed against a different address."""
    return hashlib.sha256(f"{email.strip().lower()}:{code}".encode()).hexdigest()


def _init_codes(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_codes (
            email     TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            created   TEXT NOT NULL,
            expires   TEXT NOT NULL,
            attempts  INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_code_sends (
            email TEXT NOT NULL,
            ts    TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_code_sends ON login_code_sends(email, ts)")


def issue_code(email: str) -> tuple[str, str]:
    """
    Mint a sign-in code for this address.

    Returns (code, error). On success the code is the plaintext to email and
    error is ""; on refusal the code is "" and error is something safe to show.
    Only ever one live code per address — asking again replaces the old one, so
    a forwarded or shoulder-surfed code stops working the moment a new one is
    requested.
    """
    email = (email or "").strip().lower()
    if not people.valid_email(email):
        return "", "That doesn't look like an email address."
    init()
    conn = _connect()
    try:
        _init_codes(conn)
        now = datetime.now(timezone.utc)
        # Rate limit first, before anything is written or sent.
        # timespec matches how the rows are stored, so the string comparison
        # covers a true hour rather than an hour minus some microseconds.
        hour_ago = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute("DELETE FROM login_code_sends WHERE ts < ?", (hour_ago,))
        # Per inbox, keyed on the collapsed form so + tags and Gmail dots
        # cannot be used to get five fresh codes per spelling.
        inbox = _inbox_key(email)
        recent = conn.execute(
            "SELECT COUNT(*) FROM login_code_sends WHERE email=? AND ts>=?",
            (inbox, hour_ago)).fetchone()[0]
        if recent >= CODE_MAX_PER_HOUR:
            return "", "That's a lot of codes. Try again in an hour."
        # And across everyone. Without this a script walking arbitrary
        # addresses never trips the per-inbox limit at all, drains the day's
        # mail quota in under a minute, and locks every real person out of
        # signing in — because sign-in is email.
        total = conn.execute(
            "SELECT COUNT(*) FROM login_code_sends WHERE email=? AND ts>=?",
            (_GLOBAL_KEY, hour_ago)).fetchone()[0]
        if total >= CODE_MAX_PER_HOUR_GLOBAL:
            print(f"  accounts: GLOBAL code cap hit ({total} in the last hour) "
                  f"— refusing new sign-in codes", flush=True)
            return "", "Sign-in is busy right now. Try again in a few minutes."
        # secrets, not random: this is a credential.
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires = (now + timedelta(minutes=CODE_TTL_MIN)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO login_codes (email, code_hash, created, expires, attempts) "
            "VALUES (?,?,?,?,0) "
            "ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash, "
            "  created=excluded.created, expires=excluded.expires, attempts=0",
            (email, _code_hash(email, code), now.isoformat(timespec="seconds"), expires))
        # Two ledger rows per send: one against the collapsed inbox, one
        # against the global bucket. The code row itself stays keyed on the
        # exact address the person typed, because that is what they will be
        # verifying against.
        _stamp = now.isoformat(timespec="seconds")
        conn.executemany("INSERT INTO login_code_sends (email, ts) VALUES (?,?)",
                         [(inbox, _stamp), (_GLOBAL_KEY, _stamp)])
        conn.commit()
        return code, ""
    finally:
        conn.close()


def check_code(email: str, code: str) -> tuple[bool, str]:
    """
    Is this the live code for this address? Consumes it on success.

    Returns (ok, error). Every failure path burns an attempt, so guessing is
    bounded whether the code is wrong, expired or already used.
    """
    email = (email or "").strip().lower()
    code = (code or "").strip().replace(" ", "")
    init()
    conn = _connect()
    try:
        _init_codes(conn)
        row = conn.execute("SELECT * FROM login_codes WHERE email=?",
                           (email,)).fetchone()
        if not row:
            return False, "Ask for a new code."
        if _parse(row["expires"]) and _parse(row["expires"]) < datetime.now(timezone.utc):
            conn.execute("DELETE FROM login_codes WHERE email=?", (email,))
            conn.commit()
            return False, "That code expired. Ask for a new one."
        if int(row["attempts"]) >= CODE_MAX_ATTEMPTS:
            conn.execute("DELETE FROM login_codes WHERE email=?", (email,))
            conn.commit()
            return False, "Too many tries. Ask for a new code."
        # compare_digest, not ==: a plain comparison leaks how much of the hash
        # matched through how long it took to fail.
        if not secrets.compare_digest(row["code_hash"], _code_hash(email, code)):
            conn.execute("UPDATE login_codes SET attempts = attempts + 1 WHERE email=?",
                         (email,))
            conn.commit()
            left = CODE_MAX_ATTEMPTS - int(row["attempts"]) - 1
            return False, ("That code isn't right." if left > 0
                          else "Too many tries. Ask for a new code.")
        # Single use: the code dies the moment it works.
        conn.execute("DELETE FROM login_codes WHERE email=?", (email,))
        conn.commit()
        return True, ""
    finally:
        conn.close()


def unsubscribe(tok: str) -> bool:
    """
    Opt this account out of every email. Takes an EMAIL token, not a sign-in
    token — see email_token() for why a link that travels in a mailbox must
    not be a credential.

    Applies to every email (welcome, weekly digest), not just whichever one
    carried the link; there's one opt-out per person, not one per email type,
    because "stop only the digest but keep the welcome email" isn't a real
    preference anyone has and a second toggle would just be a second thing to
    explain.
    """
    acc = by_email_token(tok)
    if not acc:
        return False
    email = acc["email"]
    init()
    conn = _connect()
    conn.execute("UPDATE accounts SET email_opt_out=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()
    _mirror(email)
    return True


# Owner accounts get the admin panel just by being signed in, no ?admin= key.
# Stored as SHA-256 rather than plaintext because this repo is public and an
# email in source is an email in every scraper's list. Add more via the
# ADMIN_EMAILS env var (comma separated) without touching code.
_OWNER_HASHES = {
    "d0aca616576886f35178b7693756b1aa408ce73e1d585d474009a54cc6e2569d",
}


def is_owner(email: str | None) -> bool:
    """True if this address may see the admin panel."""
    e = (email or "").strip().lower()
    if not e:
        return False
    extra = {x.strip().lower()
             for x in os.environ.get("ADMIN_EMAILS", "").split(",") if x.strip()}
    if e in extra:
        return True
    return hashlib.sha256(e.encode()).hexdigest() in _OWNER_HASHES


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

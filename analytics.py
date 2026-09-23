"""
analytics.py — who showed up, what they did, and who raised their hand.

Two jobs:

  1. VISITS   — count sessions and which views people open, so you can answer
                "did anyone actually come, and did they look around?"
  2. SIGNUPS  — capture an email plus the one question that matters:
                would you pay for this?

Deliberately NOT a third-party script. Streamlit strips <script> tags from the
main page, so Google Analytics and friends can't run there without ugly hacks.
Doing it in Python is boring, reliable, cookie-free, and it can see things an
off-the-shelf tracker never could (which category was clicked, whether someone
generated a draft).

WHERE IT LIVES: its own SQLite file, separate from the gig database, so
reseeding the gigs never wipes your signups.

IMPORTANT — surviving redeploys: on Render's free tier the disk is wiped every
deploy, so this data resets. Two ways to make it permanent:
  • set DATA_DIR to a mounted persistent disk (see paths.py), or
  • set SIGNUP_WEBHOOK_URL and every signup is also POSTed there the moment it
    happens (a Zapier/Make catch hook, a Google Apps Script, a form endpoint).
The webhook is the belt-and-braces option: even if the disk vanishes, the email
already left the building.
"""
import os
import re
import sqlite3
import threading as _threading
from datetime import datetime, timedelta, timezone

from paths import data_file

DB_PATH = data_file("nabbly_signals.db")

# Set this in Render → Environment to mirror every signup somewhere permanent.
WEBHOOK_URL = os.environ.get("SIGNUP_WEBHOOK_URL", "").strip()

# Visit ?admin=<key> to see the numbers. Set ADMIN_KEY in Render → Environment.
#
# NO DEFAULT, on purpose. This used to fall back to a literal string in this
# file, and this repo is public — so the admin panel, which lists signup
# addresses, everything people typed into the feedback box, their "would you
# pay" answers and a CSV export of the lot, was open to anyone who read the
# source and appended ?admin=<that string>. Verified open on the live site
# before this change.
#
# Empty means the ?admin= door is simply shut (app.py's IS_ADMIN requires a
# truthy key), which is the right default for a secret: absent, not guessable.
# The founder still gets in by being signed in on an owner account — see
# accounts.is_owner — so nothing is lost by leaving this unset.
ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init():
    """Create the two tables the first time we run. Safe to call every time."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      TEXT NOT NULL,
            session TEXT,
            event   TEXT NOT NULL,   -- 'session', 'view', 'click', 'signup'
            detail  TEXT             -- which view, which category, etc.
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signups (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            ts    TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pay   TEXT DEFAULT '',   -- 'yes' / 'maybe' / 'no'
            note  TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()


def track(event: str, detail: str = "", session: str = ""):
    """Record one thing that happened. Never allowed to break the page."""
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO events (ts, session, event, detail) VALUES (?,?,?,?)",
            (_now(), session, event, detail[:200]),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass  # analytics must never take the app down
    # Optional second destination, off unless POSTHOG_API_KEY is set. Mirrored
    # from here rather than from each call site so there is exactly one place
    # events leave the building, and so this file stays the source of truth.
    try:
        import telemetry
        # The app has no request path to pass — Streamlit routes with ?nav=,
        # and its events already name themselves ("view", "session", "ref").
        # Left blank rather than invented, so PostHog's URL column is honestly
        # empty for the app and populated for the board.
        telemetry.capture(event, detail, session)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Where the traffic came from
# ---------------------------------------------------------------------------
# Referrers arrive as full URLs; we only keep the host, and only long enough to
# answer "is anyone actually coming from Reddit". No paths, no query strings,
# nothing that could identify a person.
_OWN_HOSTS = ("nabbly.co", "localhost", "127.0.0.1", "onrender.com")


def referrer_label(referer: str) -> str:
    """'https://www.reddit.com/r/forhire/x' -> 'reddit.com'. '' -> 'Direct'."""
    ref = (referer or "").strip()
    if not ref:
        return "Direct"
    try:
        from urllib.parse import urlparse
        host = (urlparse(ref).hostname or "").lower().lstrip("www.")
    except Exception:
        return "Other"
    if not host:
        return "Direct"
    if any(host.endswith(h) for h in _OWN_HOSTS):
        return "Direct"          # a click from one Nabbly page to another
    return host[:60]


# ---------------------------------------------------------------------------
# Campaigns: "did that collaboration actually work?"
# ---------------------------------------------------------------------------
# referrer_label answers "which site sent them", which blurs the moment a
# partner posts the link in three places, or a newsletter shows up as
# "Direct" because mail clients strip the referrer. A tag the partner carries
# in their own link answers it directly: ?ref=partnername.
#
# Kept deliberately small and dumb: a short slug, no free text. It ends up in
# a database and on an admin page, so it gets the same treatment as anything
# else arriving from a URL.
_CAMPAIGN_OK = re.compile(r"[^a-z0-9_-]+")


def campaign_label(raw: str) -> str:
    """'?ref=Sarah's Newsletter!' -> 'sarahs-newsletter'. '' if nothing usable."""
    tag = (raw or "").strip().lower()
    if not tag:
        return ""
    tag = _CAMPAIGN_OK.sub("-", tag).strip("-")
    return tag[:40]


def campaign_funnel(days: int = 30) -> list[dict]:
    """
    Per partner link: how many landed, and how many of them signed up.

    Visits alone can't tell you whether a collaboration worked — a thousand
    people bouncing looks identical to a thousand people arriving. Sessions
    come from the events table, signups from people.campaign, joined on the
    tag itself.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    out = {}
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT detail AS tag, COUNT(DISTINCT session) AS n FROM events "
            "WHERE event='campaign' AND ts >= ? AND detail != '' "
            "GROUP BY detail", (since,)).fetchall()
        conn.close()
        for r in rows:
            out[r["tag"]] = {"tag": r["tag"], "sessions": int(r["n"]), "signups": 0}
    except sqlite3.Error:
        return []
    try:
        import people
        conn = sqlite3.connect(people.DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT campaign AS tag, COUNT(*) AS n FROM people "
            "WHERE COALESCE(campaign,'') != '' AND created >= ? "
            "GROUP BY campaign", (since,)).fetchall()
        conn.close()
        for r in rows:
            out.setdefault(r["tag"], {"tag": r["tag"], "sessions": 0, "signups": 0})
            out[r["tag"]]["signups"] = int(r["n"])
    except Exception:
        pass
    for v in out.values():
        v["rate"] = (100 * v["signups"] / v["sessions"]) if v["sessions"] else 0.0
    return sorted(out.values(), key=lambda d: -d["sessions"])


# ---------------------------------------------------------------------------
# Unmet demand: what people typed that the board barely had anything for
# ---------------------------------------------------------------------------
def search_misses(days: int = 30, limit: int = 40) -> list[dict]:
    """
    Searches that came back with ~nothing, grouped and counted.

    app.py logs one 'search_miss' event (the raw query as `detail`) the first
    time a search drops to 2 results or fewer in a session — see note()'s
    per-session dedup, so someone retyping the same bad query a few times
    only counts once. Grouping by the raw text is intentionally simple: no
    stemming or fuzzy merging, so "logo design" and "logo designer" show as
    two rows rather than risking two genuinely different asks getting
    silently folded into one.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT detail AS query, COUNT(*) AS n, MAX(ts) AS last_seen "
            "FROM events WHERE event='search_miss' AND ts >= ? AND detail != '' "
            "GROUP BY detail ORDER BY n DESC, last_seen DESC LIMIT ?",
            (since, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def device_label(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if not ua:
        return "Unknown"
    if any(k in ua for k in ("iphone", "android", "ipod", "mobile")):
        return "Mobile"
    if "ipad" in ua or "tablet" in ua:
        return "Tablet"
    return "Desktop"


def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match((email or "").strip()))


def add_signup(email: str, note: str = "") -> tuple:
    """
    Save an email. Returns (ok, message).

    A repeat email is treated as success, not an error — someone typing their
    address twice should not be told off.
    """
    email = (email or "").strip().lower()
    if not valid_email(email):
        return False, "That doesn't look like an email address."
    try:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO signups (ts, email, note) VALUES (?,?,?)",
            (_now(), email, note[:500]),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return False, "Couldn't save that just now. Try again in a moment."
    _mirror({"type": "signup", "email": email, "note": note, "at": _now()})
    return True, "You're on the list."


def set_pay_answer(email: str, answer: str):
    """Record the would-you-pay answer for someone who already left an email."""
    email = (email or "").strip().lower()
    try:
        conn = _connect()
        conn.execute("UPDATE signups SET pay = ? WHERE email = ?", (answer, email))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return
    _mirror({"type": "pay", "email": email, "pay": answer, "at": _now()})


def _mirror(payload: dict):
    """POST a copy somewhere permanent, if a webhook is configured."""
    if not WEBHOOK_URL:
        return
    try:
        import requests
        requests.post(WEBHOOK_URL, json=payload, timeout=6)
    except Exception:
        pass  # a dead webhook must never block a signup


def _count(conn, sql, *args):
    row = conn.execute(sql, args).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def stats() -> dict:
    """Everything the admin panel needs, in one trip."""
    out = {"sessions": 0, "sessions_24h": 0, "sessions_7d": 0, "views": [],
           "clicks": [], "signups": 0, "pay": {}, "started": ""}
    try:
        conn = _connect()
        day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
        week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")

        out["sessions"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events WHERE event='session'")
        out["sessions_24h"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts >= ?", day)
        out["sessions_7d"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts >= ?", week)
        out["views"] = [(r["detail"], r["n"]) for r in conn.execute(
            "SELECT detail, COUNT(*) n FROM events WHERE event='view' "
            "GROUP BY detail ORDER BY n DESC")]
        out["clicks"] = [(r["detail"], r["n"]) for r in conn.execute(
            "SELECT detail, COUNT(*) n FROM events WHERE event='click' "
            "GROUP BY detail ORDER BY n DESC LIMIT 15")]
        out["signups"] = _count(conn, "SELECT COUNT(*) FROM signups")
        out["pay"] = {r["pay"]: r["n"] for r in conn.execute(
            "SELECT pay, COUNT(*) n FROM signups WHERE pay != '' GROUP BY pay")}
        row = conn.execute("SELECT MIN(ts) t FROM events").fetchone()
        out["started"] = (row["t"] or "") if row else ""
        conn.close()
    except sqlite3.Error:
        pass
    # EVERYTHING ABOVE READS ONE SERVICE'S LOCAL DISK, which is why the admin
    # panel stopped moving on 2026-08-31: it was reading the Streamlit app's
    # table while every visitor was on the board, whose events never land
    # there. history() is the whole picture -- both services, all the days
    # that survived a deploy -- so the headline numbers come from it whenever
    # it knows more than the disk does.
    try:
        hist = history(3650)
        if hist:
            today = datetime.now(timezone.utc).date()
            week = (today - timedelta(days=7)).isoformat()
            out["sessions"] = max(out["sessions"],
                                  sum(r.get("sessions", 0) for _, r in hist))
            out["sessions_24h"] = max(
                out["sessions_24h"],
                sum(r.get("sessions", 0) for d, r in hist
                    if d == today.isoformat()))
            out["sessions_7d"] = max(
                out["sessions_7d"],
                sum(r.get("sessions", 0) for d, r in hist if d >= week))
            merged = {}
            for _, r in hist:
                merged = _merge_rollup(merged, r)
            if merged["views"]:
                out["views"] = sorted(merged["views"].items(),
                                      key=lambda x: -x[1])
            if merged["clicks"]:
                out["clicks"] = sorted(merged["clicks"].items(),
                                       key=lambda x: -x[1])[:15]
            if not out["started"]:
                out["started"] = hist[0][0]
    except Exception:
        pass          # the panel is better stale than broken
    return out


# ---------------------------------------------------------------------------
# Surviving a redeploy
# ---------------------------------------------------------------------------
# The events table lives on Render's disk, which is wiped on every deploy, so
# raw traffic history would reset each time you ship. Rather than write every
# page view straight to Supabase (a network round trip per view would slow the
# page down), we roll each day up into one small record and mirror that. Days
# are immutable once past, so re-sending today's rollup repeatedly is cheap and
# always correct.
_ANALYTICS_SCOPE = "_analytics"


def _day_bounds(day: str):
    return f"{day}T00:00:00+00:00", f"{day}T23:59:59+00:00"


def day_rollup(day: str) -> dict:
    """Everything that happened on one UTC day, as a small dict."""
    lo, hi = _day_bounds(day)
    out = {"sessions": 0, "views": {}, "clicks": {}, "refs": {}, "devices": {}}
    try:
        conn = _connect()
        out["sessions"] = _count(
            conn, "SELECT COUNT(DISTINCT session) FROM events "
                  "WHERE event='session' AND ts BETWEEN ? AND ?", lo, hi)
        for key, ev in (("views", "view"), ("clicks", "click"),
                        ("refs", "ref"), ("devices", "device")):
            out[key] = {r["detail"]: r["n"] for r in conn.execute(
                "SELECT detail, COUNT(*) n FROM events WHERE event=? "
                "AND ts BETWEEN ? AND ? GROUP BY detail ORDER BY n DESC LIMIT 25",
                (ev, lo, hi))}
        conn.close()
    except sqlite3.Error:
        pass
    return out


# ---------------------------------------------------------------------------
# THE BOARD'S OWN NUMBERS.
#
# track() above writes a row to local SQLite on the calling thread. That is
# fine for the Streamlit app and wrong for the board, which answers /gigs in
# 3-4ms and whose disk Render wipes on every deploy -- so web/main._ev() sends
# events to PostHog instead and never touches the events table here.
#
# The cost of that choice only showed up later: the admin panel reads THIS
# module, so when people moved from app.nabbly.co to board.nabbly.co (30 Aug
# to 1 Sep 2026) its traffic chart froze on 2026-08-31 and stayed there,
# showing a surface nobody visits while the real board went unmeasured.
#
# So the board keeps counters in memory and folds them into the durable store
# every refresh cycle. In memory because incrementing a dict costs nothing on
# a hot path; folded rather than written because the process can restart at
# any moment and a deploy must not reset the day to zero.
#
# UNDER ITS OWN KEY, "<day>#live", never the app's "<day>". flush() below
# recomputes a whole day from local SQLite and overwrites; this one adds a
# delta. Pointing both at one key would mean whichever ran last won, and the
# app -- which still runs this loop, and still has its old rows -- would
# silently erase the board's numbers. history() merges the pair on read.
_LIVE_SUFFIX = "#live"
_live_lock = _threading.Lock()
_live: dict = {}


def _live_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def bump(kind: str, key: str, n: int = 1):
    """Count one thing on the board. Never touches the disk or the network."""
    if not key:
        return
    try:
        with _live_lock:
            day = _live.setdefault(_live_day(), {})
            if kind == "sessions":
                day["sessions"] = day.get("sessions", 0) + n
            else:
                bucket = day.setdefault(kind, {})
                bucket[key[:60]] = bucket.get(key[:60], 0) + n
    except Exception:
        pass          # a counter must never stand between someone and a gig


def _merge_rollup(base: dict, extra: dict) -> dict:
    """base + extra, summing sessions and every per-key bucket."""
    out = {"sessions": 0, "views": {}, "clicks": {}, "refs": {}, "devices": {}}
    for src in (base or {}, extra or {}):
        out["sessions"] += int(src.get("sessions") or 0)
        for kind in ("views", "clicks", "refs", "devices"):
            for k, v in (src.get(kind) or {}).items():
                out[kind][k] = out[kind].get(k, 0) + int(v or 0)
    return out


def flush_live() -> int:
    """
    Fold the board's in-memory counters into the durable store. Returns days sent.

    Read-add-write rather than write: the stored day already holds everything
    counted before this process started, and a deploy in the middle of a busy
    afternoon must add to that rather than replace it.

    Counters are cleared only after the write is accepted. A failed write
    therefore costs nothing -- the same numbers are folded in on the next
    cycle, which is the behaviour the mirror-drift rule asks for everywhere
    else in this codebase.
    """
    import store
    if not store.enabled():
        return 0
    with _live_lock:
        pending = {d: r for d, r in _live.items() if r}
        _live.clear()
    if not pending:
        return 0
    sent = 0
    for day, delta in pending.items():
        key = f"{day}{_LIVE_SUFFIX}"
        try:
            current = store.get(_ANALYTICS_SCOPE, key) or {}
            if store.put(_ANALYTICS_SCOPE, key, _merge_rollup(current, delta)):
                sent += 1
                continue
        except Exception:
            pass
        # Put it back for the next cycle rather than dropping it.
        with _live_lock:
            _live[day] = _merge_rollup(_live.get(day, {}), delta)
    return sent


def flush(days_back: int = 2) -> int:
    """
    Mirror recent days to the durable store. Returns how many days were sent.

    Covers a couple of days rather than just today so a deploy that happens
    right after midnight doesn't strand yesterday's numbers on the dead disk.
    """
    import store
    if not store.enabled():
        return 0
    sent = 0
    today = datetime.now(timezone.utc).date()
    for back in range(days_back):
        day = (today - timedelta(days=back)).isoformat()
        roll = day_rollup(day)
        if roll["sessions"] or roll["views"]:
            if store.put(_ANALYTICS_SCOPE, day, roll):
                sent += 1
    return sent


def history(days: int = 30) -> list:
    """
    [(day, rollup)] oldest-first, merging the durable store with today's live
    local numbers so the newest day is never stale.
    """
    import store
    raw = store.list_scope(_ANALYTICS_SCOPE) or {}
    today = datetime.now(timezone.utc).date().isoformat()
    # Two writers, one scope: the app recomputes a whole day into "<day>", the
    # board adds deltas into "<day>#live". Kept apart while reading, because
    # they need opposite treatment for today (below), then folded per day.
    app_days: dict = {}
    board_days: dict = {}
    for key, roll in raw.items():
        if key.endswith(_LIVE_SUFFIX):
            day = key[: -len(_LIVE_SUFFIX)]
            board_days[day] = _merge_rollup(board_days.get(day, {}), roll)
        else:
            app_days[key] = _merge_rollup(app_days.get(key, {}), roll)
    # Today only. The app's local table holds the SAME events as its stored
    # "<day>" -- flush() recomputes the whole day -- so it replaces rather than
    # adds, or every read would count the app's day twice. The board's pending
    # counters are the opposite: increments not yet folded in, so they add.
    local = day_rollup(today)
    if local["sessions"] or local["views"]:
        app_days[today] = local
    with _live_lock:
        pending = dict(_live.get(today) or {})
    if pending:
        board_days[today] = _merge_rollup(board_days.get(today, {}), pending)
    saved = {d: _merge_rollup(app_days.get(d, {}), board_days.get(d, {}))
             for d in set(app_days) | set(board_days)}
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    return sorted(((d, r) for d, r in saved.items() if d >= cutoff),
                  key=lambda x: x[0])


def traffic_summary(days: int = 30) -> dict:
    """Totals across the retained history — what the admin panel charts."""
    hist = history(days)
    refs, devices, daily = {}, {}, []
    total = 0
    for day, r in hist:
        total += r.get("sessions", 0)
        daily.append({"day": day, "sessions": r.get("sessions", 0)})
        for k, v in (r.get("refs") or {}).items():
            refs[k] = refs.get(k, 0) + v
        for k, v in (r.get("devices") or {}).items():
            devices[k] = devices.get(k, 0) + v
    return {
        "daily": daily,
        "total_sessions": total,
        "refs": sorted(refs.items(), key=lambda x: -x[1]),
        "devices": sorted(devices.items(), key=lambda x: -x[1]),
        "days_kept": len(daily),
    }


def signup_rows() -> list:
    """Every signup, newest first — for the admin table and CSV export."""
    try:
        conn = _connect()
        rows = [dict(r) for r in conn.execute(
            "SELECT ts, email, pay, note FROM signups ORDER BY id DESC")]
        conn.close()
        return rows
    except sqlite3.Error:
        return []

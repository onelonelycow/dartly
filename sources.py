"""
sources.py — pulls raw "who's hiring" posts from many public sources.

Every source returns a list of plain dicts in the same shape:
  {source, source_id, url, title, body, posted_at}

All sources here are public APIs/feeds that need no login or API key.
Turn sources on/off in config.ENABLE_SOURCES.
"""
import re
import time
import html as _html
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests
import functools

import feedparser

import config

HEADERS = {"User-Agent": "nabbly/0.1 (public job & gig aggregator)"}
TIMEOUT = 25


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
# UTF-8 sequences that got read as latin-1: a lead byte (C2-DF for 2-byte chars,
# E0-EF for 3-byte) followed by continuation bytes, all in \x80-\xbf.
_MOJIBAKE_RE = re.compile("[\xc2-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}")


def _redecode(m):
    try:
        return m.group(0).encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return m.group(0)


def _fix_mojibake(text: str) -> str:
    """Repair text whose UTF-8 bytes were mistakenly read as latin-1 (e.g. an
    en-dash '–' showing up as 'â\\x80\\x93', or 'á' as 'Ã¡'). Safe on clean text:
    a real 'â'/'Ã' isn't followed by continuation bytes, so it won't match."""
    if not any(c in text for c in ("Ã", "â", "Â")):
        return text
    # Whole-string round-trip first: cleanest when the entire value was mangled.
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        if "â" not in fixed and "Ã" not in fixed:
            return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    # Otherwise re-decode each mangled sequence in place (handles partial mangle
    # and any character — accents, dashes, quotes — without a hand-maintained list).
    return _MOJIBAKE_RE.sub(_redecode, text)


# RemoteOK ends every listing with an anti-scraping block ("Please mention the
# word X and tag R…") followed by an SEO keyword dump. It always runs to the end
# of the description and is pure noise to a reader, so we cut from there on.
BOILERPLATE = re.compile(r"\s*please mention the word\b.*$", re.I | re.S)


def _strip(text) -> str:
    """
    Feed text -> clean prose.

    ORDER MATTERS, and it was wrong: this stripped tags first and unescaped
    second. A feed that sends its HTML escaped ("&lt;p&gt;About us&lt;/p&gt;")
    survives the tag regex untouched — there are no real angle brackets yet —
    and then unescape turns it into "<p>About us</p>" AFTER the only step that
    would have removed it. 310 listings were showing raw <h1>/<p>/&nbsp; in
    their description because of it.

    Unescape first, then strip. Twice, because some feeds double-encode.
    """
    if not text:
        return ""
    text = _fix_mojibake(str(text))
    for _ in range(3):
        unescaped = _html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = re.sub(r"<[^>]+>", " ", text)
    text = BOILERPLATE.sub("", text)
    # \xa0 (from &nbsp;) is whitespace to Python's \s, so this folds it away too.
    return re.sub(r"\s+", " ", text).strip()


# Some sources (e.g. Freelancer.com) append a timestamp to the title, like
# "... - 20/07/2026 11:00 EDT". Strip that trailing date/time for clean titles.
_TITLE_TS = re.compile(
    r"\s*[-–—]\s*\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*[A-Za-z]{0,4}\s*$")


def _clean_title(text: str) -> str:
    return _TITLE_TS.sub("", _strip(text)).strip()


# Every source carries two kinds of text: the description a HUMAN should read,
# and machine hints (skill tags, salary, categories) that only the classifier
# and the keyword search care about. Gluing them together made previews read
# like "...a set of minim Graphic Design Logo Design Photoshop $20 - $250".
# We still keep both in one column, but separate them with an invisible
# character so the preview can show only the human half. See display_body().
HINT_SEP = "\x1f"


def _body(human, *hints) -> str:
    """Human description first, machine hints after an invisible separator."""
    human = _strip(human or "")
    tail = _strip(" ".join(str(h) for h in hints if h))
    return f"{human}{HINT_SEP}{tail}" if tail else human


def _epoch_to_iso(epoch):
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()
    except Exception:
        return None


def to_iso(value):
    """
    Any date a feed hands us -> one ISO 8601 string (or '').

    THIS IS NOT COSMETIC. posted_at is a TEXT column and the board sorts with
    "ORDER BY COALESCE(posted_at, fetched_at) DESC", which on text is an
    alphabetical sort. Feeds hand back RFC 2822 ("Wed, 24 Jun 2026 22:25:04
    +0000"), and sorting those strings sorts by the WEEKDAY NAME: every "Wed"
    gig outranks every "Thu" one, whatever year it's from. The live board had a
    January 2024 post sitting at the top of "Fresh off the boards" because of
    it, and people were clicking through to listings that closed months ago.

    Everything goes through here now, so the column holds one comparable
    format and the sort means what it says.
    """
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return _epoch_to_iso(value) or ""
    s = str(value).strip()
    if not s:
        return ""
    # Already ISO-ish (what our own rows and a few APIs use).
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).isoformat()
    except ValueError:
        pass
    # RFC 2822, the RSS default: "Wed, 24 Jun 2026 22:25:04 +0000".
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(s)
        if d:
            return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).isoformat()
    except Exception:
        pass
    # A few feeds send a bare date, or an epoch as a string.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    try:
        return _epoch_to_iso(float(s)) or ""
    except (TypeError, ValueError):
        return ""


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    # These APIs serve UTF-8 JSON; force it so responses that omit their charset
    # don't get decoded as latin-1 (which turns em-dashes etc. into mojibake).
    r.encoding = "utf-8"
    return r


# ---------------------------------------------------------------------------
# Reddit — public [Hiring] gig posts via search RSS (throttled, so paced)
# ---------------------------------------------------------------------------
def fetch_reddit() -> list[dict]:
    query = "flair:Hiring OR flair:Task"
    posts = {}
    for i, sub in enumerate(config.SUBREDDITS):
        url = (f"https://old.reddit.com/r/{sub}/search.rss"
               f"?q={quote_plus(query)}&restrict_sr=on&sort=new&limit=50&t=month")
        resp = None
        for attempt in range(3):
            try:
                resp = _get(url)
            except Exception as e:
                print(f"  ! reddit r/{sub}: {e}"); break
            if resp.status_code == 200:
                break
            if resp.status_code == 429:
                time.sleep(8 * (attempt + 1)); continue
            break
        if not resp or resp.status_code != 200:
            print(f"  ! reddit r/{sub}: HTTP {resp.status_code if resp else 'ERR'}")
            continue
        for e in feedparser.parse(resp.content).entries:
            link = e.get("link", "")
            sid = e.get("id", link)
            if sid in posts:
                continue
            posts[sid] = {
                "source": "reddit", "source_id": sid, "url": link,
                "title": _strip(e.get("title", "")),
                "body": _strip(e.get("summary", "")),
                "posted_at": to_iso(e.get("updated") or e.get("published")),
            }
        if i < len(config.SUBREDDITS) - 1:
            time.sleep(18)
    return list(posts.values())


# ---------------------------------------------------------------------------
# RemoteOK — https://remoteok.com/api  (JSON list; first item is metadata)
# ---------------------------------------------------------------------------
def fetch_remoteok() -> list[dict]:
    r = _get("https://remoteok.com/api")
    if r.status_code != 200:
        print(f"  ! remoteok: HTTP {r.status_code}"); return []
    out = []
    for it in r.json():
        if not isinstance(it, dict) or not it.get("id"):
            continue
        salary = ""
        if it.get("salary_min"):
            salary = f"${it.get('salary_min')} - ${it.get('salary_max','')} /year"
        tags = " ".join(it.get("tags", []) or [])
        out.append({
            "source": "remoteok", "source_id": str(it["id"]),
            "url": it.get("url") or it.get("apply_url", ""),
            "title": f"{it.get('position','')} — {it.get('company','')}".strip(" —"),
            "body": _body(it.get("description", ""), tags, salary),
            "posted_at": to_iso(it.get("date")),
        })
    return out


# ---------------------------------------------------------------------------
# Remotive — https://remotive.com/api/remote-jobs
# ---------------------------------------------------------------------------
def fetch_remotive() -> list[dict]:
    r = _get("https://remotive.com/api/remote-jobs")
    if r.status_code != 200:
        print(f"  ! remotive: HTTP {r.status_code}"); return []
    out = []
    for it in r.json().get("jobs", []):
        out.append({
            "source": "remotive", "source_id": str(it.get("id")),
            "url": it.get("url", ""),
            "title": f"{it.get('title','')} — {it.get('company_name','')}".strip(" —"),
            "body": _body(it.get("description", ""), it.get("category", ""),
                          it.get("salary", ""), " ".join(it.get("tags", []) or [])),
            "posted_at": to_iso(it.get("publication_date")),
        })
    return out


# ---------------------------------------------------------------------------
# Arbeitnow — https://www.arbeitnow.com/api/job-board-api
# ---------------------------------------------------------------------------
def fetch_arbeitnow() -> list[dict]:
    r = _get("https://www.arbeitnow.com/api/job-board-api")
    if r.status_code != 200:
        print(f"  ! arbeitnow: HTTP {r.status_code}"); return []
    out = []
    for it in r.json().get("data", []):
        out.append({
            "source": "arbeitnow", "source_id": str(it.get("slug")),
            "url": it.get("url", ""),
            "title": f"{it.get('title','')} — {it.get('company_name','')}".strip(" —"),
            "body": _body(it.get("description", ""),
                          " ".join(it.get("tags", []) or []),
                          " ".join(it.get("job_types", []) or [])),
            "posted_at": _epoch_to_iso(it.get("created_at")),
        })
    return out


# ---------------------------------------------------------------------------
# Jobicy — https://jobicy.com/api/v2/remote-jobs
# ---------------------------------------------------------------------------
def fetch_jobicy() -> list[dict]:
    r = _get("https://jobicy.com/api/v2/remote-jobs?count=100")
    if r.status_code != 200:
        print(f"  ! jobicy: HTTP {r.status_code}"); return []
    out = []
    for it in r.json().get("jobs", []):
        salary = ""
        if it.get("annualSalaryMin"):
            salary = f"${it.get('annualSalaryMin')} - ${it.get('annualSalaryMax','')} /year"
        out.append({
            "source": "jobicy", "source_id": str(it.get("id")),
            "url": it.get("url", ""),
            "title": f"{it.get('jobTitle','')} — {it.get('companyName','')}".strip(" —"),
            "body": _body(f"{it.get('jobExcerpt','')} {it.get('jobDescription','')}",
                          " ".join(it.get("jobIndustry", []) or []), salary),
            "posted_at": to_iso(it.get("pubDate")),
        })
    return out


# ---------------------------------------------------------------------------
# Freelancer.com — active fixed-price projects (many small budgets)
# ---------------------------------------------------------------------------
def fetch_freelancer() -> list[dict]:
    url = ("https://www.freelancer.com/api/projects/0.1/projects/active/"
           "?limit=100&full_description=true&job_details=true")
    r = _get(url)
    if r.status_code != 200:
        print(f"  ! freelancer: HTTP {r.status_code}"); return []
    projs = r.json().get("result", {}).get("projects", [])
    out = []
    for p in projs:
        cur = (p.get("currency") or {}).get("code", "")
        b = p.get("budget") or {}
        lo, hi = b.get("minimum"), b.get("maximum")
        # Roughly dollar-equivalent currencies -> mark with $ so the budget
        # classifier reads the amount. Others (e.g. INR) are left unparsed.
        dollarish = {"USD", "EUR", "GBP", "CAD", "AUD", "NZD", "SGD", "CHF"}
        if lo is not None and cur in dollarish:
            budget = f"${int(lo)} - ${int(hi)} budget"
        elif lo is not None:
            budget = f"{lo} - {hi} {cur} budget"
        else:
            budget = ""
        jobs = " ".join(j.get("name", "") for j in (p.get("jobs") or []))
        # preview_description is Freelancer's own truncated summary — often
        # cut off mid-sentence ("...confirming the integrity of three footings
        # at"), which made "Show more" reveal nothing for a short posting since
        # there was nothing fuller stored to reveal. full_description=true is
        # already in the request URL above; description is the real full text.
        desc = p.get("description") or p.get("preview_description") or ""
        seo = p.get("seo_url")
        url_p = (f"https://www.freelancer.com/projects/{seo}" if seo
                 else f"https://www.freelancer.com/projects/{p.get('id')}")
        out.append({
            "source": "freelancer", "source_id": str(p.get("id")),
            "url": url_p,
            "title": _clean_title(p.get("title", "")),
            "body": _body(desc, jobs, budget),
            "posted_at": _epoch_to_iso(p.get("time_submitted")),
        })
    return out


# ---------------------------------------------------------------------------
# Working Nomads — JSON API. Its own apply link (/job/go/{id}/) 302s straight
# to the employer's real application page — no Working Nomads account needed,
# confirmed on a live listing before adding this source.
# ---------------------------------------------------------------------------
def fetch_workingnomads() -> list[dict]:
    r = _get("https://www.workingnomads.co/api/exposed_jobs/")
    if r.status_code != 200:
        print(f"  ! workingnomads: HTTP {r.status_code}"); return []
    out = []
    for j in r.json():
        url = j.get("url", "")
        if not url:
            continue
        out.append({
            "source": "workingnomads", "source_id": url,
            "url": url,
            "title": _clean_title(j.get("title", "")),
            "body": _body(j.get("description", ""), j.get("category_name", ""),
                          (j.get("tags") or "").replace(",", " "), j.get("location", "")),
            "posted_at": to_iso(j.get("pub_date")),
        })
    return out


# ---------------------------------------------------------------------------
# We Work Remotely — RSS
# ---------------------------------------------------------------------------
def fetch_weworkremotely() -> list[dict]:
    r = _get("https://weworkremotely.com/remote-jobs.rss")
    if r.status_code != 200:
        print(f"  ! weworkremotely: HTTP {r.status_code}"); return []
    out = []
    for e in feedparser.parse(r.content).entries:
        out.append({
            "source": "weworkremotely", "source_id": e.get("id", e.get("link", "")),
            "url": e.get("link", ""),
            "title": _strip(e.get("title", "")),
            "body": _strip(e.get("summary", "")),
            "posted_at": to_iso(e.get("published")),
        })
    return out


# ---------------------------------------------------------------------------
# Soundlister — audio/sound-design jobs, real and live, but not RSS-shaped
# like everything else here. Its feed publishes one roundup POST a week
# ("32 great new audio jobs at NBCUniversal, Warner Bros., …"), not one item
# per opening, so fetch_rss's one-item-per-entry assumption would file 32
# real jobs as a single garbled listing. This walks the feed for the recent
# roundup posts, then opens each post and pulls the "direct links" list each
# one publishes — a plain <li><a href=…>Title</a> at Company (Location)</li>
# block that links straight to the employer's own ATS (Greenhouse, Workday,
# Lever, …), not to Soundlister.
#
# Each post also leads with 2-3 "featured" jobs told as prose instead of that
# list — deliberately skipped. They're a minority of each post, and parsing
# free text for a title/company/link reliably is a different, harder problem
# than this list; missing a few featured slots is honest, guessing wrong
# isn't. See sources.py's file docstring for the same reasoning applied
# everywhere else here.
# ---------------------------------------------------------------------------
_SOUNDLISTER_JOB = re.compile(
    r'<li><strong><a href="([^"]+)"[^>]*>([^<]+)</a></strong>\s*at\s*'
    r'<strong>([^<]+)</strong>\s*\(([^)]*)\)</li>')


def fetch_soundlister() -> list[dict]:
    r = _get("https://soundlister.com/category/audio-jobs/feed/")
    if r.status_code != 200:
        print(f"  ! soundlister: HTTP {r.status_code}"); return []
    out = []
    for e in feedparser.parse(r.content).entries:
        post_url = e.get("link", "")
        if not post_url:
            continue
        posted = to_iso(e.get("published"))
        try:
            pr = _get(post_url)
        except Exception as ex:
            print(f"  ! soundlister post: {type(ex).__name__}"); continue
        if pr.status_code != 200:
            continue
        for job_url, title, company, location in _SOUNDLISTER_JOB.findall(pr.text):
            title, company, location = _strip(title), _strip(company), _strip(location)
            out.append({
                "source": "soundlister", "source_id": job_url,
                "url": job_url,
                "title": f"{title} — {company}" if company else title,
                "body": _body(f"{company} · {location}" if location else company),
                "posted_at": posted,
            })
    return out


# ---------------------------------------------------------------------------
# registry + orchestration
# ---------------------------------------------------------------------------
def fetch_rss(key: str) -> list[dict]:
    """
    Any board that publishes an RSS feed, driven entirely by config.

    Every other fetcher here is bespoke code for one site, which is fine for
    seven boards and hopeless for seventy. This one reads config.RSS_SOURCES,
    so adding a board is a line of config rather than a new function to write
    and keep alive.
    """
    spec = config.RSS_SOURCES.get(key) or {}
    url = spec.get("url")
    if not url:
        return []
    # Several feeds can belong to one board (per-category feeds), in which case
    # they share a source name and dedupe against each other on source_id.
    src = spec.get("source", key)
    r = _get(url)
    if r.status_code != 200:
        print(f"  ! {key}: HTTP {r.status_code}")
        return []
    out = []
    for e in feedparser.parse(r.content).entries:
        link = e.get("link", "")
        if not link:
            continue
        out.append({
            "source": src,
            "source_id": e.get("id") or link,
            "url": link,
            "title": _strip(e.get("title", "")),
            "body": _strip(e.get("summary", "") or e.get("description", "")),
            "posted_at": to_iso(e.get("published") or e.get("updated")),
        })
    return out


_FETCHERS = {
    "reddit": fetch_reddit,
    "freelancer": fetch_freelancer,
    "remoteok": fetch_remoteok,
    "remotive": fetch_remotive,
    "arbeitnow": fetch_arbeitnow,
    "jobicy": fetch_jobicy,
    "weworkremotely": fetch_weworkremotely,
    "workingnomads": fetch_workingnomads,
    "soundlister": fetch_soundlister,
}

# Bespoke fetchers (not config-only RSS_SOURCES entries) that still need the
# slow cadence below — soundlister posts weekly and costs ~10 requests per
# pull (the feed, then each roundup post), so running it every 2-minute cycle
# would hammer one host for content that hasn't moved.
_SLOW_BESPOKE = {"soundlister"}


# Category feeds are breadth, not freshness: the main board feed already brings
# the newest rows, and these backfill the verticals it under-reports. Polling 20
# of them on the 2-minute ingest loop would be several hundred requests an hour
# at one host, which is both rude and a good way to get blocked, so anything
# marked "slow" is fetched once every _SLOW_EVERY passes instead.
_SLOW_EVERY = 15          # ~every 30 min against a 2-minute loop
_rotate = 0               # where the next cycle starts (see fetch_all)
_cycle = 0


# One cycle may not run longer than this. 40 sources at a 25s timeout is a
# 16-minute worst case against a 120-second loop, so a bad afternoon upstream
# turns "every gig the moment it drops" into a cycle every quarter hour with
# nothing saying why.
_CYCLE_BUDGET_S = 90

# Per-source health, so a single feed going quiet is visible. Total volume
# barely moves when one of forty stops, which is what makes this the easiest
# kind of failure to miss: everything still works, just less.
#   best       most this source has ever returned — evidence it used to work
#   zero_run   consecutive cycles it was asked and returned nothing
#   err_run    consecutive cycles it raised
_HEALTH: dict[str, dict] = {}


def health() -> dict:
    """Per-source counters for the admin page. See _HEALTH."""
    return {k: dict(v) for k, v in _HEALTH.items()}


def _note_source(name: str, got: int, err: str = ""):
    import time as _t
    h = _HEALTH.setdefault(
        name, {"best": 0, "last": 0, "total": 0, "zero_run": 0, "err_run": 0,
               "last_ok": 0.0, "last_error": ""})
    h["last"] = got
    h["total"] += got
    h["best"] = max(h["best"], got)
    if err:
        h["err_run"] += 1
        h["last_error"] = err[:200]
        if h["err_run"] in (3, 12) or h["err_run"] % 50 == 0:
            print(f"  ! source {name} has failed {h['err_run']} cycles in a row: "
                  f"{h['last_error']}", flush=True)
        return
    h["err_run"] = 0
    h["last_error"] = ""
    if got:
        h["zero_run"] = 0
        h["last_ok"] = _t.time()
        return
    h["zero_run"] += 1
    # Zero is normal in a quiet cycle. Zero over and over from a source that
    # has produced before is a feed that changed shape and is now parsing to
    # nothing — no error, no gigs, no sign.
    if h["best"] and (h["zero_run"] in (12, 60) or h["zero_run"] % 200 == 0):
        print(f"  ! source {name} has returned nothing for {h['zero_run']} "
              f"cycles (best was {h['best']}) — it may have changed shape",
              flush=True)


def fetch_all() -> list[dict]:
    global _cycle
    _cycle += 1
    out = []
    started = time.time()

    # Resume where the last cycle ran out of time. The budget below cuts the
    # tail off, and a fixed order would cut the SAME sources every time,
    # forever — they would simply never be fetched, while the log still showed
    # a healthy cycle finding gigs. Starting at the first one we didn't get to
    # means the cut moves and every source gets its turn.
    global _rotate
    names = list(config.ENABLE_SOURCES)
    if names:
        _rotate %= len(names)
        names = names[_rotate:] + names[:_rotate]

    skipped = 0
    considered = 0
    for i, name in enumerate(names):
        if time.time() - started > _CYCLE_BUDGET_S:
            skipped = len(names) - i
            break
        considered = i + 1
        if name in _SLOW_BESPOKE and _cycle % _SLOW_EVERY != 1:
            continue
        fetcher = _FETCHERS.get(name)
        spec = config.RSS_SOURCES.get(name)
        if fetcher is None and spec is not None:
            if spec.get("slow") and _cycle % _SLOW_EVERY != 1:
                continue
            fetcher = functools.partial(fetch_rss, name)
        if not fetcher:
            continue
        print(f"Fetching {name}…")
        try:
            got = fetcher()
            _note_source(name, len(got))
        except Exception as e:
            print(f"  ! {name} failed: {e}")
            _note_source(name, 0, f"{type(e).__name__}: {e}")
            got = []
        print(f"  → {len(got)} from {name}")
        out += got

    # Advance by what we actually got through, so the deferred ones are first
    # in line next cycle rather than waiting for the rotation to come round.
    if names:
        _rotate = (_rotate + considered) % len(names)
    if skipped:
        print(f"  cycle hit its {_CYCLE_BUDGET_S}s budget — {skipped} source(s) "
              f"deferred; they lead the next pass", flush=True)
    return out

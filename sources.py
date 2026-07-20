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
import feedparser

import config

HEADERS = {"User-Agent": "dartly/0.1 (public job & gig aggregator)"}
TIMEOUT = 25


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _fix_mojibake(text: str) -> str:
    """Repair text whose UTF-8 bytes were mistakenly read as latin-1 (e.g. an
    en-dash '–' showing up as 'â\\x80\\x93'). Safe on clean text: real unicode
    isn't latin-1-encodable, so those strings are left untouched."""
    if "Ã" not in text and "â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _strip(text) -> str:
    if not text:
        return ""
    text = _fix_mojibake(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip()


def _epoch_to_iso(epoch):
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()
    except Exception:
        return None


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
                "posted_at": str(e.get("updated") or e.get("published") or ""),
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
            "body": _strip(f"{it.get('description','')} {tags} {salary}"),
            "posted_at": it.get("date"),
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
            "body": _strip(f"{it.get('description','')} "
                           f"{it.get('category','')} {it.get('salary','')} "
                           f"{' '.join(it.get('tags',[]) or [])}"),
            "posted_at": it.get("publication_date"),
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
            "body": _strip(f"{it.get('description','')} "
                           f"{' '.join(it.get('tags',[]) or [])} "
                           f"{' '.join(it.get('job_types',[]) or [])}"),
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
            "body": _strip(f"{it.get('jobExcerpt','')} {it.get('jobDescription','')} "
                           f"{' '.join(it.get('jobIndustry',[]) or [])} {salary}"),
            "posted_at": it.get("pubDate"),
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
        desc = p.get("preview_description") or ""
        seo = p.get("seo_url")
        url_p = (f"https://www.freelancer.com/projects/{seo}" if seo
                 else f"https://www.freelancer.com/projects/{p.get('id')}")
        out.append({
            "source": "freelancer", "source_id": str(p.get("id")),
            "url": url_p,
            "title": _strip(p.get("title", "")),
            "body": _strip(f"{desc} {jobs} {budget}"),
            "posted_at": _epoch_to_iso(p.get("time_submitted")),
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
            "posted_at": str(e.get("published") or ""),
        })
    return out


# ---------------------------------------------------------------------------
# registry + orchestration
# ---------------------------------------------------------------------------
_FETCHERS = {
    "reddit": fetch_reddit,
    "freelancer": fetch_freelancer,
    "remoteok": fetch_remoteok,
    "remotive": fetch_remotive,
    "arbeitnow": fetch_arbeitnow,
    "jobicy": fetch_jobicy,
    "weworkremotely": fetch_weworkremotely,
}


def fetch_all() -> list[dict]:
    out = []
    for name in config.ENABLE_SOURCES:
        fetcher = _FETCHERS.get(name)
        if not fetcher:
            continue
        print(f"Fetching {name}…")
        try:
            got = fetcher()
        except Exception as e:
            print(f"  ! {name} failed: {e}")
            got = []
        print(f"  → {len(got)} from {name}")
        out += got
    return out

"""
web/main.py — the public board, served as ordinary HTML over HTTP.

WHY THIS EXISTS. The Streamlit board re-executes a 5,500-line script for every
visitor on every interaction, holding the whole 53,525-gig board in memory to
show 25 cards. Measured: ~1s per render, ~190MB transient, and five concurrent
readers took a 2GB instance over its memory limit. Nothing about that is
fixable inside Streamlit — it is what "rerun the script" means.

Here a request is: run one indexed query, render 25 rows, return. No board in
memory, no per-visitor session, no websocket held open. The work is measured
in milliseconds and the memory in kilobytes.

Anonymous board views are IDENTICAL for every visitor, so they carry
Cache-Control and can be served by Render's CDN without this process running
at all. That is the part no amount of Streamlit tuning could ever buy.

Runs alongside the Streamlit app rather than replacing it — same database,
same db.py. Nothing here writes.
"""
import os
import secrets
import sys
import time

from datetime import datetime, timedelta, timezone

from urllib.parse import quote_plus

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import (http_exception_handler,
                                        request_validation_exception_handler)
from fastapi.exceptions import RequestValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import accounts  # noqa: E402
import analytics  # noqa: E402
import config  # noqa: E402
import googleauth  # noqa: E402
import location  # noqa: E402
import paths  # noqa: E402
import queries  # noqa: E402
import telemetry  # noqa: E402
import textfmt  # noqa: E402
import webauth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))

# Cache-buster for the shared stylesheet. Its mtime changes when
# tools/extract_css.py regenerates it, so a deploy busts the cache without
# anyone having to remember a version number.
try:
    CSS_V = str(int(os.path.getmtime(os.path.join(STATIC, "nabbly.css"))))
except OSError:
    CSS_V = "0"

# How recent counts as "New" on a card.
NEW_MINUTES = 90

# The fields someone can say they work in — same list the app offers.
ALL_SKILLS = list(config.JOB_TYPES.keys()) + ["Other / general"]

# The five families the Dashboard already sorts work into, reused so the
# profile groups fields the way the reader has already seen them rather than
# inventing a second taxonomy. Anything the table misses lands in "Everything
# else" instead of vanishing — today that is only "Other / general", but a new
# job type added to config would otherwise silently stop being selectable.
def _skill_groups():
    grouped, seen = [], set()
    for name, fields in getattr(config, "CATEGORY_GROUPS", {}).items():
        keep = [f for f in fields if f in ALL_SKILLS]
        if keep:
            grouped.append((name, keep))
            seen.update(keep)
    rest = [s for s in ALL_SKILLS if s not in seen]
    if rest:
        grouped.append(("Everything else", rest))
    return grouped


SKILL_GROUPS = _skill_groups()

# Where the Streamlit app lives, for the handful of pages still served there.
APP_URL = (os.environ.get("NABBLY_APP_URL")
           or "https://app.nabbly.co").rstrip("/")


def decorate(rows, ranked=False):
    """
    Add the two display strings a card needs, using the app's own formatters.

    Done here rather than in the template because both are real logic — a body
    preview that respects word boundaries, and a date phrased the way the app
    phrases it. textfmt is shared with app.py precisely so these read the same
    on both.
    """
    # "New" is a real column on the app's own table but the durable mirror does
    # not carry it, so it cannot survive the trip to this service. Derived from
    # recency instead, which is what the badge means to a reader anyway: this
    # landed while you were away.
    fresh_cut = (datetime.now(timezone.utc) - timedelta(minutes=NEW_MINUTES)).isoformat()
    for r in rows:
        r["is_new"] = bool((r.get("sort_at") or "") >= fresh_cut)
        r["preview"] = textfmt.smart_trim(
            textfmt.display_body(r.get("body")), target=620, hard=1200)
        # DOES THIS CARD ACTUALLY HAVE MORE TO SHOW? The body is clamped to
        # three lines in CSS and a "See more" was drawn on every card that had
        # a body at all — so on roughly half of them the label was there and
        # pressing it did nothing, because the text already fitted.
        #
        # CSS cannot measure text, so this is a character count, and it is
        # deliberately generous: below the threshold the clamp is released as
        # well as the label being dropped, so a body that would have wrapped
        # past three lines on a narrow phone is shown in full rather than
        # being cut off with no way to open it. Nothing is ever hidden without
        # a control, and no control is ever there without something behind it.
        r["clamped"] = len(r["preview"]) > 300
        # Falls back to fetched_at exactly as the SQL sort does. Without it a
        # gig with no posted_at reads "Posted recently", which sounds like
        # minutes ago and actually means we could not read a date.
        r["posted_line"] = (
            f"Posted {textfmt.human_time(r.get('posted_at') or r.get('sort_at'))}"
            f" · via {config.source_label(r.get('source') or '')}")
        # What applying actually involves, said BEFORE the click rather than
        # discovered after it. The source name already says which board; this
        # says whether you need an account there. A free signup and a paywall
        # are deliberately two different pills — they are not the same ask.
        src = (r.get("source") or "").lower()
        # Where the work can be done, using the app's own wording via
        # location.label(). Skipped when it would only repeat the source name —
        # a "Remote" pill on a gig from We Work Remotely says nothing the row
        # does not already say, which is the rule app.py follows.
        tag = {"onsite": bool(r.get("is_onsite")),
               "restrict": (r.get("restrict_cc") or "") or None,
               "worldwide": bool(r.get("is_worldwide")),
               "remote": bool(r.get("is_remote"))}
        lbl = location.label(tag)
        if lbl and not (src in getattr(config, "REMOTE_ONLY_SOURCES", ())
                        and lbl.strip().lower().endswith("remote")):
            r["loc_note"] = lbl
            r["loc_cls"] = "locoff" if tag["restrict"] else "loc"
        else:
            r["loc_note"] = ""
        for k in ("is_remote", "is_onsite", "restrict_cc", "is_worldwide"):
            r.pop(k, None)
        if (r.get("apply_email") or "").strip():
            r["apply_note"], r["apply_cls"] = "Apply by email", "match"
        elif src in getattr(config, "SUBSCRIPTION_REQUIRED_SOURCES", ()):
            r["apply_note"], r["apply_cls"] = "Paid subscription to apply", "urgent"
        elif src in getattr(config, "ACCOUNT_REQUIRED_SOURCES", ()):
            r["apply_note"], r["apply_cls"] = "Free account needed to apply", "locoff"
        else:
            r["apply_note"] = ""
        r.pop("apply_email", None)   # a real address; never reaches the page
        r.pop("body", None)      # not rendered raw; drop it before the template
    return rows


app = FastAPI(title="Nabbly board", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=STATIC), name="static")

# same_site="lax" is the CSRF defence for the POST routes below: a form on
# someone else's site cannot make the browser attach this cookie. https_only
# is off in local dev because there is no TLS on localhost and the cookie
# would simply never be set, making sign-in untestable.
_session_kw = {}
if webauth.SESSION_DOMAIN:
    # Only passed when actually set — Starlette treats domain=None and an
    # absent key differently in older versions, and a cookie scoped to a domain
    # the response did not come from is dropped silently by the browser.
    _session_kw["domain"] = webauth.SESSION_DOMAIN
# The partner tag, remembered from whichever page it arrived on.
#
# WHY THIS IS MIDDLEWARE AND NOT A QUERY PARAMETER READ AT SIGN-IN. A partner
# links to ?ref=nextnw, but nobody signs in on the page they land on: they read
# the board, click a gig, come back, and only then sign in — and by that point
# the tag is several navigations gone. accounts.sign_in() applies
# PARTNER_GRANTS from it, so losing it means a Next Northwest member is created
# on Free instead of their 90-day grant. That exact failure has already
# happened once on the app's Google path.
#
# REGISTERED BEFORE SessionMiddleware, WHICH MAKES IT RUN AFTER IT.
# Starlette's add_middleware does user_middleware.insert(0, ...), so the LAST
# one registered ends up outermost and runs FIRST. Registering this after
# SessionMiddleware — the intuitive reading — put it outside the session, where
# request.session raises "SessionMiddleware must be installed", and the except
# below quietly ate the error: every partner tag was dropped and the page
# rendered perfectly. Caught only because the end-to-end test checked the grant
# a test account actually received rather than that the request returned 200.
# First tag wins — someone who arrives through a partner and later wanders back
# in from a search result should still be credited to the partner.
# Deliberately a substring list rather than anything clever. Every one of these
# appears in the user agent of something that is not a person, they are all
# lowercase-matched, and a name that slips through costs one inflated row —
# where a false positive would silently drop a real visitor.
_BOT_UA = ("bot", "crawler", "spider", "slurp", "curl/", "wget", "python-requests",
           "httpx", "headless", "monitor", "uptime", "preview", "scrape",
           "fetcher", "facebookexternalhit", "embedly", "phantomjs", "selenium",
           "nabbly-selfcheck")   # our own monitoring is not a visitor either


def _is_bot(ua: str) -> bool:
    ua = (ua or "").lower()
    return not ua or any(b in ua for b in _BOT_UA)


def _ev(request: Request, event: str, detail: str = ""):
    """
    Record one thing a visitor did.

    THE BOARD RECORDED NOTHING UNTIL NOW. Every event Nabbly had came from the
    Streamlit app, and when the Gigs tab moved here the event stream did not
    follow — so the place people actually browse was invisible, and so was
    every arrival from the marketing site.

    Straight to telemetry, not through analytics.track(), for a reason: track()
    opens SQLite, inserts, commits and closes on the calling thread, and this
    route answers in 3-4ms. The PostHog client appends to an in-memory queue
    and a background thread does the sending, so the cost here is a dict lookup
    and a list append. It is also honest about this service's disk, which
    Render wipes on every deploy — a local events table here would be lost
    every time you shipped.

    The distinct id is a random key kept in the session cookie. Not an email
    and not an account id, which is exactly what the privacy page now promises:
    a rotating session identifier and nothing that identifies you.
    """
    try:
        # CRAWLERS MUST NOT COUNT AS PEOPLE. This service is indexable and the
        # /out/ links are followed by bots that never see a page — left in,
        # they would inflate gig_click most of all, and a number you cannot
        # trust is worse than no number, because you act on it.
        if _is_bot(request.headers.get("user-agent", "")):
            return
        sid = request.session.get("_vid")
        if not sid:
            sid = secrets.token_urlsafe(9)
            request.session["_vid"] = sid
        path = request.url.path
        telemetry.capture(event, detail, sid, path)
        camp = request.session.get("_camp")
        if camp and event == "board_view":
            telemetry.capture("from_campaign", camp, sid, path)
    except Exception:
        pass          # a counter must never stand between someone and a gig


@app.middleware("http")
async def _remember_campaign(request: Request, call_next):
    try:
        if not request.session.get("_camp"):
            tag = analytics.campaign_label(
                request.query_params.get("ref", "")
                or request.query_params.get("utm_source", ""))
            if tag:
                request.session["_camp"] = tag
    except AssertionError:
        # Only reachable if the ordering above is broken again. Attribution is
        # not worth failing a render for, but it IS worth saying out loud,
        # because silence is what made this cost an afternoon.
        print("  ! campaign middleware ran outside the session — check the "
              "middleware registration order in web/main.py", flush=True)
    except Exception:
        pass
    return await call_next(request)


app.add_middleware(
    SessionMiddleware, secret_key=webauth._SECRET,
    session_cookie=webauth.SESSION_COOKIE, max_age=webauth.SESSION_MAX_AGE,
    same_site="lax", https_only=os.environ.get("NABBLY_LOCAL") != "1",
    **_session_kw)

def _safe_next(v: str) -> str:
    """
    A same-site path, or nothing.

    This value decides where a browser goes immediately after authenticating,
    which is exactly the value an attacker wants control of: an absolute URL
    here turns sign-in into an open redirect onto a page that can imitate this
    one and ask for something. Only a plain absolute path is allowed, and
    "//evil.example" is rejected too — the browser reads that as a host, not a
    path, which is the classic way past a naive startswith("/") check.
    """
    v = (v or "").strip()
    if not v.startswith("/") or v.startswith("//") or v.startswith("/\\"):
        return ""
    return v[:300]


def _signin_to(path: str) -> str:
    """Bounce to sign-in, remembering where they were trying to get to."""
    nxt = _safe_next(path)
    return f"/signin?next={quote_plus(nxt)}" if nxt else "/signin"


def _landing(request, nxt: str) -> str:
    """
    Where someone lands the moment they finish signing in.

    Three different people arrive here and they do not want the same page.

    Someone who was MID-ACTION — they clicked save on a gig, or a draft — is
    returned to where they were. They already said what they wanted; sending
    them to a dashboard makes them find that gig a second time.

    Someone with NO FIELDS SET goes to their profile. "Best match" is gated on
    having at least one, so their board is still plain newest-first: dropping
    them on the dashboard shows them the identical page they saw signed out,
    and the act of signing in appears to have done nothing at all.

    Everyone else goes to the board, because that is what they came back for
    and it is now sorted for them.
    """
    if nxt:
        return nxt
    # The scope was resolved at the top of this request, when this person was
    # still anonymous. Re-resolve it or profile.load() reads the guest scope
    # and every returning member looks like they have no fields.
    webauth.scope_for_request(request)
    try:
        import profile as profile_mod
        if not ((profile_mod.load() or {}).get("skills") or []):
            return "/profile?welcome=1"
    except Exception:
        # Never let a profile read decide whether sign-in succeeds.
        pass
    return "/"


def _reading_languages(prof) -> list[str]:
    """
    Which languages this reader's board should include — the app's rule.

    THE DEFAULT IS NOT "EVERYTHING", AND THIS SERVICE USED TO THINK IT WAS.
    app.py's reading_languages() gives everyone English plus whatever their
    country implies, so somebody in Germany keeps their German gigs without
    hunting for a setting, and everybody else is not shown listings they
    cannot read. This service only ever looked at the ?langs= URL parameter,
    so with none supplied it filtered nothing.

    That single difference was the whole app/board gap. Measured 2026-08-16,
    sampled together: the app served 43,278 and this service 46,825, and the
    3,547 difference was spread proportionally across all 25 fields — no
    missing source, no bad field, just 3,209 German listings and a few hundred
    others that the app hides and this did not. Once the front door moved
    here, that was the first thing a visitor saw.

    An explicit ?langs= still wins: this only supplies the default.
    """
    prof = prof or {}
    if prof.get("show_all_languages"):
        return []                      # they asked for everything
    codes = {"en"}
    try:
        import lang as _lang
        implied = _lang.COUNTRY_LANG.get((prof.get("country") or "").strip())
        if implied:
            codes.add(implied)
    except Exception:
        # A missing table must not silently widen the board back out to every
        # language; English alone is the safe answer.
        pass
    return sorted(codes)


def _campaign(request) -> str:
    try:
        return (request.session.get("_camp") or "").strip()
    except Exception:
        return ""

# NABBLY_DB points at an existing SQLite file (local dev, tests). With it
# unset, the service maintains its own copy from the durable mirror — which is
# what runs on Render, where this service has its own filesystem and cannot see
# the Streamlit app's database. See web/sync.py.
DB_PATH = os.environ.get("NABBLY_DB") or None
_SYNC = not DB_PATH and os.environ.get("NABBLY_NO_SYNC") != "1"


@app.on_event("startup")
def _boot():
    if not _SYNC:
        return
    import sync
    # NON-BLOCKING. uvicorn must bind the port before Render's port scan gives
    # up — a ~50s boot pull inside the startup hook failed the deploy with
    # "No open ports detected". /health reports unhealthy until rows land, so
    # Render holds traffic on the old instance meanwhile.
    sync.start_background()
    global DB_PATH
    DB_PATH = sync.BOARD_DB

# Anonymous board pages are the same for everyone, so let the CDN keep one copy
# for a minute. New gigs land every couple of minutes; a stale-while-revalidate
# window means nobody ever waits on a rebuild.
_CACHE = "public, max-age=60, stale-while-revalidate=300"


class _Facets:
    """
    Filter-chip counts, cached per filter combination.

    Four GROUP BYs, measured at ~43ms unfiltered — the most expensive thing on
    the page. They depend on which filters are active (see queries.facets for
    why they must), so one cached value is not enough.

    BOUNDED ON PURPOSE. Keying a cache on user-supplied filters means anyone
    can mint new keys by sending combinations, and an unbounded dict of them is
    a memory leak with a request interface attached. _MAX evicts oldest-first,
    so the common combinations stay hot and the long tail simply recomputes.
    The board version is part of every key, so entries retire when gigs arrive
    rather than going stale.
    """

    _MAX = 64

    def __init__(self):
        self._c: dict = {}
        self._ver = None
        self._at = 0.0

    @staticmethod
    def _key(ctx):
        return tuple(sorted(
            (k, tuple(v) if isinstance(v, list) else v) for k, v in ctx.items()))

    def get(self, conn, ctx):
        ver = queries.board_total(conn)
        # A 120s floor keeps a busy board from dumping the cache on every
        # ingest; the version check is what keeps it honest.
        if ver != self._ver and time.time() - self._at > 120:
            self._c.clear()
            self._ver, self._at = ver, time.time()
        k = self._key(ctx)
        if k not in self._c:
            if len(self._c) >= self._MAX:
                self._c.pop(next(iter(self._c)))
            # The location toggle's counts are cached HERE rather than
            # separately: same inputs, same lifetime, and left uncached it was
            # the slowest thing left on the page — every request paying ~18ms
            # to add up two flags, which at 100 concurrent is most of a second
            # of queueing on its own.
            self._c[k] = (queries.facets(conn, ctx),
                          queries.location_counts(conn, ctx))
        return self._c[k]


_facets = _Facets()


def _csv(v: str | None) -> list[str]:
    return [x for x in (v or "").split(",") if x.strip()]


# Off by default. This board is incomplete, and an incomplete version of a page
# you already rank for is worse than no page: Google would have it competing
# with the 23 static field pages for the same queries. Flip NABBLY_INDEXABLE=1
# only once it is the real board and something links to it.
_INDEXABLE = os.environ.get("NABBLY_INDEXABLE") == "1"


# A DEAD END SHOULD STILL LOOK LIKE NABBLY. FastAPI's default is a bare JSON
# body — {"detail":"Not Found"} — with no branding and no way back, and this
# service is now indexable, so a crawler following a stale link lands on raw
# API output. Same for the 405 a GET on /signout or /save produces, which a
# link prefetcher will hit on its own.
#
# The STATUS CODE IS UNCHANGED. A 404 must stay a 404 or search engines will
# happily index every dead URL as a real page.
#
# Falls back to the default response if anything here raises: an error page
# that can itself error is worse than the bare JSON it replaces.
@app.exception_handler(StarletteHTTPException)
async def _pretty_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code not in (404, 405):
        return await http_exception_handler(request, exc)
    try:
        webauth.scope_for_request(request)
        me = webauth.current_email(request)
    except Exception:
        me = ""
    text = {
        404: ("Not found",
              "That page doesn't exist, or the gig behind it has come off the "
              "board. The board itself is still here."),
        405: ("That link needs a button",
              "This address only answers to a form on the site, not a direct "
              "visit. Nothing is broken."),
    }[exc.status_code]
    try:
        return _oops_page(request, exc.status_code, text[0], text[1], me)
    except Exception:
        return await http_exception_handler(request, exc)


# A BAD QUERY STRING IS THE THIRD WAY TO GET RAW JSON, and it was still open
# after 404 and 405 were closed. FastAPI raises RequestValidationError, which
# is not an HTTPException, so the handler above never saw it: /gigs?sort=newest
# answered with a pydantic error dump naming the internal pattern. Anyone with
# an old bookmark or a mistyped link got that.
#
# 422 is kept. The request really was malformed, and softening it to a 200
# would teach crawlers that every wrong URL is a real page.
@app.exception_handler(RequestValidationError)
async def _pretty_validation_error(request: Request,
                                   exc: RequestValidationError):
    try:
        webauth.scope_for_request(request)
        me = webauth.current_email(request)
    except Exception:
        me = ""
    try:
        return _oops_page(
            request, 422, "That address has a setting the board doesn't use",
            "Something in the link asks the board to sort or filter in a way "
            "it doesn't recognise. The board itself is fine, and browsing from "
            "here works normally.", me)
    except Exception:
        return await request_validation_exception_handler(request, exc)


def _oops_page(request: Request, status: int, heading: str, message: str,
               me: str):
    """The one branded dead end, shared by every handler that needs it."""
    return templates.TemplateResponse(
        request, "oops.html",
        {"status": status, "heading": heading, "message": message,
         "me": me, "tab": "", "css_v": CSS_V, "indexable": False,
         "app_url": APP_URL, "took_ms": 0.0},
        status_code=status,
        headers={"X-Robots-Tag": "noindex, nofollow"})


@app.get("/robots.txt")
def robots():
    from fastapi.responses import PlainTextResponse
    body = ("User-agent: *\nAllow: /\n" if _INDEXABLE
            else "User-agent: *\nDisallow: /\n")
    return PlainTextResponse(body)


@app.get("/signin", response_class=HTMLResponse)
def signin_page(request: Request, sent: str = Query(""), err: str = Query(""),
                next: str = Query("")):
    webauth.scope_for_request(request)
    if webauth.current_email(request):
        return RedirectResponse("/", status_code=303)
    # Held in the session, not in the form: it has to survive the round trip to
    # Google and back, and that return leg carries only Google's own query
    # string. Re-validated on the way out too — a session is a cookie, and a
    # cookie is not a thing to trust blindly on a redirect.
    nxt = _safe_next(next)
    if nxt:
        request.session["_next"] = nxt
    return templates.TemplateResponse(request, "signin.html", {
        "sent": sent, "err": err, "mail_ok": webauth.mail_enabled(),
        "google_ok": googleauth.enabled(),
        "me": "", "tab": "", "css_v": CSS_V, "indexable": _INDEXABLE,
        "app_url": APP_URL, "took_ms": 0.0,
    })


@app.get("/auth/google")
def google_start(request: Request):
    """Begin the handshake. The state is the CSRF guard, minted per attempt."""
    webauth.scope_for_request(request)
    if not googleauth.enabled():
        return _back("/signin", err="Google sign-in isn't available right now.")
    state = googleauth.new_state()
    request.session[googleauth.STATE_KEY] = state
    return RedirectResponse(googleauth.authorize_url(state, request),
                            status_code=303)


@app.get("/auth/google/callback")
def google_callback(request: Request, code: str = Query(""),
                    state: str = Query(""), error: str = Query("")):
    """
    Where Google sends the browser back.

    The state is compared against the one minted at /auth/google and then
    DROPPED whatever the outcome, so a code can never be replayed against a
    still-valid state. Without that check this endpoint would accept a code
    from anywhere, which is the login-CSRF that lets an attacker land a visitor
    in the attacker's own account.
    """
    webauth.scope_for_request(request)
    want = request.session.pop(googleauth.STATE_KEY, "")
    if error:
        # The ordinary case here is someone pressing "cancel" on Google's own
        # screen, which is not an error worth shouting about.
        return _back("/signin", err="" if error == "access_denied"
                     else "Google couldn't complete that sign-in.")
    if not code or not state or not want or state != want:
        return _back("/signin", err="That sign-in link expired. Try again.")
    email, err = googleauth.email_for_code(code, request)
    if err:
        return _back("/signin", err=err)
    nxt = _safe_next(request.session.get("_next", ""))
    ok, err = webauth.sign_in_google(email, campaign=_campaign(request))
    if not ok:
        return _back("/signin", err=err)
    webauth.sign_in_session(request, email)
    return RedirectResponse(_landing(request, nxt), status_code=303)


@app.post("/signin")
def signin_send(request: Request, email: str = Form("")):
    webauth.scope_for_request(request)
    if not webauth.rate_ok(request):
        return _back("/signin", err="Too many codes requested. Wait a few minutes.")
    ok, err = webauth.send_code(email)
    if not ok:
        return _back("/signin", err=err)
    return _back("/signin", sent=email.strip().lower())


@app.post("/signin/verify")
def signin_verify(request: Request, email: str = Form(""), code: str = Form("")):
    webauth.scope_for_request(request)
    # Read BEFORE sign_in_session, which clears the session and would take the
    # partner tag with it.
    camp = _campaign(request)
    nxt = _safe_next(request.session.get("_next", ""))
    ok, err = webauth.verify(email, code, campaign=camp)
    if not ok:
        return _back("/signin", sent=email.strip().lower(), err=err)
    webauth.sign_in_session(request, email)
    return RedirectResponse(_landing(request, nxt), status_code=303)


@app.post("/save")
def save(request: Request, gig: str = Form(""), back: str = Form("/")):
    """
    Toggle a saved gig, then send the browser back where it came from.

    `back` is taken from a form field rather than the Referer header, which is
    absent often enough (privacy settings, some proxies) that half the saves
    would dump people on page one of the board.
    """
    webauth.scope_for_request(request)
    if not webauth.current_email(request):
        return RedirectResponse(_signin_to(back), status_code=303)
    if gig:
        try:
            import saved as saved_mod
            saved_mod.toggle(gig)
        except Exception:
            pass
    # Never redirect to a caller-supplied absolute URL: that turns this into an
    # open redirect anyone can point at a phishing page. Only same-site paths.
    if not back.startswith("/") or back.startswith("//"):
        back = "/"
    return RedirectResponse(back, status_code=303)


def _sid(request: Request) -> str:
    """The per-visit key the resume is held against. Never an email."""
    sid = request.session.get("_vid")
    if not sid:
        sid = secrets.token_urlsafe(9)
        request.session["_vid"] = sid
    return sid


@app.post("/resume")
async def resume_upload(request: Request):
    """
    Take a resume, keep the text in memory for this visit, never on disk.

    Same promise the app has always made and site/privacy.html still states:
    processed only to write your reply, never stored. resume_store.py holds it
    in a process-local dict with a two-hour life.

    A file it cannot read is not an error. extract_text returns "" for a
    scanned PDF, something corrupt or something oversized, and the honest
    answer then is "that one did not read", not a stack trace on a page
    somebody came to for settings.
    """
    webauth.scope_for_request(request)
    if not webauth.current_email(request):
        return RedirectResponse(_signin_to("/profile"), status_code=303)
    form = await request.form()
    up = form.get("resume")
    text = ""
    if up is not None and getattr(up, "filename", ""):
        try:
            import resume as resume_mod
            import resume_store
            raw = await up.read()

            class _Shim:      # extract_text wants .name and .getvalue()
                name = up.filename
                def getvalue(self_inner):
                    return raw
            text = resume_mod.extract_text(_Shim())
            if text:
                resume_store.put(_sid(request), text)
        except Exception:
            text = ""
    return RedirectResponse(
        "/profile?tab=you&" + ("saved_ok=1" if text else "resume_bad=1"),
        status_code=303)


@app.post("/resume/clear")
async def resume_clear(request: Request):
    webauth.scope_for_request(request)
    try:
        import resume_store
        resume_store.clear(_sid(request))
    except Exception:
        pass
    return RedirectResponse("/profile?tab=you&saved_ok=1", status_code=303)


@app.post("/feedback")
async def feedback_post(request: Request):
    """
    The feedback box on the Account tab.

    Straight into the same store the app's own box writes to, so there is one
    list to read rather than two. Never allowed to fail loudly: somebody
    telling you something is broken should not meet a second broken thing.
    """
    webauth.scope_for_request(request)
    me = webauth.current_email(request)
    if not me:
        return RedirectResponse(_signin_to("/profile"), status_code=303)
    form = await request.form()
    msg = (form.get("feedback") or "").strip()[:2000]
    if msg:
        try:
            import people
            people.add_feedback(msg, email=me, page="board-profile")
        except Exception:
            pass
    return RedirectResponse("/profile?saved_ok=1&tab=acct", status_code=303)


@app.post("/signout")
def signout(request: Request):
    webauth.sign_out_session(request)
    return RedirectResponse("/", status_code=303)


def _back(path: str, **params):
    """
    Redirect after POST, always — never render a page in response to one.

    Without this a refresh re-submits the form, which here means mailing
    another sign-in code or burning another verification attempt.
    """
    qs = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items() if v)
    return RedirectResponse(f"{path}?{qs}" if qs else path, status_code=303)


@app.get("/saved", response_class=HTMLResponse)
def saved_page(request: Request):
    """
    Gigs this person kept. Signed-out gets the pitch, not a redirect — being
    bounced to a sign-in form explains nothing about why you would want one.
    """
    t0 = time.perf_counter()
    webauth.scope_for_request(request)   # MUST be first; see webauth's threading note
    me = webauth.current_email(request)
    rows, ids = [], []
    if me:
        try:
            import saved as saved_mod
            ids = saved_mod.ids()
        except Exception:
            ids = []
        if ids:
            conn = queries.connect(DB_PATH)
            try:
                rows = decorate(queries.by_ids(ids, conn=conn))
            finally:
                conn.close()

    resp = templates.TemplateResponse(request, "saved.html", {
        "rows": rows, "me": me, "saved_ids": set(ids),
        "missing": max(0, len(ids) - len(rows)),
        "here": "/saved", "tab": "saved",
        "css_v": CSS_V, "indexable": _INDEXABLE, "app_url": APP_URL,
        "took_ms": (time.perf_counter() - t0) * 1000,
    })
    # Personal by definition — never hand this to the CDN.
    resp.headers["Cache-Control"] = "private, no-store"
    if not _INDEXABLE:
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.get("/draft/{gig_id}", response_class=HTMLResponse)
def draft_page(request: Request, gig_id: int, back: str = Query("/gigs"),
               regen: int = Query(0), saved_ok: int = Query(0)):
    """
    A reply, drafted for one gig, generated ON REQUEST.

    ONE CLICK, ONE DRAFT — this is why it is a page and not an expander on the
    board. The Streamlit version only generates when someone opens the
    expander; the equivalent mistake here would be drafting all 25 cards on
    every page load, which for a Pro reader is 25 model calls to render a list.
    A page also gives the draft a URL you can come back to.

    Free gets pitch.draft_template: no model, no cost, instant. Pro gets
    draft_pitch, which is already budget-gated and cached upstream — nothing
    here needs to re-invent either.
    """
    t0 = time.perf_counter()
    webauth.scope_for_request(request)      # MUST be first
    me = webauth.current_email(request)
    if not back.startswith("/") or back.startswith("//"):
        back = "/gigs"                       # never redirect off-site
    if not me:
        return RedirectResponse(_signin_to(f"/draft/{gig_id}"), status_code=303)

    conn = queries.connect(DB_PATH)
    try:
        rows = queries.by_ids([gig_id], conn=conn)
    finally:
        conn.close()
    if not rows:
        return RedirectResponse(back, status_code=303)
    g = rows[0]

    import drafts as drafts_mod
    import pitch
    import profile as profile_mod
    prof = profile_mod.load() or {}
    acc = webauth.account_for(request)
    pro = bool(accounts.status(acc).get("pro"))

    # An edited draft is the reader's, not ours — never overwrite it with a
    # fresh generation unless they explicitly ask for one.
    text = "" if regen else drafts_mod.load(gig_id)
    if not text:
        if pro and pitch.ai_available():
            # THE RESUME IS WHY THIS MOVED. A draft that can name real work
            # beats one written from a one-line bio, and until now the board
            # could not do that at all — the upload only existed on the app.
            try:
                import resume_store
                _cv = resume_store.get(_sid(request))
            except Exception:
                _cv = ""
            text = pitch.draft_pitch(g, prof, who=me, resume_text=_cv)
        else:
            text = pitch.draft_template(g, prof)

    mailto = ""
    addr = (g.get("apply_email") or "").strip()
    if addr:
        subj = quote_plus(f"Re: {g.get('title') or 'your posting'}")
        mailto = f"mailto:{addr}?subject={subj}&body={quote_plus(text)}"

    resp = templates.TemplateResponse(request, "draft.html", {
        "g": g, "draft": text, "pro": pro, "me": me, "back": back,
        "mailto": mailto, "saved_ok": bool(saved_ok),
        "upsell": "" if pro else pitch.free_draft_note(g),
        "tab": "gigs", "css_v": CSS_V, "indexable": _INDEXABLE,
        "app_url": APP_URL, "took_ms": (time.perf_counter() - t0) * 1000,
    })
    resp.headers["Cache-Control"] = "private, no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.post("/draft/{gig_id}/save")
def draft_save(request: Request, gig_id: int, text: str = Form(""),
               back: str = Form("/gigs")):
    webauth.scope_for_request(request)
    if not webauth.current_email(request):
        return RedirectResponse(_signin_to(f"/draft/{gig_id}"), status_code=303)
    import drafts as drafts_mod
    drafts_mod.save(gig_id, text)
    if not back.startswith("/") or back.startswith("//"):
        back = "/gigs"
    return RedirectResponse(
        f"/draft/{gig_id}?saved_ok=1&back={quote_plus(back)}", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, saved_ok: int = Query(0),
                 welcome: int = Query(0), tab: str = Query(""),
                 resume_bad: int = Query(0)):
    """
    What ranks the board and what drafts are written from.

    Without this page a signed-in reader on the board cannot set skills, and
    "Best match" is gated on having them — so the feature that makes the board
    theirs would be switchable only over on the Streamlit app.
    """
    t0 = time.perf_counter()
    webauth.scope_for_request(request)      # MUST be first
    me = webauth.current_email(request)
    if not me:
        return RedirectResponse(_signin_to("/profile"), status_code=303)
    import alerts as alerts_mod
    import profile as profile_mod
    st_ = {}
    try:
        st_ = accounts.status(webauth.account_for(request)) or {}
    except Exception:
        st_ = {}
    is_pro = bool(st_.get("pro"))
    # What the Account tab says you are on. Read from accounts.status rather
    # than inferred from is_pro, so a trial with days left reads as a trial.
    if is_pro and st_.get("plan") == "trial":
        plan = {"name": "Pro trial", "tag": f"{st_.get('days_left', 0)} days left",
                "what": "Everything Pro does, free until it runs out."}
    elif is_pro:
        plan = {"name": "Pro", "tag": "Active",
                "what": "Ranking, post-aware drafts, market rates and instant alerts."}
    else:
        plan = {"name": "Free", "tag": "The whole board",
                "what": "Every gig from every source, search and browse, "
                        "and a drafted reply on every card."}
    # The forwarding address, if the mailbox behind it is configured at all.
    try:
        import inbox as inbox_mod
        inbox_address = inbox_mod.address_for(me) if inbox_mod.enabled() else ""
    except Exception:
        inbox_address = ""
    try:
        import resume_store
        _resume_chars = resume_store.held_chars(_sid(request))
    except Exception:
        _resume_chars = 0
    resp = templates.TemplateResponse(request, "profile.html", {
        "prof": profile_mod.load(), "prefs": alerts_mod.load_prefs(),
        "is_pro": is_pro, "plan": plan, "inbox_address": inbox_address,
        "resume_chars": _resume_chars, "resume_bad": bool(resume_bad),
        "all_skills": ALL_SKILLS, "skill_groups": SKILL_GROUPS, "me": me,
        "tab_open": tab if tab in ("board", "acct") else "you",
        "saved_ok": bool(saved_ok), "welcome": bool(welcome), "tab": "profile",
        "css_v": CSS_V, "indexable": _INDEXABLE, "app_url": APP_URL,
        "took_ms": (time.perf_counter() - t0) * 1000,
    })
    resp.headers["Cache-Control"] = "private, no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.post("/profile")
async def profile_save(request: Request):
    """
    Saved field by field onto the EXISTING profile, never as a wholesale
    replacement: profile.py's DEFAULT carries keys this form does not show, and
    writing the form's dict straight over the top would silently wipe them.
    """
    webauth.scope_for_request(request)
    if not webauth.current_email(request):
        return RedirectResponse(_signin_to("/profile"), status_code=303)
    import profile as profile_mod
    form = await request.form()
    prof = profile_mod.load()

    prof["skills"] = [s for s in form.getlist("skills") if s in ALL_SKILLS]
    for field in ("keywords", "mute", "city", "country", "name", "headline",
                  "portfolio", "bio", "rate_unit"):
        prof[field] = (form.get(field) or "").strip()[:400]
    try:
        prof["rate_floor"] = max(0, int(float(form.get("rate_floor") or 0)))
    except (TypeError, ValueError):
        prof["rate_floor"] = 0
    # An unchecked checkbox sends nothing at all, so presence IS the value.
    prof["open_to_relocate"] = bool(form.get("open_to_relocate"))
    prof["show_all_languages"] = bool(form.get("show_all_languages"))

    # How drafted replies read — Pro only.
    #
    # ONLY WRITTEN WHEN THEY ARE PRO, and deliberately not zeroed otherwise.
    # The inputs render disabled for a free account, and a disabled input
    # submits nothing, so a blanket write here would silently erase what a
    # lapsed subscriber had configured the moment they saved anything else on
    # this page. Their settings sit dormant instead and come back with them.
    try:
        _pro = bool(accounts.status(webauth.account_for(request)).get("pro"))
    except Exception:
        _pro = False
    if _pro:
        _len = (form.get("draft_length") or "standard").strip().lower()
        prof["draft_length"] = _len if _len in ("brief", "standard", "detailed") \
            else "standard"
        prof["draft_signoff"] = (form.get("draft_signoff") or "").strip()[:80]
        prof["draft_always"] = (form.get("draft_always") or "").strip()[:200]
        prof["draft_never"] = (form.get("draft_never") or "").strip()[:200]
    profile_mod.save(prof)

    # Alert channels live in their own store (alert_prefs.json) but are edited
    # on this one form, because that is where the app puts them.
    import alerts as alerts_mod
    prefs = alerts_mod.load_prefs()
    for field in ("sms_to", "ntfy_topic", "discord_webhook",
                  "telegram_token", "telegram_chat"):
        prefs[field] = (form.get(field) or "").strip()[:300]
    # A malformed number silently never delivers, so refuse it rather than
    # storing something that looks saved and does nothing.
    if prefs["sms_to"] and not alerts_mod.valid_phone(prefs["sms_to"]):
        prefs["sms_to"] = ""
    for field, allowed in (("every_min", (5, 15, 30, 60, 180)),
                           ("max_per_alert", (3, 5, 10, 20))):
        try:
            v = int(form.get(field) or 0)
        except (TypeError, ValueError):
            v = 0
        if v in allowed:
            prefs[field] = v
    prefs["urgent_only"] = bool(form.get("urgent_only"))
    alerts_mod.save_prefs(prefs)
    # Back to the tab they were on. Saving from "Preferences" and landing on
    # "About you" reads as the page having thrown the edit away.
    #
    # The VALUE stays "board" — that is the object being configured, and it is
    # this product's own noun ("feed" was imported from elsewhere and only ever
    # appeared in these tabs). The LABEL is "Preferences", which is the
    # convention for exactly this content: LinkedIn ships "Feed preferences",
    # X ships "Content preferences", and "Preferences" specifically implies
    # personalization where "Settings" is the generic catch-all.
    _ptab = (form.get("ptab") or "").strip()
    _tab = _ptab if _ptab in ("board", "acct") else "you"
    return RedirectResponse(f"/profile?saved_ok=1&tab={_tab}", status_code=303)


@app.get("/out/{gig_id}")
def out(request: Request, gig_id: int):
    """
    Log an apply click, then send the browser to the posting.

    The board used to link straight at the gig's URL, which is faster and
    perfectly honest as a link — and meant applies were never counted. That
    number feeds the weekly digest and is the one signal that says the board
    actually worked for someone, so it cannot be the thing we drop for a few
    milliseconds.

    A real 302, not the app's meta-refresh: the browser follows it before
    painting anything, so there is no blank flash, and a bot that ignores
    redirects does not get counted as a human applying.

    Only counted for someone signed in. An anonymous click has nobody to
    attribute it to, and inventing an attribution would corrupt the only
    outcome metric Nabbly has.
    """
    webauth.scope_for_request(request)
    conn = queries.connect(DB_PATH)
    try:
        rows = queries.by_ids([gig_id], conn=conn)
    finally:
        conn.close()
    if not rows or not (rows[0].get("url") or "").startswith(("http://", "https://")):
        return RedirectResponse("/gigs", status_code=303)
    # Which kinds of gig actually pull a click, from everyone rather than only
    # from members. activity.log_apply below stays members-only on purpose: it
    # feeds the outcomes number, and an anonymous click has nobody to
    # attribute it to.
    _ev(request, "gig_click", (rows[0].get("job_type") or "")[:60])
    if webauth.current_email(request):
        try:
            import activity
            activity.log_apply(paths.get_scope(), gig_id)
        except Exception:
            pass          # a counter must never stand between someone and a gig
    return RedirectResponse(rows[0]["url"], status_code=302)


@app.get("/health")
def health():
    """
    Liveness plus the number that actually matters in production: how far
    behind the mirror this copy has drifted. A board serving stale gigs looks
    identical to a board serving fresh ones, so drift has to be visible or it
    is not monitored.
    """
    out = {"ok": True}
    if _SYNC:
        import sync
        s = sync.state()
        out.update(rows=s["rows"], drift_s=s["drift_s"],
                   archived=s["archived"], errors=s["errors"])
        if s["note"]:
            out["note"] = s["note"]
        # An empty board is not healthy. This reported ok:true while serving
        # zero gigs on the first Render deploy (DATABASE_URL was unset, so the
        # mirror pull returned nothing) — a green health check on a site with
        # no content, which is the exact failure the drift check below exists
        # to prevent, missed one field over.
        if not s["rows"]:
            out["ok"] = False
            # An empty board during the first minute is a service still filling
            # itself, not a misconfigured one. Saying "is DATABASE_URL set?"
            # while it boots normally sends someone chasing a problem that does
            # not exist — and the first pull now takes ~50s, so that window is
            # every single deploy.
            out["status"] = "starting"
            out.setdefault(
                "note",
                "still loading the board from the mirror"
                if s.get("errors", 0) == 0 and not s.get("note")
                else "board is empty — is DATABASE_URL set?")
        # Two missed refreshes is a real problem, not a blip.
        if s["drift_s"] is not None and s["drift_s"] > sync.REFRESH_S * 3:
            out["ok"] = False
    return out


@app.get("/", response_class=HTMLResponse)
@app.get("/gigs", response_class=HTMLResponse)
def board(request: Request,
          q: str = Query("", max_length=120),
          field: str = Query(""),
          size: str = Query(""),
          source: str = Query(""),
          urgent: int = Query(0),
          where: str = Query("", pattern="^(remote|onsite|)$"),
          langs: str = Query(""),
          sort: str = Query("", pattern="^(fit|new|)$"),
          qf: str = Query("", pattern="^(recent|mine|urgent|)$"),
          page: int = Query(0, ge=0, le=2000)):
    t0 = time.perf_counter()
    # MUST be first: sets the thread-local scope the per-user helpers read.
    webauth.scope_for_request(request)
    me = webauth.current_email(request)
    ctx = {"job_types": _csv(field), "sizes": _csv(size),
           "sources": _csv(source), "languages": _csv(langs),
           "urgent_only": bool(urgent), "where_work": where, "since_hours": 0}
    # Fit ranking is a Pro feature AND needs a profile with something in it.
    # score.fit_score gives every gig a flat +30 when there are no skills, so
    # an empty profile would produce the same number on every card and present
    # it as personalisation — the same reason the Streamlit board refuses to
    # score in that case.
    prof, can_rank = {}, False
    if me:
        try:
            import profile as profile_mod
            prof = profile_mod.load() or {}
            acc = webauth.account_for(request)
            can_rank = bool(accounts.status(acc).get("pro")) and bool(prof.get("skills"))
        except Exception:
            prof, can_rank = {}, False
    # Applied AFTER the profile loads, because the answer depends on it, and
    # only when the reader has not chosen languages explicitly in the URL.
    # Anonymous visitors get English, which is what the app gives them.
    if not ctx["languages"]:
        ctx["languages"] = _reading_languages(prof)
    # Metro-pinned gigs, on app.py's rule (apply_city_lock). Anonymous readers
    # have no city, so pinned gigs are hidden from them — which is exactly what
    # the app does, and was the last 190 gigs of the app/board gap.
    ctx["city"] = (prof.get("city") or "").strip()
    ctx["relocate"] = bool(prof.get("open_to_relocate"))
    ranked = sort == "fit" and can_rank

    # Quick-filters, the same three the Dashboard's stat clicks send:
    # "posted in the last 24h", "in your skills", "urgent only".
    #
    # `mine` with an empty skills list is REFUSED rather than silently ignored.
    # On the Streamlit board that combination showed the whole board under a
    # pill claiming it was narrowed to your skills — a filter that says it ran
    # and didn't. Here it turns into a message that says what happened.
    qf_note = ""
    if qf == "urgent":
        ctx["urgent_only"] = True
    elif qf == "recent":
        ctx["since_hours"] = 24
    elif qf == "mine":
        mine = [s for s in (prof.get("skills") or []) if s]
        if mine:
            ctx["job_types"] = sorted(set(ctx["job_types"]) & set(mine)) or mine
        else:
            qf = ""
            qf_note = ("Add your skills on Profile and this becomes your "
                       "shortlist. Right now it's the whole board.")
    QF_LABEL = {"recent": "posted in the last 24h", "mine": "in your skills",
                "urgent": "urgent only"}

    conn = queries.connect(DB_PATH)
    try:
        if ranked:
            res = queries.fit_ranked(prof, keyword=q, page=page, conn=conn, **ctx)
        else:
            res = queries.board(keyword=q, page=page, conn=conn, **ctx)
        # WHAT PEOPLE WANT, AND WHAT THEY WANTED AND DID NOT GET. A search that
        # returns nothing is the most useful line in the whole stream: it is
        # somebody telling you, in their own words, what the board is missing.
        _ev(request, "board_view", (field or "all")[:60])
        if q:
            _ev(request, "search" if res.get("total") else "search_empty",
                q.strip().lower()[:60])
        # The chip counts take the same filters MINUS the quick-filter, so a
        # chip still says how many it would give you, not how many survive a
        # temporary narrowing you are about to replace.
        facets, loc = _facets.get(conn, {k: v for k, v in ctx.items()
                                         if k != "since_hours"})
    finally:
        conn.close()

    # Which of the gigs ON THIS PAGE are saved — a set of at most 25 ids, not
    # the whole saved list rendered into every card's state.
    saved_ids = set()
    if me:
        try:
            import saved as saved_mod
            saved_ids = set(saved_mod.ids())
        except Exception:
            saved_ids = set()

    # robots.txt alone does not stop a page that gets linked to from being
    # indexed; the header does. Belt and braces while this is unfinished.
    # One place that builds a link with a single filter changed and everything
    # else preserved. Hand-assembling these in the template is how a filter
    # quietly drops another one when both are set.
    # STAYS ON THE PAGE YOU ARE ON. This hardcoded "/", so every filter chip
    # and both pagination buttons on /gigs sent the visitor to the DASHBOARD
    # instead. Verified on the live board 2026-08-17 from path /gigs: "Next ›"
    # pointed at /?page=1, "Remote I can take" at /?where=remote, "Everywhere"
    # at /. Clicking any filter, or simply turning the page, silently dropped
    # you out of the board and onto the landing view — on the page the
    # marketing site now sends everyone to.
    #
    # It went unnoticed because every test, mine included, requested
    # /gigs?field=... directly rather than following a link the page drew.
    base = "/" if request.url.path == "/" else "/gigs"

    def link(**over):
        cur = {"q": q, "field": field, "size": size, "source": source,
               "urgent": urgent or "", "where": where, "langs": langs,
               "sort": sort, "qf": qf, "page": ""}
        cur.update(over)
        parts = [f"{k}={quote_plus(str(v))}" for k, v in cur.items() if v not in ("", None)]
        return f"{base}?" + "&".join(parts) if parts else base

    # The landing view is the app's Dashboard shape: hero, category groups, a
    # short "Fresh off the boards" list. /gigs is the full board with filters
    # and paging. One handler because they are the same query with a different
    # frame — two would drift the moment either changed.
    # A page past the end is a wrong URL, not an empty board. Left alone it
    # rendered "0 gigs for you", "Page 2,000 of 1" and "Nothing matches" all at
    # once — three untrue things on one screen. Send them to the last real page
    # instead, which is what someone hand-editing a page number meant anyway.
    if page > 0 and not res["rows"] and res.get("total"):
        last = max(0, res["pages"] - 1)
        if page != last:
            return RedirectResponse(link(page=last), status_code=303)

    landing = request.url.path == "/"
    if landing:
        res["rows"] = res["rows"][:8]
    decorate(res["rows"], ranked)
    # Ordered by how many gigs sit behind each bucket, not by however the dict
    # happens to be written — the app's dashboard leads with the biggest, and a
    # different order is the kind of difference you feel without being able to
    # name it.
    counts = facets.get("job_type", {})
    groups = sorted(
        ({"name": g, "fields": subs,
          "n": sum(counts.get(s, 0) for s in subs)}
         for g, subs in config.CATEGORY_GROUPS.items()),
        key=lambda x: -x["n"])
    carry = {k: v for k, v in
             {"field": field, "size": size, "source": source, "langs": langs,
              "where": where, "sort": sort, "qf": qf,
              "urgent": urgent or ""}.items() if v}

    # AN EMPTY BOARD MID-DEPLOY IS NOT AN EMPTY BOARD. Render wipes the disk on
    # every deploy and the mirror pull takes over a minute, so a visitor in that
    # window was told "that is unusual" about the most usual thing there is.
    # Same signal /health already uses, so the two cannot drift apart.
    booting = False
    try:
        if not res.get("total"):
            import sync
            booting = not int(sync.state().get("rows") or 0)
    except Exception:
        booting = False
    resp = templates.TemplateResponse(request, "board.html", {
        "booting": booting,
        "landing": landing, "groups": groups, "carry": carry,
        "css_v": CSS_V, "indexable": _INDEXABLE, "app_url": APP_URL,
        "tab": "dashboard" if landing else "gigs",
        "res": res, "facets": facets, "q": q, "loc": loc,
        "sel_field": _csv(field), "sel_size": _csv(size),
        "sel_source": _csv(source), "sel_langs": _csv(langs),
        "urgent": bool(urgent), "where": where, "link": link,
        "sort": sort, "ranked": ranked, "can_rank": can_rank,
        "qf": qf, "qf_label": QF_LABEL.get(qf, ""), "qf_note": qf_note,
        # Relative, not str(request.url): the absolute form would carry the
        # host into a form field, and /save refuses anything but a same-site
        # path, so a proxied host would silently bounce every save to page one.
        "me": me, "saved_ids": saved_ids,
        "here": request.url.path + (f"?{request.url.query}" if request.url.query else ""),
        "took_ms": (time.perf_counter() - t0) * 1000,
    })
    # A signed-in page is personal — it shows which gigs THIS person saved — so
    # it must never be handed to the CDN for the next visitor. Only the
    # anonymous board is cacheable, and that is the page the caching was for.
    resp.headers["Cache-Control"] = "private, no-store" if me else _CACHE
    if not _INDEXABLE:
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp

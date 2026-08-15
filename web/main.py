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
import sys
import time

from datetime import datetime, timedelta, timezone

from urllib.parse import quote_plus

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import accounts  # noqa: E402
import config  # noqa: E402
import location  # noqa: E402
import paths  # noqa: E402
import queries  # noqa: E402
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
app.add_middleware(
    SessionMiddleware, secret_key=webauth._SECRET,
    session_cookie=webauth.SESSION_COOKIE, max_age=webauth.SESSION_MAX_AGE,
    same_site="lax", https_only=os.environ.get("NABBLY_LOCAL") != "1")

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
    sync.start()                       # blocks on the first pull, then threads
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


@app.get("/robots.txt")
def robots():
    from fastapi.responses import PlainTextResponse
    body = ("User-agent: *\nAllow: /\n" if _INDEXABLE
            else "User-agent: *\nDisallow: /\n")
    return PlainTextResponse(body)


@app.get("/signin", response_class=HTMLResponse)
def signin_page(request: Request, sent: str = Query(""), err: str = Query("")):
    webauth.scope_for_request(request)
    if webauth.current_email(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "signin.html", {
        "sent": sent, "err": err, "mail_ok": webauth.mail_enabled(),
        "me": "", "tab": "", "css_v": CSS_V, "indexable": _INDEXABLE,
        "app_url": APP_URL, "took_ms": 0.0,
    })


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
    ok, err = webauth.verify(email, code)
    if not ok:
        return _back("/signin", sent=email.strip().lower(), err=err)
    webauth.sign_in_session(request, email)
    return RedirectResponse("/", status_code=303)


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
        return RedirectResponse("/signin", status_code=303)
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
        return RedirectResponse("/signin", status_code=303)

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
            text = pitch.draft_pitch(g, prof, who=me)
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
        return RedirectResponse("/signin", status_code=303)
    import drafts as drafts_mod
    drafts_mod.save(gig_id, text)
    if not back.startswith("/") or back.startswith("//"):
        back = "/gigs"
    return RedirectResponse(
        f"/draft/{gig_id}?saved_ok=1&back={quote_plus(back)}", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, saved_ok: int = Query(0)):
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
        return RedirectResponse("/signin", status_code=303)
    import alerts as alerts_mod
    import profile as profile_mod
    resp = templates.TemplateResponse(request, "profile.html", {
        "prof": profile_mod.load(), "prefs": alerts_mod.load_prefs(),
        "all_skills": ALL_SKILLS, "me": me,
        "saved_ok": bool(saved_ok), "tab": "profile",
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
        return RedirectResponse("/signin", status_code=303)
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
    return RedirectResponse("/profile?saved_ok=1#alerts", status_code=303)


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
            out.setdefault("note", "board is empty — is DATABASE_URL set?")
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
    def link(**over):
        cur = {"q": q, "field": field, "size": size, "source": source,
               "urgent": urgent or "", "where": where, "langs": langs,
               "sort": sort, "qf": qf, "page": ""}
        cur.update(over)
        parts = [f"{k}={quote_plus(str(v))}" for k, v in cur.items() if v not in ("", None)]
        return "/?" + "&".join(parts) if parts else "/"

    # The landing view is the app's Dashboard shape: hero, category groups, a
    # short "Fresh off the boards" list. /gigs is the full board with filters
    # and paging. One handler because they are the same query with a different
    # frame — two would drift the moment either changed.
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

    resp = templates.TemplateResponse(request, "board.html", {
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

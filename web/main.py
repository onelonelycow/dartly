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

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import queries  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))
app = FastAPI(title="Nabbly board", docs_url=None, redoc_url=None)

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
    Filter-chip counts, cached.

    Three GROUP BYs over the whole board, measured at ~43ms — by far the most
    expensive thing on the page, and identical for every visitor. This is the
    same mistake that cost the Streamlit app its memory twice (per-visitor work
    that only depends on the board), so it gets computed once and shared. Keyed
    on the board's row count, so it refreshes when gigs actually arrive rather
    than on a timer.
    """

    def __init__(self):
        self._val = None
        self._key = None
        self._at = 0.0

    def get(self, conn):
        key = queries.board_total(conn)
        # The count is the cheap half of the check; the 120s floor keeps a busy
        # board from rebuilding facets on every single ingest.
        if self._val is None or (key != self._key and time.time() - self._at > 120):
            self._val = queries.facets(conn)
            self._key, self._at = key, time.time()
        return self._val


_facets = _Facets()


def _csv(v: str | None) -> list[str]:
    return [x for x in (v or "").split(",") if x.strip()]


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
        # Two missed refreshes is a real problem, not a blip.
        if s["drift_s"] is not None and s["drift_s"] > sync.REFRESH_S * 3:
            out["ok"] = False
    return out


@app.get("/", response_class=HTMLResponse)
def board(request: Request,
          q: str = Query("", max_length=120),
          field: str = Query(""),
          size: str = Query(""),
          source: str = Query(""),
          urgent: int = Query(0),
          page: int = Query(0, ge=0, le=2000)):
    t0 = time.perf_counter()
    conn = queries.connect(DB_PATH)
    try:
        res = queries.board(keyword=q, job_types=_csv(field), sizes=_csv(size),
                            sources=_csv(source), urgent_only=bool(urgent),
                            page=page, conn=conn)
        facets = _facets.get(conn)
    finally:
        conn.close()

    resp = templates.TemplateResponse(request, "board.html", {
        "res": res, "facets": facets, "q": q,
        "sel_field": _csv(field), "sel_size": _csv(size),
        "urgent": bool(urgent),
        "took_ms": (time.perf_counter() - t0) * 1000,
        "qs": {"q": q, "field": field, "size": size,
               "source": source, "urgent": urgent},
    })
    resp.headers["Cache-Control"] = _CACHE
    return resp

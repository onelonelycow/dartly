"""
telemetry.py — optional mirror of the first-party event stream to PostHog.

OFF UNTIL TWO THINGS ARE TRUE: POSTHOG_API_KEY is set, and the posthog package
is installed. Until then every call here is a no-op, so this file can ship,
sit in main, and change nothing about how Nabbly runs. Turning it on is a
dashboard variable and one line in requirements.txt.

WHY SERVER-SIDE AND NOT THE BROWSER SDK
---------------------------------------
Three reasons, in the order they matter here:

  1. Streamlit strips <script> tags from the main page (analytics.py has said
     so since Google Analytics was tried), so a browser SDK cannot run on
     app.nabbly.co at all — which is exactly where pricing, checkout and plan
     live. Server-side has no such hole: the funnel that ends in money is the
     one it covers best.
  2. No cookies. nabbly.co sets none today, verified against the live headers,
     and a browser SDK would mean a consent banner on a site that currently
     needs none.
  3. The events are already clean. This mirrors analytics.track(), which
     stores an event name, a short label and a session id — referrers are
     already reduced to a bare host with "no paths, no query strings, nothing
     that could identify a person". Nothing new is collected here. The same
     stream simply goes to a second place.

WHAT MUST NEVER GO THROUGH HERE
-------------------------------
Behaviour, not content. Page views, clicks, funnel steps, "generated a draft",
"started checkout" are all fine. What members typed is not: the Include and
Avoid boxes, the bio, the resume, forwarded newsletters. Those hold rates,
availability and sometimes client names, and people wrote them believing they
were private. _clean() below is the enforcement, not the intention — it drops
anything carrying an @ or a longer free-text run, so a future caller cannot
quietly widen this by passing a richer detail string.

The first-party stream in analytics.py stays the source of truth. This is for
the tooling on top — funnels, cohorts, retention — not a replacement.
"""
import os
import re

# EU by default. If this is ever switched on, it should be switched on in the
# region that keeps the promise on the FAQ page easiest to keep.
HOST = (os.environ.get("POSTHOG_HOST") or "https://eu.i.posthog.com").strip()
_KEY = (os.environ.get("POSTHOG_API_KEY") or "").strip()

_MAX_DETAIL = 200          # same cap the events table uses
_client = None
_state = "off"             # off | ready | no-package | failed
_warned = False

# An @ means an address. A run of four or more words means somebody started
# passing prose, which is the failure mode this guard exists for.
_LOOKS_PERSONAL = re.compile(r"@|(?:\S+\s+){3,}\S+")


def _clean(detail: str) -> str:
    """Behaviour survives, content does not."""
    d = (detail or "").strip()[:_MAX_DETAIL]
    return "" if _LOOKS_PERSONAL.search(d) else d


def enabled() -> bool:
    return _connect() is not None


def status() -> str:
    """For the admin page and the uptime check: why it is or is not running."""
    _connect()
    return _state


def _connect():
    """
    Build the client once, and never raise.

    A missing package is a normal state, not an error: the key can be set
    before the dependency is added, and the honest answer then is "not
    running", not a stack trace on somebody's dashboard.
    """
    global _client, _state, _warned
    if _client is not None or not _KEY:
        return _client
    try:
        from posthog import Posthog
    except Exception:
        _state = "no-package"
        if not _warned:
            print("telemetry: POSTHOG_API_KEY is set but the posthog package "
                  "is not installed — add it to requirements.txt to turn this "
                  "on. Nothing is being sent.")
            _warned = True
        return None
    try:
        _client = Posthog(project_api_key=_KEY, host=HOST,
                          # Batched on a background thread so a slow or down
                          # PostHog can never sit in front of a page render.
                          sync_mode=False, timeout=3)
        _state = "ready"
    except Exception as e:
        _state = "failed"
        if not _warned:
            print(f"telemetry: could not start the PostHog client ({e}). "
                  "Nothing is being sent.")
            _warned = True
        _client = None
    return _client


def capture(event: str, detail: str = "", session: str = ""):
    """
    Mirror one already-recorded event. Never allowed to break the page.

    `session` becomes the distinct id. It is the same rotating session key the
    events table uses, not an email and not an account id, so PostHog sees a
    visitor's path through a session without being handed who they are.
    """
    c = _connect()
    if c is None or not event:
        return
    try:
        props = {"source": "nabbly-server"}
        d = _clean(detail)
        if d:
            props["detail"] = d
        c.capture(distinct_id=(session or "anonymous"),
                  event=str(event)[:64], properties=props)
    except Exception:
        pass  # analytics must never take the app down


def flush():
    """Called on shutdown so a batch in flight is not lost."""
    c = _connect()
    if c is not None:
        try:
            c.flush()
        except Exception:
            pass

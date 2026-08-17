"""
web/webauth.py — sign-in for the board service.

SHARES THE APP'S IDENTITY, DOES NOT INVENT A SECOND ONE. The six-digit code
flow, the rate limits, the account records and the Supabase mirror all already
exist in accounts.py, and this calls them. A second user store would be a second
thing to get wrong, and the two would disagree about who is Pro the first time
one of them was updated alone.

What is genuinely new here is the SESSION. Streamlit keeps identity in its own
per-connection state; an HTTP service has cookies. This sets a signed,
HttpOnly cookie holding an email address and nothing else — no token, no
plan, no name. Everything else is looked up per request from accounts, so a
downgrade or an expired trial takes effect immediately rather than whenever
the cookie happens to be reissued.

NO CREDENTIAL EVER GOES IN A URL. The Streamlit app passes its sign-in token as
a query parameter, which is how it survives a page navigation there. A URL is
copied into chats, kept in history, and sent in Referer headers, so this uses a
cookie instead and the token never leaves the server.

THREADING: paths.set_scope() is thread-local and uvicorn reuses threads between
requests, so a scope left over from the previous request on that thread would
silently serve one person another's saved gigs. scope_for_request() is called
at the top of EVERY request, signed in or not, so a stale scope can never be
read. This also means route handlers must stay sync `def` — an `async def`
handler runs many requests on one thread and would break that guarantee.

TESTING SIGN-IN WITHOUT WRITING TO PRODUCTION — READ THIS BEFORE YOU DO IT.
accounts.sign_in() is find-or-create AND mirrors to Supabase, so exercising
this flow against the real DATABASE_URL creates real accounts. It happened:
three test addresses were created in the live account store on 2026-08-13,
each consuming one of the fifty founding slots, because the board service needs
DATABASE_URL to pull the board and the auth path quietly writes as well as
reads. Deleted afterwards, but the fix is not to be careful — it is to run
tests where the write cannot reach:

    DATABASE_URL unset  +  NABBLY_DB=web/board.db

With DATABASE_URL unset, store.enabled() is False, so accounts stay in the
local SQLite file and nothing mirrors. NABBLY_DB points the board at an
already-synced copy, so it still has 50,000 gigs to serve and sync.start() is
skipped. Add MAIL_OUTBOX so codes land in a file, and NABBLY_LOCAL=1 so the
session cookie is not Secure-only over plain http.
"""
import os
import secrets
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import accounts  # noqa: E402
import mailer  # noqa: E402
import paths  # noqa: E402
import people  # noqa: E402

# Reuses the app's cookie secret so both services sign with the same key and a
# rotation is one change. Falls back to a per-process random value, which is
# correct-but-forgetful: sessions do not survive a restart, and that is far
# better than a predictable default that would let anyone forge one.
_SECRET = (os.environ.get("AUTH_COOKIE_SECRET", "").strip()
           or secrets.token_urlsafe(32))
SESSION_COOKIE = "nb_session"

# Which host(s) the session cookie covers.
#
# UNSET IS CORRECT UNTIL board.nabbly.co EXISTS. With no domain, the cookie is
# scoped to whatever host served it, which is right for a service answering on
# nabbly-board.onrender.com — a cookie scoped to ".nabbly.co" from an
# onrender.com response is simply rejected by the browser, and sign-in would
# fail with no visible reason.
#
# Set it to ".nabbly.co" once the board answers on board.nabbly.co, and signing
# in on either host covers both. Without that, a visitor moving between
# app.nabbly.co and the board appears signed out on arrival, because browsers
# do not share cookies across domains.
SESSION_DOMAIN = os.environ.get("NABBLY_COOKIE_DOMAIN", "").strip()
SESSION_MAX_AGE = 60 * 60 * 24 * 30      # 30 days

# Mailing a code is an unauthenticated action that sends mail to an address the
# sender chooses, which is a spam cannon if left open. accounts.issue_code
# already bounds attempts PER ADDRESS; this bounds requests per client so
# nobody can walk a list of addresses. In-process and best-effort — a real
# deployment behind multiple instances would want this in the database, and
# with one instance it is exactly right.
_CODE_WINDOW_S = 900
_CODE_MAX = 5
_recent: dict[str, list] = {}


def mail_enabled() -> bool:
    """Offering email sign-in without being able to send is a dead end."""
    return mailer.enabled()


def _client(request) -> str:
    # Render terminates TLS and proxies, so the socket peer is the proxy.
    # Trust the first hop only; the rest of the chain is client-supplied.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def rate_ok(request) -> bool:
    now = time.time()
    key = _client(request)
    hits = [t for t in _recent.get(key, []) if now - t < _CODE_WINDOW_S]
    if len(hits) >= _CODE_MAX:
        _recent[key] = hits
        return False
    hits.append(now)
    _recent[key] = hits
    # Bounded: without this the dict grows one entry per client forever, which
    # is a slow memory leak reachable by anyone who can make a request.
    if len(_recent) > 4096:
        for k in [k for k, v in _recent.items()
                  if not v or now - v[-1] > _CODE_WINDOW_S][:2048]:
            _recent.pop(k, None)
    return True


def send_code(email: str) -> tuple[bool, str]:
    """Mint a code and mail it. Same path the Streamlit app uses."""
    email = (email or "").strip().lower()
    if not people.valid_email(email):
        return False, "That doesn't look like an email address."
    if not mail_enabled():
        return False, "Email sign-in isn't available right now."
    code, err = accounts.issue_code(email)
    if err:
        return False, err
    subject, html_body, text_body = mailer.signin_code_email(code)
    if not mailer.send(email, subject, html_body, text_body):
        # Never leave someone staring at a code box for mail that never left.
        return False, "We couldn't send that email. Try again in a minute."
    return True, ""


def verify(email: str, code: str, campaign: str = "") -> tuple[bool, str]:
    """
    Check a code and, only if it is right, resolve the account.

    Deliberately nothing is created before the code is proven — same rule the
    app follows. An unverified address must not be able to mint an account.

    CAMPAIGN MUST BE PASSED THROUGH. accounts.sign_in() reads it to apply
    PARTNER_GRANTS, and it defaulted to "" here, so a Next Northwest member who
    arrived on ?ref=nextnw and signed in on the board was created on FREE with
    no 90-day grant — silently contradicting the offer the landing page made
    them. The app hit this exact bug on its own Google path; this is the same
    bug on this service, and it becomes reachable the moment the marketing site
    points anyone here.
    """
    email = (email or "").strip().lower()
    ok, err = accounts.check_code(email, code)
    if not ok:
        return False, err or "That code didn't work."
    acc, _is_new = accounts.sign_in(email, source="board", campaign=campaign)
    if not acc:
        return False, "We couldn't sign you in. Try again."
    return True, ""


def sign_in_google(email: str, campaign: str = "") -> tuple[bool, str]:
    """
    Resolve the account for an address Google has already verified.

    No code to check: googleauth only returns an address Google reports as
    verified, which is a stronger proof than a code we mailed. `source` matches
    what the Streamlit app records for the same act, so the two surfaces do not
    split one member's history across two labels.
    """
    email = (email or "").strip().lower()
    if not email:
        return False, "Google didn't share an email address."
    acc, _is_new = accounts.sign_in(email, source="google", campaign=campaign)
    if not acc:
        return False, "We couldn't sign you in. Try again."
    return True, ""


def sign_in_session(request, email: str):
    request.session.clear()          # never merge into a previous identity
    request.session["email"] = (email or "").strip().lower()
    request.session["at"] = int(time.time())


def sign_out_session(request):
    request.session.clear()


def current_email(request) -> str:
    return (request.session.get("email") or "").strip().lower()


def account_for(request):
    """
    The live account record, or None.

    Looked up per request rather than cached in the cookie, so a plan change,
    an expired trial or a deleted account is reflected immediately.
    """
    email = current_email(request)
    if not email:
        return None
    try:
        return accounts.by_email(email)
    except accounts.StoreUnavailable:
        # "Database unreadable" is not "no such account". Returning None here
        # would sign everybody out for the duration of a blip, so this raises
        # to the caller, which shows a degraded page rather than a logged-out
        # one.
        raise
    except Exception:
        return None


def scope_for_request(request) -> str:
    """
    Point the per-user file helpers at whoever this request is.

    MUST run on every request — see the threading note in the module docstring.
    An anonymous request gets a scratch scope so the helpers still work and
    still write nowhere durable.
    """
    email = current_email(request)
    scope = paths.scope_for(email) if email else "guest-web"
    paths.set_scope(scope)
    return scope

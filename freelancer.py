"""
freelancer.py — connect a member's Freelancer.com account, and bid for them.

WHY THIS EXISTS. Freelancer is the only source on the board where applying is
gated by a login AND there is an API to get past it. Himalayas (the largest
source by volume) hands every job an `applicationLink` out to the employer's
own ATS, and We Work Remotely's API is for employers posting jobs. So "apply
from Nabbly" means, precisely, "place a bid on Freelancer from Nabbly" — about
a quarter of the board, and the quarter where speed to bid actually wins work.

EVERY ENDPOINT AND FIELD BELOW WAS READ OFF developers.freelancer.com on
2026-09-10, not remembered:

  authorize  GET  {accounts}/oauth/authorize
                  response_type=code, client_id, redirect_uri, scope=basic,
                  advanced_scopes=<space-separated NUMERIC ids>, prompt
  token      POST {accounts}/oauth/token   (form-encoded)
                  grant_type=authorization_code|refresh_token, code|refresh_token,
                  client_id, client_secret, redirect_uri
             -> {scope, access_token, refresh_token, expires_in, token_type}
  api        *    {api}/projects/0.1/...   header: freelancer-oauth-v1: <token>
  bid        POST /projects/0.1/bids/      scopes: basic + fln:project_manage
  retract    PUT  /projects/0.1/bids/{id}/ action=retract

SANDBOX BY DEFAULT. Bids are scarce (a free Freelancer account gets six a
month) and irreversible enough to matter, so this talks to the sandbox unless
someone deliberately sets FREELANCER_LIVE=1. Getting that backwards would
spend real bids from real accounts during development.
"""
import base64
import hashlib
import os
import time

import requests

# The advanced scope we need, by NUMERIC id — the authorize endpoint takes ids,
# not names. 2 = fln:project_manage, "Manage your projects, bids and milestones
# on freelancer.com on your behalf". We ask for nothing else: project_create,
# contest_*, messaging and location tracking are all out of scope for placing a
# bid, and an app that asks for more than it uses is one people decline.
SCOPE_PROJECT_MANAGE = "2"

CLIENT_ID = os.environ.get("FREELANCER_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("FREELANCER_CLIENT_SECRET", "").strip()
LIVE = os.environ.get("FREELANCER_LIVE") == "1"

_ACCOUNTS = ("https://accounts.freelancer.com" if LIVE
             else "https://accounts.freelancer-sandbox.com")
_API = ("https://www.freelancer.com/api" if LIVE
        else "https://www.freelancer-sandbox.com/api")

# Where Freelancer sends the browser back. Fixed rather than derived from the
# request for the same reason googleauth fixes its own: behind Render's proxy
# the request's scheme and host are not reliably the public ones, and the
# redirect_uri has to match the registered value character for character.
PUBLIC_URL = (os.environ.get("NABBLY_PUBLIC_URL", "")
              or "https://board.nabbly.co").strip().rstrip("/")
CALLBACK_PATH = "/connect/freelancer/callback"

STATE_KEY = "_flstate"
PENDING_KEY = "_flpending"

_TIMEOUT = 15
# Tokens live 30 days (expires_in: 2592000). Refresh with a day to spare rather
# than on expiry, so a bid never fails because the token died mid-request.
_REFRESH_MARGIN_S = 86400

TOKEN_FILE = "freelancer.json"


def enabled() -> bool:
    """No credentials, no feature — and no half-drawn Connect button."""
    return bool(CLIENT_ID and CLIENT_SECRET)


def redirect_uri() -> str:
    return f"{PUBLIC_URL}{CALLBACK_PATH}"


# ---------------------------------------------------------------------------
# tokens at rest
#
# Freelancer's API T&Cs say "All Data should be stored and served using strong
# encryption", and a refresh token here is the right to bid as that person for
# thirty days. paths.write_user_json mirrors to Supabase, so the plaintext
# would otherwise sit in a table this code reads over the open internet.
#
# Fernet (AES-128-CBC + HMAC-SHA256, timestamped) from `cryptography`, keyed by
# a SHA-256 of AUTH_COOKIE_SECRET. Deriving from that secret rather than adding
# another one is deliberate: rotating it already signs everybody out, so having
# it also invalidate stored third-party tokens is the behaviour you want, not a
# surprise.
# ---------------------------------------------------------------------------
def _fernet():
    from cryptography.fernet import Fernet
    secret = (os.environ.get("FREELANCER_TOKEN_KEY")
              or os.environ.get("AUTH_COOKIE_SECRET") or "").strip()
    if not secret:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def save_tokens(tok: dict) -> bool:
    """Encrypt and store this person's tokens. Scope comes from paths."""
    import paths
    f = _fernet()
    if not f:
        print("  freelancer: no AUTH_COOKIE_SECRET — refusing to store a token "
              "in plaintext", flush=True)
        return False
    body = {
        "access_token": tok.get("access_token", ""),
        "refresh_token": tok.get("refresh_token", ""),
        "expires_at": time.time() + float(tok.get("expires_in") or 0),
        "user_id": tok.get("user_id"),
        "username": tok.get("username", ""),
        "sandbox": not LIVE,
    }
    import json
    blob = f.encrypt(json.dumps(body).encode()).decode()
    # Only the ciphertext and the two things the UI needs to render a
    # "connected as" row are stored unencrypted — never a token.
    paths.write_user_json(TOKEN_FILE, {
        "v": 1, "enc": blob,
        "username": body["username"], "sandbox": body["sandbox"],
    })
    return True


def load_tokens() -> dict | None:
    """This person's tokens, refreshed if they are close to expiry."""
    import json
    import paths
    rec = paths.read_user_json(TOKEN_FILE, None)
    if not rec or not rec.get("enc"):
        return None
    f = _fernet()
    if not f:
        return None
    try:
        body = json.loads(f.decrypt(rec["enc"].encode()).decode())
    except Exception:
        # A rotated secret, or a record written by the other environment.
        # Neither is an error worth raising at a caller who just wanted to
        # know whether to draw a Connect button.
        return None
    # A token minted against the sandbox is useless against production and
    # vice versa; treat the mismatch as "not connected" rather than sending a
    # sandbox token to the live API.
    if bool(body.get("sandbox")) != (not LIVE):
        return None
    if body.get("expires_at", 0) - time.time() < _REFRESH_MARGIN_S:
        fresh, err = refresh(body.get("refresh_token", ""))
        if err:
            return None
        fresh["username"] = body.get("username", "")
        fresh["user_id"] = body.get("user_id")
        save_tokens(fresh)
        fresh["expires_at"] = time.time() + float(fresh.get("expires_in") or 0)
        return fresh
    return body


def connected() -> dict | None:
    """What the profile page needs to render, without decrypting anything."""
    import paths
    rec = paths.read_user_json(TOKEN_FILE, None)
    if not rec or not rec.get("enc"):
        return None
    return {"username": rec.get("username", ""), "sandbox": rec.get("sandbox")}


def disconnect() -> bool:
    import paths
    paths.write_user_json(TOKEN_FILE, {})
    return True


# ---------------------------------------------------------------------------
# the handshake
# ---------------------------------------------------------------------------
def new_state() -> str:
    import secrets
    return secrets.token_urlsafe(24)


def authorize_url(state: str) -> str:
    from urllib.parse import urlencode
    # `state` IS NOT IN FREELANCER'S DOCUMENTED PARAMETER LIST. It is sent
    # anyway because most OAuth servers echo it and it costs nothing, but
    # NOTHING HERE MAY ASSUME IT COMES BACK — web/main.py's callback treats a
    # missing state as unverified and routes to a confirmation page instead of
    # binding the account silently. See the note there.
    return f"{_ACCOUNTS}/oauth/authorize?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri(),
        "scope": "basic",
        "advanced_scopes": SCOPE_PROJECT_MANAGE,
        "prompt": "select_account consent",
        "state": state,
    })


def _token_request(data: dict) -> tuple[dict, str]:
    try:
        r = requests.post(f"{_ACCOUNTS}/oauth/token", data=data,
                          headers={"content-type":
                                   "application/x-www-form-urlencoded"},
                          timeout=_TIMEOUT)
    except Exception as e:
        return {}, f"Couldn't reach Freelancer ({type(e).__name__})."
    if r.status_code >= 300:
        # NEVER echo the body: it is the one place a client_secret can appear
        # in an error, and this string is rendered to a page.
        print(f"  freelancer: token endpoint {r.status_code}", flush=True)
        return {}, "Freelancer refused that sign-in. Try connecting again."
    try:
        out = r.json()
    except Exception:
        return {}, "Freelancer sent something we couldn't read."
    if not out.get("access_token"):
        return {}, "Freelancer didn't return an access token."
    return out, ""


def exchange_code(code: str) -> tuple[dict, str]:
    return _token_request({
        "grant_type": "authorization_code", "code": code,
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": redirect_uri(),
    })


def refresh(refresh_token: str) -> tuple[dict, str]:
    if not refresh_token:
        return {}, "No refresh token stored."
    return _token_request({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    })


# ---------------------------------------------------------------------------
# the API
# ---------------------------------------------------------------------------
def _call(method: str, path: str, token: str, **kw) -> tuple[dict, str]:
    try:
        r = requests.request(method, f"{_API}{path}",
                             headers={"freelancer-oauth-v1": token},
                             timeout=_TIMEOUT, **kw)
    except Exception as e:
        return {}, f"Couldn't reach Freelancer ({type(e).__name__})."
    try:
        body = r.json()
    except Exception:
        return {}, f"Freelancer sent a {r.status_code} we couldn't read."
    if body.get("status") != "success":
        msg = (body.get("message") or body.get("error_code")
               or f"HTTP {r.status_code}")
        return {}, str(msg)[:200]
    return body.get("result") or {}, ""


def me(token: str) -> tuple[dict, str]:
    """Who this token belongs to — the bidder_id every bid needs."""
    return _call("GET", "/users/0.1/self/", token)


def bids_left(token: str) -> tuple[int | None, str]:
    """
    How many bids this person has left this month.

    THE WHOLE REASON THE UI NEEDS THIS. A free Freelancer account gets six
    bids a month (paid tiers: 15 / 50 / 100 / 300 / 500). A product that makes
    bidding one click without showing the remaining count would help somebody
    burn all six before lunch, which is worse than not shipping the button.
    """
    res, err = _call("GET", "/users/0.1/self/?membership_details=true"
                     "&user_membership_details=true", token)
    if err:
        return None, err
    for key in ("bid_limit", "bids_left", "remaining_bids"):
        if isinstance(res, dict) and res.get(key) is not None:
            return int(res[key]), ""
    status = (res or {}).get("membership_package") or {}
    if status.get("bid_limit") is not None:
        return int(status["bid_limit"]), ""
    # Shape unconfirmed against a live account — see STEP 1 note in the commit.
    # Returning None means "unknown", and the UI says so rather than inventing
    # a number somebody would spend bids against.
    return None, ""


def place_bid(token: str, project_id: int, bidder_id: int, amount: float,
              period_days: int, description: str) -> tuple[dict, str]:
    """
    POST /projects/0.1/bids/ — scopes basic + fln:project_manage.

    Never called without an explicit submit from the member: the amount, the
    period and the text are all theirs to edit first. A bid is scarce and
    public under their name.
    """
    return _call("POST", "/projects/0.1/bids/", token, json={
        "project_id": int(project_id),
        "bidder_id": int(bidder_id),
        "amount": float(amount),
        "period": int(period_days),
        "milestone_percentage": 100,
        "description": description,
    })


def retract_bid(token: str, bid_id: int) -> tuple[dict, str]:
    """Withdraw a bid — the undo that makes the button safe to offer."""
    return _call("PUT", f"/projects/0.1/bids/{int(bid_id)}/", token,
                 json={"action": "retract"})

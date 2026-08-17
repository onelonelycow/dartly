"""
web/googleauth.py — "Continue with Google" for the board service.

The Streamlit app gets this from st.login(), which is Streamlit's own OIDC
client and does not exist outside Streamlit. This is the same handshake done by
hand, against the same Google credential, resolving to the same accounts.py
record and the same `.nabbly.co` session cookie. Someone who signs in with
Google here is the same member, with the same plan, as if they had done it on
the app.

REGISTERING THE REDIRECT URI IS A MANUAL STEP AND NOTHING HERE CAN DO IT.
Google rejects any redirect_uri not listed on the credential, character for
character, with redirect_uri_mismatch. The board's URI has to be added in the
Google Cloud console alongside the app's existing one.

WHY THE USERINFO ENDPOINT RATHER THAN READING THE ID TOKEN. An id_token is a
JWT, and a JWT is only worth what its verification is worth: the signature, the
issuer, the audience and the expiry all have to be checked against Google's
rotating keys, and getting any one of them wrong turns "verified identity" into
"whatever the caller sent". The code is exchanged server to server over TLS,
authenticated with the client secret, and the resulting access token is spent
on one more server-to-server call that returns the address. Nothing
attacker-controlled is ever parsed, so there is no verification to get wrong.

IF IT ISN'T CONFIGURED: enabled() is False and the sign-in page shows the email
form alone. Same rule auth.py follows for the app, so local development and any
deploy without Google credentials keep working rather than offering a button
that fails.
"""
import os
import secrets

import requests

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

# Where Google is told to come back to. An env var rather than something
# derived from the request: behind Render's proxy the request's own idea of its
# scheme and host is not reliably the public one, and a redirect_uri that
# differs from the registered value by so much as "http" fails the handshake.
PUBLIC_URL = (os.environ.get("NABBLY_PUBLIC_URL", "") or "").strip().rstrip("/")

CALLBACK_PATH = "/auth/google/callback"

_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN = "https://oauth2.googleapis.com/token"
_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"

# Every network call here sits between a person and their sign-in, so none of
# them may hang. Google being slow should fail the attempt and show a message,
# not hold a worker open.
_TIMEOUT = 10

STATE_KEY = "_gstate"


def enabled() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET)


def redirect_uri(request=None) -> str:
    base = PUBLIC_URL
    if not base and request is not None:
        base = str(request.base_url).rstrip("/")
    return f"{base}{CALLBACK_PATH}"


def new_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(state: str, request=None) -> str:
    """Where to send the browser to start the handshake."""
    from urllib.parse import urlencode
    return _AUTHORIZE + "?" + urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri(request),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        # Ask for the account chooser rather than silently reusing whichever
        # Google account the browser happens to be signed into. Someone with a
        # work and a personal address should get to say which one this is.
        "prompt": "select_account",
    })


def email_for_code(code: str, request=None) -> tuple[str, str]:
    """
    Trade the one-time code for a verified email. Returns (email, error).

    Only ever returns an address Google itself reports as verified. An
    unverified one would let anyone who can add an unconfirmed address to a
    Google account sign in as that address here.
    """
    if not enabled():
        return "", "Google sign-in isn't available right now."
    try:
        r = requests.post(_TOKEN, timeout=_TIMEOUT, data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": redirect_uri(request),
            "grant_type": "authorization_code",
        })
        if r.status_code != 200:
            # Google's own reason is the useful half of this and it never
            # reaches the visitor, so log it and show something plain.
            print(f"  ! google token exchange {r.status_code}: {r.text[:300]}",
                  flush=True)
            return "", "Google couldn't complete that sign-in. Try again."
        access = (r.json() or {}).get("access_token") or ""
        if not access:
            return "", "Google couldn't complete that sign-in. Try again."

        u = requests.get(_USERINFO, timeout=_TIMEOUT,
                         headers={"Authorization": f"Bearer {access}"})
        if u.status_code != 200:
            print(f"  ! google userinfo {u.status_code}: {u.text[:300]}",
                  flush=True)
            return "", "Google couldn't complete that sign-in. Try again."
        info = u.json() or {}
        email = (info.get("email") or "").strip().lower()
        if not email:
            return "", "Google didn't share an email address."
        if not info.get("email_verified"):
            return "", ("That Google account's email isn't verified. "
                        "Use the email code instead.")
        return email, ""
    except requests.RequestException as e:
        print(f"  ! google sign-in unreachable: {type(e).__name__}: {e}",
              flush=True)
        return "", "Couldn't reach Google just now. Try again in a moment."

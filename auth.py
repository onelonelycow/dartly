"""
auth.py — "Continue with Google", and the plumbing that makes it work on Render.

WHY: the first version of sign-in put a random token in the URL. It kept the
signup to one field, which was the point, but anyone holding the link is that
person, and a typed email was never checked, so nothing stopped someone
entering an address that wasn't theirs. Google hands us an email it has already
verified, which removes both problems.

WHAT GOOGLE DOES AND DOESN'T DO HERE: it answers "which email address is this,
really". That is all. Whether that person is on a trial, on Pro, or expired
still lives in accounts.py, so the entitlement logic did not have to change.

THE SECRETS FILE: Streamlit reads OIDC settings from .streamlit/secrets.toml,
which is a file, and secrets do not belong in a repo. So we write it at boot
from environment variables instead. On Render you set them in the dashboard
next to SIGNUP_WEBHOOK_URL, nothing is committed, and the file lives only on
the instance's own temporary disk.

IF IT ISN'T CONFIGURED: enabled() is False and the app falls back to the email
form. Local development and any deploy without Google credentials keep working
exactly as before, rather than showing a broken button.
"""
import os
import secrets as _secrets
from pathlib import Path

CONFIG_DIR = Path(__file__).parent / ".streamlit"
SECRETS_PATH = CONFIG_DIR / "secrets.toml"

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
# Must match a redirect URI registered on the Google credential, exactly.
REDIRECT_URI = (os.environ.get("OAUTH_REDIRECT_URI")
                or os.environ.get("PUBLIC_URL", "http://localhost:8501").rstrip("/")
                + "/oauth2callback")
COOKIE_SECRET = os.environ.get("AUTH_COOKIE_SECRET", "").strip()

_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
_ready: bool | None = None


def _quote(v: str) -> str:
    """TOML string, with anything that would break the file escaped."""
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def configure() -> bool:
    """
    Write .streamlit/secrets.toml from the environment. Returns True if Google
    sign-in is usable. Safe to call on every rerun; the file is written once.
    """
    global _ready
    if _ready is not None:
        return _ready
    if not (CLIENT_ID and CLIENT_SECRET):
        _ready = False
        return False

    # The cookie secret signs the session cookie. A generated one is fine for a
    # single instance, but it changes on restart and signs everyone out, so set
    # AUTH_COOKIE_SECRET in Render to keep people logged in across deploys.
    cookie = COOKIE_SECRET or _secrets.token_urlsafe(32)
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SECRETS_PATH.write_text(
            "# Generated at startup from environment variables by auth.py.\n"
            "# Do not commit this file; it is rewritten on every boot.\n"
            "[auth]\n"
            f"redirect_uri = {_quote(REDIRECT_URI)}\n"
            f"cookie_secret = {_quote(cookie)}\n"
            "\n[auth.google]\n"
            f"client_id = {_quote(CLIENT_ID)}\n"
            f"client_secret = {_quote(CLIENT_SECRET)}\n"
            f"server_metadata_url = {_quote(_DISCOVERY)}\n"
        )
        SECRETS_PATH.chmod(0o600)
        _ready = True
    except Exception:
        _ready = False       # read-only disk, odd permissions: fall back quietly
    return _ready


def enabled() -> bool:
    return configure()


def google_email(st) -> str:
    """
    The verified Google address of whoever is logged in, or ''.

    Only trusts an address Google says it verified. An unverified one would let
    somebody claim a Google account attached to an address they don't own,
    which is the exact hole this was meant to close.
    """
    if not enabled():
        return ""
    try:
        user = st.user
        if not getattr(user, "is_logged_in", False):
            return ""
        if user.get("email_verified") is False:
            return ""
        return (user.get("email") or "").strip().lower()
    except Exception:
        return ""


def display_name(st) -> str:
    try:
        u = st.user
        return (u.get("given_name") or u.get("name") or "").strip()
    except Exception:
        return ""


def setup_help() -> str:
    """Shown on the admin page so the steps aren't only in a chat log."""
    return (
        "Google sign-in is off. To switch it on, create an OAuth client "
        "(type: Web application) at console.cloud.google.com, add "
        f"`{REDIRECT_URI}` as an authorised redirect URI, then set "
        "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and AUTH_COOKIE_SECRET in "
        "Render. Until then the email form is used."
    )

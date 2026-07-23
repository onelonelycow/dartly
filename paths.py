"""
paths.py — where the app keeps its data files.

By default everything lives next to the code (great for running locally). On a
host like Render you can set the DATA_DIR environment variable to a mounted
persistent disk (e.g. /var/data) and the database, profiles, and alert
preferences will survive redeploys, with no code changes needed.

Two kinds of file live here:

  * Shared, one copy for the whole app: the gig database, the people table.
  * Per person: profile, alert channels, saved drafts.

The second kind used to be shared too, which was fine while the only user was
the person who built it. With more than one visitor it meant everyone loaded
and overwrote the same profile, and the Alerts page showed whichever phone
number was typed last. Anything private now goes through user_file(), which
keeps each person's copy in their own directory.
"""
import hashlib
import os
import threading
from pathlib import Path

# DATA_DIR env var wins; otherwise use the folder this file sits in.
DATA_DIR = Path(os.environ.get("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_DIR = DATA_DIR / "users"

# Streamlit serves every visitor from one process, so the "who am I" pointer
# has to be per thread. A module-level string would let one visitor's request
# read another's profile.
_local = threading.local()
_ANON = "_anon"


def data_file(name: str) -> Path:
    """A file shared by the whole app (the gig db, the people table)."""
    return DATA_DIR / name


def scope_for(email: str | None) -> str:
    """
    A stable, opaque directory name for one person.

    Hashed rather than using the raw email so that anyone who gets a look at
    the disk does not get a list of everyone's address, and so the name is
    always filesystem-safe.
    """
    email = (email or "").strip().lower()
    if not email:
        return _ANON
    return hashlib.sha256(email.encode()).hexdigest()[:24]


def set_scope(scope: str | None):
    """Point subsequent user_file() calls at this person. Call once per run."""
    _local.scope = scope or _ANON


def get_scope() -> str:
    return getattr(_local, "scope", _ANON)


def user_file(name: str, scope: str | None = None) -> Path:
    """A file private to one person (profile, alert channels, drafts)."""
    d = USERS_DIR / (scope or get_scope())
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def all_scopes() -> list[str]:
    """Every person with saved data. Used by the background alerter."""
    if not USERS_DIR.exists():
        return []
    return sorted(p.name for p in USERS_DIR.iterdir()
                  if p.is_dir() and p.name != _ANON)

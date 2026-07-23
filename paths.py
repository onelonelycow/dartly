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


def read_user_json(name: str, default):
    """
    Load one of this person's JSON files, healing a wiped disk.

    If the local file is gone but the durable mirror has a copy (which is what a
    Render redeploy looks like: fresh disk, data still in Supabase), pull it
    back, rewrite it locally so the rest of the run is fast, and return it.
    """
    import json
    import store
    p = user_file(name)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    # Only a signed-in person has durable data worth restoring. A not-signed-in
    # visitor's scope is a per-session scratch space that's never mirrored, so
    # don't hit the database for it — otherwise every anonymous page load makes
    # a needless round-trip (and, with a bad password, a needless auth failure).
    if not _is_scratch(get_scope()):
        obj = store.get(get_scope(), name)
        if obj is not None:
            try:
                p.write_text(json.dumps(obj, indent=2))
            except Exception:
                pass
            return obj
    return default


def write_user_json(name: str, obj):
    """Save one of this person's JSON files locally and to the durable mirror."""
    import json
    import store
    user_file(name).write_text(json.dumps(obj, indent=2))
    if not _is_scratch(get_scope()):
        store.put(get_scope(), name, obj)


_SCRATCH_PREFIXES = ("free-", "guest-")   # "guest-" is the pre-rename name


def _is_scratch(name: str) -> bool:
    return name == _ANON or name.startswith(_SCRATCH_PREFIXES)


def all_scopes() -> list[str]:
    """
    Every signed-in person's directory.

    Skips the throwaway ones. A not-signed-in visitor gets a "free-" scratch
    space that lasts as long as their browser session, and treating those as
    real people would have the background alerter walking thousands of empty
    directories that nobody can be reached at.
    """
    if not USERS_DIR.exists():
        return []
    return sorted(p.name for p in USERS_DIR.iterdir()
                  if p.is_dir() and not _is_scratch(p.name))


def prune_scratch(max_age_hours: float = 48) -> int:
    """
    Delete stale not-signed-in scratch directories.

    Every anonymous visitor mints a "free-" (or, before the rename, "guest-")
    directory. They're keyed to a browser session that's long gone, so without
    a sweep they pile up on the disk forever. A signed-in person's directory is
    named from their email hash and is never touched here. Returns how many
    were removed.
    """
    import shutil
    import time
    if not USERS_DIR.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for p in USERS_DIR.iterdir():
        if not (p.is_dir() and _is_scratch(p.name)):
            continue
        try:
            if p.stat().st_mtime < cutoff:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    return removed

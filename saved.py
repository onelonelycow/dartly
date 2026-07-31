"""
saved.py — gigs someone has bookmarked to come back to.

The board moves fast, which is the whole point of it, and that's exactly why
this exists: a gig worth a proper reply at 11pm is buried under four hundred
newer ones by morning. Saving pins it so it stays findable.

Stored as a list of gig ids in saved.json via the shared per-account helpers,
so this inherits everything they already do — scoped to the signed-in person,
mirrored to Supabase, and healed back after a Render redeploy wipes the disk.
Same shape as drafts.py, deliberately: a new store here would be a second
thing to get wrong for no gain.

Ids, not copies of the gig. A saved row would go stale the moment the posting
was re-classified or its description backfilled, and it would quietly resurrect
gigs the board had already archived as dead. Holding the id means a saved gig
is always rendered from whatever the board currently knows.
"""
from paths import read_user_json, write_user_json

_FILE = "saved.json"


def _all() -> list[str]:
    v = read_user_json(_FILE, [])
    # Tolerate anything that isn't a list: this file is small, user-scoped, and
    # restored from a network mirror, so "unreadable" should degrade to "you
    # have nothing saved yet" rather than take down the page that reads it.
    return [str(x) for x in v] if isinstance(v, list) else []


def ids() -> list[str]:
    """Every saved gig id, newest save first."""
    return _all()


def has(gig_id) -> bool:
    return str(gig_id) in _all()


def add(gig_id):
    """Save a gig. No-op if it's already saved."""
    gid = str(gig_id)
    cur = _all()
    if gid in cur:
        return
    # Prepended, so the list reads newest-saved-first without needing a
    # timestamp per entry — the order IS the record of when they saved it.
    write_user_json(_FILE, [gid] + cur)


def remove(gig_id):
    gid = str(gig_id)
    cur = _all()
    if gid in cur:
        write_user_json(_FILE, [x for x in cur if x != gid])


def toggle(gig_id) -> bool:
    """Flip saved state. Returns True if it is now saved."""
    if has(gig_id):
        remove(gig_id)
        return False
    add(gig_id)
    return True


def count() -> int:
    return len(_all())

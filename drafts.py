"""
drafts.py — saved pitch drafts (Pro).

When a Pro user tweaks a drafted reply, we keep their edited version so they can
come back and refine it later instead of losing it to a fresh auto-draft. Stored
in drafts.json (keyed by gig id) via the shared DATA_DIR.
"""
from paths import read_user_json, write_user_json


def _all() -> dict:
    return read_user_json("drafts.json", {})


def load(gig_id) -> str:
    """The user's saved draft for this gig, or '' if none."""
    return _all().get(str(gig_id), "")


def save(gig_id, text: str):
    d = _all()
    d[str(gig_id)] = text
    write_user_json("drafts.json", d)


def delete(gig_id):
    d = _all()
    if str(gig_id) in d:
        del d[str(gig_id)]
        write_user_json("drafts.json", d)


def has(gig_id) -> bool:
    return bool(_all().get(str(gig_id)))

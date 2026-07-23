"""
drafts.py — saved pitch drafts (Pro).

When a Pro user tweaks a drafted reply, we keep their edited version so they can
come back and refine it later instead of losing it to a fresh auto-draft. Stored
in drafts.json (keyed by gig id) via the shared DATA_DIR.
"""
import json

from paths import user_file

def _path():
    return user_file("drafts.json")


def _all() -> dict:
    PATH = _path()
    if PATH.exists():
        try:
            return json.loads(PATH.read_text())
        except Exception:
            pass
    return {}


def load(gig_id) -> str:
    """The user's saved draft for this gig, or '' if none."""
    return _all().get(str(gig_id), "")


def save(gig_id, text: str):
    d = _all()
    d[str(gig_id)] = text
    _path().write_text(json.dumps(d, indent=2))


def delete(gig_id):
    d = _all()
    if str(gig_id) in d:
        del d[str(gig_id)]
        _path().write_text(json.dumps(d, indent=2))


def has(gig_id) -> bool:
    return bool(_all().get(str(gig_id)))

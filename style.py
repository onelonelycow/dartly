"""
style.py — per-account learning: how this person actually finalizes a draft.

pitch.py writes the AI's first attempt at a gig; drafts.py stores whatever
the person ends up saving. Nothing used to compare the two, so nothing
captured HOW someone changes a draft — a shorter open, fewer questions, a
different sign-off habit. This does: it keeps the AI's original attempt per
gig (written once, never overwritten, so later re-edits still diff against
what the AI actually first wrote), and at save time records a bounded
rolling history of (original, edited) pairs. pitch.py's prompt then includes
the most recent couple of pairs as real examples of this person's own
editing instincts, so the next draft starts closer to where they'd end up
by hand.

Everything here reads and writes through paths.py's per-account scope, the
same way profile.py and drafts.py already do — no explicit account id is
threaded through, because whichever account is signed in during this request
is whichever account's files these functions touch.
"""
import difflib

from paths import read_user_json, write_user_json

_MAX_HISTORY = 3
# A ratio above this is a typo fix or a comma, not a style choice — not worth
# spending prompt tokens on every future draft to relearn it.
_SIMILARITY_CEILING = 0.97


def stash_original(gig_id, text: str):
    """Record the AI's first attempt at this gig, once. Idempotent on purpose:
    a later "Start fresh" regenerate calls this again, and it must NOT
    overwrite the true original — the learning signal is "what did the AI
    first suggest" vs. "what did this person settle on," not vs. whatever
    the most recent regenerate happened to produce."""
    if not text:
        return
    d = read_user_json("draft_originals.json", {})
    key = str(gig_id)
    if key not in d:
        d[key] = text
        write_user_json("draft_originals.json", d)


def original_for(gig_id) -> str:
    return read_user_json("draft_originals.json", {}).get(str(gig_id), "")


def record_edit(gig_id, edited: str):
    """Compare what got saved against the AI's original attempt for this
    gig, and keep the pair if it's a real style choice, not noise."""
    original = original_for(gig_id).strip()
    edited = (edited or "").strip()
    if not original or not edited or original == edited:
        return
    ratio = difflib.SequenceMatcher(None, original, edited).ratio()
    if ratio > _SIMILARITY_CEILING:
        return
    hist = read_user_json("edit_history.json", [])
    # One entry per gig — a second edit of the same draft replaces the first
    # rather than filling the rolling window with the same gig twice.
    hist = [h for h in hist if h.get("gig_id") != str(gig_id)]
    hist.append({"gig_id": str(gig_id), "original": original, "edited": edited})
    write_user_json("edit_history.json", hist[-_MAX_HISTORY:])


def recent_edits(limit: int = 2) -> list[dict]:
    """The most recent real edits, freshest last — for pitch.py's prompt."""
    return read_user_json("edit_history.json", [])[-limit:]

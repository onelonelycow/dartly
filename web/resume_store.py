"""
resume_store.py — a member's resume text, in memory, for the length of a visit.

WHY NOT A DATABASE. The app has held resumes in st.session_state since the
feature shipped, and site/privacy.html tells people so: processed only to write
their reply, never stored. Moving the upload to the board must not quietly turn
that into a row on a disk somewhere. So this is the same guarantee in a
different framework — a process-local dict, never written anywhere, gone when
the service restarts.

SAFE ONLY BECAUSE THE BOARD RUNS ONE WORKER. render.yaml starts uvicorn with
--workers 1, so there is exactly one process and one dict. If that ever becomes
two, an upload would land on one worker and be invisible to the other, and this
file is where that breaks — the fix then is a shared store with the same
promise, not more workers with this.

TTL rather than "when the tab closes", which is the one honest difference from
the Streamlit version: HTTP has no way to know a tab closed. Two hours is long
enough to read the board and write a few replies, short enough that a shared
computer does not hand the next person a resume.
"""
import time

TTL_S = 2 * 60 * 60        # a visit, not a subscription
MAX_HELD = 500             # a ceiling, so a flood cannot eat the instance
MAX_CHARS = 20_000         # same cap resume.py already applies

_held: dict[str, tuple[str, float]] = {}


def _sweep(now: float):
    """Drop anything expired. Cheap, and runs on the paths that touch it."""
    for k in [k for k, (_, exp) in _held.items() if exp <= now]:
        _held.pop(k, None)


def put(sid: str, text: str):
    if not sid:
        return
    now = time.time()
    _sweep(now)
    text = (text or "").strip()[:MAX_CHARS]
    if not text:
        _held.pop(sid, None)
        return
    # Oldest out first if somebody is trying to fill the process with resumes.
    if len(_held) >= MAX_HELD and sid not in _held:
        oldest = min(_held, key=lambda k: _held[k][1])
        _held.pop(oldest, None)
    _held[sid] = (text, now + TTL_S)


def get(sid: str) -> str:
    if not sid:
        return ""
    now = time.time()
    _sweep(now)
    held = _held.get(sid)
    return held[0] if held else ""


def clear(sid: str):
    _held.pop(sid, None)


def held_chars(sid: str) -> int:
    return len(get(sid))

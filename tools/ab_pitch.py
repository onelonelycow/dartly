"""
ab_pitch.py — run one real gig through the current draft prompt and a proposed
one, print both, and change nothing.

pitch.SYSTEM is tuned line by line and is the only thing standing between a
drafted reply and something that reads as generated, so it does not get edited
on instinct. This writes no files and mutates no module state: it builds the
candidate as a separate string, calls the model twice, and prints the pair for
a human to judge.

Run:  .venv/bin/python tools/ab_pitch.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import pitch                                              # noqa: E402

# A REAL POSTING, NOT A FIXTURE. Captured from board.nabbly.co on 2026-08-22;
# this is the gig the demo video was built from. Embedded rather than read out
# of the local demand_radar.db, which is the Streamlit app's schema and has no
# sort_at column, so web.queries cannot read it. draft_pitch only ever touches
# these five fields (see pitch.py:179-189).
GIG = {
    "id": 344,
    "title": "Luxury Skincare Packaging Design",
    "job_type": "Design / creative",
    "size_tier": "Medium",
    "urgency": "",
    "body": (
        "I'm launching a premium skincare line and need a complete packaging "
        "concept that instantly signals luxury on the shelf and online. The "
        "product family includes a face serum, moisturizer, and eye cream, all "
        "housed in glass containers; I'd like an outer carton that complements "
        "the weight and elegance of the bottles. Here's what I have in mind: "
        "rich, refined visuals, a restrained palette, and typography that reads "
        "clearly at small sizes. Deliverables should include dielines and "
        "print-ready files."
    ),
}

# The delta under test. Everything the current prompt says about sounding human
# is about avoiding tells; none of it asks the reply to be WARM. These four are
# additive — the existing rules still apply.
ADDITIONS = """\
- Write to them, not about the job. "your glass bottles" beats "the glass \
containers"; "you'll want" beats "the requirement is". If a sentence could \
just as easily describe the project to a stranger, rewrite it so it is aimed \
at the person reading.
- No colon-led labels. "My approach:", "Quick question:", "A couple of \
things:" are slide headings pasted into a message. Say the thing in a sentence \
instead.
- Stack fewer nouns. "nail the colour and material story" is three nouns doing \
one verb's work, and noun-stacking is what makes competent writing read cold. \
Prefer the verb.
- Let one human beat through: a reaction, a preference, something they would \
only say if they had actually thought about it. "I'd want to see the bottle \
before I touched the carton." Not praise, not enthusiasm — just evidence that \
a person is on the other end.\
"""

ANCHOR = '- Skip transition scaffolding: "That said", "Additionally", "Furthermore".'
CANDIDATE = pitch.SYSTEM.replace(ANCHOR, ANCHOR + "\n" + ADDITIONS)
assert CANDIDATE != pitch.SYSTEM, "anchor line not found — prompt has moved"

PROFILE = {
    "name": "Alex Rivera",
    "headline": "Brand designer for early-stage teams",
    "bio": "Ten years on brand identity, mostly for SaaS and healthcare.",
    "draft_always": "ten years on brand identity",
    "draft_never": "hourly rates",
    "draft_signoff": "Alex",
    "draft_length": "standard",
}


def run(system: str, gig: dict) -> str:
    """
    One call, with SYSTEM swapped for the duration and restored after.

    THE CACHE KEY DOES NOT INCLUDE THE SYSTEM PROMPT. _cache_key hashes the gig,
    the profile and the resume, so B would be handed A's text and the two would
    look identical for the wrong reason. Reads are forced to miss and writes are
    dropped, so this comparison also cannot poison the shared cache with drafts
    written by a prompt that may never ship.
    """
    import budget
    original, r, wfn = pitch.SYSTEM, budget.cached_ai, budget.cache_ai
    pitch.SYSTEM = system
    budget.cached_ai = lambda key: ""
    budget.cache_ai = lambda key, text: None
    try:
        return pitch.draft_pitch(gig, PROFILE, who="alex@example.com")
    finally:
        pitch.SYSTEM, budget.cached_ai, budget.cache_ai = original, r, wfn


def main():
    if not pitch.ai_available():
        sys.exit("No ANTHROPIC_API_KEY — add it to .env first.")

    gig = GIG

    print("=" * 72)
    print("GIG:", gig.get("title"))
    print("=" * 72)
    for label, system in (("A — CURRENT", pitch.SYSTEM), ("B — CANDIDATE", CANDIDATE)):
        print(f"\n----- {label} " + "-" * (60 - len(label)))
        print(run(system, gig))
    print("\n" + "=" * 72)
    print("Nothing was written. pitch.py is untouched.")


if __name__ == "__main__":
    main()

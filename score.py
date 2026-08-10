"""
score.py — fit scoring (Pro feature).

Turns a gig + your profile into a 0-100 "match" score and a short list of reasons,
so the best-fitting gigs float to the top instead of you filtering by hand.

Weights (roughly): skill 50, keywords 25, budget fit 20, urgency 5.
"""
import re

import config

MONEY = re.compile(r"[$£€]\s?([0-9][0-9,]*)")

# Freelancer.com (and several job boards) post a budget as a fixed tier —
# "$250 - $750", "$30,000 – $50,000" — rather than a number the client typed.
# Taking the largest dollar amount in the post, as this used to do
# unconditionally, means every gig in a tier reads as its tier's UPPER edge,
# so "typical" for any skill dominated by one platform collapses onto
# whichever edge that platform's most common tier happens to sit on — every
# skill on the whole board showed an identical, suspiciously round $250.
# Detecting the range and taking its midpoint is what "budget" actually
# means here, and it's the same number gig_amount's other callers (fit_score,
# the lowball check) want too.
RANGE = re.compile(r"[$£€]\s?([0-9][0-9,]*)\s*(?:-|–|—|to)\s*[$£€]?\s?([0-9][0-9,]*)")


def gig_amount(gig: dict):
    """Largest dollar-ish amount mentioned in a gig, if any — the midpoint
    when it's stated as a range."""
    text = f"{gig.get('title','')} {gig.get('body','')}"
    m = RANGE.search(text)
    if m:
        try:
            lo, hi = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
            if hi >= lo:
                return round((lo + hi) / 2)
        except ValueError:
            pass
    amounts = []
    for m in MONEY.findall(text):
        try:
            amounts.append(int(m.replace(",", "")))
        except ValueError:
            pass
    return max(amounts) if amounts else None


# Every gig field fit_score() reads, including through gig_amount(). Callers
# ranking a whole board narrow to these before building dicts — a board frame
# carries 18 columns and converting the other 13 per gig is pure waste.
#
# IF YOU READ A NEW FIELD BELOW, ADD IT HERE. A field missing from this list
# doesn't raise; .get() hands back "" and the gig is simply scored as though it
# had nothing there, which is the kind of wrong that never shows up as an error.
FIT_FIELDS = ("title", "body", "job_type", "size_tier", "urgency")


def fit_score(gig: dict, profile: dict, resume_text: str = "") -> tuple[int, list[str]]:
    """Returns (0-100 score, short 'why' notes). The notes only mention the
    *extra* signal — skill/budget/urgent already show as pills, so we skip those
    and keep this to a glanceable line.

    resume_text is optional and session-only (see resume.py — it is never
    persisted, by design). When present it adds a small, ADDITIVE bonus on
    top of the existing skill/keyword/budget/urgency weights below, rather
    than taking a slice of their point budget: those four were already
    calibrated against real cards before this existed, and reshuffling them
    to make room for a fifth signal would shift everyone's match numbers as
    a side effect of a feature most gigs won't even trigger (most scores
    don't sit at the 100 ceiling, so a few extra points below the cap are
    still visible, not silently clipped away)."""
    score = 0
    why = []
    skills = profile.get("skills") or []
    text = f"{gig.get('title','')} {gig.get('body','')}".lower()

    # --- Skill (up to 50) — no note; the skill pill already says it ---
    if not skills:
        score += 30
    elif gig.get("job_type") in skills:
        score += 50

    # --- Keywords (up to 25) ---
    kws = [k.strip() for k in (profile.get("keywords") or "").lower().split(",") if k.strip()]
    if kws:
        hits = [k for k in kws if k in text]
        if hits:
            score += min(25, 9 * len(hits))
            why.append(", ".join(hits[:2]))  # chip in the UI frames it
    else:
        score += 10

    # --- Budget fit (up to 20) ---
    amt = gig_amount(gig)
    floor = int(profile.get("rate_floor") or 0)
    if floor and amt is not None:
        if amt >= floor:
            score += 20
            why.append("pays your rate")
    else:
        score += {"Large": 18, "Medium": 11, "Small": 6}.get(gig.get("size_tier"), 10)

    # --- Urgency (up to 5) — no note; the 🔥 pill already says it ---
    if gig.get("urgency") == "Urgent":
        score += 5

    # --- Resume relevance (up to 8, additive — see docstring above) ---
    # config.JOB_TYPES gives, per category, the curated skill/tool phrases
    # that classify a gig INTO that category in the first place. Reusing it
    # here checks whether the resume actually uses that category's real
    # vocabulary ("figma", "logo", "branding" for Design / creative) rather
    # than matching arbitrary prose against arbitrary prose, and it credits
    # real experience even when someone never got around to typing keywords.
    if resume_text:
        resume_lower = resume_text.lower()
        cat_terms = config.JOB_TYPES.get(gig.get("job_type"), [])
        hits = [t for t in cat_terms if t in resume_lower]
        if hits:
            score += min(8, 4 * len(hits))
            why.append(f"resume: {hits[0]}")

    return min(100, score), why

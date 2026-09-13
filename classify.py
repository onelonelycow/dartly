"""
classify.py — the v0 "brain" for Nabbly.

Given a gig post's title + body, decide:
  - is this a real CLIENT hiring (demand)?  -> title tag [Hiring] / [Task]
  - what SKILL is it?                        -> job type
  - how big is the BUDGET?                   -> job size
  - is it URGENT?

Keyword rules only (no API key, no cost). We can upgrade to an AI classifier later.
"""
import functools
import re

import config

_MONEY = re.compile(r"[$£€]\s?([0-9][0-9,]*)")


def _contains_any(text, phrases):
    """Plain substring test. Right for budget/urgent signals, which are often
    fragments glued to numbers ('/month', 'k/yr', '$20') that word boundaries
    would break."""
    return any(p in text for p in phrases)


@functools.lru_cache(maxsize=8192)
def _skill_re(keyword: str):
    """
    Whole-word matcher for a skill keyword.

    Substring matching is what wrecked job-type accuracy: 'bot' matched inside
    'both'/'about', and 'api' inside 'capital'/'therapist', so unrelated roles
    (a bank sales manager) piled up under Development/tech. This requires the
    keyword to sit on word boundaries, so 'bot' matches only 'bot'/'bots'.
    re.escape keeps punctuation keywords like 'ui/ux' and 'full-stack' working;
    .strip() drops the hand-rolled spacing hacks (' ml ', ' va ', ' sql') the
    old list used as makeshift boundaries.

    THE OPTIONAL TRAILING s IS NOT COSMETIC. Without it "Telephone Interpreters"
    did not match the keyword "interpreter" and "Linguistics Specialists" did
    not match "linguist", because the plural s is a word character and the
    lookahead refused it. Measured against the live board: allowing it alone
    moved 274 gigs out of "Other / general" and left 96%+ of everything already
    classified exactly where it was.
    """
    return re.compile(r"(?<!\w)" + re.escape(keyword.strip()) + r"s?(?!\w)")


def title_key(title: str) -> str:
    """
    A title reduced to what makes two postings the same posting.

    ONE DEFINITION, IMPORTED BY BOTH CALLERS. db.mark_rare() uses it to decide
    whether a gig also exists on a mainstream board, and tools/probe_source.py
    uses it to score a candidate source. If those two ever disagreed about what
    "the same posting" means, the board would badge gigs as hard-to-find using
    one rule while the tool that justified the badge used another.

    Boards decorate the same role differently — "Senior Rails Engineer (m/w/d)",
    "Senior Rails Engineer — Acme GmbH", "senior rails engineer" — so raw string
    equality would call almost everything unique, which is the flattering answer
    and the wrong one.
    """
    t = (title or "").lower()
    t = re.sub(r"\((?:[^)]{0,24})\)", " ", t)       # (m/w/d), (remote), (uk)
    t = re.split(r"\s+[—–|]\s+| at | - ", t)[0]     # trailing company
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def _matches_skill(text: str, keywords) -> bool:
    return any(_skill_re(k).search(text) for k in keywords)


# A title match is worth this many body matches. 3 measured best on the
# 2026-09-13 fixture (1:1 and 5:1 were both worse); the body is where a
# posting mentions every tool it touches, the title is where it names the job.
_TITLE_WEIGHT = 3


@functools.lru_cache(maxsize=64)
def _category_re(skill: str):
    """
    One compiled alternation for a whole category's keyword list.

    Scoring every category over the body meant ~850 keyword regexes per
    posting; the first-match code it replaced stopped at the first title hit
    and rarely read the body at all. Measured on 38,840 rows: 65s before,
    612s scored keyword-by-keyword -- and reclassify_all() runs at boot on the
    process that serves pages. One regex per category brings it back to 24
    scans per text. Longest alternative first, so "software engineer" is
    matched as itself and not as "engineer" inside it.
    """
    kws = sorted((k.strip() for k in config.JOB_TYPES.get(skill, ()) if k.strip()),
                 key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in kws) + r")s?(?!\w)")


def _found(rx, text: str) -> set:
    """Distinct keywords matched, with the plural s the pattern allows stripped."""
    out = set()
    for m in rx.finditer(text):
        w = m.group(0)
        out.add(w[:-1] if w.endswith("s") and not w[:-1].endswith("s") else w)
    return out


def _job_type(title_l: str, body_l: str) -> str:
    """
    The category with the strongest claim, not the first one that matched.

    This used to be "first category in config.JOB_TYPES with any keyword in
    the title, else the first with any keyword in the body". Measured on 300
    judged rows (CLASSIFIER.md, 2026-09-13): Design / creative sits second in
    that dict and Development / tech seventh, so "Makhana E-commerce Website
    Development" was Design because its body said "web design" -- 32 of 111
    misses were the right category matching and losing on dict order.

    Now every category is scored: each matched keyword counts its word count
    (so "website development" outweighs "brand"), title matches count
    _TITLE_WEIGHT times, and the highest total wins. Dict order is only the
    tie-break it always was. A keyword found in both places counts once, as a
    title match.
    """
    best, best_score = "Other / general", 0
    for skill in config.JOB_TYPES:
        rx = _category_re(skill)
        in_title = _found(rx, title_l)
        in_body = _found(rx, body_l) - in_title if body_l else set()
        score = (_TITLE_WEIGHT * sum(len(k.split()) for k in in_title)
                 + sum(len(k.split()) for k in in_body))
        if score > best_score:
            best, best_score = skill, score
    if best_score == 0:
        # config.JOB_TYPE_FALLBACKS: a word too generic to outrank anything,
        # allowed to decide only when nothing did.
        for skill, kws in getattr(config, "JOB_TYPE_FALLBACKS", {}).items():
            if any(_skill_re(k).search(title_l) for k in kws):
                return skill
    return best


def _budget_amounts(text):
    out = []
    for m in _MONEY.findall(text):
        try:
            out.append(int(m.replace(",", "")))
        except ValueError:
            pass
    return out


def _is_not_an_opening(title_l: str) -> bool:
    """
    True when the TITLE says this is not a job you can apply to and be paid for.

    Title only, deliberately. The phrases here appear innocently in the bodies of
    real jobs — "talent pool" in 100 of them, "candidate pool" in 29 — so reading
    the body would delete real work. config.NOT_AN_OPENING carries the full
    reasoning and the traps.

    Phrases that contain punctuation at either end, like "(unpaid)" or
    "- unpaid", are matched as plain substrings: a bracket is not a word
    character, so the word-boundary lookarounds would refuse to match at all.
    Everything else gets whole-word matching, which is what keeps "test job"
    from firing on "latest jobs".
    """
    for phrases in config.NOT_AN_OPENING.values():
        for p in phrases:
            if not (p[0].isalnum() and p[-1].isalnum()):
                if p in title_l:
                    return True
            elif _skill_re(p).search(title_l):
                return True
    return False


def classify(title: str, body: str, source: str) -> dict:
    title_l = (title or "").lower()
    text = f"{title} {body}".lower()

    # --- Is this a client hiring (demand)? ---
    # Reddit gig posts must carry a [Hiring]/[Task] tag; job-board postings are
    # all real openings, so they count as demand automatically.
    if source == "reddit":
        is_demand = _contains_any(title_l, config.HIRING_TAGS)
    else:
        is_demand = True

    # A job board posting is an opening by default, but not all of them are.
    # Talent pools, spontaneous applications, "future opportunities" and test
    # rows are postings you cannot apply to and be paid for, and showing one is
    # the board saying something untrue. Gated on the same is_demand flag the
    # stale sweep uses, so nothing downstream has to learn a new concept.
    if is_demand and _is_not_an_opening(title_l):
        is_demand = False

    job_type = _job_type(title_l, (body or "").lower())

    # --- Budget tier ---
    amounts = _budget_amounts(text)
    top = max(amounts) if amounts else None
    monthly = _contains_any(text, config.BIG_JOB_SIGNALS)
    small_sig = _contains_any(text, config.SMALL_JOB_SIGNALS)

    if monthly or (top is not None and top >= 800):
        size_tier = "Large"
    elif (top is not None and top <= 60) or (small_sig and not top):
        size_tier = "Small"
    elif top is not None:
        size_tier = "Medium"
    else:
        size_tier = "Medium"  # unknown budget -> middle by default

    urgency = "Urgent" if _contains_any(text, config.URGENT_SIGNALS) else ""

    return {
        "is_demand": 1 if is_demand else 0,
        "job_type": job_type,
        "size_tier": size_tier,
        "urgency": urgency,
    }

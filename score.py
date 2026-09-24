"""
score.py — fit scoring (Pro feature).

Turns a gig + your profile into a 0-100 "match" score and a short list of reasons,
so the best-fitting gigs float to the top instead of you filtering by hand.

Weights (roughly): skill 50, keywords 25, budget fit 20, urgency 5.
"""
import functools
import re

import config

MONEY = re.compile(r"[$£€]\s?([0-9][0-9,]*(?:\.[0-9]+)?)\s*([KkMmBb])?")

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

# NOT EVERY DOLLAR SIGN IN A JOB POST IS PAY, and until 2026-08-17 this file
# assumed otherwise. Measured across 12,572 priced gigs on the live board,
# 7.2% of the amounts feeding the Market page sat next to wording that made
# them something else entirely:
#
#   "We're at $350M ARR"            -> parsed as 350
#   "an industry worth over $400B"  -> parsed as 400
#   "401k Matching - $1 for $1"     -> parsed as 1
#
# Those are company revenue, market size and a benefits line. They were being
# averaged into "what work like yours pays" and sold as a Pro feature.
# BENEFITS ARE NOT PAY. Measured on the live board: 202 of 9,405 priced posts
# had their winning amount sitting in a perk — "$1,000 annual professional
# development stipend", "a dedicated annual L&D budget of EUR 2,000", a
# wellness programme "scaling to EUR 1,000 annually". Those carry a period, so
# they sailed past every other check and landed in the yearly bucket, which is
# why Development / tech reported a "typical" salary of $1,000 a year off 67
# samples. It is not only a statistics problem: gig_amount drives ranking and
# the lowball flag, so a gig could be ranked on the size of its home-office
# budget.
#
# The specific phrases only. Bare "budget" stays allowed, because on
# Freelancer.com "Budget $30-250" IS the pay.
# Two lists, because these terms are not equally damning.
#
# HARD: the number is never the pay, whatever surrounds it. A valuation, a
# market size, a stipend, an L&D budget.
#
# SOFT: the number is often the pay, and the term is merely mentioned in the
# same breath. "Salary: $120,000 per year plus equity" is a salary. So is
# "Pays $85/hr. Benefits include 401k matching." Both were being thrown away,
# which is the mirror of the perk bug: discarding real pay instead of counting
# fake pay, and it quietly shrank the sample every rate figure is drawn from.
# A soft term only disqualifies when nothing nearby says this IS pay.
_NOT_PAY_HARD = re.compile(
    r"\b(ARR|MRR|valuation|valued|raised|funding|funded|backed by|Series\s+[A-J]\b|"
    r"revenue|industry|market\s+(?:size|worth|cap)|worth\s+over|"
    r"in\s+sales|portfolio|assets|AUM|"
    r"budget\s+of\s+the\s+(?:company|department)|"
    r"stipend|reimbursement|reimbursed|allowance|"
    r"signing\s+bonus|referral\s+bonus|wellness|well\s?-?being|"
    r"professional\s+development|learning\s*&\s*development|"
    r"(?:L&D|learning|training|education|home\s?-?office|equipment|wellness|"
    r"annual|yearly)\s+budget)\b", re.I)

_NOT_PAY_SOFT = re.compile(
    r"\b(401\s?k|match(?:ing|es)?|equity|company\s+match|pension)\b", re.I)

# What says "this number is the pay". Read from the text BEFORE the number
# only: "$120,000 plus equity" needs the salary label in front of it, and
# looking after would let the perk itself vouch for the number.
_PAY_SAYS = re.compile(
    r"\b(salary|salaries|salaried|compensation|remuneration|base\s+pay|"
    r"pay(?:s|ing)?|paid|rate\s+is|earn(?:s|ing)?)\b", re.I)
# "we offer" and "offering" are deliberately NOT here. They introduce a
# benefit at least as often as a wage — "We offer a $5,000 401k match" — and
# including them handed the soft veto's own examples a free pass.
_PAY_BEFORE = 40

# "$10 trillion annually" is a market-size statistic, not a salary. _is_pay
# already refuses the LETTER suffixes on $350M and $2.4B; spelled out, the same
# number walked straight through.
_BIG_WORD = re.compile(r"\s*(?:million|billion|trillion|quadrillion)\b", re.I)

# The unit is what makes a number comparable. 95.5% of postings state an amount
# with no unit at all, so it can never be assumed — an unmarked 140 might be an
# hourly rate, a project total, or a week of travel nursing, and blending those
# into one median is how healthcare came to publish $109 while its largest
# specialist source said $2,500.
_UNIT_PATTERNS = (
    ("hour",    re.compile(r"(?:per\s+hour|/\s?h(?:r|our)?\b|an\s+hour|hourly|p/?h\b)", re.I)),
    ("day",     re.compile(r"(?:per\s+day|/\s?day\b|a\s+day|daily\s+rate|day\s+rate)", re.I)),
    ("week",    re.compile(r"(?:per\s+week|/\s?w(?:k|eek)\b|a\s+week|weekly)", re.I)),
    ("month",   re.compile(r"(?:per\s+month|/\s?mo(?:nth)?\b|a\s+month|monthly|pcm\b)", re.I)),
    ("year",    re.compile(r"(?:per\s+year|/\s?y(?:r|ear)\b|a\s+year|annual(?:ly)?|per\s+annum|pa\b)", re.I)),
    ("project", re.compile(r"(?:per\s+project|fixed[- ]price|flat\s+fee|total\s+budget|for\s+the\s+project)", re.I)),
)

# How far to read around a number. The disqualifying context ("$350M ARR") can
# sit either side and a little further out, but the UNIT has to be close, and
# mostly AFTER: "$75 per hour" states its own period, whereas a wide window let
# "$5,000 signing bonus. Rate is $75 per hour." hand the bonus the hourly unit
# and then win on size. Caught by test, not by reading it back.
_WINDOW = 42
_UNIT_BEFORE = 26      # "an hourly rate of $75"
_UNIT_AFTER = 18       # "$75 per hour"

# Below this, it is not a rate for a piece of work — "$0.20 per word" rounds to
# nothing useful and per-word is not a period this compares anyway.
_MIN_PAY = 1


def _unit_near(text: str, lo: int, hi: int) -> str:
    """The pay period stated tight around this number, or "" when none is."""
    ctx = text[max(0, lo - _UNIT_BEFORE):hi + _UNIT_AFTER]
    for name, rx in _UNIT_PATTERNS:
        if rx.search(ctx):
            return name
    return ""


def _is_pay(text: str, lo: int, hi: int, suffix: str) -> bool:
    """False when this number is plainly not what the gig pays."""
    # $350M / $2.4B is never a rate for one piece of work. K is, so it stays.
    if suffix and suffix.lower() in ("m", "b"):
        return False
    if _BIG_WORD.match(text[hi:hi + 12]):        # "...$10 trillion annually"
        return False
    window = text[max(0, lo - _WINDOW):hi + _WINDOW]
    if _NOT_PAY_HARD.search(window):
        return False
    if (_NOT_PAY_SOFT.search(window)
            and not _PAY_SAYS.search(text[max(0, lo - _PAY_BEFORE):lo])):
        return False
    return True


def gig_pay(gig: dict, allow_range: bool = True):
    """
    (amount, unit) for what this gig pays, or None.

    `unit` is "" when the posting never says — which is the overwhelming
    majority — and callers must not assume one. Aggregations should group by
    unit rather than average across it.

    allow_range=False DROPS a ranged posting entirely rather than re-reading
    it. The midpoint of a range is fine for ranking one gig against another,
    and useless for a statistic: Freelancer.com does not let a client type a
    budget, it offers a dropdown, so ~a quarter of its posts carry the same
    "$30 - $250" and every one of them lands on exactly $140. Aggregated, that
    is not a market rate, it is one platform's menu — see market.skill_stats.
    Note it must SKIP the post, not just skip this branch: the single-figure
    scan below would otherwise read "$30 - $250" as $250 and be more wrong.
    """
    text = f"{gig.get('title','')} {gig.get('body','')}"

    # A stated range is the clearest signal of intent, so it wins — but only
    # if it survives the same context test as everything else.
    m = RANGE.search(text)
    if m and _is_pay(text, m.start(), m.end(), ""):
        if not allow_range:
            return None
        try:
            lo_v, hi_v = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
            if hi_v >= lo_v:
                return round((lo_v + hi_v) / 2), _unit_near(text, m.start(), m.end())
        except ValueError:
            pass

    stated, bare = [], []
    for mm in MONEY.finditer(text):
        if not _is_pay(text, mm.start(), mm.end(), mm.group(2) or ""):
            continue
        try:
            v = float(mm.group(1).replace(",", ""))
        except ValueError:
            continue
        if (mm.group(2) or "").lower() == "k":
            v *= 1000
        if v < _MIN_PAY:
            continue
        v = round(v)
        u = _unit_near(text, mm.start(), mm.end())
        (stated if u else bare).append((v, u))

    # An amount the posting actually attached a period to beats one it didn't:
    # "$36.00 per hour" is the pay, "$5,000 signing bonus" in the same post is
    # not, and picking the largest number would take the bonus every time.
    if stated:
        return max(stated, key=lambda x: x[0])
    if bare:
        return max(bare, key=lambda x: x[0])[0], ""
    return None


def gig_amount(gig: dict):
    """
    Largest dollar-ish amount mentioned in a gig, if any — the midpoint when
    it's stated as a range, and nothing when the only figures in the post are
    the company's ARR or its 401k match.

    Kept returning a bare number so fit_score, market.lowball, market.skill_stats
    and the outcomes recorder don't all have to change at once. New callers that
    care what the number MEANS should use gig_pay().
    """
    got = gig_pay(gig)
    return got[0] if got else None


# Every gig field fit_score() reads, including through gig_amount(). Callers
# ranking a whole board narrow to these before building dicts — a board frame
# carries 18 columns and converting the other 13 per gig is pure waste.
#
# IF YOU READ A NEW FIELD BELOW, ADD IT HERE. A field missing from this list
# doesn't raise; .get() hands back "" and the gig is simply scored as though it
# had nothing there, which is the kind of wrong that never shows up as an error.
FIT_FIELDS = ("title", "body", "job_type", "size_tier", "urgency")


@functools.lru_cache(maxsize=2048)
def _term_re(term: str):
    """Whole-word matcher for a resume keyword, compiled once per term."""
    return re.compile(r"(?<!\w)" + re.escape(term.strip()) + r"s?(?!\w)")


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
        # WORD BOUNDARIES, NOT SUBSTRINGS. Plain `t in resume_lower` matched
        # "va" inside "Java" and "available": measured over 2,000 live rows,
        # a backend engineer's resume matched 81 of 81 Admin/VA gigs. Eighteen
        # keywords are three characters or fewer (api, aws, sql, seo, tax, va)
        # and every one of them had this shape. Same family as bare "hr"
        # matching "$77/hr". It skewed ranking silently; the moment the reason
        # is printed on a card it becomes visibly wrong.
        hits = [t for t in cat_terms if _term_re(t).search(resume_lower)]
        if hits:
            score += min(8, 4 * len(hits))
            why.append(f"resume: {hits[0]}")

    # THE STRONGEST SIGNAL WAS THE ONE WITH NO WORDS. A skill match is worth
    # more than anything else here and deliberately said nothing, because the
    # job-type pill sits right beside it on a card. That holds on /gigs; it
    # does not hold in a "why this matched you" block, where a member whose
    # profile is skills-only saw an EMPTY box on all 25 cards — measured. Said
    # last so keyword and rate reasons, which are more specific, come first.
    if not why and gig.get("job_type") and gig.get("job_type") in (profile.get("skills") or []):
        why.append(gig["job_type"])

    return min(100, score), why

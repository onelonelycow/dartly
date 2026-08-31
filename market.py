"""
market.py — rate & demand intelligence (Pro feature).

Uses the whole aggregated dataset (the thing only you have) to show:
  - how many gigs each skill has right now (demand)
  - the typical gig budget per skill (rate)
  - a per-gig 'lowball' flag when a budget is well below normal or your floor

Note: budgets still blend project, hourly and annual figures across sources —
most postings never state a period — so the 'typical gig budget' is a range to
price against, not a rate. We cap at $20k to focus on gig/project budgets
rather than full salaries.

Two rules keep it from being worse than that. RANGED POSTS DO NOT COUNT, and a
skill needs several sources before it gets a number at all; both are explained
where they are enforced below.
"""
from collections import defaultdict
from statistics import median

from score import gig_amount, gig_pay  # reuse the same amount parser

GIG_CAP = 20000  # ignore amounts above this for the "gig budget" stat (they're salaries)

# One source (Freelancer.com) supplies ~85% of every priced gig on the whole
# board, and it doesn't let clients type a budget — they pick from a fixed
# dropdown of ranges. A straight median-of-all-posts is really "the median
# Freelancer.com post," and since most of its posts land in the same cheap
# tier, that number came out nearly identical across every skill category —
# not wrong exactly, but not a real cross-platform rate either. Taking each
# source's own median first, then a median across sources, gives every
# platform an equal vote regardless of how many posts it happened to
# contribute. A source needs at least this many priced posts for a skill
# before its median counts as a vote — one post shouldn't sway the number as
# hard as a platform with hundreds.
MIN_PER_SOURCE = 3

# ...and a skill needs this many sources with a vote before it gets a number.
#
# MIN_PER_SOURCE guards how much data one source needs. NOTHING guarded how
# many sources a skill needed, so a skill could be "typical $140" on the
# strength of three votes that disagreed by an order of magnitude — and the
# median of three is just the middle one, which was reliably Freelancer's
# dropdown. Measured on the live board: at 3 sources, 13 of 25 skills keep a
# number and no two skills share one. At 4 only 4 survive, which is a chart
# with nothing on it.
MIN_SOURCES = 3


def skill_stats(posts: list[dict]) -> dict:
    counts = defaultdict(int)
    amounts = defaultdict(lambda: defaultdict(list))  # skill -> source -> [amount]
    for p in posts:
        skill = p.get("job_type", "Other / general")
        counts[skill] += 1
        # allow_range=False: a ranged post is DROPPED, not read as its
        # midpoint. Freelancer.com is ~85% of every priced gig and gives
        # clients a dropdown rather than a text box, so roughly a quarter of
        # its posts carry the identical "$30 - $250" and every one of them
        # lands on exactly $140. That put four unrelated skills on the live
        # board at the same "typical budget" — one platform's menu, printed
        # as a market rate. gig_amount() still midpoints, because ranking one
        # gig against another is a different job from aggregating thousands.
        got = gig_pay(p, allow_range=False)
        if got is not None and 5 <= got[0] <= GIG_CAP:
            amounts[skill][p.get("source", "")].append(got[0])
    stats = {}
    for skill in counts:
        by_source = amounts[skill]
        all_vals = [a for vals in by_source.values() for a in vals]
        # Only sources with enough of their own data get a vote; thin skills
        # (no source clears the bar) fall back to the plain median so they
        # still get a number instead of silently going blank.
        per_source = [median(v) for v in by_source.values() if len(v) >= MIN_PER_SOURCE]
        # NO FALLBACK. This used to drop to a plain median of everything when
        # no source cleared the bar, so that thin skills "still get a number
        # instead of silently going blank" — but a number nobody can stand
        # behind is worse than a blank, and on a page someone pays for it is
        # the blank that is honest. Too few sources now means no figure, and
        # the chart simply carries the skills that have the evidence.
        typical = median(per_source) if len(per_source) >= MIN_SOURCES else None
        stats[skill] = {
            "count": counts[skill],
            "typical": int(typical) if typical is not None else None,
            "n_priced": len(all_vals),
        }
    return stats


def hot_skills(stats: dict, top: int = 5) -> list[tuple]:
    return sorted(((s, d["count"]) for s, d in stats.items()),
                 key=lambda x: -x[1])[:top]


def lowball(gig: dict, stats: dict, profile: dict | None = None):
    """Returns (is_lowball, reason)."""
    a = gig_amount(gig)
    if a is None or a > GIG_CAP:
        return False, None
    floor = int((profile or {}).get("rate_floor") or 0)
    if floor and a < floor:
        return True, f"${a:,} — under your ${floor:,} floor"
    typical = stats.get(gig.get("job_type"), {}).get("typical")
    if typical and a < 0.5 * typical:
        return True, f"${a:,} vs ~${typical:,} typical"
    return False, None

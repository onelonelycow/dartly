"""
market.py — rate & demand intelligence (Pro feature).

Uses the whole aggregated dataset (the thing only you have) to show:
  - how many gigs each skill has right now (demand)
  - the typical gig budget per skill (rate)
  - a per-gig 'lowball' flag when a budget is well below normal or your floor

Note: budgets blend project, hourly, and annual figures across sources, so the
'typical gig budget' is a rough directional number — we cap at $20k to focus on
gig/project budgets rather than full salaries.
"""
from collections import defaultdict
from statistics import median

from score import gig_amount  # reuse the same amount parser

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


def skill_stats(posts: list[dict]) -> dict:
    counts = defaultdict(int)
    amounts = defaultdict(lambda: defaultdict(list))  # skill -> source -> [amount]
    for p in posts:
        skill = p.get("job_type", "Other / general")
        counts[skill] += 1
        a = gig_amount(p)
        if a is not None and 5 <= a <= GIG_CAP:
            amounts[skill][p.get("source", "")].append(a)
    stats = {}
    for skill in counts:
        by_source = amounts[skill]
        all_vals = [a for vals in by_source.values() for a in vals]
        # Only sources with enough of their own data get a vote; thin skills
        # (no source clears the bar) fall back to the plain median so they
        # still get a number instead of silently going blank.
        per_source = [median(v) for v in by_source.values() if len(v) >= MIN_PER_SOURCE]
        typical = median(per_source) if per_source else (median(all_vals) if all_vals else None)
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

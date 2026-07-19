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


def skill_stats(posts: list[dict]) -> dict:
    counts = defaultdict(int)
    amounts = defaultdict(list)
    for p in posts:
        skill = p.get("job_type", "Other / general")
        counts[skill] += 1
        a = gig_amount(p)
        if a is not None and 5 <= a <= GIG_CAP:
            amounts[skill].append(a)
    stats = {}
    for skill in counts:
        vals = amounts[skill]
        stats[skill] = {
            "count": counts[skill],
            "typical": int(median(vals)) if vals else None,
            "n_priced": len(vals),
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

"""
Acquisition and activation by campaign, from the durable store.

    python tools/acquisition.py            # last 30 days
    python tools/acquisition.py 90

One table, one row per campaign tag (plus "(none)" for organic/direct), read
from the two records that survive a redeploy: people (created, campaign) and
accounts (last_seen, trial_start, plan, stripe_subscription_id). The founder's
account and the internal test domain are left out, the same rule web/main.py
applies to analytics events.

What this can and cannot say:
  signups     accounts created in the window, by the tag they arrived on
  returned    came back at least 7 days after signing up (last_seen)
  trials      opted into the 14-day trial (founding grants are not trials)
  paying      hold a Stripe subscription today
The per-session steps between those -- draft viewed, apply link followed --
live in PostHog, cut by the `campaign` property on every event. This script is
the money-and-people view; PostHog is the behaviour view.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import accounts   # noqa: E402
import store      # noqa: E402

INTERNAL = tuple(d.strip().lower() for d in (
    os.environ.get("NABBLY_INTERNAL_DOMAINS") or "onelonelycow.com").split(",") if d.strip())


def _internal(email: str) -> bool:
    e = (email or "").lower()
    return accounts.is_owner(e) or e.rsplit("@", 1)[-1] in INTERNAL


def _dt(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def main(days: int = 30):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    # accounts is the record that is always populated; people carries the
    # campaign tag when the signup wrote one (every signup since 2026-09-21;
    # the five members before that predate the mirror and show as "(none)").
    accts = store.list_scope("_accounts") or {}
    accts = list(accts.values()) if isinstance(accts, dict) else accts
    people = store.list_scope("_people") or {}
    people = people.values() if isinstance(people, dict) else people
    tag_of = {}
    for rows in people:
        for r in (rows if isinstance(rows, list) else [rows]):
            if r.get("email"):
                tag_of[r["email"].lower()] = (r.get("campaign") or "").strip()
    rows = {}
    for a in accts:
        email = (a.get("email") or "").lower()
        created = _dt(a.get("created"))
        if not email or _internal(email) or not created or created < since:
            continue
        tag = tag_of.get(email) or "(none)"
        r = rows.setdefault(tag, {"signups": 0, "returned": 0, "trials": 0, "paying": 0})
        r["signups"] += 1
        seen = _dt(a.get("last_seen"))
        if seen and seen - created >= timedelta(days=7):
            r["returned"] += 1
        if a.get("trial_start"):
            r["trials"] += 1
        if a.get("stripe_subscription_id"):
            r["paying"] += 1
    print(f"Signups in the last {days} days, by campaign (internal accounts excluded)\n")
    print(f"{'campaign':24} {'signups':>8} {'returned>=7d':>13} {'trials':>7} {'paying':>7}")
    for tag, r in sorted(rows.items(), key=lambda kv: -kv[1]["signups"]):
        print(f"{tag:24} {r['signups']:8} {r['returned']:13} {r['trials']:7} {r['paying']:7}")
    if not rows:
        print("(no signups in the window)")
    print("\nBehaviour between signup and payment -- draft_view, gig_click, market_view --\n"
          "is in PostHog: filter any event by the `campaign` property.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)

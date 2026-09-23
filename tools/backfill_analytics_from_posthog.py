"""
One-time repair: put the board's 1-22 September 2026 traffic back on the admin
panel.

WHY THIS EXISTS. The admin panel reads analytics.py, and analytics.track() is
called only from app.py. Between 30 August and 1 September 2026 every visitor
moved to board.nabbly.co, whose _ev() sends events to PostHog instead -- so the
panel's chart froze on 2026-08-31 while the real board went unrecorded. From
2026-09-23 the board folds its own counters into the durable store
(analytics.flush_live), and this script recovers the three weeks in between,
which exist in PostHog and nowhere else.

WHAT IT CANNOT RECOVER. The board never sent a device label to PostHog, so the
desktop/mobile split for these days stays empty rather than invented. Sessions,
page views, actions and referrers are all real.

Reads a PostHog PERSONAL api key -- the project key in POSTHOG_API_KEY is
write-only and cannot query. Nothing is written without --write.

    POSTHOG_PERSONAL_API_KEY=phx_...  POSTHOG_PROJECT_ID=12345 \
        python tools/backfill_analytics_from_posthog.py            # dry run
        python tools/backfill_analytics_from_posthog.py --write    # commit it
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics  # noqa: E402  (for _ROLLUP-style naming and the merge helper)

START = os.environ.get("BACKFILL_START", "2026-09-01")
END = os.environ.get("BACKFILL_END", "2026-09-23")      # exclusive
HOST = (os.environ.get("POSTHOG_HOST") or "https://us.posthog.com").strip().rstrip("/")
KEY = (os.environ.get("POSTHOG_PERSONAL_API_KEY") or "").strip()
PROJECT = (os.environ.get("POSTHOG_PROJECT_ID") or "").strip()

# Same mapping web/main.py uses, kept here so a backfilled day is labelled
# exactly like a live one. Anything unlisted becomes a click under its own name.
BUCKET = {
    "board_view":  ("views", "Gigs"),
    "market_view": ("views", "Market"),
    "draft_view":  ("views", "Draft a reply"),
    "gig_click":   ("clicks", "Opened a gig"),
    "search":      ("clicks", "Search"),
    "signup":      ("clicks", "Signed up"),
    "trial_start": ("clicks", "Started a trial"),
    "purchase":    ("clicks", "Paid"),
    "cancel":      ("clicks", "Cancelled"),
    "resume":      ("clicks", "Resumed"),
    "plan_switch": ("clicks", "Switched plan"),
    "bid_placed":  ("clicks", "Placed a bid"),
    "bid_retracted": ("clicks", "Retracted a bid"),
    "unsubscribe": ("clicks", "Unsubscribed"),
    # The Streamlit app's own names, for days when it was still the product.
    "view":   ("views", "Gigs"),
    "click":  ("clicks", "Opened a gig"),
    "search_empty": ("clicks", "Search"),
}
# Not visitor actions: 'arrival' is the referrer marker counted separately, and
# 'from_campaign' is a duplicate of board_view carrying the tag.
SKIP = {"arrival", "from_campaign", "session", "device", "ref"}


def query(sql: str) -> list:
    """
    Run one HogQL query, and refuse a partial answer.

    PostHog caps an unbounded query at 100 rows and says so only in `hasMore`.
    A 34-day breakdown is ~440 rows, so the first run of this script silently
    got August and nothing after it, and wrote days whose page views were
    empty because the rows never arrived. A truncated read that looks like a
    complete one is the worst shape a backfill can have: it does not fail, it
    just stores something wrong. Ask for a high limit, then check anyway.
    """
    import requests
    if " limit " not in sql.lower():
        sql = f"{sql} LIMIT 100000"
    r = requests.post(
        f"{HOST}/api/projects/{PROJECT}/query/",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"query": {"kind": "HogQLQuery", "query": sql}},
        timeout=90,
    )
    if r.status_code != 200:
        sys.exit(f"PostHog said {r.status_code}: {r.text[:300]}")
    body = r.json()
    if body.get("hasMore"):
        sys.exit("PostHog truncated this query. Narrow the window and re-run; "
                 "storing a partial day is worse than storing nothing.")
    return body.get("results") or []


def main():
    if not KEY or not PROJECT:
        sys.exit("Need POSTHOG_PERSONAL_API_KEY and POSTHOG_PROJECT_ID "
                 "(the project key in POSTHOG_API_KEY is write-only).")

    window = (f"timestamp >= toDateTime('{START} 00:00:00') "
              f"AND timestamp < toDateTime('{END} 00:00:00')")
    # Only what this board sent. Anything else in the project is not ours.
    ours = "properties.source = 'nabbly-server'"

    # ENGAGED ONLY, and this is the whole point of the script.
    #
    # Raw PostHog for 1-22 Sep is 2,370 "visitors", of whom 2,318 arrived with
    # no referrer, saw one page and were never seen again under that id --
    # scrapers without a user agent the board's blocklist knows. Writing that
    # in would have the panel claim ~108 visitors a day when about four were
    # people, which is worse than the blank chart it replaces.
    #
    # A visitor counts if they did a SECOND thing, or arrived from somewhere
    # real -- the same rule web/main._ev now applies live, so a backfilled day
    # and a recorded one mean the same thing.
    #
    # COUNTED ON ACTIONS, NOT ON EVENTS, because the two surfaces announce
    # themselves differently. The Streamlit app fires session+device+ref once
    # per visitor before they do anything (1,622 of each across 20-31 Aug, one
    # per id), so "three or more events" would wave through every bot it ever
    # saw. Only a page viewed or a thing clicked counts, from either surface.
    ACTIONS = ("'board_view','gig_click','market_view','search','draft_view',"
               "'view','click','search_empty'")
    REFERRED = "'arrival','ref'"          # whichever surface recorded it
    engaged = (
        f"distinct_id IN (SELECT distinct_id FROM events WHERE {window} "
        f"AND {ours} GROUP BY distinct_id "
        f"HAVING countIf(event IN ({ACTIONS})) >= 2 "
        f"OR countIf(event IN ({REFERRED}) "
        f"AND properties.detail NOT IN ('Direct','')) > 0)")

    days = defaultdict(lambda: {"sessions": 0, "views": {}, "clicks": {},
                                "refs": {}, "devices": {}})

    # A session is one distinct id, the rotating _vid cookie -- the same thing
    # the live counter counts once per new session.
    for day, n in query(
            f"SELECT toString(toDate(timestamp)) AS d, "
            f"count(DISTINCT distinct_id) FROM events "
            f"WHERE {window} AND {ours} AND {engaged} GROUP BY d ORDER BY d"):
        days[day]["sessions"] = int(n)

    for day, event, n in query(
            f"SELECT toString(toDate(timestamp)) AS d, event, count() "
            f"FROM events WHERE {window} AND {ours} AND {engaged} "
            f"GROUP BY d, event ORDER BY d"):
        if event in SKIP:
            continue
        kind, label = BUCKET.get(event, ("clicks", event))
        days[day][kind][label] = days[day][kind].get(label, 0) + int(n)

    for day, ref, n in query(
            f"SELECT toString(toDate(timestamp)) AS d, "
            f"properties.detail, count() FROM events "
            f"WHERE {window} AND {ours} AND {engaged} AND event = 'arrival' "
            f"GROUP BY d, properties.detail ORDER BY d"):
        label = (ref or "Direct").strip() or "Direct"
        days[day]["refs"][label] = days[day]["refs"].get(label, 0) + int(n)

    if not days:
        sys.exit("PostHog returned nothing for that window. Check the project "
                 "id and that the dates are right before assuming it is empty.")

    total = sum(r["sessions"] for r in days.values())
    print(f"{len(days)} days, {total:,} sessions, {START} to {END} (exclusive)\n")
    for day in sorted(days):
        r = days[day]
        print(f"  {day}  {r['sessions']:4d} sessions  "
              f"views={dict(sorted(r['views'].items(), key=lambda x: -x[1])[:3])}  "
              f"refs={dict(sorted(r['refs'].items(), key=lambda x: -x[1])[:2])}")

    if "--write" not in sys.argv:
        print("\nDry run. Re-run with --write to store these.")
        return

    import store
    if not store.enabled():
        sys.exit("No durable store configured (DATABASE_URL).")
    # --replace rewrites the app's own "<day>" key. Needed only for days the
    # app also recorded: adding a second key there would SUM an inflated count
    # with a corrected one and make the day worse than before. Everything it
    # overwrites is printed first and saved to a file, because this is the one
    # operation here that destroys a number somebody might want back.
    replace = "--replace" in sys.argv
    wrote = 0
    if replace:
        import json
        backup = {d: (store.get(analytics._ANALYTICS_SCOPE, d) or {})
                  for d in sorted(days)}
        path = f"analytics-backup-{START}-to-{END}.json"
        with open(path, "w") as fh:
            json.dump(backup, fh, indent=1)
        print(f"\nprevious values saved to {path}")
    for day in sorted(days):
        if replace:
            key, payload = day, days[day]
        else:
            key = f"{day}{analytics._LIVE_SUFFIX}"
            # Merge, never replace: if the live counter has already written
            # anything for a day in this range, it is real and must survive.
            payload = analytics._merge_rollup(
                store.get(analytics._ANALYTICS_SCOPE, key) or {}, days[day])
        if store.put(analytics._ANALYTICS_SCOPE, key, payload):
            wrote += 1
        else:
            print(f"  ! refused to store {key}")
    print(f"\nstored {wrote}/{len(days)} days"
          f"{' (replaced the app key)' if replace else ''}")


if __name__ == "__main__":
    main()

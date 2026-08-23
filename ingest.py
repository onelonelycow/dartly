"""
ingest.py — the "go fetch new demand" job.

Run it with:   python ingest.py

It pulls posts from all sources, classifies each one, and saves the new ones.
You can run it as often as you like; already-seen posts are skipped.
"""
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()  # read Reddit credentials from a local .env file if present

import db
import sources
import classify


def run() -> dict:
    db.init_db()
    db.reset_new_flags()  # only posts from THIS fetch will be marked "new"
    raw_posts = sources.fetch_all()

    now = datetime.now(timezone.utc).isoformat()
    new_count = 0
    demand_count = 0
    stale_count = 0
    fresh = []          # newly-stored gigs, mirrored to the durable board below

    # Anything already past the retention cutoff on arrival. Several feeds
    # serve postings years old — measured 2026-08-14, gigs dated 2022 and 2023
    # arriving fresh from dribbble and weworkremotely — and without this they
    # are ingested, classified, mirrored, then archived by the next
    # archive_stale pass, having sat on the board for up to a day in between.
    # Refusing them here costs one comparison and saves the whole round trip.
    # Measured at the time: 1,541 rows in the mirror waiting to be retired.
    cutoff = (datetime.now(timezone.utc)
              - timedelta(days=db.STALE_DAYS)).isoformat()

    for post in raw_posts:
        # A gig with no date at all is kept: unknown is not the same as old,
        # and fetched_at will stand in as its sort key.
        when = (post.get("posted_at") or "").strip()
        if when and when < cutoff:
            stale_count += 1
            continue
        # EVERY title and body passes through _strip here, whatever the fetcher
        # did. Five fetchers assemble titles straight from API fields
        # ("position — company") with no cleaning, which is how "BÃ¢timent" and
        # "&amp;" reached members' screens — the cleaning existed, those paths
        # skipped it. One choke point protects future fetchers too, and _strip
        # is idempotent on already-clean text so the double pass costs nothing.
        post["title"] = sources.clean_stored(post["title"])
        post["body"] = sources.clean_stored(post["body"])
        tags = classify.classify(post["title"], post["body"], post["source"])
        record = {
            **post,
            "fetched_at": now,
            "is_demand": tags["is_demand"],
            "job_type": tags["job_type"],
            "size_tier": tags["size_tier"],
            "urgency": tags["urgency"],
        }
        if db.upsert_post(record):
            new_count += 1
            demand_count += tags["is_demand"]
            fresh.append(record)

    # Back up this cycle's new gigs to Supabase so the board survives a redeploy
    # or idle spin-down instead of resetting to the seed. Best-effort and a no-op
    # when the mirror isn't configured.
    if fresh:
        try:
            import board_store
            board_store.push(fresh)
        except Exception:
            pass

    print("\n──────────────────────────────")
    print(f"  Pulled {len(raw_posts)} posts total")
    if stale_count:
        print(f"  {stale_count} arrived already past the {db.STALE_DAYS}-day cutoff and were skipped")
    print(f"  {new_count} were new to us")
    print(f"  {demand_count} of those look like real hiring gigs")
    print(f"  Total demand posts saved: {db.count()}")
    print("──────────────────────────────")
    return {"pulled": len(raw_posts), "new": new_count, "demand": demand_count,
            "stale_skipped": stale_count}


if __name__ == "__main__":
    run()

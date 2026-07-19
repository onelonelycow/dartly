"""
ingest.py — the "go fetch new demand" job.

Run it with:   python ingest.py

It pulls posts from all sources, classifies each one, and saves the new ones.
You can run it as often as you like; already-seen posts are skipped.
"""
from datetime import datetime, timezone

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

    for post in raw_posts:
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

    print("\n──────────────────────────────")
    print(f"  Pulled {len(raw_posts)} posts total")
    print(f"  {new_count} were new to us")
    print(f"  {demand_count} of those look like real hiring gigs")
    print(f"  Total demand posts saved: {db.count()}")
    print("──────────────────────────────")
    return {"pulled": len(raw_posts), "new": new_count, "demand": demand_count}


if __name__ == "__main__":
    run()

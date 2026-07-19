"""
seed_samples.py — loads a few CLEARLY-LABELED example posts so you can see the
dashboard and filters working before the live data source is connected.

⚠️  These are ILLUSTRATIVE EXAMPLES written to demonstrate the product.
    They are NOT real leads. Never show them to a landscaper as real demand.

Run:   python seed_samples.py
Clear: delete the demand_radar.db file, or run  python seed_samples.py --clear
"""
import sys
from datetime import datetime, timezone

import db
import classify

SAMPLES = [
    ("Looking for someone to clear overgrown blackberries in SE Portland",
     "Our backyard is completely taken over by blackberry bushes and ivy. Need it "
     "cleared out and hauled away. Decent size, maybe a quarter of the lot. Quotes?"),
    ("Need weekly lawn mowing in Beaverton",
     "Small front and back lawn, looking for someone reliable to mow every week "
     "through the summer. Nothing fancy."),
    ("Recommendations for a landscaper to redo our whole front yard?",
     "We want to tear out the grass and put in a low-water design with pavers and "
     "a small retaining wall. Bigger project, hoping for a full landscape redesign."),
    ("Urgent: tree limb down after storm, need removal ASAP",
     "A big limb came down on our fence last night. Need someone today or tomorrow "
     "to remove it and check the rest of the tree."),
    ("Anyone know a good gardener for planting beds in NE?",
     "Looking to get some flower beds planted and mulched this spring. Small job."),
    ("Leaf cleanup for a large yard in Lake Oswego",
     "Huge maple dropped everything. Need a full leaf cleanup and haul-off. Yard is "
     "on the larger side, close to half an acre."),
    ("Hedge trimming and general yard tidy-up",
     "Overgrown hedges along the driveway need trimming, plus some general weeding. "
     "Medium-ish one-time job."),
    ("ISO lawn care company for a small apartment complex",
     "We manage a small complex and need ongoing monthly maintenance — mowing, edging, "
     "weeding. This would be a recurring commercial contract."),
    ("Need gravel driveway regraded and drainage fixed",
     "Water pools badly. Looking for someone who does drainage and can regrade the "
     "gravel. Probably a larger job with equipment."),
    ("Who does stump grinding in the Portland area?",
     "Had two trees taken down, now stuck with the stumps. Need them ground out."),
    ("Small weeding job, front garden only",
     "Just need someone to pull weeds in the front garden bed. Quick one-time thing."),
    ("Sod installation for backyard - quotes?",
     "Want to put in new sod in the back. About 800 sq ft. Looking for install quotes."),
]


def clear():
    from db import DB_PATH
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Cleared demand_radar.db")


def run():
    db.init_db()
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    for i, (title, body) in enumerate(SAMPLES):
        tags = classify.classify(title, body, "sample")
        # Force these to count as demand so they all show (they're curated examples).
        tags["is_demand"] = 1
        rec = {
            "source": "sample",
            "source_id": f"sample-{i}",
            "url": "https://example.com/sample",
            "title": title,
            "body": body,
            "posted_at": now,
            "fetched_at": now,
            **tags,
        }
        if db.upsert_post(rec):
            added += 1
    print(f"Added {added} SAMPLE posts (labeled 'sample'). "
          f"These are examples, not real leads.")


if __name__ == "__main__":
    if "--clear" in sys.argv:
        clear()
    else:
        run()

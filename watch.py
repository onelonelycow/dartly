"""
watch.py — the always-on speed-to-lead engine.

Leave this running in a terminal. Every few minutes it fetches fresh gigs and
alerts you (desktop popup + Discord/Slack + email, whatever you've set up) about
new ones matching your saved alert preferences — so you can respond first.

Run:   python watch.py           (checks every 10 minutes)
       python watch.py 5         (checks every 5 minutes)
Stop:  press Ctrl+C
"""
import sys
import time

from dotenv import load_dotenv
load_dotenv()

import ingest
import alerts


def main():
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    prefs = alerts.load_prefs()
    print(f"⚡ Gig Radar watcher — checking every {minutes} min. Ctrl+C to stop.")
    print(f"   Alerting on: skills={prefs['skills'] or 'ALL'} "
          f"budgets={prefs['budgets'] or 'ALL'} keyword={prefs['keyword'] or '—'}\n")
    while True:
        try:
            ingest.run()
            n = alerts.notify_new(prefs)
            print(f"  → {n} new matching gig(s) alerted.\n")
        except Exception as e:
            print("  ! watch cycle error:", e)
        time.sleep(minutes * 60)


if __name__ == "__main__":
    main()

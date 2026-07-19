"""
digest.py — the Free tier's once-a-day roundup.

Builds a summary of today's gigs in your profile's skills and emails it (if email
is set up in .env) or prints it. This is the FREE counterpart to Pro's instant
alerts: Free gets a daily digest, Pro gets pinged the moment a gig drops.

Run once a day:   python digest.py
(Schedule it with cron or the app's scheduler for a real daily email.)
"""
import ssl
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

import db
import profile


def build(limit: int = 25) -> list[dict]:
    prof = profile.load()
    skills = set(prof.get("skills") or [])
    posts = db.all_posts(demand_only=True)
    matched = [p for p in posts if not skills or p.get("job_type") in skills]
    return matched[:limit]


def _email(gigs: list[dict]) -> bool:
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = os.environ.get("ALERT_EMAIL_TO", user)
    if not (host and user and pw and to):
        return False
    body = "\n\n".join(f"{g['title']}\n{g['job_type']} · {g['size_tier']} budget · "
                       f"{g['source']}\n{g['url']}" for g in gigs)
    msg = EmailMessage()
    msg["Subject"] = f"🗞️ Dartly daily digest — {len(gigs)} gigs in your skills"
    msg["From"] = user
    msg["To"] = to
    msg.set_content("Today's gigs in your skills:\n\n" + body)
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as e:
        print("  digest email failed:", e)
        return False


def run():
    gigs = build()
    if _email(gigs):
        print(f"Emailed daily digest — {len(gigs)} gigs.")
    else:
        print(f"Daily digest — {len(gigs)} gigs in your skills "
              f"(set up email in .env to get this delivered):\n")
        for g in gigs:
            print(f"  • [{g['job_type']} / {g['size_tier']}] {g['title'][:70]}")
            print(f"    {g['url']}")


if __name__ == "__main__":
    run()

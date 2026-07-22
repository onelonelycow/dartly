"""
alerts.py — the speed-to-lead engine.

Finds gigs that match your saved alert preferences and haven't been alerted yet,
then notifies you across whatever channels are set up:
  - macOS desktop notification (zero setup)
  - Discord / Slack webhook   (paste a webhook URL — no password)
  - email                     (SMTP settings in .env — you set these up)

Preferences (which skills/budgets/keyword to alert on, + webhook URL) live in
alert_prefs.json. Email secrets live in .env.
"""
import os
import ssl
import json
import smtplib
import subprocess
from email.message import EmailMessage

import requests

import db
from paths import data_file

PREFS_PATH = data_file("alert_prefs.json")
DEFAULT_PREFS = {"skills": [], "budgets": [], "keyword": "", "discord_webhook": "",
                 "ntfy_topic": "", "telegram_token": "", "telegram_chat": ""}
# empty skills/budgets = match everything


def load_prefs() -> dict:
    if PREFS_PATH.exists():
        try:
            return {**DEFAULT_PREFS, **json.loads(PREFS_PATH.read_text())}
        except Exception:
            pass
    return dict(DEFAULT_PREFS)


def save_prefs(prefs: dict):
    PREFS_PATH.write_text(json.dumps({**DEFAULT_PREFS, **prefs}, indent=2))


def matches(post: dict, prefs: dict) -> bool:
    if prefs.get("skills") and post.get("job_type") not in prefs["skills"]:
        return False
    if prefs.get("budgets") and post.get("size_tier") not in prefs["budgets"]:
        return False
    kw = (prefs.get("keyword") or "").strip().lower()
    if kw and kw not in f"{post.get('title','')} {post.get('body','')}".lower():
        return False
    return True


# ---------------------------------------------------------------------------
# channels
# ---------------------------------------------------------------------------
def send_desktop(title: str, message: str) -> bool:
    try:
        subprocess.run(
            ["osascript", "-e",
             f"display notification {json.dumps(message)} with title {json.dumps(title)}"],
            check=False,
        )
        return True
    except Exception as e:
        print("  desktop notify failed:", e)
        return False


def send_discord(webhook: str, gigs: list[dict]) -> bool:
    if not webhook:
        return False
    lines = [f"**{g['title']}**\n{g['job_type']} · {g['size_tier']} budget · "
             f"{g['source']}\n{g['url']}" for g in gigs[:8]]
    content = "⚡ **New matching gigs on Nabbly:**\n\n" + "\n\n".join(lines)
    try:
        r = requests.post(webhook, json={"content": content[:1900]}, timeout=15)
        return r.status_code in (200, 204)
    except Exception as e:
        print("  discord/slack failed:", e)
        return False


def send_ntfy(topic: str, gigs: list[dict]) -> bool:
    """Instant phone push via ntfy.sh — free, no account, fires even when the
    site is closed. The user installs the ntfy app and subscribes to `topic`."""
    if not topic:
        return False
    top = gigs[0]
    msg = f"{len(gigs)} new gig(s). Top: {top['title'][:90]}"
    try:
        r = requests.post(
            f"https://ntfy.sh/{topic}", data=msg.encode("utf-8"),
            headers={"Title": "⚡ Nabbly", "Tags": "zap",
                     "Click": top.get("url", "")}, timeout=10)
        return r.status_code < 300
    except Exception as e:
        print("  ntfy push failed:", e)
        return False


def send_telegram(token: str, chat_id: str, gigs: list[dict]) -> bool:
    if not (token and chat_id):
        return False
    lines = [f"⚡ {len(gigs)} new gig(s) on Nabbly:"]
    for g in gigs[:6]:
        lines.append(f"• {g['title'][:90]}\n{g['url']}")
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines),
                  "disable_web_page_preview": True}, timeout=10)
        return r.status_code < 300
    except Exception as e:
        print("  telegram failed:", e)
        return False


def send_email(gigs: list[dict]) -> bool:
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = os.environ.get("ALERT_EMAIL_TO", user)
    if not (host and user and pw and to):
        return False
    body = "\n\n".join(f"{g['title']}\n{g['job_type']} · {g['size_tier']} budget · "
                       f"{g['source']}\n{g['url']}" for g in gigs)
    msg = EmailMessage()
    msg["Subject"] = f"⚡ {len(gigs)} new Nabbly match(es)"
    msg["From"] = user
    msg["To"] = to
    msg.set_content("New matching gigs:\n\n" + body)
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as e:
        print("  email failed:", e)
        return False


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def notify_new(prefs: dict | None = None, desktop: bool = True) -> int:
    """Alert on all not-yet-alerted gigs matching prefs. Returns how many."""
    prefs = prefs or load_prefs()
    fresh = [p for p in db.unalerted() if matches(p, prefs)]
    if not fresh:
        return 0
    if desktop:
        send_desktop("⚡ Nabbly",
                     f"{len(fresh)} new matching gig(s)! Top: {fresh[0]['title'][:60]}")
    send_ntfy(prefs.get("ntfy_topic", ""), fresh)
    send_telegram(prefs.get("telegram_token", ""), prefs.get("telegram_chat", ""), fresh)
    send_discord(prefs.get("discord_webhook") or os.environ.get("DISCORD_WEBHOOK_URL", ""),
                 fresh)
    send_email(fresh)
    db.mark_alerted([p["id"] for p in fresh])
    return len(fresh)

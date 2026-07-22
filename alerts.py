"""
alerts.py — the speed-to-lead engine.

Finds gigs that match your saved alert preferences and haven't been alerted yet,
then notifies you across whatever channels are set up:
  - macOS desktop notification (zero setup)
  - phone push via ntfy       (free, install the app, pick a topic)
  - text message via Twilio   (TWILIO_* keys in .env — the one paid channel)
  - Discord / Slack webhook   (paste a webhook URL — no password)
  - Telegram bot              (bot token + chat id)
  - email                     (SMTP settings in .env — you set these up)

Preferences (which skills/budgets/keyword to alert on, + webhook URL) live in
alert_prefs.json. Email secrets live in .env.
"""
import os
import re
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
                 "ntfy_topic": "", "telegram_token": "", "telegram_chat": "",
                 "sms_to": ""}
# empty skills/budgets = match everything

# Phone numbers must be E.164: a + then country code, e.g. +15551234567.
_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def valid_phone(number: str) -> bool:
    return bool(_PHONE_RE.match((number or "").strip()))


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
            # .strip() because a trailing space pasted into an env var would
            # publish to a topic nobody is subscribed to, silently.
            f"https://ntfy.sh/{topic.strip()}", data=msg.encode("utf-8"),
            # HTTP headers are latin-1 ONLY. This Title used to read "⚡ Nabbly",
            # and that emoji made requests raise UnicodeEncodeError before
            # anything left the machine — so every push failed, silently, from
            # the day it was written. The "zap" tag already draws a ⚡ on the
            # phone, so the emoji was breaking it for nothing. Keep this ASCII.
            headers={"Title": "Nabbly", "Tags": "zap",
                     "Click": top.get("url", "")}, timeout=10)
        if r.status_code >= 300:
            print("  ntfy push failed:", r.status_code, r.text[:140])
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


def sms_ready() -> bool:
    """True when the server has Twilio credentials, so texts can actually go out."""
    return all(os.environ.get(k, "").strip() for k in
               ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"))


def send_sms(to_number: str, gigs: list[dict]) -> bool:
    """
    Text message via Twilio.

    Needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM in the
    environment. Unlike the other channels there's no free option here — a
    carrier has to be paid to deliver a text — so this stays quiet unless the
    keys are present. Kept to one gig and one link: a text people read at a
    glance beats a wall they scroll past.
    """
    to_number = (to_number or "").strip()
    if not (gigs and valid_phone(to_number) and sms_ready()):
        return False
    sid = os.environ["TWILIO_ACCOUNT_SID"].strip()
    token = os.environ["TWILIO_AUTH_TOKEN"].strip()
    frm = os.environ["TWILIO_FROM"].strip()
    top = gigs[0]
    more = f" (+{len(gigs) - 1} more)" if len(gigs) > 1 else ""
    body = f"Nabbly: {top['title'][:80]}{more}\n{top.get('url', '')}"
    try:
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": frm, "To": to_number, "Body": body}, timeout=15)
        if r.status_code >= 300:
            print("  sms failed:", r.status_code, r.text[:160])
        return r.status_code < 300
    except Exception as e:
        print("  sms failed:", e)
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


def send_test(prefs: dict | None = None) -> dict:
    """
    Fire a sample alert at every configured channel and report what worked.

    Why this exists: "Send a test ping" used to call notify_new(), which only
    sends when there are gigs nobody has been alerted about yet. The background
    fetcher runs every couple of minutes and consumes exactly those, so by the
    time anyone pressed the button the queue was empty and it always reported
    "0 new gigs" — telling you nothing about whether your channels work.

    This ignores the queue, sends a real message, and returns
    {channel: True/False} so a failure is visible instead of silent.
    """
    prefs = prefs or load_prefs()
    sample = [{
        "title": "Nabbly test alert — this is what a match looks like",
        "url": "https://nabbly.co",
        "job_type": "Test", "size_tier": "Medium", "source": "nabbly",
    }]
    # Saved pref first, then the env var, matching notify_new.
    ntfy = prefs.get("ntfy_topic") or os.environ.get("NTFY_TOPIC", "")
    sms = prefs.get("sms_to") or os.environ.get("ALERT_SMS_TO", "")
    tg_t = prefs.get("telegram_token") or os.environ.get("TELEGRAM_TOKEN", "")
    tg_c = prefs.get("telegram_chat") or os.environ.get("TELEGRAM_CHAT", "")
    hook = prefs.get("discord_webhook") or os.environ.get("DISCORD_WEBHOOK_URL", "")

    out = {}
    if ntfy:
        out["phone push"] = send_ntfy(ntfy, sample)
    if sms and sms_ready():
        out["text"] = send_sms(sms, sample)
    if hook:
        out["Discord/Slack"] = send_discord(hook, sample)
    if tg_t and tg_c:
        out["Telegram"] = send_telegram(tg_t, tg_c, sample)
    if os.environ.get("SMTP_HOST"):
        out["email"] = send_email(sample)
    return out


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
    # Saved prefs win, but each channel falls back to an environment variable.
    # alert_prefs.json lives on the server's disk, which Render's free tier
    # wipes on every deploy — so anything configured only in the UI goes quiet
    # after the next push, silently. Set these in Render and they stick.
    send_ntfy(prefs.get("ntfy_topic") or os.environ.get("NTFY_TOPIC", ""), fresh)
    send_sms(prefs.get("sms_to") or os.environ.get("ALERT_SMS_TO", ""), fresh)
    send_telegram(prefs.get("telegram_token") or os.environ.get("TELEGRAM_TOKEN", ""),
                  prefs.get("telegram_chat") or os.environ.get("TELEGRAM_CHAT", ""),
                  fresh)
    send_discord(prefs.get("discord_webhook") or os.environ.get("DISCORD_WEBHOOK_URL", ""),
                 fresh)
    send_email(fresh)
    db.mark_alerted([p["id"] for p in fresh])
    return len(fresh)

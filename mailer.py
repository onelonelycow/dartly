"""
mailer.py — outbound email via Resend, the only place that talks to the API.

Two emails send through here so far: the welcome email (accounts.py, fired
once when sign_in() creates a new account) and the weekly digest
(weekly_digest.py, fired once per account roughly every 7 days). Both are
plain functions that build a (subject, html, text) tuple and hand it to
send() — nothing else in the codebase should import requests and call
Resend directly, so there's exactly one place that needs to change if the
provider ever does.

HTML EMAIL, NOT THE APP: this deliberately does NOT reuse FEEL.md's dark
ground. Email dark-mode support is inconsistent across clients (Outlook
desktop's Word rendering engine, Gmail's own re-coloring of anything that
doesn't declare color-scheme) in a way a browser never has to worry about, so
a light card with dark ink and Nabbly's amber as the one accent is the same
brand, safely. Same tokens as everywhere else (--ink, --mute, --amber), just
on a light ground instead of a dark one.
"""
import os
import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
# hello@ on the verified sending subdomain — never the bare root domain, so a
# sending-reputation problem can never touch nabbly.co's own DNS standing.
FROM_ADDRESS = os.environ.get("MAIL_FROM", "Nabbly <hello@mail.nabbly.co>")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://nabbly.co").rstrip("/")
# The marketing site (nabbly.co) and the actual Streamlit app (app.nabbly.co)
# are different hosts — every link that has to land on a real page inside the
# product (the board, the unsubscribe route) needs the app host, not the
# marketing one. Computed once here rather than repeated at each call site.
APP_URL = PUBLIC_URL.replace("://nabbly.co", "://app.nabbly.co")

INK = "#1a1d23"
MUTE = "#6b7280"
FAINT = "#9aa1ac"
LINE = "#e6e2da"
BG = "#faf8f4"
AMBER = "#CB6F16"       # darker than the app's on-dark amber — needs to hold
AMBER_BG = "#fdf1e2"    # its own contrast against a light card, not a black one


def enabled() -> bool:
    return bool(RESEND_API_KEY)


def send(to: str, subject: str, html_body: str, text_body: str) -> bool:
    """The only function in the codebase that calls Resend. Never raises —
    a failed send should never take down a signup or a background cycle."""
    if not enabled():
        print(f"  mailer: RESEND_API_KEY not set, skipped '{subject}' to {to}")
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": FROM_ADDRESS, "to": [to], "subject": subject,
                  "html": html_body, "text": text_body},
            timeout=15)
        if r.status_code >= 300:
            print(f"  mailer: send failed {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print("  mailer: send failed:", e)
        return False


# ---------------------------------------------------------------------------
# shared shell — table-based, inline-styled: the two things that survive
# Outlook's Word rendering engine and Gmail stripping <style> blocks.
# ---------------------------------------------------------------------------
def _shell(preheader: str, body_html: str, unsub_token: str) -> str:
    unsub = f"{APP_URL}/?nav=unsubscribe&t={unsub_token}" if unsub_token else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title></title>
</head>
<body style="margin:0;padding:0;background:{BG};
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
  style="max-width:560px;background:#ffffff;border:1px solid {LINE};border-radius:14px;overflow:hidden;">
<tr><td style="padding:28px 32px 20px;border-bottom:1px solid {LINE};">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:18px;font-weight:700;letter-spacing:-.02em;color:{INK};">
      Nabb<span style="color:{AMBER};">ly</span>
    </td>
  </tr></table>
</td></tr>
<tr><td style="padding:28px 32px 8px;">
{body_html}
</td></tr>
<tr><td style="padding:20px 32px 28px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
    style="border-top:1px solid {LINE};padding-top:16px;">
    <tr><td style="font-size:12px;color:{FAINT};line-height:1.6;">
      Nabbly &middot; real-time freelance demand, in one place.<br>
      {f'<a href="{unsub}" style="color:{FAINT};">Unsubscribe</a>' if unsub else ''}
    </td></tr>
  </table>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _button(label: str, url: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td style="border-radius:10px;background:{AMBER};">'
            f'<a href="{url}" style="display:inline-block;padding:12px 22px;'
            f'font-size:15px;font-weight:650;color:#ffffff;text-decoration:none;'
            f'border-radius:10px;">{label}</a></td></tr></table>')


# ---------------------------------------------------------------------------
# welcome email
# ---------------------------------------------------------------------------
def welcome_email(email: str, name: str, founding: bool, token: str) -> tuple[str, str, str]:
    board_url = f"{APP_URL}/?nav=dashboard"
    hi = f"Hi {name}," if name else "Hi,"
    founding_line = (
        f'<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">'
        f'You\'re one of our first fifty members, so Pro is already on for '
        f'the next two months, on us. No card, nothing to cancel.</p>'
        if founding else "")
    subject = "Welcome to Nabbly"
    body = f"""
<h1 style="font-size:22px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  {hi} you're in.
</h1>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  Nabbly watches every freelance job board and hiring community at once and
  puts new work in one place the moment it posts, so you're the one
  who replies first.
</p>
{founding_line}
<p style="font-size:14.5px;color:{MUTE};line-height:1.6;margin:0 0 22px;">
  Add your skills to your profile and the board sorts itself around you.
  It takes about a minute.
</p>
{_button("Open the board", board_url)}
"""
    text = (f"{hi} you're in.\n\n"
            "Nabbly watches every freelance job board and hiring community at once "
            "and puts new work in one place the moment it posts.\n\n"
            + ("You're one of our first fifty members, so Pro is already on for the "
               "next two months, on us.\n\n" if founding else "")
            + f"Open the board: {board_url}\n")
    return subject, _shell("You're in. Here's what Nabbly does.", body, token), text


# ---------------------------------------------------------------------------
# weekly digest
# ---------------------------------------------------------------------------
def digest_email(name: str, gigs: list[dict], total: int, token: str) -> tuple[str, str, str]:
    board_url = f"{APP_URL}/?nav=gigs"
    hi = f"{name}, " if name else ""
    plural = "s" if total != 1 else ""
    subject = f"{hi}{total} gig{plural} matched your profile this week".strip()
    if not hi:
        subject = subject[0].upper() + subject[1:]

    import config
    rows = []
    for g in gigs:
        src = config.source_label(g.get("source", ""))
        rows.append(f"""
<tr><td style="padding:14px 0;border-top:1px solid {LINE};">
  <a href="{g['url']}" style="font-size:14.5px;font-weight:650;color:{INK};text-decoration:none;">
    {g['title']}
  </a>
  <div style="font-size:12.5px;color:{MUTE};margin-top:4px;">
    {g.get('job_type','')} &middot; {g.get('size_tier','')} budget &middot; {src}
  </div>
</td></tr>""")
    more_line = ""
    if total > len(gigs):
        more_line = (f'<p style="font-size:13px;color:{MUTE};margin:14px 0 0;">'
                     f'and {total - len(gigs)} more on the board.</p>')

    body = f"""
<h1 style="font-size:20px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 6px;">
  This week, at a glance
</h1>
<p style="font-size:14px;color:{MUTE};line-height:1.6;margin:0 0 18px;">
  {total} gig{plural} matched your profile in the last 7 days. Here are the best fits.
</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{''.join(rows)}
</table>
{more_line}
<div style="margin-top:22px;">
{_button("See the whole board", board_url)}
</div>
"""
    text_rows = "\n".join(
        f"- {g['title']}\n  {g.get('job_type','')} - {g.get('size_tier','')} budget - "
        f"{config.source_label(g.get('source', ''))}\n  {g['url']}" for g in gigs)
    text = (f"This week, at a glance\n\n{total} gig{plural} matched your profile in the "
            f"last 7 days.\n\n{text_rows}\n\nSee the whole board: {board_url}\n")
    return subject, _shell(f"{total} gigs matched your profile this week.", body, token), text

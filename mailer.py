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
    """Can we actually deliver mail right now?

    Not just "is there an API key" — send() also delivers to a local file when
    MAIL_OUTBOX is set. Callers gate real behaviour on this (the sign-in page
    refuses to offer email sign-in without it, since an unverifiable address is
    exactly the hole codes exist to close), so it has to agree with what send()
    will actually do or the two drift apart.
    """
    return bool(RESEND_API_KEY) or bool(os.environ.get("MAIL_OUTBOX", "").strip())


def send(to: str, subject: str, html_body: str, text_body: str) -> bool:
    """The only function in the codebase that calls Resend. Never raises —
    a failed send should never take down a signup or a background cycle."""
    # Local development: write the mail to a file instead of sending it. The
    # sign-in code flow is impossible to exercise end to end otherwise — you
    # cannot read the code you were supposed to be emailed. Only ever active
    # when MAIL_OUTBOX is explicitly set, which nothing in production does, and
    # it deliberately does NOT require an API key so a local run needs no
    # credentials at all.
    outbox = os.environ.get("MAIL_OUTBOX", "").strip()
    if outbox:
        try:
            with open(outbox, "w") as fh:
                fh.write(f"TO: {to}\nSUBJECT: {subject}\n\n{text_body}")
            print(f"  mailer: MAIL_OUTBOX set, wrote '{subject}' to {outbox}")
            return True
        except Exception as e:
            print("  mailer: outbox write failed:", e)
            return False
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
# welcome email — two genuinely different emails, not one email with a
# paragraph toggled on. Whoever's reading this already knows what Nabbly is
# (they just signed up for it), so neither version re-explains the product;
# each just gets straight to the one thing that's actually news to THEM.
# ---------------------------------------------------------------------------
def _welcome_founding(name: str, token: str) -> tuple[str, str, str]:
    board_url = f"{APP_URL}/?nav=dashboard"
    hi = f"{name}, y" if name else "Y"
    subject = "You're one of Nabbly's first fifty"
    body = f"""
<h1 style="font-size:22px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  {hi}ou made the first fifty.
</h1>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  Pro's already on for you, free for the next two months. No card, nothing
  to cancel. Your profile shows what's left on it any time.
</p>
<p style="font-size:14.5px;color:{MUTE};line-height:1.6;margin:0 0 22px;">
  Add your skills to your profile and the board sorts itself around you.
  Welcome to Nabbly.
</p>
{_button("Open the board", board_url)}
"""
    text = (f"{hi}ou made the first fifty.\n\n"
            "Pro's already on for you, free for the next two months. No card, "
            "nothing to cancel. Your profile shows what's left on it any time.\n\n"
            f"Add your skills to your profile and the board sorts itself around "
            f"you. Welcome to Nabbly.\n\nOpen the board: {board_url}\n")
    return subject, _shell("Pro's on for two months, free.", body, token), text


def _welcome_standard(name: str, token: str) -> tuple[str, str, str]:
    board_url = f"{APP_URL}/?nav=dashboard"
    hi = f"Hi {name}," if name else "Hi,"
    subject = "Welcome to Nabbly"
    body = f"""
<h1 style="font-size:22px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  {hi} you're in.
</h1>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  Add your skills to your profile and the board sorts itself around you.
  Welcome to Nabbly.
</p>
<p style="font-size:14.5px;color:{MUTE};line-height:1.6;margin:0 0 22px;">
  Pro's free to try for 14 days whenever you want to see the full thing.
  No rush, start it from your profile when you're ready.
</p>
{_button("Open the board", board_url)}
"""
    text = (f"{hi} you're in.\n\n"
            "Add your skills to your profile and the board sorts itself around "
            "you. Welcome to Nabbly.\n\n"
            "Pro's free to try for 14 days whenever you want to see the full "
            "thing. No rush, start it from your profile when you're ready.\n\n"
            f"Open the board: {board_url}\n")
    return subject, _shell("You're in.", body, token), text


def welcome_email(email: str, name: str, founding: bool, token: str) -> tuple[str, str, str]:
    return (_welcome_founding(name, token) if founding
           else _welcome_standard(name, token))


# ---------------------------------------------------------------------------
# lapsed-trial nudge — the one email to someone who told us, in their own
# words, that they'd pay for this (people.set_pay), then let the trial that
# would have proven it lapse without upgrading. Sent once, ever, per account
# — see lapsed_nudge.py.
# ---------------------------------------------------------------------------
def lapsed_payer_email(name: str, signin_token: str, unsub_token: str) -> tuple[str, str, str]:
    # The real sign-in token, not the derived email_token: the whole point is
    # a one-click path straight to a working "Upgrade to Pro" button, and
    # that button only renders for someone the app recognizes as signed in
    # (app.py's "Keep Pro after your trial" card checks ACCESS["signed_in"]
    # first). Same tradeoff signin_link_email already makes, for the same
    # reason.
    link = f"{APP_URL}/?u={signin_token}&nav=pricing"
    hi = f"{name}, y" if name else "Y"
    subject = "Your Nabbly trial has ended"
    body = f"""
<h1 style="font-size:22px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  Sorry to see your trial end.
</h1>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  {hi}our 14 days of Pro are up. Everything you've built here, your profile,
  your saved gigs, your board, is exactly where you left it. You're just
  back on the free plan for now.
</p>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  If you'd like Pro back, it's one click below. If not, there's nothing
  else to do.
</p>
{_button("Upgrade to Pro — $12/mo", link)}
"""
    text = ("Sorry to see your trial end.\n\n"
            f"{hi}our 14 days of Pro are up. Everything you've built here, "
            "your profile, your saved gigs, your board, is exactly where you "
            "left it. You're just back on the free plan for now.\n\n"
            "If you'd like Pro back, it's one click below. If not, there's "
            f"nothing else to do.\n\nUpgrade to Pro — $12/mo: {link}\n")
    return subject, _shell("Sorry to see your trial end.", body, unsub_token), text


# ---------------------------------------------------------------------------
# sign-in code — the one email that has to arrive fast
# ---------------------------------------------------------------------------
def signin_code_email(code: str) -> tuple[str, str, str]:
    """
    The six digits, and as little else as possible.

    Someone reading this is mid-sign-in with a form open in another tab, so the
    code goes in the subject line too — on a phone that often means never
    opening the email at all. No unsubscribe footer: this is a direct reply to
    something they just did, not a mailing (empty token drops it in _shell).
    """
    subject = f"{code} is your Nabbly sign-in code"
    body = f"""
<h1 style="font-size:20px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 16px;">
  Your sign-in code
</h1>
<div style="font-size:34px;font-weight:700;letter-spacing:.18em;color:{INK};
  background:{AMBER_BG};border-radius:12px;padding:18px 20px;text-align:center;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;">{code}</div>
<p style="font-size:14px;color:{MUTE};line-height:1.6;margin:18px 0 0;">
  Type this back into Nabbly to finish signing in. It works once and runs out
  after 10 minutes.
</p>
<p style="font-size:12.5px;color:{FAINT};line-height:1.6;margin:14px 0 0;">
  If you didn't ask to sign in, you can ignore this. Nobody can get into your
  board without the code.
</p>
"""
    text = (f"Your Nabbly sign-in code is {code}\n\n"
            "Type it back into Nabbly to finish signing in. It works once and "
            "runs out after 10 minutes.\n\n"
            "If you didn't ask to sign in, you can ignore this.\n")
    return subject, _shell(f"{code} — type this back into Nabbly.", body, ""), text


# ---------------------------------------------------------------------------
# sign-in link — the passwordless equivalent of a password reset
# ---------------------------------------------------------------------------
def signin_link_email(name: str, token: str) -> tuple[str, str, str]:
    """
    Their own sign-in link, in their inbox.

    Nabbly has no passwords, so there is nothing to reset — identity is a
    token in a link. What someone actually needs is that link somewhere
    durable they can get to from any device, which is what this is.

    Deliberately NOT sent with an unsubscribe link: this is a transactional
    reply to something they just clicked, not a mailing. Passing an empty
    token to _shell() drops the footer link.
    """
    link = f"{APP_URL}/?u={token}"
    hi = f"Hi {name}," if name else "Hi,"
    subject = "Your Nabbly sign-in link"
    body = f"""
<h1 style="font-size:20px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  Your sign-in link
</h1>
<p style="font-size:14.5px;color:{INK};line-height:1.6;margin:0 0 16px;">
  {hi} open this on any device and you're signed straight in. There's no
  password to remember, so keep this email if it's handy.
</p>
{_button("Sign me in", link)}
<p style="font-size:12.5px;color:{FAINT};line-height:1.6;margin:20px 0 0;">
  Anyone with this link can get into your board, so treat it like a password
  and don't forward it.
</p>
"""
    text = (f"{hi} here's your Nabbly sign-in link. Open it on any device and "
            f"you're signed straight in.\n\n{link}\n\n"
            "Anyone with this link can get into your board, so treat it like a "
            "password and don't forward it.\n")
    return subject, _shell("Open it on any device to sign in.", body, ""), text


# ---------------------------------------------------------------------------
# weekly digest
# ---------------------------------------------------------------------------
def _gig_out_url(gig: dict, email_tok: str) -> str:
    """
    Routed through the same ?nav=out redirect the in-app gig cards use, so a
    click from the email counts toward the same "applied" number the email is
    reporting, on whatever device it was opened on.

    Carries the EMAIL token (accounts.email_token), never the sign-in one.
    This link sits on every row of a weekly digest, which is exactly the thing
    people forward to a friend — "have you seen this gig?" must not also mean
    "here is my account". It identifies who clicked, for the count; it does
    not sign anyone in.
    """
    gid = gig.get("id")
    if gid is None:
        return gig.get("url", "")
    return f"{APP_URL}/?nav=out&gid={gid}&e={email_tok}"


def digest_email(name: str, gigs: list[dict], total: int, token: str,
                 stats: dict | None = None) -> tuple[str, str, str]:
    """
    gigs: each dict also carries _score (0-100, from score.fit_score()) and
    _reasons (its short "why" list) — the exact ranking and reasoning the
    dashboard's "Picked for you" already shows, not a separate email-only
    guess at fit.
    stats: {"applied": int, "urgent": int} — real counts (activity.py,
    the same urgency field the dashboard's pills read). Nothing here is
    invented; a number this app can't actually back up doesn't go in front
    of someone.
    """
    stats = stats or {}
    board_url = f"{APP_URL}/?nav=gigs"
    hi = f"{name}, " if name else ""
    plural = "s" if total != 1 else ""
    subject = f"{hi}{total} gig{plural} matched your profile this week".strip()
    if not hi:
        subject = subject[0].upper() + subject[1:]

    import config

    stat_cells = [(f"{total}", f"gig{plural} matched")]
    if "applied" in stats:
        stat_cells.append((f"{stats['applied']}", "applied this week"))
    if stats.get("urgent"):
        stat_cells.append((f"{stats['urgent']}", "urgent"))
    # Explicit equal width per cell — td left to auto-size sizes itself to its
    # OWN content ("6453 gigs matched" vs "353 urgent" are very different
    # widths), so the leftover row space bunches up unevenly instead of
    # splitting between them. Forced here rather than left to flexbox/grid,
    # which several email clients (Outlook chief among them) don't render.
    _cell_w = f"{100 / len(stat_cells):.3f}%"
    stats_html = "".join(
        f'<td width="{_cell_w}" style="width:{_cell_w};text-align:center;padding:12px 6px;">'
        f'<div style="font-size:20px;font-weight:700;color:{AMBER};letter-spacing:-.02em;">{n}</div>'
        f'<div style="font-size:11.5px;color:{MUTE};margin-top:2px;">{label}</div></td>'
        for n, label in stat_cells)

    rows = []
    for g in gigs:
        src = config.source_label(g.get("source", ""))
        score_html = ""
        if g.get("_score") is not None:
            score_html = (f'<span style="color:{AMBER};font-weight:650;">'
                          f'{int(g["_score"])}% match</span> &middot; ')
        why_html = ""
        if g.get("_reasons"):
            why_html = (f'<div style="font-size:12px;color:{FAINT};margin-top:3px;">'
                       f'why: {", ".join(g["_reasons"])}</div>')
        rows.append(f"""
<tr><td style="padding:14px 0;border-top:1px solid {LINE};">
  <a href="{_gig_out_url(g, token)}" style="font-size:14.5px;font-weight:650;color:{INK};text-decoration:none;">
    {g['title']}
  </a>
  <div style="font-size:12.5px;color:{MUTE};margin-top:4px;">
    {score_html}{g.get('job_type','')} &middot; {g.get('size_tier','')} budget &middot; {src}
  </div>
  {why_html}
</td></tr>""")
    # One link at the end, not a text line AND a separate button saying the
    # same thing twice. It's their own personal board either way (board_url
    # already carries ?nav=gigs, ranked and filtered around their profile the
    # same as everything above it) — just worded around whether there's an
    # actual remainder to name.
    if total > len(gigs):
        more_line = (f'<p style="font-size:13.5px;margin:16px 0 0;">'
                     f'<a href="{board_url}" style="color:{AMBER};font-weight:650;'
                     f'text-decoration:none;">and {total - len(gigs)} more on the board '
                     f'&rarr;</a></p>')
    else:
        more_line = (f'<p style="font-size:13.5px;margin:16px 0 0;">'
                     f'<a href="{board_url}" style="color:{AMBER};font-weight:650;'
                     f'text-decoration:none;">See the whole board &rarr;</a></p>')

    body = f"""
<h1 style="font-size:20px;font-weight:700;letter-spacing:-.02em;color:{INK};margin:0 0 14px;">
  This week, at a glance
</h1>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
  style="background:{AMBER_BG};border-radius:12px;margin:0 0 20px;">
<tr>{stats_html}</tr>
</table>
<p style="font-size:13px;color:{FAINT};margin:0 0 18px;">
  The best fits from the last 7 days, ranked the same way the dashboard ranks them.
</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{''.join(rows)}
</table>
{more_line}
"""
    text_stats = " | ".join(f"{n} {label}" for n, label in stat_cells)
    text_rows = "\n".join(
        f"- {g['title']}"
        + (f" ({int(g['_score'])}% match)" if g.get("_score") is not None else "")
        + f"\n  {g.get('job_type','')} - {g.get('size_tier','')} budget - "
        f"{config.source_label(g.get('source', ''))}\n  {_gig_out_url(g, token)}" for g in gigs)
    text = (f"This week, at a glance\n\n{text_stats}\n\n"
            f"The best fits from the last 7 days, ranked the same way the dashboard "
            f"ranks them.\n\n{text_rows}\n\nSee the whole board: {board_url}\n")
    return subject, _shell(f"{total} gigs matched your profile this week.", body, token), text

"""
legal.py — the privacy policy and terms, written once and used everywhere.

Kept as markdown in one module so the in-app pages and the static site can't
drift apart: app.py renders these directly, and tools/make_legal.py turns the
same strings into site/privacy.html and site/terms.html.

Everything here describes what the code ACTUALLY does today. If a feature
changes (a new processor, a new field, billing going live), update this file in
the same commit — a privacy policy that quietly stops being true is worse than
not having one.
"""

UPDATED = "28 July 2026"
CONTACT = "hello@nabbly.co"


def to_html(md: str) -> str:
    """
    The small markdown subset these documents use: ##/### headings, **bold**,
    - lists, paragraphs.

    Lives here rather than in the site generator because BOTH consumers need it
    — the in-app pages and the static site — and two implementations would
    drift. Bold is substituted after a paragraph is joined, never per line: the
    source wraps at ~79 columns, so **…** frequently straddles a newline and a
    per-line pass would leave asterisks sitting in the page.
    """
    import html as _html
    import re as _re

    out, buf, in_list = [], [], False

    def bold(text):
        return _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=_re.S)

    def flush():
        nonlocal buf
        if buf:
            out.append("<p>" + bold(" ".join(buf)) + "</p>")
            buf = []

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in (md or "").strip().splitlines():
        line = raw.strip()
        if not line:
            flush(); close_list(); continue
        esc = _html.escape(line)
        if esc.startswith("### "):
            flush(); close_list(); out.append(f"<h3>{bold(esc[4:])}</h3>")
        elif esc.startswith("## "):
            flush(); close_list(); out.append(f"<h2>{bold(esc[3:])}</h2>")
        elif esc.startswith("- "):
            flush()
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{bold(esc[2:])}</li>")
        else:
            close_list(); buf.append(esc)
    flush(); close_list()
    return "\n".join(out)

PRIVACY = f"""
## Privacy Policy

**Last updated: {UPDATED}**

Nabbly helps freelancers find work by gathering job postings from public boards
and putting them in one place. This policy explains what we collect, why, and
what we never do with it. It is written to be read, not to be survived.

### The short version

We collect the little we need to show you relevant gigs and let you sign back
in. We do not sell your data, we do not run advertising trackers, and we do not
share your information with advertisers. Analytics are counted on our own
server.

### What we collect

**When you sign in.** Your email address. If you use Google sign-in, Google
tells us your verified email address and your name, and nothing else. We only
accept an address Google has confirmed as verified. If you sign in by email
instead, we store the address you type.

**Your profile, if you fill it in.** Your name, what you do, your skills, the
rate you will not work below, keywords to prioritise, words to mute, a portfolio
link, a short bio, and your country and city. All of it is optional, and it is
used to sort the board around you.

**Your resume, if you upload one (Pro).** You can upload a resume so drafted
replies can cite your real, specific experience instead of a generic bio line.
**We do not store it.** It is held only in your browser's session — never
written to our database, never mirrored anywhere — and it disappears the
moment you close the tab or upload a new one. The one thing that does happen:
when you ask for a drafted reply, the resume text is sent to Anthropic to
write that reply, the same as the rest of your profile. It is not retained by
us before or after that.

**Your alert settings, if you set them up.** Only the channels you choose to
configure: a phone number for SMS, a notification topic, a Telegram bot token
and chat ID, or a Slack or Discord webhook address. We need these to send the
alerts you asked for.

**Newsletters you forward, if you use that feature.** You can forward mailing
lists and newsletters to a private Nabbly address. We read those messages to
pull the individual opportunities out of them. **Gigs extracted this way are
private to your account. They are never added to the public board and no other
user can see them.**

**Feedback you send us**, and the message you wrote.

**Basic usage analytics.** Page views, clicks, which site referred you, and
whether you are on a desktop or a phone. These are counted on our own server. We
do not use Google Analytics or any third-party analytics service, and we set no
advertising cookies and no tracking pixels.

**A sign-in token.** A random token identifies you between visits. It is held in
your browser session and appears in your address bar. Anyone who obtains that
link can access your account, so treat it like a password and do not share it.

### What we do not collect

We never ask for and never store passwords, payment card details, government
identification, or your contacts. Nabbly does not currently take payments at
all.

### Who we share it with

We do not sell your data or share it with advertisers, ever. We use a small
number of service providers to run Nabbly, and they only handle what they need
to:

- **Render** hosts the application.
- **Supabase** stores the database, so your account and profile survive a
  redeploy.
- **Google** handles sign-in, if you choose that option.
- **ip-api.com** is queried only if you press "Detect my location", to guess a
  country and city from an IP address.
- **Anthropic** powers drafted replies where that feature is switched on. When
  you ask for a draft, the text of that job posting, the relevant parts of your
  profile, and your uploaded resume (if you added one) are sent to generate it.
- **The alert channel you choose** (your SMS provider, Telegram, Slack, Discord,
  or your notification service) receives the alerts you asked us to send.

We will also disclose information if the law genuinely requires it.

### Where your data is held

Nabbly is operated from the United States, and the services we rely on store
data there. If you use Nabbly from elsewhere, including the UK or the EU, your
information is transferred to and processed in the United States.

### How long we keep it

We keep your account and profile for as long as your account exists, so you can
sign back in and keep your settings. Ask us to delete your account and we will
remove your account record, your profile, your alert settings, and any gigs you
forwarded in.

### Your choices

You can edit or clear your profile at any time from the Profile page, turn off
any alert channel by removing it, stop forwarding newsletters at any time, and
ask us to delete your account entirely. Email **{CONTACT}** and we will action
it.

Depending on where you live you may have additional rights over your data, such
as requesting a copy of it or asking us to correct it. Email us and we will
help.

### Children

Nabbly is meant for working adults and is not directed at children under 16. We
do not knowingly collect their information.

### Security, honestly stated

We take reasonable care with your data, but Nabbly is an early product built by
a very small team. Sign-in works through a link-based token rather than a
password, which is convenient and less secure than a full password system.
Please do not store anything sensitive in your profile.

### Changes

If we change this policy we will update the date at the top. If a change
meaningfully affects how we handle your data, we will say so clearly in the app.

### Contact

Questions, corrections, or deletion requests: **{CONTACT}**
"""


TERMS = f"""
## Terms of Service

**Last updated: {UPDATED}**

These terms cover your use of Nabbly. By using it, you agree to them. Please
read the parts about job listings and drafted replies especially carefully.

### What Nabbly is

Nabbly gathers job and project postings from public job boards and hiring
communities and shows them in one place, sorted by field, budget and urgency. If
you choose, it can also read newsletters you forward to a private address and
pull opportunities out of them for your own board.

Nabbly is an early preview. Features may change or be withdrawn, and the service
may be unavailable at times.

### Job listings are not ours, and we do not vet them

This is the most important thing on this page.

The listings on Nabbly are **written and posted by third parties**, gathered as
they were published. We classify and rank them. **We do not verify them, we do
not screen the people behind them, and we are not a party to any arrangement you
make with them.**

Treat every listing with the same caution you would anywhere else. Be
particularly wary of anyone asking you to pay money up front, requesting unpaid
"test" work, asking for identity documents or bank details early, or pushing you
to move quickly off-platform. We are not responsible for the conduct of anyone
who posts a listing, for listings that turn out to be inaccurate, expired, or
fraudulent, or for how any engagement you enter into turns out.

We make no promise that you will find work, win any particular job, or earn any
particular amount.

### Drafted replies

Where the drafted reply feature is available, Nabbly uses AI to write a starting
draft based on the posting and your profile. **It is a starting point, not
finished work.** AI can be wrong, can misread a posting, and can invent details.
You are responsible for reading, editing, and standing behind anything you send.

### Your account

You are responsible for what happens under your account. Sign-in uses a link
containing a private token rather than a password, so anyone with that link can
use your account. Keep it to yourself. Tell us at **{CONTACT}** if you think
someone else has access.

Give us accurate information when you sign up, and do not impersonate anyone
else.

### Free and Pro

The board itself is free to search and browse. Pro adds ranked picks, drafted
replies, market rate data, and instant alerts.

Nabbly does not currently charge anyone. Where we offer free Pro access, whether
as a founding-member gift or a trial, it lasts for the period stated at the
time and then your account returns to the free tier. Pressing an upgrade button
today records your interest and does not create a payment or an obligation. If
we introduce paid plans, we will make the price and terms clear before anyone is
charged.

### Forwarded newsletters

If you forward material to Nabbly, you confirm you are allowed to do so, and you
remain bound by the terms of whatever subscription or list it came from. Gigs we
extract from your forwarded email stay private to your account and are not added
to the public board or shown to other users. Do not forward material you are
contractually forbidden from sharing.

### Using Nabbly fairly

Please do not scrape, bulk-download, or republish the board; resell or
redistribute Nabbly's content as your own product; try to break, overload, or
gain unauthorised access to the service; use Nabbly to send spam or anything
unlawful; or use it to collect other people's personal information.

### Our content

The Nabbly name, logo, design, and software belong to us. Job listings belong to
whoever wrote them. Anything you write, such as your profile and bio, remains
yours; you give us permission to use it to operate the service for you, for
example by including relevant details in a drafted reply you request.

### No warranty

Nabbly is provided "as is". We do not promise it will be uninterrupted,
error-free, complete, or that any listing is accurate or still open. To the
fullest extent the law allows, we exclude implied warranties.

### Limitation of liability

To the fullest extent the law allows, Nabbly and the people behind it are not
liable for lost income, lost opportunities, lost data, or any indirect or
consequential loss arising from your use of the service, or from any dealings
with a person or company whose listing you found through us.

Nothing here excludes liability that cannot legally be excluded.

### Ending it

You can stop using Nabbly whenever you like and ask us to delete your account at
**{CONTACT}**. We may suspend or close an account that breaches these terms or
puts the service or its users at risk.

### Governing law

These terms are governed by the laws of the State of Oregon, United States,
without regard to its conflict of law rules. You and we agree that any dispute
arising out of these terms or your use of Nabbly will be brought in the state or
federal courts located in Oregon, and we each consent to those courts having
jurisdiction.

If you use Nabbly from outside the United States, you do so on your own
initiative and are responsible for complying with your own local laws.

### Changes

We may update these terms. We will change the date at the top and, where the
change matters, say so in the app. Continuing to use Nabbly after that means you
accept the updated terms.

### Contact

**{CONTACT}**
"""

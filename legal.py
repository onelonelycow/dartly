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

UPDATED = "24 August 2026"
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

### Summary

We collect the little we need to show you relevant gigs and let you sign back
in. We do not sell your data, we do not run advertising trackers, and we do not
share your information with advertisers. Usage is counted on our own server,
and a copy of those counts goes to PostHog, the service we use to read them.

### Information We Collect

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
**It is stored with your account** — the extracted text, kept alongside your
profile — so it is still there the next time you sign in, and **you can
delete it at any moment** from your settings, which removes it immediately
and everywhere. It is read for exactly one purpose: when you ask for a
drafted reply, the resume text is sent to Anthropic to write that reply, the
same as the rest of your profile. It is never shown to anyone else, never
used for anything but your own drafts, and never sent anywhere except to
write a reply you asked for.

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
whether you are on a desktop or a phone. These are counted on our own server,
and a copy is sent to PostHog, a product analytics service, so we can see which
parts of Nabbly are used and make it better.

PostHog receives a rotating session identifier and nothing that identifies you:
not your email, not your name, and nothing you have written into Nabbly — your
profile, your resume and anything you forward are never sent. The counts are
sent from our server, so there is no analytics script running in your browser,
and we set no advertising cookies and no tracking pixels.

**A sign-in token.** A random token identifies you between visits. It is held in
your browser session and appears in your address bar. Anyone who obtains that
link can access your account, so treat it like a password and do not share it.

### Information We Do Not Collect

We never ask for and never store passwords, payment card details, government
identification, or your contacts. Nabbly does not currently take payments at
all.

### How We Share Information

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

### Where Your Data Is Stored

Nabbly is operated from the United States, and the services we rely on store
data there. If you use Nabbly from elsewhere, including the UK or the EU, your
information is transferred to and processed in the United States.

### Data Retention

We keep your account and profile for as long as your account exists, so you can
sign back in and keep your settings. Ask us to delete your account and we will
remove your account record, your profile, your alert settings, and any gigs you
forwarded in.

### Your Rights and Choices

You can edit or clear your profile at any time from the Profile page, turn off
any alert channel by removing it, stop forwarding newsletters at any time, and
ask us to delete your account entirely. Email **{CONTACT}** and we will action
it.

Depending on where you live you may have additional rights over your data, such
as requesting a copy of it or asking us to correct it. Email us and we will
help.

### Children's Privacy

Nabbly is meant for working adults and is not directed at children under 16. We
do not knowingly collect their information.

### Security

We take reasonable care with your data, but Nabbly is an early product built by
a very small team. Sign-in works through a link-based token rather than a
password, which is convenient and less secure than a full password system.
Please do not store anything sensitive in your profile.

### Changes to This Policy

If we change this policy we will update the date at the top. If a change
meaningfully affects how we handle your data, we will say so clearly in the app.

### Contact

Questions, corrections, or deletion requests: **{CONTACT}**
"""


TERMS = f"""
## Terms of Service

**Last updated: {UPDATED}**

These Terms of Service ("Terms") govern your access to and use of Nabbly (the
"Service"). By accessing or using the Service, you agree to be bound by these
Terms. Sections 2 and 3, covering third-party listings and AI-assisted drafts,
limit what you may rely on the Service for and warrant close attention.

### 1. The Service

Nabbly gathers job and project postings from public job boards and hiring
communities and shows them in one place, sorted by field, budget and urgency. If
you choose, it can also read newsletters you forward to a private address and
pull opportunities out of them for your own board.

Nabbly is an early preview. Features may change or be withdrawn, and the service
may be unavailable at times.

### 2. Third-Party Listings

Listings displayed on the Service are **created and published by third
parties** and are collected substantially as published. Nabbly classifies,
ranks and presents them. **Nabbly does not verify listings, does not screen the
parties who post them, and is not a party to any agreement you enter into with
them.**

You should exercise the same diligence you would apply to any other source of
work. In particular, treat as high-risk any request for advance payment,
unpaid "test" work, identity documents or financial details early in a
conversation, or pressure to move quickly to another channel. Nabbly is not
responsible for the conduct of any party who posts a listing, for listings that
prove inaccurate, expired or fraudulent, or for the outcome of any engagement
you enter into.

Nabbly makes no representation that you will obtain work, be selected for any
particular engagement, or earn any particular amount.

### 3. AI-Assisted Drafts

Where the drafted reply feature is available, Nabbly uses artificial
intelligence to generate a draft based on the listing and your profile.
**Drafts are a starting point and are not finished work.** AI systems can
produce inaccurate output, misinterpret a listing, or state details that are
not correct. You are solely responsible for reviewing, editing and verifying
any material before you send it, and for its content once sent.

### 4. Your Account

You are responsible for all activity that occurs under your account.
Authentication uses a link containing a private token rather than a password;
any person holding that link can access your account. Keep it confidential and
notify us at **{CONTACT}** if you believe your account has been accessed by
someone else.

You agree to provide accurate information when registering and not to
impersonate any other person or entity. You must be at least 16 years old to
hold an account.

### 5. Plans, Trials and Payment

The board itself is free to search and browse, and every gig comes with a
drafted reply on any plan. Pro adds ranked picks, replies drafted from the
posting itself, market rate data, and instant alerts.

Nabbly does not currently charge anyone. Where we offer free Pro access, whether
as a founding-member gift or a trial, it lasts for the period stated at the
time and then your account returns to the free tier. Pressing an upgrade button
today records your interest and does not create a payment or an obligation. If
we introduce paid plans, we will make the price and terms clear before anyone is
charged.

### 6. Forwarded Material

If you forward material to Nabbly, you confirm you are allowed to do so, and you
remain bound by the terms of whatever subscription or list it came from. Gigs we
extract from your forwarded email stay private to your account and are not added
to the public board or shown to other users. Do not forward material you are
contractually forbidden from sharing.

### 7. Acceptable Use

You agree not to: scrape, bulk-download or republish the board; resell or
redistribute Nabbly's content as your own product or service; attempt to
disrupt, overload, or gain unauthorised access to the Service or its
infrastructure; use the Service to transmit unsolicited or unlawful material;
or use it to collect personal information about other people.

### 8. Intellectual Property

The Nabbly name, logo, design and software are owned by us and protected by
applicable intellectual property law. Listings remain the property of their
authors. Content you provide, including your profile and biography, remains
yours; you grant us a limited, non-exclusive licence to use it solely to
operate the Service on your behalf, such as incorporating relevant details into
a draft you have requested. That licence ends when you delete the content or
your account.

### 9. Disclaimer of Warranties

The Service is provided "as is" and "as available". To the fullest extent
permitted by law, Nabbly disclaims all warranties, express or implied,
including any implied warranties of merchantability, fitness for a particular
purpose and non-infringement. We do not warrant that the Service will be
uninterrupted, error-free or complete, or that any listing is accurate,
current or still open.

### 10. Limitation of Liability

To the fullest extent permitted by law, Nabbly and its operators shall not be
liable for lost income, lost opportunities, lost data, or any indirect,
incidental, special or consequential damages arising out of or relating to your
use of the Service, or to any dealings with a party whose listing you found
through it.

Nothing in these Terms excludes or limits liability that cannot lawfully be
excluded or limited.

### 11. Suspension and Termination

You may stop using the Service at any time and may request deletion of your
account at **{CONTACT}**. We may suspend or terminate an account that breaches
these Terms or that places the Service or its users at risk. Sections 8 through
10 survive termination.

### 12. Governing Law and Venue

These terms are governed by the laws of the State of Oregon, United States,
without regard to its conflict of law rules. You and we agree that any dispute
arising out of these terms or your use of Nabbly will be brought in the state or
federal courts located in Oregon, and we each consent to those courts having
jurisdiction.

If you use Nabbly from outside the United States, you do so on your own
initiative and are responsible for complying with your own local laws.

### 13. General

If any provision of these Terms is held unenforceable, that provision will be
limited or severed to the minimum extent necessary and the remaining
provisions will remain in full force. Our failure to enforce any provision is
not a waiver of it. You may not assign or transfer these Terms without our
written consent; we may assign them in connection with a merger, acquisition
or sale of assets.

### 14. Entire Agreement

These Terms, together with the Privacy Policy, constitute the entire agreement
between you and Nabbly regarding the Service and supersede any prior
understandings on that subject.

### 15. Changes to These Terms

We may update these terms. We will change the date at the top and, where the
change matters, say so in the app. Continuing to use Nabbly after that means you
accept the updated terms.

### 16. Contact

**{CONTACT}**
"""

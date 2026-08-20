"""
content.py — prose that appears in more than one place, kept in exactly one.

The FAQ used to live as a literal inside app.py, which meant the version a
signed-in visitor read and the version on nabbly.co were two separate texts
maintained by hand. They drifted, and not harmlessly: the in-app copy went on
naming every source we read long after that was removed from the marketing
site for exactly that reason, and it kept claiming the first reply wins the
work months after the rest of the product stopped saying so.

Both surfaces import from here now. There is no second copy to forget.

Plain data and plain strings on purpose — no Streamlit import — so the static
site generator in tools/ can read it without pulling the whole app in.
"""

# ── FAQ ──────────────────────────────────────────────────────────────────────
# Order matters: it is the order a stranger would ask them in, and it is the
# order they render on /faq.html, where the first two answers are the ones a
# search result is most likely to land on.
FAQ = [
    ("Where do the gigs come from?",
     # NO SOURCE NAMES. This answer used to list all seven by name, which is
     # the one thing the rest of the site is careful never to do: the feed is
     # the product, where it comes from is plumbing, and a reader handed the
     # list has six other places to go instead of here.
     "Public job boards and hiring communities, read continuously and gathered "
     "in one place so you are not keeping ten tabs open. Nabbly collects "
     "postings as they are published. It does not host work of its own and "
     "nobody pays to appear on the board."),

    ("How fresh are they?",
     # "the person who answers first usually gets the work" was here. It is not
     # true — a fast reply loses to a better fit all day — and the rest of the
     # site stopped saying it.
     "The board refreshes itself every couple of minutes, around the clock. "
     "Most gigs show up within minutes of being posted, which is the whole "
     "point: being early is the part you can actually control."),

    ("Do I have to sign up?",
     "No. The entire board is free to search and browse without an account. "
     "Signing in saves your profile so the board can sort itself around you. "
     "Pro is free to try for 14 days whenever you want it; you choose if and "
     "when to start, so you're never dropped into a trial you didn't ask for."),

    ("What's the difference between Free and Pro?",
     "Free gives you every gig from every source, search and browse, plus a "
     "drafted reply on every card to start from. Pro adds the parts that help "
     "you reply first: gigs ranked by how well they fit you, replies drafted "
     "from the actual post instead of a template, market rate data, and "
     "instant alerts."),

    ("How do the alerts work?",
     "You pick the channel — phone push, Slack or Discord, Telegram, SMS or "
     "email — plus how often you'll tolerate being pinged, which sources "
     "count, and how many gigs per message. Then new matches come to you "
     "instead of you refreshing a page."),

    ("Do you really write the reply for me?",
     "Yes, even on Free — every gig gets a drafted reply built from your "
     "profile, ready to send or edit. On Pro it reads the actual post too, so "
     "it can skip questions the listing already answered and speak to "
     "specifics a template can't. Either way, it's a starting point that beats "
     "staring at a blank message, not a promise you'll never touch it."),

    ("Are the gigs verified?",
     "No, and be careful. These are public postings gathered as they were "
     "written; we classify and rank them, we don't vet the people behind them. "
     "Treat anything asking for money up front or unpaid \"test work\" the way "
     "you would anywhere else."),

    ("What do you do with my data?",
     "We keep your email so you can sign back in, plus the profile you fill in "
     "so we can match gigs to you. We also count what gets used, which pages "
     "are opened and which buttons are pressed, so we can see what's working "
     "and make Nabbly better for you. We read those counts in an outside tool, "
     "and they record what happened, not who did it. There are no advertising "
     "cookies and no tracking scripts in your browser. What you write never "
     "leaves us: your profile, your resume, and anything you forward. Nothing "
     "is sold."),

    ("Why is a gig in the wrong category?",
     "Categories are worked out from the words in each post, so it gets most "
     "of them right and occasionally gets one wrong. If you spot a bad one, "
     "the feedback box on your profile goes straight to the person building "
     "this."),
]

# ── About ────────────────────────────────────────────────────────────────────
# Written for someone who arrived from a search result and has never heard of
# Nabbly, which is a different reader from the one already inside the app.
ABOUT_LEAD = (
    "Nabbly is a single board for freelance projects and remote roles, built "
    "because finding the work is its own unpaid job.")

ABOUT = [
    ("The problem it solves",
     "Freelance briefs and remote roles are scattered across a dozen job "
     "boards, hiring communities and mailing lists. Checking them properly "
     "means keeping tabs open all day; checking them casually means missing "
     "the ones worth having. Either way the searching is unpaid, and it never "
     "really stops."),

    ("What it actually does",
     "Nabbly watches those places continuously and puts every new posting in "
     "one place, usually within minutes. Each one is tagged by field, budget "
     "and urgency, so a board of tens of thousands becomes a short list of the "
     "work that fits you. Tell it what you do and it ranks around that; it can "
     "also ping you the moment something lands, and draft an opening reply "
     "from the posting itself."),

    ("What it doesn't do",
     "It doesn't host work of its own, take a cut, or charge anyone to post. "
     "It doesn't vet the people behind a listing either — these are public "
     "postings gathered as they were written, so the usual caution applies to "
     "anything asking for money up front. And it can't promise you the job: "
     "replying early gets you read, it doesn't beat being the better fit."),

    # A MESSAGE, NOT A CREDIT LINE. This was one sentence about who built it,
    # which answered a question nobody was asking. People subscribe to the why,
    # so this is the why, written to the reader rather than about the founder:
    # the paragraph turns on "You're not", and the last line hands the looking
    # from them to Nabbly.
    ("A message from our founder",
     "I'm Benjamin. I freelance, same as you. I built Nabbly because of how "
     "that actually feels."
     "\n\n"
     "Not the work itself. The work is the good part. It's everything around "
     "it. The Sunday night you count what's booked and it isn't enough. The "
     "gig you'd have been perfect for, found four days after it closed. The "
     "week you spent refreshing tabs instead of doing the thing you're good "
     "at, telling yourself that counted as working."
     "\n\n"
     "Nobody warns you that going out on your own means the looking never "
     "stops. It follows you into evenings and weekends, and into the holiday "
     "you finally took. It sits in your chest at 2am, doing arithmetic about "
     "next month."
     "\n\n"
     "And because it's unpaid, and nobody sees it, you start to assume "
     "everyone else has this figured out. That you're the only one scrambling. "
     "You're not. It's the job nobody put in the job description."
     "\n\n"
     "I wanted the opposite. Not more hustle. Less. A version of freelancing "
     "where the work comes to you, where security stops being something you "
     "chase and becomes something you have. Whatever you do, whatever field "
     "you're in, there should always be something worth going after. Finding "
     "it shouldn't cost you your evenings."
     "\n\n"
     "That's the whole reason this exists. Freedom is the point. Not the word "
     "on a brochure. The real kind: knowing something is coming next. Turning "
     "down the work that's wrong for you. Asking for what you're worth. "
     "Resting on a Sunday."
     "\n\n"
     "You didn't go freelance to spend your evenings looking. Take them back. "
     "Leave the looking to us, and let the work come to you."),
]


# ── The applying guide ───────────────────────────────────────────────────────
# Every rule here is one Nabbly's own drafter already follows. pitch.py's SYSTEM
# prompt is the product's working opinion about what makes a first reply land,
# arrived at by writing thousands of them against real postings, so this page is
# not repackaged advice from elsewhere. It is the thing the software does,
# explained to the person doing it by hand.
#
# Deliberately no promise that any of it wins the work. The rest of the site
# stopped claiming speed or technique decides who gets hired, and a guide is
# exactly where that claim would sneak back in.
GUIDE_APPLY_TITLE = "How to reply to a freelance job post"
GUIDE_APPLY_LEAD = (
    "Most replies to a job post are interchangeable. That is the whole "
    "opportunity: a client reading twenty of them is looking for a reason to "
    "stop, and being the one that is obviously about their post is usually "
    "enough to get read.")

GUIDE_APPLY = [
    ("Name something specific from the post in the first two lines",
     "This is the single biggest thing, and almost nobody does it. Not \"I saw "
     "your posting and would love to help\" — the actual deliverable, their "
     "tool, their deadline, their industry, a constraint they mentioned. A "
     "client can tell in one line whether you read what they wrote or pasted "
     "the same message you sent to forty other people. Everything else in this "
     "guide matters less than this."),

    ("Lead with the part of their problem you have already handled",
     "Not your whole background. The bit that maps onto what they asked for. "
     "If they need a five minute explainer animated and you have made "
     "explainers, that is the first thing they should learn about you. "
     "Never invent experience, clients, numbers or credentials to make the "
     "match closer. Clients check, and a fabricated line costs you far more "
     "than the gap it was covering."),

    ("Ask at most two questions, and only about what the post does not answer",
     "Questions are good. They show you are thinking about the work rather "
     "than the job. But asking about a detail they already stated proves you "
     "skimmed it, and a client noticing their post already answered your "
     "question is a worse impression than any amount of clumsy phrasing. Read "
     "it twice, then ask about the thing that is genuinely missing: scope, "
     "budget shape, who signs off, what done looks like."),

    ("Match how they wrote",
     "A scrappy one line post gets a short human reply. A detailed corporate "
     "brief gets something more structured. Sending a formal three paragraph "
     "letter to someone who wrote \"need a logo by friday, budget 300\" reads "
     "as badly as sending one line to a brief that took someone an hour to "
     "write."),

    ("Keep it to roughly 90 to 150 words",
     "Short replies get read. Long ones get skimmed for the price and closed. "
     "If you cannot say why you fit in a paragraph, the problem is usually that "
     "you have not decided which part of the job you are answering."),

    ("Sound like a person typing",
     "Use contractions. Vary your sentence length, because two long balanced "
     "sentences in a row is the clearest tell that something was generated. A "
     "four word sentence is fine. So is a fragment. And do not explain their "
     "own business or trade back to them, which is the most common way a "
     "confident sounding reply becomes annoying."),

    ("Watch for the posts worth skipping",
     "Anything asking for money up front, or for unpaid \"test work\" beyond a "
     "few minutes, is a bad trade however good the brief looks. Public "
     "postings are gathered as they were written and nobody vets who is behind "
     "them, on Nabbly or anywhere else. Treat a stranger on the internet the "
     "way you would anywhere else."),
]

# Shown side by side. The weak one is not a strawman: it is what most replies
# actually look like, which is exactly why the specific one stands out.
GUIDE_APPLY_EXAMPLE_BAD = (
    "Hi there, I hope this message finds you well. I came across your posting "
    "and I would love the opportunity to work with you. I am a highly "
    "experienced professional with a strong background in a wide range of "
    "projects, and I pride myself on delivering high quality work on time and "
    "on budget. I am confident I would be a great fit for this role. Please "
    "find my portfolio attached. I look forward to hearing from you.")

GUIDE_APPLY_EXAMPLE_GOOD = (
    "Hi Sam, the five minute explainer for the onboarding flow is the kind of "
    "thing I do most weeks. Last one was a similar length for a fintech app, "
    "storyboard through final cut. Your Friday date is doable if we lock the "
    "script by Tuesday. Two things the post does not say: do you have brand "
    "assets and a voiceover already, or is that part of this? And is it one "
    "video or a series with this as the first? Happy to send the fintech one "
    "over if it helps.")

GUIDE_APPLY_CLOSE = (
    "None of this guarantees the work. A well aimed reply loses to a better "
    "fit all the time, and it should. What it does is get you read, which is "
    "the part you can actually control.")

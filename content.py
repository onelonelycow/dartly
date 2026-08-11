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
     "so we can match gigs to you. Analytics are counted on our own server "
     "with no third-party trackers and no advertising cookies. Nothing is "
     "sold, and nothing is shared."),

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

    ("Who made it",
     "One freelancer who wanted it to exist, and got tired of refreshing ten "
     "tabs to find the work. It is still small and still being built, which is "
     "why the feedback box goes straight to a person rather than a queue."),
]

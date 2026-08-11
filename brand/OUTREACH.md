# Getting Nabbly listed

Every query a freelancer types returns roundups, not products. "Best freelance
job boards", "best remote job boards", "where to find freelance work" all come
back as articles listing twenty sites. Ranking against those articles takes
years. Getting *into* them takes an email.

This is the highest-leverage SEO work available right now, and none of it is
code. A new domain with no backlinks cannot rank on page quality alone; links
from pages that already rank are what makes the field pages start to move.

Work down the tiers. Tier 1 has the highest hit rate and the lowest effort, so
do not skip to Tier 3 because it looks more impressive.

---

## Tier 1 — Directories that accept submissions

These exist to list job boards. Submission is a form and approval is usually
days rather than weeks.

**Read the dofollow question before paying anyone.** JobBoardSearch's page
says plainly that "any of the PAID listings include a do-follow backlink",
which means the free one almost certainly does not. That is worth knowing
because the SEO value people imagine they are buying is the dofollow link, and
paying for a link that passes PageRank is exactly what Google's link scheme
guidance prohibits. Take the free listing. It still puts Nabbly in front of a
26k subreddit and a 16k newsletter, and those are real people rather than a
ranking signal.

| Where | Link | What it is |
|---|---|---|
| JobBoardSearch | jobboardsearch.com/add-board | The biggest of the three. Their own numbers: DR 44, ~132k pageviews a month, 26k subreddit, 16k newsletter. Free tier is "Basic listing with logo", goes on a waiting list and ranks below paid. Paid starts at $19 and **auto-renews every 30 days unless you disable it after submitting** — if you ever do pay, turn that off immediately. |
| Job Search Database | jobsearchdb.com/submissions | Reviewed and published by a real person, which makes it a genuine editorial listing rather than a link farm. Asks for name, URL, audience, description, and whether the tool is free or paid. Do not submit twice. |
| Job Board Fast | jobboardfast.com/job-board-directory/remote | Smallest of the three. Remote category is the right fit. Low effort, submit and forget. |

Submit `https://nabbly.co/`, not the app. The app is a nine-word page to a
crawler and cannot carry a link's value anywhere useful.

**One field on the JobBoardSearch form needs a decision before you fill it in.**
It asks for an API or RSS feed, and offers to push those jobs into its own
Telegram, subreddit, newsletter, and the Google for Jobs network. Handing it a
feed means Nabbly's listings, which are other people's postings, get
republished somewhere else again. That is the same question as building
JobPosting pages, arriving early and through a side door. Leave the feed field
empty for now and take the plain directory listing, which is the part with the
backlink. The feed can always be added later; it cannot be taken back.

### Submitted 2026-08-11: JobBoardSearch (free tier)

Recorded so the other submissions match, and so nobody re-derives it later.

| Field | Value |
|---|---|
| Job board name | Nabbly |
| URL | https://nabbly.co |
| API / RSS URL | **left empty, deliberately** — see the note above |
| Job board title | Freelance and remote work from every board, in one place |
| Job board software | Custom / Built in-house |
| Tier | Basic listing with logo, free. No upgrades ticked. |

Feature tags used, all of them true of the product:

> Data from multiple job boards · Job alerts · Category Filters · Skills
> Filter · Posting Date Filter · Role Filter · Timezone/location-based
> filtering · Freelance · Remote Jobs · Jobs (full time, part time, contract
> positions) · Software Engineering · Design Jobs · Sales · Marketing Jobs ·
> Video Editing · Data science and data engineering jobs · Healthcare ·
> Finance · Content Writing

**Tags deliberately NOT used, because they would be untrue.** A reviewer who
catches one false tag discounts the rest, and these directories are read by
people:

- *Remote jobs only* — much of the board is not remote
- *Hand Curated Jobs* — classification is automated
- *Fast apply jobs* — Nabbly drafts a reply, it does not submit applications
- *Payments through platform* — there are none
- *Salary / Salary required / Salary data extracted by hand* — what Nabbly has
  is a budget tier inferred from the wording of a post, which is a different
  claim

**What to put in the description field**, since most of these ask for one:

> Nabbly gathers freelance projects and remote roles from job boards and hiring
> communities into a single board, minutes after they post. Free to search
> without an account, across 25 fields from design and writing to development
> and healthcare.

---

## Tier 2 — Launch platforms

Worth one push each. They bring a spike of real visitors rather than steady
traffic, and the links are typically nofollow, so treat them as an audience
play rather than an SEO one.

- **Product Hunt** — schedule rather than post on impulse; a Tuesday or
  Wednesday launch gets more attention than a weekend.
- **Indie Hackers** — a build-log post about the problem does better than a
  product announcement.
- **Hacker News (Show HN)** — only if you can stand the comments. The audience
  is technical, so lead with how the aggregation works, not the marketing.
- **Relevant subreddits** — r/freelance, r/forhire, r/digitalnomad. Read each
  one's self-promotion rules first; several ban links outright and a ban is
  worse than a missed post.

---

## Tier 3 — The roundup articles

Slowest, and the biggest prize. These are the pages currently taking the
traffic you want.

Realistic targets are the independent blogs, not the corporate ones. Upwork and
Hostinger publish these lists to sell their own product and will not add a
competitor. Smaller sites update their lists to stay current and are often glad
of the tip.

Find current targets by searching "best freelance job boards", "best remote job
boards" and "freelance job boards for <field>", then take the results that are
not owned by a marketplace. Look for a byline, an author page, or a contact
form; a real person is what you are after.

### The email

Short. Editors skim. Nothing about "reaching out" or "circling back".

> **Subject:** A board for your freelance job boards list
>
> Hi <name>,
>
> Your piece on the best freelance job boards is what comes up when I search
> for this, so I wanted to put one more on your radar.
>
> Nabbly pulls freelance projects and remote roles from job boards and hiring
> communities into one board, usually within minutes of a posting going live.
> It is free to search without an account, and it covers 25 fields, so it is
> useful to more than one kind of reader.
>
> If it is a fit for the list: https://nabbly.co/
>
> Either way, thanks for keeping that article current. It is genuinely one of
> the better ones.
>
> <name>
> nabbly.co

**Rules for this email.** Name the actual article. Never send the same text to
two people on the same site. Do not follow up more than once, and leave at
least a week. Do not offer payment for a link, which violates Google's
guidelines and can be penalised.

---

## What not to bother with

- **Paid link packages and "we'll submit you to 500 directories"** services.
  The links come from sites nobody reads, and Google is good at spotting them.
  This actively harms a young domain.
- **Comment and forum link drops.** Nofollow, removed quickly, and they make
  the brand look desperate.
- **Reciprocal link swaps** with unrelated sites.

---

## Measuring it

Search Console, **Links** in the left nav, shows referring domains as Google
finds them. Expect a lag of weeks, not days.

The signal that this is working is not traffic. It is the field pages moving
from "Discovered" to "Indexed" under **Indexing → Pages**, and impressions
starting in **Performance**. Links are what tips a new domain from crawled to
ranked.

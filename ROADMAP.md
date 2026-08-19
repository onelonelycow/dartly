# Nabbly — where the money and the growth could come from

Everything below was raised, argued about, and in several cases already tested.
This file exists so none of it has to be re-derived, and so the ideas that were
explored and **rejected** stay rejected instead of coming back around every few
months looking fresh.

Two rules used throughout:

**A new revenue line and a marketing claim are not the same thing.** Several of
the ideas here make the existing $12/mo easier to justify. That is worth having,
but it is not a second income stream and should not be presented as one.

**"Verified" means checked against the code, not remembered.** Where this file
says something exists or doesn't, it was grepped on 2026-08-17.

---

## Shipped already

Listed so they don't get re-proposed as opportunities.

| What | Why it mattered |
|---|---|
| Personalization wired everywhere | Thumbs-up/down bias only affected the Dashboard's "Picked for you". The main Gigs page — what most people actually use — ignored it, while the site claimed "it keeps learning from what you rate". The claim is now true. |
| Lapsed-payer nudge | `people.set_pay` had been recording yes/maybe/no for months and it only ever appeared in an admin table. People who said **yes** and let the trial lapse were warm leads nobody followed up. |
| Resume-boosted matching | Resume text used to die at the end of the session and only flavoured draft text. It now feeds `fit_score`, which is a personalization signal a scraper-based competitor cannot replicate. |
| Multilingual categorization + Language filter | Non-English postings were being mis-filed and, separately, shown to people who could not read them. |

---

## Open — genuinely new revenue

Ranked by revenue per unit of work, not by how interesting they are.

### 1. Agency / team accounts

**The strongest one, and it is not close.**

Today one person pays $12/mo to watch their own skills. An agency has eight
people and needs design *and* copywriting *and* video simultaneously. Their only
option right now is eight separate accounts that cannot see each other.

The reason this outranks everything else is not the feature, it is the buyer. A
solo freelancer weighs $12 carefully. An agency owner is comparing it to one
recruiter's salary. Same product, an order of magnitude more revenue per
account.

**What exists:** nothing. `accounts.py` is single-user from top to bottom — no
seats, no org, no shared board, no routing.

**Watch out:** the Pricing page currently says, in as many words, *"No seats, no
contracts."* That copy was written to reassure solo freelancers and it directly
contradicts this. It has to change in the same breath, or the pricing page
argues against the product.

### 2. Rate intelligence, as a product rather than a perk

The Market page already answers "what does work like this pay", computed across
the whole board, and it is gated behind Pro. Aggregated rate data assembled from
this many sources is genuinely something nobody else has.

**What exists:** `view_market()` with hand-built CSS charts (deliberately no
altair — that import cost 51MB and is the likeliest cause of an outage the night
before the NextNW send). The data and the maths are there.

**What is missing:** packaging it for a buyer who is not an individual
freelancer, and pricing it.

**The question to settle first, before any work:** this would mean selling data
derived from other people's job postings. That is the same question as the
RSS-feed field on the JobBoardSearch form that we deliberately left empty — it
arrives early and through a side door. Decide it on purpose.

### 3. Alerts-only tier

The cheapest of the three to build and the smallest upside. Right now it is Free
or $12/mo Pro, so everyone who finds $12 too much converts to nothing. An
alerts-only tier catches them.

**What exists:** alerts are built and working. There is exactly one Stripe price
(`STRIPE_PRO_PRICE_ID`). This is a second price and a feature gate, not a new
system.

---

## Open — defensibility, not revenue

These make the existing price easier to justify. Do not put them in a deck as
monetization; it reads as padding and someone will notice.

### 4. Verified private demand

Members forward newsletters into their own private board. Those gigs never
appeared on any public board, and nothing anywhere counts them. An anonymized,
published count is the most concrete answer to "why can't someone just build
this?" — because they cannot get at that supply at all.

Called "dark demand" originally. That was jargon; if the founder had to ask, a
board member would too.

**What exists:** the private forwarding itself works and is owner-scoped. No
public count.

### 5. Outcomes stats

`outcomes.site_stats()` is built and returns gigs landed and dollars landed. It
is shown on an admin view only, **deliberately** — the code carries a comment
saying "3 gigs landed" reads as a scoreboard nobody is using and would undercut
trust rather than build it.

**The gate here is the number, not the work.** When it is a real number it
belongs on the front page far more than a gig count does.

---

### 6. Learning from what people configure

**Founder's idea, 2026-08-19.** The Pro draft controls (Include / Avoid /
Signature / Length) are the first place members tell Nabbly, in their own
words, what a good reply looks like. Right now each answer only affects that
one person. In aggregate it is a product signal nobody else has.

**Why it is worth having.** If a few hundred people fill in **Avoid** and most
write some version of "my rate", that does not mean add a filter — it means
*the default draft raises rates too often*, which is a defect in the drafting
prompt that would otherwise never surface. Same in the other direction: if
half of **Include** is availability, that is a field that should exist on its
own rather than being typed into a free-text box every time.

It is the same shape as two things already shipped — the thumbs-up/down bias
and the willingness-to-pay question — where a small deliberate input compounds
into something a scraper-based competitor cannot copy, because they have no
members to ask.

**What exists:** the four fields ship as of 2026-08-19 and are stored per user.
Nothing aggregates them. No counts, no clustering, no reporting.

**Two conditions before this is built, both real:**

1. **It can only ever be pattern-level and anonymised.** These fields will
   contain rates, "I'm new to this", availability, sometimes client names.
   Reading them as raw text across accounts is not something to do to people
   who wrote them believing they were private, and the FAQ's promise —
   "Nothing is sold, and nothing is shared" — has to keep being true.
2. **It needs enough users to mean anything.** With today's numbers the output
   would be noise dressed as insight. Same gate as the outcomes stats above:
   the blocker is the sample, not the work.

**A caveat on the framing, because it is easy to assume otherwise:** the model
never sees the field LABELS. It receives the assembled instruction text (see
pitch._style_rules). Renaming a label changes nothing about what can be
learned; only aggregating the VALUES does.

## Parked

**Translating non-English postings.** Explicitly deferred. The language work
that shipped makes them correctly categorized and filterable; it does not make
them readable. Roughly 8.5% of the board is not English, mostly German.

---

## Closed — tested and rejected

Kept because both were real attempts to grow outside the freelancer user base,
both were researched properly, and both would look attractive again to anyone
who did not see the research.

### Local service demand (landscaping), 2026-07-17

**No open, high-volume, legally-clean source of local demand exists.** About
twenty sources were tested live. Demand sorts into three buckets and every one
is a dead end:

- **Where the demand actually is, it is gated and hostile:** Nextdoor (login and
  address gated, `Disallow: /`, litigates), Facebook Groups (Groups API killed
  2024), Craigslist gigs (403s automated access, litigated 3Taps), Reddit
  (thinner, and the official API is the only legitimate path).
- **What is open is empty:** ClassifiedAds, Geebo, USNetAds, 5miles, Hoobly,
  AmericanListed all carry goods and hiring, no "services wanted".
- **The rest is hidden and already sold:** Bark, Thumbtack, Angi, Yelp,
  TaskRabbit, Google LSA, Houzz, Care.com paywall the demand and resell it.

### Permit radar for small residential contractors, 2026-07-17

**CAUTION → NO-GO** on that framing, for three compounding reasons:

1. **The timing is backwards.** A residential permit is pulled by the
   contractor-of-record *after* the homeowner has already hired someone. As a
   signal for winning homeowner work it means "this job is gone."
2. **The buyer does not work that way.** Small contractors do not work cold
   prospecting lists — even permit vendors admit subscriptions go unused — and
   they pay *more* for inbound "hire me" leads, which close at 40–60% against
   15–20% cold.
3. **It is already commoditized.** A free PortlandMaps CSV export plus
   PermitStack, Permit Ledger and PermitGrab at $19–149/mo.

Permit data only works with a dedicated sales team and a time-sensitive trigger,
which is a different company.

---

## Channels, not products

**NextNW** is the first organised-group partnership. The founder is a member;
Kent made the introduction and already knew the pitch, which is why the drafted
intro email was never sent and sits in reserve at
`partners/nextnw-intro-email.md`. Announcement squares are rendered and
deliberately unposted. Partner grants are live in `accounts.PARTNER_GRANTS` —
90 days of Pro, no founding slot — and the board service now carries `?ref=`
through to signup, which it did not until 2026-08-17.

**Roundup outreach** is the highest-leverage SEO work available and none of it
is code. Nine live targets, the email template, and the rules are in
[brand/OUTREACH.md](brand/OUTREACH.md). Not started.

---

# Scoped work

## The public data page — NOT a rate page

**The kind of data changed after measuring it.** The original scope said
"publish rates". The data cannot support that, and the reason is not
Freelancer's budget bands — those were already handled, because
`market.skill_stats()` gives each source one vote rather than one per gig.

**The real blocker: 86% of postings state an amount with no period at all.**
An unmarked "$140" might be an hourly rate, a project total, or a week of
travel nursing. Publishing only rates whose period is actually stated leaves:

| period stated | gigs | fields with a 30+ sample |
|---|---|---|
| hourly | 664 | **6** of 25 |
| yearly | 713 | **8** of 25 |
| monthly | 314 | 2 |
| weekly | 99 | 1 |
| **per project** | **12** | **0** |

Per-project is the number freelancers most want and there are twelve of them on
the whole board. A rate page is not honestly buildable from this.

### What IS true, and nobody else has it

Everything counted directly rather than parsed out of prose. Measured
2026-08-17 across 47,858 live gigs from 21 sources:

- **1,852 gigs arriving per day.**
- **Only 27% of postings say what they pay at all** — and it swings from **55%
  in video** and **51% in design** down to **17% in finance** and **9% in
  general**. That is a genuinely novel, quotable finding, and it is an
  advocacy angle rather than another rate table: which fields actually tell
  you the money up front.
- **Remote share by field**, which is nothing like uniform — data 42% and sales
  41% against video 7% and design 16%.
- **Urgency share**, roughly 8-9% in most fields.
- **Volume and velocity by field.**

None of it needs a unit, none of it can be wrong, and no competitor publishes
it because no competitor aggregates 40 sources continuously. It also happens to
be what the product is actually called: a demand radar.

### The number moves, and the movement is the story

**Budget disclosure is falling, not holding.** Measured by week on the live
board:

| week | gigs | says pay | rate | biggest source that week |
|---|---|---|---|---|
| 2026-W30 | 3,029 | 1,100 | **36%** | freelancer (33%) |
| 2026-W31 | 10,973 | 3,868 | **35%** | freelancer (45%) |
| 2026-W32 | 17,747 | 4,338 | **24%** | himalayas (42%) |
| 2026-W33 | 15,437 | 3,542 | **23%** | himalayas (52%) |

The board grew five-fold across those four weeks and the rate nearly halved.
**More gigs do not raise it. Source mix sets it, and volume has nothing to do
with it.**

Disclosure by source, which is the whole explanation:

| source | share of board | states pay |
|---|---|---|
| reddit | small | **71%** |
| freelancer | 30% | **64%** |
| nurserecruiter | small | 46% |
| weworkremotely | small | 36% |
| jobicy | 4% | 27% |
| arbeitnow | 20% | 16% |
| remoteok | 2% | 12% |
| **himalayas** | **39%** | **4%** |
| entcareers / soundlister / dribbble | small | **0%** |

Freelancer's form demands a budget, so every listing has one. Himalayas is a
remote job board where salary is optional and usually left out. When himalayas
overtook freelancer as the dominant source, the rate followed it down.

**Two consequences for the page.**

Any figure published needs a date attached, because it is drifting.

And the drift is the better story. "27% of postings say what they pay" is a
static number a reader cannot check. *"Budget transparency fell from 36% to 23%
in a month as remote job boards displaced freelance marketplaces"* is a trend
with a named cause, measured across 21 sources — which is a thing to link to,
and nobody else is positioned to report it because nobody else watches all of
them at once.

**It is also a lever, not just a metric.** If the disclosure rate matters to
the pitch, the way to raise it is adding marketplace-style sources that require
a budget field, not adding more gigs.

### The prerequisite, now done

`gig_amount()` treated every dollar figure as pay — 7.2% of them were ARR,
valuations, market sizes and 401k matches. Fixed 2026-08-17 (`gig_pay()`),
which moved healthcare's published typical from $109 to $500 and improved
fit scoring, lowball detection and the recorded value of won gigs at the same
time. Any budget figure shown publicly must come from the new parser AND carry
its sample size.

## The old rate-page scope, superseded

Replaced by the section above. It said "publish rates", which the data cannot
support: 86% of postings state an amount with no period, and per-project — the
number freelancers most want — has twelve examples on the whole board. The
detail is in the commit history if anyone needs it.

## Which sources earn their place

Volume and quality moved in opposite directions as the board scaled. Between
W30 and W33 it grew five-fold, and over the same period budget disclosure
nearly halved and the median listing got shorter. Both were caused by the same
thing: one source becoming dominant.

Audited 2026-08-17 across 47,858 live gigs.

| source | share | thin bodies | states pay | dead links (sampled) |
|---|---|---|---|---|
| himalayas | **39%** | **72%** | **4%** | 0 of 15 |
| freelancer | 30% | 5% | 64% | **5 of 60 (8%)** |
| arbeitnow | 20% | 1% | 16% | 0 of 15 |
| jobicy | 4% | 13% | 27% | 1 of 60 (2%) |
| weworkremotely | 1% | — | 36% | blocks bots, unmeasurable |
| entcareers | 0.5% | **100%** | **0%** | 0 of 15 |
| soundlister | 0.4% | **100%** | **0%** | 0 of 15 |
| dribbble | 0.1% | **100%** | **0%** | **10 of 60 (17%)** |

"Thin" is a body under 200 characters. 32% of the whole board is thin.

**Dribbble is the clear cut.** 62 gigs, median body length of **zero
characters**, 17% of its links already dead, no pay information. It contributes
count and nothing else.

**Soundlister and entcareers next.** 100% thin, 0% disclosure, median bodies of
19 and 139 characters. Entcareers was also dark for three days in August.

**Freelancer stays, and gets swept.** 8% dead is the worst of the big three,
but it is the best source on the board for substance (1,039-char median body)
and by far the best for pay disclosure (64%).

**Himalayas is a decision, not a defect.** Its links are fine. It is a remote
job board with terse listings, and at 39% of the board its 150-character median
and 4% disclosure set the tone for the whole product. The answer is not removal;
it is labelling thin listings so people can skip them, and not letting one
source dominate the default view unannounced.

### The link sweep cannot keep up, and that is the bigger problem

`link_checked` is set on **42 of 47,858 gigs — 0.1%**. `sweep_dead_links()`
checks 6 links per 2-minute cycle, which is 4,320 a day against a board taking
in ~1,852 new gigs a day and holding 47,858. It needs 11 days for one pass and
never gets a clean one. In practice, when someone clicks a gig, nobody has ever
verified that link is alive.

Prioritising gigs about to be *shown* would beat sweeping uniformly.

### A method warning, because it nearly cost a good source

The first pass sampled 15 links per source and reported jobicy at **27% dead**.
It was not dead. It was returning `429 Too Many Requests` because the sample
itself was hammering it, and the checker counted that as a failure. At 60 links
with backoff it is **2%**.

Sample small, conclude big, cut a healthy source. Any future source cull needs
a sample that distinguishes "gone" from "throttled", and weworkremotely cannot
be measured this way at all — it returns 403 to every automated request.

### What would settle this properly

Apply-clicks per gig, by source. That turns "quality" from a judgement into a
number: a source whose gigs nobody clicks is not earning its place regardless
of how its bodies read. The counter exists (`activity.log_apply`) but has only
test traffic so far. Revisit once real apply volume accumulates.

## Validating team accounts before building

The architecture is readier than expected — per-user storage runs through one
chokepoint, `paths.user_file(name, scope)`, which already takes a scope, and
only ~10 places check `pro` across both services. A shared team board is
several accounts resolving to a shared scope, not a storage rewrite.

The risk is not technical. It is that there are **zero agency customers today**,
and the buyer is assumed rather than known.

**What the market says the buyer is worth:** agencies routinely spend
$50–$10,000/month on finding work, with tools in the $50–$200 band unremarkable.
Against that, $12 is noise. That is the argument for the idea; it is not
evidence anyone wants this specific thing.

### Ask before building

NextNW is the natural first conversation. Ask these without describing the
feature first — a described feature gets a polite yes.

1. When a project comes in that isn't your own specialism, how do you find out
   about it today?
2. Who on your team is looking for incoming work, and how many of them?
3. What are you already paying for to find work? What does it cost?
4. When something good comes in, how does it get to the right person?
5. Last time you missed something you'd have wanted — what happened?

Only then describe one shared board across everyone's skills, with the owner
seeing everything, and ask what it would have to do to be worth paying for.

### What would kill it

If the answer to (3) is "nothing", the budget is theoretical. If (4) is "we
just forward it in Slack", the routing half has no value and this collapses
back into several individual accounts, which they can already buy.

### Blocked on a copy change either way

The Pricing page says **"No seats, no contracts."** That has to change in the
same release, or the pricing page argues against the product being sold.

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

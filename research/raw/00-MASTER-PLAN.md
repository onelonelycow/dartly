# Nabbly: the combined plan

Synthesised 2026-08-25 from three research passes:
- `01-seo-content.md` (10,700 words) — keywords, guides, technical
- `02-data-partnerships.md` (1,336 lines) — the data asset, legal, reports
- `03-outreach-representation.md` (927 lines) — directories, communities, press

This document is the sequence. The three source documents are the detail.

---

## The one-paragraph version

Nabbly's problem is not that its SEO is bad. It is that the site has no internal
link structure, points its pages at words nobody types, and has never published
anything only Nabbly could publish. All three research passes independently
arrived at the same asset: the board sees roughly 4,200 new gigs a day across 24
fields, and nobody else can describe what that market is actually doing. That one
asset is simultaneously the SEO answer (original content on a site that has
none), the press answer (a data story that needs no source list), and the
long-term business answer (an index, not a feed). The plan is to stop treating
those as three projects.

---

## Where the three passes agreed without being asked to

This matters more than any individual finding, because three separate passes
converged on it from different directions.

| The finding | SEO pass called it | Data pass called it | Outreach pass called it |
|---|---|---|---|
| Publish what the board sees | The only original content the domain can produce | The Rate Bands report | The press asset that needs no source list |
| Don't fight for "best job boards" | Recommendation-intent SERP, listicles only | n/a | Get listed on those lists instead |
| Nabbly's edge is speed/recency | Nobody owns "posted in the last 24 hours" | "First Hour" is uniquely yours | The pitch angle journalists respond to |
| The digest is underused | n/a | The distribution for every report | How Remotive and Wellfound actually started |

Guide #1 in the SEO plan ("what freelance design work actually pays right now")
and the Rate Bands report in the data plan are **the same piece of work**. Write
it once. It is a guide, a report, a press pitch, and a newsletter issue.

---

## Tier 0: do this week, because it cannot be undone later

### 1. Start daily aggregate archiving
**1 to 2 days of work. About $5/month. This is the only irreversible item in all
three documents.**

One row per field per day: gig counts, budget bands, urgency and size mix, skill
token counts, disappearance events. Plus versioned field definitions so the
archive stays comparable to itself.

Your 21-day retention is destroying this asset right now, today, while you read
this. History cannot be back-filled. Every data play, every recurring report, and
every partnership conversation two years out is gated on this existing. Two days
of work is the option on all of it.

### 2. Answer the subreddit collection question with a lawyer
**One billable hour, roughly $300 to $600.**

Reddit's terms require a negotiated commercial licence for commercial use, and
Reddit is currently litigating against Perplexity, SerpApi, Oxylabs and AWMProxy
for scraping obtained *indirectly* — plus Anthropic separately. This is the
largest unpriced risk in the business and it gets more expensive to fix the
longer the pipeline runs unexamined. The remedy is cheap if you need it:
commercial API access is about $0.24 per 1,000 calls.

### 3. Answer one product question
**30 minutes.**

Is board.nabbly.co browsable without an account? Show HN expects no signup wall,
and r/SideProject reacts the same way. If there is a wall, that is the highest
priority product decision of the month, because it gates half of Tier 3.

---

## Tier 1: free, fast, and the site is broken without them

These are hours, not days, and they are the difference between the SEO work
mattering and not.

### 4. Link the field pages from the homepage
**30 minutes. Biggest single item in the SEO document.**

Every href in `index.html` was extracted. The complete internal link set is `/`,
About, FAQ, Privacy, Terms, and three anchors. The homepage links to **none** of
the 23 field pages and **not** to the guide. They are reachable only via
sitemap.xml, About, the guide, and each other.

Whatever authority the domain earns lands on the homepage and stops there. Add a
marker comment to `index.html` and have the generator fill between the markers,
the same mechanism the sibling pills already use, so the homepage can never link
to a page that run did not write.

### 5. Fix the field page title pattern
**20 minutes, fixes 23 pages at once.**

The URL says `jobs`. The title and H1 say `work`. For all 24 fields, autocomplete
completes to "freelance X **jobs**" and "remote X **jobs**".

```python
title = f"Freelance {kw} jobs and remote {kw} work · Nabbly"
```

H1 pattern, same voice and line break as now:

```
Freelance {kw} jobs and remote {kw} work,
the moment it posts.
```

Meta descriptions get a per-field closing clause drawn from the `size_tier` and
`urgency` mix that already feeds `speed_line()`, so the 23 are not identical.

### 6. Fix the homepage title and description
**20 minutes.**

Current title leads with the brand, contains no noun anyone searches, and uses an
em dash your own FEEL.md forbids. The description claims "25+ fields" when the
CSV has 24 plus an "Other" bucket, which is a numbers-must-be-true violation
sitting on your most important page.

```
Freelance and remote jobs, minutes after they post · Nabbly
```

```
New freelance briefs and remote roles from every job board and hiring
community, on one board minutes after they post. Free to browse, alerts on Pro.
```

H1: add one word. "Every **freelance** gig and remote role, the moment it drops."
The brand line survives intact and now contains the query.

### 7. Point six field pages at the right noun
**45 minutes.**

The generator takes the noun from the first word of the category label. Six are
aimed at a word that means something else in search:

| Field | Gigs | Currently targets | Should target |
|---|---|---|---|
| Development / tech | 9,238 | "development" → nonprofit fundraising | **developer** |
| Data / analytics | 2,409 | "data" → data entry, data journalism | check the bucket first |
| Admin / VA | 1,979 | "admin" → UK-skewed | **virtual assistant** |
| Video / animation | 1,741 | "video" → drifts to UK/London | **video editing / editor** |
| Product / PM | 1,688 | "product" → product photography | **product manager** |
| Management / ops | 1,651 | "management" → IT remote management | **project manager** |
| Customer support | 1,518 | "support" | **customer service** |

Your 9,238-gig flagship is pointed at a word that returns charity fundraising.
Move it to `/freelance-developer-jobs/` with a 301.

For Data, check whether those 2,409 gigs are mostly analysis or mostly data
entry before writing the page. They are different terms and different pages.

### 8. Fix the two live bugs

- `/freelance-photography-jobs/` returns 200, is indexable and self-canonical,
  and is **absent from the sitemap**. The generator writes pages but never
  prunes them. Add pruning. Photography (185 gigs) should not be published
  anyway; the intent is overwhelmingly local.
- `/guides/` returns 404. Create it, with breadcrumb and Article schema.

### 9. Resolve the board robots.txt contradiction
**The intention and the implementation currently disagree.**

The plan says board.nabbly.co stays noindex except `/`, `/gigs` and field views.
But the field views *are* `/gigs?field=...`, and `board.nabbly.co/robots.txt`
carries `Disallow: /gigs?*`, which blocks exactly them. Meanwhile every field
page's amber CTA points at that blocked URL, and both `board.nabbly.co/` and
`/gigs` return `<title>Nabbly</title>` with no canonical and no meta robots, so
two pages titled "Nabbly" compete with nabbly.co on your own brand query.

**Recommended: Option A.** board.nabbly.co is not an SEO surface. Put
`<meta name="robots" content="noindex, follow">` on every board route including
`/` and `/gigs`, and leave robots.txt permissive so crawlers can actually read
the noindex. A `Disallow` prevents the crawler ever seeing the `noindex`, which
is why the current setup cannot achieve what it is aiming at.

Either way, `/gigs` should not be titled "Nabbly".

---

## Tier 2: the one real gap, and the content that compounds

### 10. Build `/new-remote-jobs/`
**3 hours. The single best new-page opportunity found.**

Nobody owns recency, and recency is your entire pitch. Verified in autocomplete:
`jobs posted in the last` returns a full ten-suggestion set (24 hours, 3 days,
week, hour, since yesterday). `remote jobs posted` returns another. The modifier
leaks into individual fields as real suggestions like "remote design jobs in the
last 3 days" and "remote qa jobs in the last week".

The page currently ranking for it, `remotesource.com/remote-jobs/posted-today`,
has 350 words and shows **zero actual jobs**.

Rebuild daily, with a visible build date so the page never lies about freshness.

### 11. Write the first data guide, which is also the first report
**2 to 3 days. Serves three purposes at once.**

SEO guide #1 is "what freelance design work actually pays right now". The data
plan's Rate Bands is "what clients actually offer, which nobody measures". Same
work. Every competitor in that SERP is writing from a survey, an opinion, or a
2019 rate card. You have the postings.

**The FEEL.md rule that makes this safe:** every figure is a share or a band,
never a live count, and every figure is stamped with its window. "Across the
design gigs Nabbly logged in the 30 days to 25 August 2026, about a third were
posted at the larger end" stays true forever, because it names its window.
Rebuild these blocks monthly and restamp.

Also publish **First Hour** (arrival timing). Five weeks is genuinely enough for
hour-of-day, and your architecture is the only thing that produces it.

### 12. The remaining guides, in order
1. What freelance design work actually pays *(= Rate Bands)*
2. How to spot a fake or scam job posting
3. Does applying early to a job actually help *(your thesis, with your data)*
4. How to get freelance work with no experience
5. Freelance rates by field: what clients are posting
6. How many gigs should you reply to in a day
7. Freelance proposal template
8. Freelance vs contract vs employed
9. Freelance writing jobs for beginners
10. How to find freelance clients without a marketplace

**Deliberately not written:** "best freelance job boards". It is the biggest
commercial term in the category and it is a listicle SERP no product page ranks
on. Worse, writing it means naming boards, which breaks the no-sources rule. The
only route onto that SERP is being named in someone else's list, which is
outreach, not content. Naming this explicitly so it stops coming back as an idea.

### 13. Build `nabbly.co/data/` and a press email
**1 day.** The permanent link target every report points at.

---

## Tier 3: distribution, once there is something to point at

Roughly six to eight hours a week. Nothing costs more than $60 unless marked.

### Week 1: claim the permanent surfaces
- AlternativeTo account **today**, to start the age clock. Submit later in the
  week, then add Nabbly as an alternative on four competitor pages. This is
  first because its pages rank for "SolidGigs alternatives" and similar, putting
  you on competitors' own comparison surfaces for free.
- JobBoardSearch (**feed field empty**, per the settled Google for Jobs
  decision), SaaSHub, Crunchbase under OneLonelyCow, Peerlist, Launching Next.
- Comment genuinely on three Product Hunt launches and three Indie Hackers posts
  **every day**. This is account seasoning and it cannot be done retroactively.

**Not yet:** G2 and Capterra (badges need 10 to 20 reviews, you have one signup).
BetaList (you are live, not beta). Uneed's free lane closed 2026-08-17, so it now
starts at $14.99.

### Week 2: say something true in public
- Peerlist Launchpad, Fazier, MicroLaunch.
- Indie Hackers Milestones post, the honest one: what you built, what comes in
  daily, that you have one signup, and what you got wrong.
- Publish guide two.

### Week 3: human outreach
- Ask Peak Freelance and Superpath for single-issue sponsorship rates. Expect
  $150 to $900.
- Pitch The Freelance Creative a guest piece on the aggregate data angle.
- Email Steve Folland at Being Freelance about guesting.
- Email five freelance tool roundup editors.

**Note:** Millo owns SolidGigs. Great outlet, bad prospect. Do not spend time
there before checking whether they will run a competitor's ad.

### Week 4: the two launches
- r/SideProject, then one SHOW IH post on r/indiehackers. **You get one per
  product, spend it deliberately.**
- Show HN, Tuesday to Thursday morning Pacific or Sunday evening Eastern. Be at
  the keyboard for six hours. Do not ask anyone to upvote. **Gated on the
  no-signup answer from Tier 0.**
- Four journalist pitches with numbers recalculated that morning.
- Book Product Hunt for week 6 or 7.

### Communities: most doors are shut
Roughly 60% of founder-facing subreddits ban self-promotion outright. r/forhire
has no legal post format for a tool at all. r/digitalnomad and
r/InternetIsBeautiful are ban risks. The legal set is small: r/SideProject, one
SHOW IH post, Indie Hackers Milestones, Show HN.

Reddit blocked automated access during this research, so **every subreddit rule
needs checking on its own sidebar before you post.**

---

## What not to spend money on

| Thing | Cost | Verdict |
|---|---|---|
| Boutique PR retainer | $3,000 to $7,000/mo | No |
| MarketerHire | from $5,000/mo | No |
| SEO agency retainer | varies | No |
| **Technical SEO audit, fixed scope, once** | $400 to $1,200 | **Defensible** |
| **Freelance PR, 5 to 10 hours, no retainer** | $80 to $150/hr | **Defensible** |
| One newsletter sponsorship test | $150 to $900 | Worth one test |

---

## Selling the data: closed for two years, and that is fine

Alt-data buyers require two to three years of history minimum and prefer five.
You have 37 days. Even at 24 months, realistic revenue is $20k to $80k, which is
140 to 550 Pro subscribers. **The data's job is to acquire subscribers, not to
become revenue.**

Do not contact a hedge fund, list on a commercial data marketplace, or attend an
alt-data event. It is not close.

**The legal ground for aggregates is favourable.** *Feist* means computed
statistics are nobody's copyright. *CV-Online Latvia v Melons* (C-762/19) is a
CJEU judgment about a job-listing meta-search engine, which is precisely Nabbly's
model: database rights apply, but only on proven harm to the source's investment,
which makes linking out both honest and legally safer. Note *hiQ* won on the CFAA
and still paid $500k on contract and tort grounds, so "it's public" is not a
shield on its own.

**At 6 to 12 months:** monthly Demand Index, Skills on the Board, apply to Dewey
Data (academic marketplace, 600+ universities, non-commercial scoped licences,
live in under two weeks, LinkUp is already there), approach the WFH Research /
Flex Index circle.

---

## The conflicts, named rather than smoothed over

**The no-sources rule costs you credibility, and that is a real cost.** Every
comparable publisher is credible partly because its source is known and singular:
Indeed's postings, ADP's payroll, Gusto's payroll. Nabbly cannot say what it
measures without either naming sources or being vague.

The workable middle: **describe the shape of the collection without naming the
members.** "Measured across 21 public job boards and hiring communities, covering
24 fields, from [date] to [date]. Postings appearing on more than one source are
counted once." That is a real method note. Flex Index does exactly this and Nick
Bloom still calls it the best dataset he knows of on its question. Method
transparency and source transparency are not the same thing, and only the first
is required.

This holds for journalists. It does **not** hold for a hedge fund's due diligence
questionnaire, which requires naming every source and documenting rights around
each. That is one more reason the commercial data path is closed, but you should
decide deliberately whether you would ever disclose the full source list under
NDA, rather than discovering the answer in a meeting.

**"Numbers must be true at all times" versus recurring reports** is resolved by
as-of-date stamping, in the same visual unit as the number, never in a footnote.
And state the observation window prominently in early reports. "Measured over
five weeks" is a limitation, and publishing it is what makes the report credible.
Readers forgive a short window that is disclosed. They do not forgive one that is
discovered.

---

## What success looks like at day 30

Set this expectation now so you do not misread the result.

- 8 to 12 permanent directory listings live.
- One or two of Show HN, r/SideProject or Indie Hackers producing a spike of a
  few hundred visits.
- **20 to 60 signups total, not 500.** Low end is normal.
- One or two newsletter replies with an actual rate quoted.
- **Zero press.** Press takes three months, and only if the data pitch lands.

SEO changes take 4 to 12 weeks to show. Nothing in Tier 1 will move a number this
month, and that is expected rather than a sign it failed.

**The stopping rule:** if day 30 produces signups but nobody comes back on day
31, stop all distribution work and fix retention. Distribution is only worth
buying for a product people return to.

---

## The pattern worth taking seriously

Remotive and Wellfound both started as email lists, not boards. Rodolphe Dutel
wrote one blog post in 2014, collected 100+ emails from it, then launched on
Product Hunt a month later **as a newsletter about remote work** and hit #1.
SolidGigs launched on top of Millo, an audience Preston Lee already had. None of
them grew from directory listings.

Nabbly's free daily digest is already that asset and it is currently framed as a
feature of the board. Every report in Tier 2 has an obvious home in it. Consider
whether the thing you launch is the digest rather than the board.

---

## Open questions for you

1. **Is the board browsable without an account?** Gates Show HN, r/SideProject,
   and half of Tier 3.
2. **Are the 2,409 Data gigs mostly analysis or mostly data entry?** Different
   keyword, different page, and data entry is the larger and easier term.
3. **Would you ever disclose the full source list privately under NDA?** If no,
   the commercial data path closes permanently, which is a legitimate choice to
   make deliberately.
4. **Does `OUTREACH.md` exist?** The brief references it; it was not in the zip.
   Agent 3 rebuilt that ground from scratch, so the two plans need reconciling.
5. **Should Management / operations merge into Consulting?** It was the weakest
   of the six noun fixes and the field label may be the real problem.

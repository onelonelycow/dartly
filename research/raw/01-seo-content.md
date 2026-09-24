# Nabbly SEO strategy and content plan

Research date: 2026-08-25 / 2026-08-26. All live checks made against nabbly.co,
board.nabbly.co and competitor sites on those dates.

---

## How to read this document

Every claim in here is labelled. There are only two labels.

**VERIFIED** means I pulled it myself today and can show the source. That covers:

- Google autocomplete suggestion sets for 79 seed phrases, pulled from
  `https://suggestqueries.google.com/complete/search?client=firefox&q=...`
  on 2026-08-25. Raw output saved alongside this file as `autocomplete.txt`,
  `autocomplete2.txt`, `autocomplete3.txt`.
- Live SERP composition for 12 queries, read on 2026-08-25.
- Competitor `<title>`, `<meta description>` and `<h1>`, read straight out of
  their live HTML today.
- The state of nabbly.co and board.nabbly.co: HTTP status codes, sitemap
  contents, robots.txt, live titles.

**ESTIMATED** means I am inferring it and you should treat it as a band, not a
number. I had no access to Ahrefs, Semrush or Keyword Planner, and Google
Trends refused my requests (HTTP 429). I have not invented a single precise
monthly volume figure anywhere in this document, and you should be suspicious
of any SEO document that gives you one without naming the tool it came from.

### How the volume bands were derived

Google's autocomplete is ranked by real query popularity. That gives a usable
ordinal signal even without volume numbers. I read it three ways:

- **AC-full**: the seed returned a complete set of ten on-topic suggestions,
  with geographic variants (uk, canada, nyc) and intent modifiers (entry level,
  part time, no experience) stacked behind it. A phrase only accumulates that
  much tail if the head has real volume.
- **AC-partial**: fewer than ten suggestions, or the set drifted to a related
  but different phrase.
- **AC-polluted**: the suggestion set was hijacked by unrelated entities. If
  "hr gig" returns H.R. Giger and "audio gigs" returns live music in Glasgow,
  that phrase is not what job seekers type, and a page targeting it is wasted.
  This turned out to be the most decisive single test in the whole exercise.
- **SERP-agg**: the results page is owned by Indeed, ZipRecruiter, Glassdoor,
  LinkedIn or Upwork template pages. Those companies only build pages at that
  scale where money is. High volume, high difficulty.
- **SERP-niche**: smaller aggregators rank. Reachable.

Bands used throughout, US monthly:
A = 50k+, B = 10k to 50k, C = 2k to 10k, D = 500 to 2k, E = 100 to 500,
F = under 100.

Difficulty is my read of the live SERP, expressed as very high / high / medium
/ low. It is not a KD score and I am not going to pretend it is one.

**One structural fact worth stating before anything else.** Nabbly's domain is
one month old and has one organic signup. Nothing in this document beats a
head term this year. Everything here is aimed at the tail that a one month old
domain can actually take, and at not wasting the good pages that already exist.

---

# Part 0. The seven things to change today, in order

Ordered by expected impact divided by effort. Details for each are further down.

| # | Change | Where | Effort |
|---|---|---|---|
| 1 | Link the field pages and the guide from the homepage. Right now the homepage links to **none** of them. | `index.html` | 30 min |
| 2 | Fix the title pattern so the page says "jobs" like the URL does, not "work". | `make_field_pages.py` | 20 min |
| 3 | Build `/new-remote-jobs/`, the recency page. This is the one real gap I found. | new page in generator | 3 hours |
| 4 | Fix the homepage title and description. | `index.html` | 20 min |
| 5 | Point six field pages at the noun people actually search, not the noun in the category label. | `make_field_pages.py` | 45 min |
| 6 | Delete the orphaned `/freelance-photography-jobs/` page and make the generator prune. | `make_field_pages.py` | 30 min |
| 7 | Create `/guides/` (it currently 404s) and add breadcrumb plus Article schema. | generator | 1 hour |

---

# Part 1. The head term and the homepage

## 1.1 What the competition actually targets

VERIFIED. I read these out of the live HTML on 2026-08-25.

| Site | `<title>` | What it targets |
|---|---|---|
| Remotive | Remote Jobs in Programming, Support, Design and more | "remote jobs" plus category words |
| Himalayas | Remote Job Board and Free AI Job Search Tools \| Himalayas | "remote job board" |
| We Work Remotely | We Work Remotely: Advanced Remote Job Search | brand, plus "remote job search" |
| Wellfound | Find Startup Jobs Near You and Remote Jobs \| Wellfound | "startup jobs", "remote jobs" |
| SolidGigs | SolidGigs, Get Freelance Leads on Autopilot. | nothing. Brand only. |
| Contra | Contra, A professional network for the jobs and skills of the future | nothing on the homepage |
| JobBoardSearch | 824 Top Job Boards for Job Seekers & Recruiters, List Yours Today | "job boards" directory |

Two things fall out of that table.

**Contra does not target on the homepage, it targets on the category page.**
VERIFIED: `contra.com/featured-jobs/freelance-design-jobs` has the title
"Freelance Design Jobs, Find New Remote Design Projects and Jobs Daily |
Contra", an H1 of exactly "Freelance Design Jobs", ten listings, an FAQ block,
and a long "Additional resources" prose section. It ranked position one for
"freelance design jobs" when I searched today. That is the same page archetype
Nabbly already built 23 of. The archetype works. Nabbly's version is missing
the exact-match title, the FAQ and the prose depth.

**Workello is down.** VERIFIED: `www.workello.com` returned a Cloudflare "DNS
points to prohibited IP" error page today. Do not spend any time benchmarking
against it.

## 1.2 The gap: nobody owns recency

This is the strongest finding in the research and it is not close.

VERIFIED autocomplete, 2026-08-25:

- `jobs posted in the last ` returns, in order:
  **24 hours, 3 days, week, 24 hours near me, week near me, hour, 7 days,
  24 hours linkedin, 24 hours remote, 24 hours since yesterday**. Ten of ten,
  all on-topic, with modifier stacking. That is an AC-full set on a phrase that
  is purely about freshness.
- `remote jobs posted ` returns: **today, in the last 24 hours, today since
  yesterday, in the last 3 days, this week, in the last week, recently,
  yesterday, in the last hour**.
- `just posted jobs` returns: **just posted jobs, near me, indeed just posted
  jobs, just posted remote jobs, jobs just posted today, how to find just
  posted jobs on linkedin, jobs just posted since yesterday**.
- `new remote jobs ` returns: **hiring now, near me, 2026, posted today,
  indeed**.

And the modifier leaks into individual fields. These are real suggestions I
pulled today, not constructed:

`remote design jobs in the last 3 days` · `freelance graphic design jobs in the
last 3 days` · `freelance graphic design jobs in the last week` ·
`remote marketing jobs in the last 3 days` · `remote finance jobs in the last 3
days` · `remote hr jobs in the last 3 days` · `remote video jobs in the last 3
days` · `remote product jobs in the last 3 days` · `remote product jobs since
yesterday` · `remote audio jobs since yesterday` · `remote qa jobs in the last
3 days` · `remote qa jobs in the last week` · `remote management jobs in the
last 3 days` · `freelance design jobs in the last 3 days`

People have learned Google's own date filter language and now type it into the
search box. Nabbly's entire pitch is that phrase.

VERIFIED SERP for "remote jobs posted in the last 24 hours": the page is
Indeed query-string pages, a set of 2021 Substack newsletter archives, and
`remotesource.com/remote-jobs/posted-today`. I fetched that Remote Source page.
It has the title "Remote Jobs Posted Today | New Listings Updated Daily |
Remote Source", an H1 of "Remote Jobs Posted Today", roughly 350 to 400 words
of prose, no structured data, and it displays **zero actual job listings**. It
says "913 remote jobs found" and then shows filters and a signup prompt.

A page with 16 to 24 real gig titles on it, honest prose, and a working link to
a live board is straightforwardly better than that.

ESTIMATED band for the recency cluster in aggregate: **B (10k to 50k US per
month)** across all the phrasings combined, with no single phrase above C.
Method: AC-full on four separate seed stems with full modifier stacking, and a
SERP that Indeed has built dedicated template pages for. Confidence: medium on
the band, high on the ranking of these phrases relative to each other.

Difficulty: **medium**. Indeed's pages will not move, but positions three
through ten on that SERP are held by a Substack archive from 2021 and one small
site showing no jobs. That is the most beatable page one I looked at all day.

## 1.3 Recommendation 1: build /new-remote-jobs/

**Target query:** "remote jobs posted today" and the "in the last 24 hours" /
"just posted" family.
**Page:** new, `/new-remote-jobs/`, generated by `make_field_pages.py`.
**Effort:** about 3 hours, most of it deciding the rebuild cadence.

Proposed title (58 characters):

```
New remote and freelance jobs, posted in the last day · Nabbly
```

Proposed meta description (152 characters):

```
The newest remote roles and freelance briefs from every job board and hiring
community, gathered on one board minutes after they post. Free to browse.
```

Proposed H1:

```
New remote and freelance jobs.
```

Proposed lead paragraph:

```
Nabbly watches job boards and hiring communities around the clock and puts new
work on the board minutes after it posts. The sample below was taken when this
page was last built. The board itself is thousands of gigs deep and changes
through the day.
```

**The honesty problem, and how to solve it.** A static page that claims
"posted today" becomes a lie the moment the build is an hour old. That is
exactly the trap FEEL.md already caught with relative timestamps, and the
generator's own docstring calls it out. Three rules make this page safe:

1. Rebuild it **daily**, not weekly. The rest of the site can stay weekly. One
   page a day is cheap.
2. Print the build date visibly under the sample: `Sample taken 25 August
   2026.` A dated statement is true forever.
3. Never print a count. "Thousands of gigs deep" is true at any board size
   above two thousand, which the board has never been below since launch.

Note the tension in the title: "posted in the last day" is a claim about the
gigs, and it is true of the sample at build time and true of the live board at
all times, because the board genuinely receives roughly 4,200 gigs a day. If
that ever stops being reliably true, the title has to change. Flag it in the
generator as a comment so nobody has to rediscover the constraint.

## 1.4 Recommendation 2: fix the homepage title

VERIFIED current state:

```
<title>Nabbly — every gig and remote role, the moment it drops</title>
```

Three problems. It leads with the brand, which nobody searches. It contains no
noun anyone types into Google, "gig" and "remote role" are not the query, "jobs"
is. And it uses an em dash, which FEEL.md section 7 tells you not to.

The meta description also says "across 25+ fields". Your own CSV has 24 fields
plus an "Other / general" bucket, and the brief says 24. That number is at best
arguable and at worst untrue, which is a FEEL.md section 7 violation sitting on
your most important page.

**Proposed title (59 characters):**

```
Freelance and remote jobs, minutes after they post · Nabbly
```

**Proposed meta description (147 characters):**

```
New freelance briefs and remote roles from every job board and hiring
community, on one board minutes after they post. Free to browse, alerts on Pro.
```

**Proposed H1 change:** keep the line, add one word.

```
Every freelance gig and remote role,
the moment it drops.
```

That is the brand line intact, in Nabbly's own vocabulary, with "freelance"
added at a cost of one word. The H1 is the single strongest on-page relevance
signal you own and it currently contains neither "freelance" nor "jobs".

**Why the brand goes last in every title.** Google truncates titles at roughly
580 pixels, near enough 60 characters. Putting `· Nabbly` at the end means the
part that gets cut is the part you least need. The field pages already do this
correctly. The homepage does not.

## 1.5 What not to chase

**"freelance job boards" and "best freelance job sites".** VERIFIED SERP: every
result on page one is a listicle. RISD's career centre, millo.co, lendio,
nocodeinstitute, freelancinghacks. No product page ranks. This is a
recommendation-intent SERP, and the only way onto it is to be named in
somebody else's list, which is outreach, not content.

There is a second, harder reason to leave it alone. Writing your own "best
freelance job boards" post means naming boards. FEEL.md section 7 says never
advertise sources, and GOOGLE-JOBS.md says the same thing at greater length.
The single highest-volume commercial term in this category is one Nabbly has
decided, for good reasons, that it cannot write about. Worth naming that
explicitly so it stops coming back as an idea.

**"gigs" as a keyword.** VERIFIED and decisive. I probed `<field> gig` for all
24 fields. The suggestion sets came back polluted for the majority:

- `design gig` returns "design gigi", "design giger", "ciga design"
- `hr gig` returns **H.R. Giger** for all ten suggestions
- `audio gigs` returns "audio gigs glasgow", live music
- `data gig` returns "data gigabytes"
- `product gig` returns "gigabyte product registration"
- `sales gig` returns generic "sales jobs" results
- `teaching gig` returns three suggestions, two of them a toy shop in Gig
  Harbor

Clean and usable: `writing gigs`, `photography gigs`, `translation gigs`,
`graphic design gigs`, `consulting gigs`, `marketing gigs`, `architecture gigs`,
`virtual assistant gigs`. That is eight out of twenty-four.

"Gigs" is Nabbly's internal vocabulary and FEEL.md is right to keep it in the
product. It is not the search vocabulary. Field page titles must say "jobs".

---

# Part 2. Keyword landscape, field by field

## 2.1 The one change that fixes 23 pages at once

VERIFIED current state, live today:

- URL: `nabbly.co/freelance-design-jobs/`
- Title: `Freelance and remote design work · Nabbly`
- H1: `Freelance and remote design work, the moment it posts.`

The URL says jobs. The title and H1 say work. VERIFIED autocomplete: for every
single one of the 24 fields, the completions are "freelance X **jobs**" and
"remote X **jobs**". "Freelance design work" does exist as a suggestion, but it
sits below "freelance designer jobs" and "freelance designer". You are ranking
a page for a word people do not type, on a URL that contains the word they do.

**Proposed title pattern:**

```python
title = f"Freelance {kw} jobs and remote {kw} work · Nabbly"
```

For fields where remote employment dominates freelance (see 2.3), flip it:

```python
title = f"Remote {kw} jobs and freelance {kw} work · Nabbly"
```

Worked examples:

- `Freelance design jobs and remote design work · Nabbly` (52 chars)
- `Freelance developer jobs and remote developer work · Nabbly` (58)
- `Remote healthcare jobs and freelance healthcare work · Nabbly` (60)
- `Freelance virtual assistant jobs and remote VA work · Nabbly` (59)

**Proposed H1 pattern:**

```
Freelance {kw} jobs and remote {kw} work,
the moment it posts.
```

Same voice, same line break, same closing phrase. It just contains the query
now.

**Proposed meta description pattern**, with a per-field closing clause so the
23 descriptions are not identical:

```
Freelance {kw} jobs and remote {kw} briefs from every job board and hiring
community, gathered minutes after they post. {shape_clause}
```

where `shape_clause` is derived from the same `size_tier` and `urgency` mix
that already feeds `speed_line()`, one of:

- `A good share is posted at the larger end.`
- `Mostly quick turnarounds.`
- `Many carry a deadline.`

## 2.2 The noun problem: six pages are aimed at the wrong word

The generator derives the prose noun from the first word of the category label.
For most fields that is fine. For six it is aimed at a phrase people do not
search, or one that means something else. All VERIFIED from autocomplete today.

**Development / tech (9,238 gigs, your biggest).** The seed `remote development
j` returns "remote development jobs **fundraising**", "remote development jobs
**nonprofit**", "remote jobs **development sector**". In search, "development"
without qualification reads as international development and charity
fundraising. "Developer" is unambiguous: `remote developer j` returns entry
level, worldwide, uk, canada, india, usa, europe, for freshers, south africa.
Ten of ten, clean.

> Target `freelance developer jobs` and `remote developer jobs`. Move the URL
> to `/freelance-developer-jobs/` with a 301 from the old path. This is your
> largest inventory and it is currently pointed at an ambiguous word.

**Admin / VA (1,979).** `freelance virtual assistant j` and `remote virtual
assistant j` both return AC-full sets with the whole beginner tail attached: no
experience, for beginners, part time, work from home, entry level. `freelance
admin j` returns an AC-full set too, but the first suggestion is "freelance
admin jobs remote" and the geography skews UK, Singapore, South Africa.
"Virtual assistant" is the US term and the higher-intent one.

> Target `freelance virtual assistant jobs`. Move to
> `/freelance-virtual-assistant-jobs/`, 301 from `/freelance-admin-jobs/`.

**Video / animation (1,741).** `remote video j` drifts to UK and London.
`remote jobs video editing`, `remote jobs video editor` and `remote junior
video editor jobs` all appear as suggestions. The job is "video editor", not
"video".

> Target `freelance video editing jobs` and `remote video editor jobs`.

**Product / PM (1,688).** `freelance product j` returns "freelance product
photography jobs", "freelance product review jobs", "freelance product listing
jobs". Wrong intent entirely. But "freelance jobs product manager", "freelance
product manager jobs remote" and "remote jobs product manager" all appear.

> Target `freelance product manager jobs`.

**Management / operations (1,651).** `remote management j` returns "remote
login vs remote management", which tells you the phrase is contaminated by
IT-admin meaning. `freelance project management jobs` and `freelance project
management jobs remote` both appear cleanly.

> Target `freelance project manager jobs`. This is the weakest of the six and
> the field label may be the real problem. Consider whether it should merge
> into Consulting.

**Customer support (1,518).** The probe for `freelance customer support j`
returned "freelance **customer service** jobs", "freelance customer service
jobs remote", "freelance customer service jobs uk" inside its own suggestion
set. Google is telling you the two are the same query and "service" is the head.

> Target `remote customer service jobs`, with "customer support" as the
> secondary. Note this is a very high difficulty term.

**Data / analytics (2,409).** `freelance data j` returns "freelance jobs
**data entry**" and "freelance database jobs" mixed with data journalism.
"Data" alone is three different jobs. If your 2,409 gigs are mostly analysis,
target `freelance data analyst jobs`. If they are mostly data entry, that is a
much larger and easier term, but it is a different page. **Check the bucket
before writing the page.** I could not check it from the CSV.

## 2.3 The full table

`live_gigs` and `new_this_week` are from your CSV, 2026-08-25. Target query,
band, and difficulty are my recommendation and estimate.

| Field | Live | Target query | Secondary | Band | Diff | Evidence |
|---|---|---|---|---|---|---|
| Development / tech | 9238 | freelance developer jobs | remote developer jobs, freelance web developer jobs | B | very high | AC-full clean on "developer", contaminated on "development". SERP-agg: Toptal, Upwork, Arc, remote.co, Working Nomads all rank. |
| Other / general | 6137 | none, correctly excluded | | | | Feeds `/new-remote-jobs/` instead. See 2.5. |
| Sales / outreach | 5173 | remote sales jobs | freelance sales jobs | B | very high | AC-full both. "sales gig" AC-polluted. SERP-agg. |
| Design / creative | 3639 | freelance design jobs | remote design jobs, freelance graphic design jobs | C to B | high | AC-full. SERP: Contra ranks #1 with the same archetype, which is the proof this page type can rank. |
| Marketing / SEO | 2774 | freelance marketing jobs | remote marketing jobs | C | high | AC-full both, "marketing gigs" clean as a third. |
| Data / analytics | 2409 | freelance data analyst jobs | remote data jobs | D to C | medium-high | AC drifts across three meanings. Verify the bucket first. |
| Finance / accounting | 2038 | remote finance jobs | freelance finance jobs, freelance bookkeeping jobs | C | high | AC-full, US state modifiers on "remote finance jobs". |
| Admin / VA | 1979 | freelance virtual assistant jobs | remote virtual assistant jobs | C to B | high | AC-full with full beginner tail. Many small sites rank, so reachable. |
| Healthcare / medical | 1832 | remote healthcare jobs | freelance healthcare writer jobs | B / E | very high | AC-full on remote, AC-partial on freelance (drifts to "self employed healthcare jobs"). Freelance healthcare is barely a concept. Lead with remote. |
| Video / animation | 1741 | freelance video editing jobs | remote video editor jobs | C | medium | AC confirms "editor" is the noun. |
| Consulting / strategy | 1714 | freelance consulting jobs | consulting gigs | D | medium | AC-full, "consulting gigs" is one of the eight clean gig terms. Good winnable page. |
| Product / PM | 1688 | freelance product manager jobs | remote product manager jobs | D | medium | AC confirms the noun. |
| Management / operations | 1651 | freelance project manager jobs | remote project management jobs | D to E | medium | Weakest concept of the 23. Consider merging. |
| Customer support | 1518 | remote customer service jobs | freelance customer support jobs | B | very high | AC-full, huge entry-level tail. Indeed owns it. |
| HR / recruiting | 1425 | remote hr jobs | freelance hr jobs, freelance recruiter jobs | C / D | medium | "remote hr j" AC-full US-heavy. "freelance hr j" AC-partial, India and Singapore heavy. **Never target "hr gigs"**, it returns H.R. Giger. |
| Architecture / 3D | 1085 | freelance architecture jobs | architecture gigs | E to D | **low** | AC-full and clean, few strong sites on the SERP. **Highest probability of a first ranking.** |
| Writing / content | 1024 | freelance writing jobs | remote writing jobs, freelance writing jobs for beginners | A to B | very high | The deepest AC set of any field: online, remote, for beginners, work from home, no experience, near me, job boards, for teens. Also the most crowded SERP in the category. See 2.4. |
| Legal | 812 | remote legal jobs | freelance paralegal jobs | D | medium | "remote legal j" AC-full with US state modifiers. "freelance legal j" AC-full but India-heavy. |
| Teaching / tutoring | 593 | online tutoring jobs | remote teaching jobs | D to C | medium-high | "freelance teaching jobs" AC-full but India and Dubai heavy. US intent lives on "online tutoring jobs". |
| QA / testing | 513 | remote qa jobs | freelance qa jobs | E to D | **low** | AC-full and clean, and the recency modifier appears natively: "remote qa jobs in the last 3 days", "in the last week". Small field, easy win. |
| Engineering | 492 | contract engineering jobs | freelance engineering jobs | E | medium | AC drifts mechanical vs software. "contract engineering jobs" appeared as a suggestion under the freelance seed. **Verify what is in this bucket**; if it is software, it belongs in Development. |
| IT / support | 402 | remote it jobs | freelance it jobs | D to C | medium | Both AC-full and clean, US-heavy. Good ratio of demand to competition. |
| Translation / language | 395 | freelance translation jobs | translation gigs, plus language pairs | D | **low** | AC-full, "translation gigs" clean, and the language-pair tail is enormous and almost uncontested: spanish to english, french to english, chinese to english, arabic english, hindi to english all appeared. **Best long tail per unit of inventory in the whole set.** |
| Photography | 185 | do not publish | | | | See 2.6. |
| Audio / music | 100 | do not publish | | | | See 2.6. |

## 2.4 The writing paradox, and what to do about it

Writing has the highest search demand of any field on this list and the third
lowest inventory of the ones you publish. 1,024 gigs against a term family that
includes "freelance writing jobs online", "for beginners", "work from home",
"no experience", "remote no experience", "for teens" and "job boards", every
one of them an AC-full suggestion.

You will not take "freelance writing jobs". Indeed, Upwork, ProBlogger,
FlexJobs and a decade of listicles hold it.

What you can take is the qualifier tail, and it should be taken with **guides**,
not with the field page. "freelance writing jobs for beginners" and "remote
writing jobs no experience" are informational-leaning queries where a genuinely
useful page beats a listing page. That is Part 3, item 4.

## 2.5 The "Other / general" bucket

6,137 live gigs, second largest field, correctly excluded from field pages
because "other" is not a search term. That inventory is not wasted though. It
is exactly what should populate `/new-remote-jobs/`, where the organising
principle is recency rather than field. Right now those 6,137 gigs are the only
segment of the board with no crawlable surface at all.

## 2.6 Thin fields: should Photography and Audio have pages?

**Audio / music, 100 gigs. No, and it is not close.** VERIFIED: `audio gigs`
autocompletes to "audio gigs near me", "audio gigs glasgow". In search,
"audio gigs" means live music. `freelance audio j` is AC-partial and drifts to
"freelance audio visual jobs". 100 gigs cannot fill a 16-title sample credibly.
The generator's `MIN_GIGS = 150` already excludes it and it is not currently
published. Correct call, leave it.

**Photography, 185 gigs. No, and there is a live bug here.** Two reasons.

First, intent. VERIFIED autocomplete: `freelance photography j` returns near
me, nyc, los angeles, chicago, charlotte nc, london. `photography gig` returns
near me, nyc, chicago, los angeles. Photography search is overwhelmingly
**local**. Nabbly is a remote-first board. Even if you ranked, the visitor
wants somebody to shoot a wedding in Chicago and you have a remote gig board.
That is a bounce, and enough of them tell Google the page does not answer the
query.

Second, and more urgent: **the page is live right now and it should not be.**
VERIFIED today:

- `https://nabbly.co/freelance-photography-jobs/` returns **HTTP 200**
- it carries `<meta name="robots" content="index, follow">` and a self-canonical
- it is **not in sitemap.xml** (I read all 28 URLs in the live sitemap)
- `https://nabbly.co/freelance-audio-jobs/` correctly 404s, and a nonsense
  control path also 404s, so this is not an SPA fallback. The directory is
  really there.

What happened is that photography crossed `MIN_GIGS` on some earlier build, got
written to disk, then fell back under on a later build. The generator writes
pages but **never deletes them**. So the file persists, indexable, orphaned,
frozen at whatever the sample was that week, with no lastmod signal and no
internal links pointing at it. That is the textbook definition of a thin
orphaned page and it is exactly the profile GOOGLE-JOBS.md section 4 was
written to avoid.

Fix, in the generator:

```python
# Anything under site/freelance-*-jobs/ that this run did not write is a
# field that dropped below MIN_GIGS. It was live and indexable until now.
# Leaving it on disk leaves a stale, orphaned page nothing links to.
live = {f"freelance-{w['slug']}-jobs" for w in written}
for d in OUT.glob("freelance-*-jobs"):
    if d.name not in live:
        shutil.rmtree(d)
        print(f"  pruned {d.name} (dropped below MIN_GIGS)")
```

And add hysteresis so a field sitting near the line does not flap in and out of
the index every week:

```python
MIN_GIGS = 400          # publish a new field page at or above this
KEEP_GIGS = 250         # keep an existing one until it falls below this
```

Photography at 185 fails both. It goes.

Also raise `MIN_GIGS` from 150 in general. At 150 gigs a field page has 16 real
titles and roughly 350 words, which is thinner than the Remote Source page I
found ranking, and that one has nothing on it. 400 is a defensible floor. On
today's CSV that keeps all 22 currently published fields except Engineering
(492 survives), IT (402 survives) and Translation (395 falls just under).
Translation is one of your best opportunities, so use 380 or keep 350 and treat
this as a judgement call rather than a rule. The important part is the pruning,
not the exact number.

---

# Part 3. Guides pipeline: the next ten

Ranked by expected impact per hour of writing. Each one has a target query,
a volume estimate with its confidence, the intent, what currently ranks and why
it is beatable, and the angle only Nabbly can write.

The recurring unfair advantage across all of these: **Nabbly sees roughly 4,200
new gigs a day across 24 fields and can describe what the market is actually
doing.** Every competitor in these SERPs is writing from a survey, an opinion,
or a rate card from 2019.

**The FEEL.md constraint on all of them.** Any figure taken from the board must
be (a) a share or a band, never a live count, and (b) stamped with the window it
was measured over. `Across the design gigs Nabbly logged in the 30 days to 25
August 2026, about a third were posted at the larger end.` That sentence stays
true forever because it names its window. Rebuild these data blocks monthly and
restamp them.

---

### 1. What freelance design work actually pays right now

- **Query:** "how much to charge for freelance graphic design", plus "freelance
  graphic design rates"
- **URL:** `/guides/what-freelance-design-work-pays/`
- **Band:** C, ESTIMATED. Method: `how much to charge for freelance ` is AC-full
  and returns ten distinct professions (social media management, graphic design,
  web development, writing, bookkeeping, editing, video editing, photography,
  illustration). `freelance graphic design rates` is AC-full with ten country
  variants. That much tail on both stems means a substantial head. Confidence:
  medium-high on the band, high on this being the strongest rate query.
- **Intent:** informational, high commercial adjacency. Someone about to quote.
- **What ranks:** VERIFIED, page one is manypixels.co, waveapps.com,
  creativepool, mocktheagency, morganoverholt, thervo, guru.com. Every one of
  them is an opinion piece or an agency price list. Several cite figures from
  2024.
- **Why beatable:** none of them have data. They have ranges somebody wrote
  down. Published 2026 aggregate figures exist and are wildly inconsistent
  (VERIFIED: one source says the middle 50% of US freelancers charge $75 to
  $150/hr, another says the average is $47.71/hr, both dated 2026). That
  inconsistency is the opening.
- **Nabbly's angle:** the distribution of posted budgets on real design briefs,
  by band, over a stated window. Not what designers say they charge, what
  clients are actually posting. That is a different and better number and
  nobody else on that SERP has it.
- **Effort:** 4 hours, plus a generator query. Rebuild monthly.
- **This is the template for a whole series.** Repeat for writing, video
  editing, web development and virtual assistant work once the first one works.
  Do not build all five up front.

---

### 2. How to spot a fake or scam job posting

- **Query:** "how to spot a fake job posting"
- **URL:** `/guides/how-to-spot-a-fake-job-posting/`
- **Band:** C to B, ESTIMATED. Method: AC-full with a deep and unusually varied
  modifier set: on indeed, on linkedin, on indeed reddit, on linkedin reddit,
  reddit, "how to identify fake job postings on linkedin", "how to spot a fake
  job advertisement". Ten of ten on-topic. The presence of three separate
  reddit-suffixed variants means people are actively dissatisfied with the
  existing answers. Confidence: medium-high.
- **Intent:** informational, anxious, high trust. This is a safety query.
- **What ranks:** Indeed and LinkedIn help-centre articles, plus generic career
  blogs. Nobody who actually looks at thousands of postings a day.
- **Why beatable:** Indeed and LinkedIn have an obvious conflict of interest
  writing about fake postings on Indeed and LinkedIn. Nabbly does not.
- **Nabbly's angle:** you classify around 4,200 postings a day and your FAQ
  already carries the honest line, "These are public postings gathered as they
  were written; we classify and rank them, we don't vet the people behind them.
  Treat anything asking for money up front or unpaid test work the way you
  would anywhere else." That paragraph is already better than most of page one.
  Expand it into the patterns you actually see, without naming any source.
- **Why it is number two despite lower volume than some below it:** safety
  content earns links and gets cited in AI answers at a much higher rate than
  commercial content, and the honesty is already written. Highest link value per
  hour of anything on this list.
- **Effort:** 3 hours.

---

### 3. Does applying early to a job actually help

- **Query:** "does applying early to a job help", plus "best time to apply for a
  job after posting"
- **URL:** `/guides/does-applying-early-to-a-job-help/`
- **Band:** D to C, ESTIMATED. Method: `does applying early ` is AC-full and the
  first two suggestions are "to a job help" and "to a job help reddit", ahead of
  all the college-admissions variants. `best time to apply to a job` is AC-full
  and includes "best time to apply for a job after posting". Confidence: medium.
- **Intent:** informational, and it is Nabbly's entire thesis posed as a
  question by the customer.
- **What ranks:** career blogs and Reddit threads, all argument, no measurement.
- **Why beatable:** the "reddit" suffix on the top suggestion is the tell.
  People do not trust the blog answers and are going to forums instead. A
  measured answer wins that.
- **Nabbly's angle:** this is the single most defensible guide on the list.
  You can describe how quickly gigs accumulate after posting, how the volume
  arriving in a field spreads across the day, and how much of a field's weekly
  intake lands in its first hours. All as shares. Nobody else can write this
  paragraph, and it is the argument for the product, so the guide sells without
  selling.
- **Careful:** FEEL.md and the generator's `speed_line()` docstring both refuse
  to claim a fast reply wins the work. Keep that discipline. "Early is the part
  you can control" is the claim, not "early wins".
- **Effort:** 4 hours.

---

### 4. How to get freelance work with no experience

- **Query:** "how to get freelance work with no experience"
- **URL:** `/guides/freelance-work-with-no-experience/`
- **Band:** C, ESTIMATED. Method: AC-full, ten of ten, with sibling stems
  ("how to find", "how to do", "how to get a freelance job with") all returning
  their own full sets. Plus the adjacent `freelance jobs for beginners` is
  AC-full with "online", "with no experience", "work from home". The beginner
  cluster is one of the largest in the whole category. Confidence: medium-high.
- **Intent:** informational, beginner, and it converts to the free tier
  perfectly. This person will not pay $12/mo yet, but they are exactly who
  should have the daily digest.
- **What ranks:** general freelance blogs, Upwork's own resources hub.
- **Why beatable:** most of it is advice to build a portfolio and network, which
  the reader has already read four times.
- **Nabbly's angle:** which fields actually post entry-level work, expressed as
  shares. VERIFIED that this is a real sub-query: "entry level" appears as an
  autocomplete modifier on remote design, data, finance, consulting,
  architecture, qa, hr, legal, engineering, marketing and writing jobs. You can
  say which of your fields carry the most junior briefs. Nobody else can.
- **Effort:** 3 hours.

---

### 5. Freelance rates by field: what clients are posting

- **Query:** "what is a good hourly rate for freelance", "how much do
  freelancers charge per hour", "freelance rates"
- **URL:** `/guides/freelance-rates/` (hub, linking to the per-field children
  from item 1)
- **Band:** C, ESTIMATED. Method: `what is a good hourly rate for freelance` is
  AC-full and pulls in "how much do freelancers charge per hour" and "how much
  should i charge as a freelancer" as siblings. `freelance rates ` is AC-full
  with ten country variants. Confidence: medium.
- **Intent:** informational, pre-quote.
- **What ranks:** VERIFIED, a crowded field of 2026 rate reports: jobbers.io,
  clockify, whatshouldicharge.io, solohourly, freelancedesk. Several publish
  genuinely detailed benchmark data.
- **Why beatable, and honestly only partly:** the competition here is real, this
  is the hardest of the ten. It earns its place because it is the hub that makes
  item 1 and its siblings a topic cluster rather than five orphan posts, and
  because every one of those competitors measures what freelancers *earn* while
  Nabbly measures what clients *post*. Different number, defensible position.
- **Effort:** 3 hours for the hub, assuming item 1 exists first. **Do not build
  this before item 1.**

---

### 6. How many gigs should you reply to in a day

- **Query:** "how many jobs should i apply to a day"
- **URL:** `/guides/how-many-gigs-to-reply-to/`
- **Band:** D to C, ESTIMATED. Method: AC-full, ten of ten, with "a day", "at
  once", "per week", "a week", "at a time", "daily", "a day reddit", "per day
  reddit". Two reddit variants again. Confidence: medium.
- **Intent:** informational, job-seeker rather than freelancer specifically.
- **What ranks:** career advice blogs with round numbers and no basis.
- **Why beatable:** everybody answers this with an invented number. Two reddit
  suffixes say the answer is not landing.
- **Nabbly's angle:** how much work actually appears in a field per day,
  expressed as shares or "hundreds" bands rather than counts, so the reader can
  reason about their own ratio instead of being handed a number. Ties directly
  to skill-ranked sorting, which is the Pro feature this reader needs.
- **Effort:** 3 hours.

---

### 7. Freelance proposal template, and what to put in it

- **Query:** "freelance proposal template", "how to write a freelance proposal"
- **URL:** `/guides/freelance-proposal-template/`
- **Band:** D, ESTIMATED. Method: `freelance proposal template ` is AC-full but
  seven of ten suggestions drift to "freelance contract template", which is a
  legal document, not a pitch. `how to write a freelance p` returns "proposal"
  first, then "pitch". Confidence: medium, with a real caveat that half this
  volume wants a contract and will bounce.
- **Intent:** transactional, wants a downloadable artifact.
- **What ranks:** template farms and invoice SaaS.
- **Why beatable:** partially. The template farms are hard to beat on a
  template query.
- **Nabbly's angle:** the drafter in `pitch.py` already encodes rules for this,
  and the existing guide at `/guides/how-to-reply-to-a-freelance-job-post/`
  covers adjacent ground.
- **Cannibalisation risk, and it is real.** This guide and the existing one
  overlap heavily. If you write it, make the split explicit: the existing guide
  is the two-line reply to a posted brief, this one is the longer proposal you
  send when the client asks for one. If you cannot state that split in one
  sentence, do not write it.
- **Effort:** 3 hours. Ranked seventh mainly because of that risk.

---

### 8. Freelance versus contract versus employed

- **Query:** "freelance vs contract work"
- **URL:** `/guides/freelance-vs-contract-work/`
- **Band:** D, ESTIMATED. Method: `freelance vs contract ` is AC-full, ten of
  ten, all on-topic: work, vs self-employed, on linkedin, vs full time,
  employment, part time, meaning, worker, employee. Unusually clean set.
  Confidence: medium-high on the band, low on the value.
- **Intent:** purely definitional. Low commercial value per visit.
- **What ranks:** HR blogs and payroll SaaS.
- **Why beatable:** it is a definition. Definitions are easy to rank and easy to
  lose. The real reason to write it is that AI answers love clean definitional
  content and this is cheap entity-building.
- **Nabbly's angle:** thin. You can say what proportion of what you see is
  project work versus ongoing remote roles, which is genuinely interesting and
  maps onto the homepage's existing "Two kinds of work. One board." section.
- **Effort:** 2 hours. Cheapest on the list, which is why it survives its low
  intent.

---

### 9. Freelance writing jobs for beginners

- **Query:** "freelance writing jobs for beginners", "remote writing jobs no
  experience"
- **URL:** `/guides/freelance-writing-jobs-for-beginners/`
- **Band:** C, ESTIMATED. Method: both appear as AC-full modifiers under the
  deepest field stem in the whole dataset. Confidence: medium.
- **Intent:** mixed informational and navigational. They want a list.
- **What ranks:** VERIFIED, listicles: theinterviewguys, thewordling, amysuto,
  makingsenseofcents, writefulcopy. Heavy, established, link-rich.
- **Why beatable:** it is not, on the head. It is beatable on the specific
  sub-question of what beginner writing work actually looks like when it is
  posted, which none of them answer with evidence.
- **Nabbly's angle:** the writing field has your worst demand-to-inventory
  ratio (1,024 gigs against the biggest search demand in the set). This guide is
  the way to compete in writing without pretending the field page can carry it.
- **Caution:** VERIFIED 2026 reporting claims freelance writing postings fell
  33% since ChatGPT's release for generic content. If your own data agrees, say
  so plainly. If it disagrees, say that instead. Do not repeat somebody else's
  statistic as though you measured it. FEEL.md section 7, no invented
  statistics, applies to borrowed ones too.
- **Effort:** 4 hours.

---

### 10. How to find freelance clients without a marketplace

- **Query:** "how to find freelance clients"
- **URL:** `/guides/how-to-find-freelance-clients/`
- **Band:** C to B, ESTIMATED. Method: AC-full with ten variants, the top ones
  being "on linkedin", plain, "reddit", "on facebook", and a whole parallel
  "how to get freelance clients" stem. Large. Confidence: medium-high on volume.
- **Intent:** informational, broad, and very well served already.
- **What ranks:** VERIFIED, a wall of 2026-dated freelance blogs plus Upwork's
  resources hub. Nine of ten results are "pick a niche, build LinkedIn, cold
  email".
- **Why it is last despite the volume:** the SERP is saturated with adequate
  answers, the query is early-funnel, and Nabbly's honest answer is "watch where
  work gets posted and be early", which is one third of an article. Write it
  when the other nine exist and you need the hub to link from.
- **Effort:** 3 hours.

---

### What I deliberately left off

**"upwork proposal template" / "upwork proposal example".** VERIFIED AC-full and
clearly high volume, including "upwork proposal generator" and "upwork proposal
2026". Ruled out because it is somebody else's brand, the content would be
parasitic, and Nabbly would be building an asset that sends people to Upwork.

**"best freelance job boards" and every listicle variant.** Cannot be written
without naming sources. See 1.5.

**"how to spot fake job postings on Indeed / LinkedIn".** The brand-suffixed
variants of item 2. Same reasoning as Upwork. Write the unbranded head, let the
branded tail pick up what it picks up.

---

# Part 4. Technical pass

Everything here is checked against the HTML in `current-site/` and against the
live site as it stood on 2026-08-26.

## 4.1 The homepage links to nothing you built

**Severity: highest technical item in this document.**

VERIFIED. I extracted every `href` from `index.html`. The complete internal link
set is: `/` (2), `/about.html` (2), `/faq.html` (2), `/privacy.html`,
`/terms.html`, three same-page anchors, and six links to board.nabbly.co.

**Zero links to any of the 23 field pages. Zero links to the guide.**

The field pages are reachable from: sitemap.xml, the sibling pill list on other
field pages, the pill list at the bottom of about.html, and the pill list at the
bottom of the guide. That is a closed loop hanging off two low-authority prose
pages, with the single most linked page on the domain pointing at none of it.

Whatever authority nabbly.co accrues from outreach lands on the homepage and
stops there.

**Fix.** Add a "Browse by field" section to `index.html`, generated by
`make_field_pages.py` in the same pass that fills the sibling pills, so it never
drifts out of sync with what was actually published:

```python
# index.html carries a marker comment; the generator replaces between the
# markers. Same mechanism as the sibling pills, so the homepage can never
# link to a field page this run did not write.
FIELDS_MARK = ("<!-- FIELDS:START -->", "<!-- FIELDS:END -->")
```

Proposed heading, in Nabbly's own style with the last word amber per FEEL.md
section 3:

```html
<h2>Browse by <span class="amber">field</span></h2>
```

Proposed line under it:

```
Every field Nabbly watches has its own page, rebuilt from the live board.
```

And a second block for guides:

```html
<h2>Reading before you <span class="amber">reply</span></h2>
```

## 4.2 /guides/ returns 404

VERIFIED: `https://nabbly.co/guides/` returns **HTTP 404** today. The single
guide lives at `/guides/how-to-reply-to-a-freelance-job-post/` with no parent.

With one guide that is merely untidy. With eleven it is a structural problem:
no hub page means no topical cluster, no place for AI crawlers to find the set,
and no internal link path between guides.

**Fix.** Generate `/guides/index.html` in `write_prose_pages()`. Title:

```
Guides for finding freelance work · Nabbly
```

Description:

```
Short, practical guides on finding freelance and remote work early, replying
well, and pricing against what clients are actually posting.
```

H1:

```
Guides
```

Add it to the sitemap, and put it in the footer of every page.

## 4.3 Footers are inconsistent

VERIFIED. Field pages carry `Nabbly · freelance and remote work from every
board, in one place · Privacy · Terms`. Prose pages (about, faq, guide) carry
the same plus `About · FAQ`.

So the 23 field pages, your highest-volume crawl surface, do not link to About
or FAQ at all. Unify on one footer across every generated page:

```
Nabbly · freelance and remote work from every board, in one place
About · FAQ · Guides
Privacy · Terms
```

Keep the existing `.legal` treatment that demotes Privacy and Terms to a
quieter line. That decision is already right.

## 4.4 The board's robots.txt contradicts the stated plan

VERIFIED, `https://board.nabbly.co/robots.txt` today:

```
User-agent: *
Allow: /
Disallow: /gigs?*
Disallow: /out/
...
```

The brief says board.nabbly.co stays noindex "except /, /gigs and field views".
But the field views **are** `/gigs?field=...`, and `Disallow: /gigs?*` blocks
exactly those. The intention and the implementation disagree.

Compounding it: every field page's primary amber CTA points at
`board.nabbly.co/gigs?field=<field>&ref=site-<slug>`, which is a robots-blocked
URL. That is fine for humans and it is fine for the `ref=` attribution the
generator comment explains. But as a crawl path it is a wall.

Also VERIFIED: `board.nabbly.co/` and `board.nabbly.co/gigs` both return
`<title>Nabbly</title>`. The root has a meta description, `/gigs` has none, and
neither carries a canonical or a meta robots tag. Two indexable pages titled
"Nabbly" on a subdomain, competing with nabbly.co on your own brand query.

**Decide one of two things and implement it properly:**

- **Option A, cleanest, and what I recommend.** board.nabbly.co is not an SEO
  surface. Put `<meta name="robots" content="noindex, follow">` on every board
  route including `/` and `/gigs`, and leave robots.txt permissive so crawlers
  can actually read the noindex. (A `Disallow` prevents the crawler from ever
  seeing a `noindex`, which is why the current setup cannot achieve what it is
  aiming at.) nabbly.co carries everything.
- **Option B.** If you genuinely want the field views indexed, remove
  `Disallow: /gigs?*`, give `/gigs` and each field view a real unique title and
  canonical, and accept that you now have two pages per field competing across
  two hosts. I do not recommend this. It splits the signal for no gain.

Either way, `/gigs` should not be titled "Nabbly".

## 4.5 The sitemap

VERIFIED, live sitemap on 2026-08-26: 28 URLs, `lastmod` 2026-08-24 on every
single one, `changefreq` daily on the field pages, priority 0.8 across all of
them regardless of inventory.

Four things.

**Every URL gets today's date on every run.** `write_sitemap()` sets
`today = date.today().isoformat()` and stamps it on all 28, including
privacy.html and terms.html, which have not changed in a month. Google's
sitemaps guidance is explicit that lastmod must be the last **significant**
modification date, and a sitemap that claims everything changed today teaches
Google to ignore the field pushed. Of the three sitemap elements, lastmod is
the only one that carries weight, so it is the only one worth getting right.

```python
def _lastmod(path: Path, new_html: str, prev: dict) -> str:
    """Today only if the bytes actually changed, otherwise the stored date."""
    import hashlib
    h = hashlib.sha256(new_html.encode("utf-8")).hexdigest()
    if prev.get(str(path)) == h:
        return prev["dates"][str(path)]
    return date.today().isoformat()
```

Store the hashes in a small committed JSON file next to the sitemap. Note that
the "Recently on the board" sample changes on nearly every field-page rebuild
anyway, so those will legitimately keep today's date. Privacy and Terms will
stop lying, which is the point.

**changefreq and priority do nothing.** Google has confirmed it does not use
either. Keep them if you like the documentation value, but do not spend a
minute tuning them, and do not let a "priority tiering" idea onto anyone's
todo list.

**Do not add a sitemap ping.** Google deprecated the sitemaps ping endpoint in
June 2023 and it now returns 404. Submitting through Search Console and the
`Sitemap:` line in robots.txt (which you already have) is the whole mechanism.

**The sitemap and the filesystem disagree.** See 2.6. `/freelance-photography-jobs/`
is live and absent from the sitemap. Once pruning is in place this cannot
recur.

## 4.6 Thin content risk across 23 near-identical pages

The generator's docstring already understands this problem better than most
SEO documents do, and the mitigations in place (16 real titles per field, the
field's own `JOB_TYPES` vocabulary, a `speed_line()` built from that field's own
budget and urgency mix, and the deliberate refusal to repeat a 37-word
paragraph) are genuinely good. The 40% to 45% body-similarity measurement noted
in the code comment is the right instinct.

Three ways to widen the gap, in order of value per line of code.

**(a) Raise `SAMPLE` from 16 to 24 on the large fields.** The sample is the only
section where no two pages share a sentence, so it is the highest-leverage
lever you have and it costs one number. Scale it: 24 titles above 2,000 gigs,
16 between 400 and 2,000. Development at 9,238 gigs can support 24 easily.

**(b) Add a visible "What these gigs pay" block.** Two or three sentences per
field built from the `size_tier` mix, which the generator already reads. Unique
per field by construction, roughly 60 words, and it directly feeds the rates
guides in Part 3. FEEL.md-safe wording:

```
Across the {noun} gigs on the board when this page was built, about a third
were posted at the larger end and the rest were smaller, faster pieces.
Sample taken 25 August 2026.
```

**(c) Add a three-question FAQ per field, visibly rendered.** Roughly 120 unique
words per page, and it is the single most AI-extractable format there is (see
Part 5). Questions:

```
How often do new {noun} gigs appear?
Do I need an account to see {noun} work?
Are these {noun} gigs remote?
```

`FAQPage` schema is legitimate here because the questions are visible, which is
the exact condition the generator's own comment sets out for faq.html. Be clear
about the payoff though: Google restricted FAQ rich results to health and
government sites in 2023, so this earns you nothing in the blue links. It earns
you extraction into AI answers. Write it for that reason or not at all.

**(d) Add the build date visibly.** `Sample taken 25 August 2026.` under
"Recently on the board". Satisfies FEEL.md's numbers-must-be-true rule, gives a
real freshness signal, and lets you add `dateModified` to the schema honestly.

## 4.7 Schema markup

VERIFIED current state:

| Page | Schema |
|---|---|
| index.html | WebSite + SearchAction, Organization, SoftwareApplication |
| field pages | CollectionPage |
| faq.html | FAQPage (correctly, questions are visible) |
| about.html | none |
| the guide | **none** |

JobPosting is off the table and stays off the table. Everything below is a
different type and none of it requires naming a source, a hiring organisation
or an expiry date.

**Field pages, add:**

- `BreadcrumbList`: Home › Freelance {kw} jobs. Two levels is fine and Google
  documents multiple structured data items coexisting on one page.
- `ItemList` of the visible sample titles, **name only**. No `url`, no `@type:
  JobPosting`, no employer, no date. It describes the list that is visibly on
  the page, which is exactly what ItemList is for on a category page. This is
  not a back door to Google for Jobs and should not be described as one.
- `dateModified` on the CollectionPage, matching the visible build date.

**The guide, add:** `Article` with `headline`, `datePublished`, `dateModified`,
`author` and `publisher` both pointing at the Organization node, plus
`BreadcrumbList`. Article is the correct type for a guide and it is currently
carrying no structured data at all.

**index.html, extend the Organization node:**

```json
{
  "@type": "Organization",
  "@id": "https://nabbly.co/#org",
  "name": "Nabbly",
  "url": "https://nabbly.co/",
  "logo": "https://nabbly.co/favicon.png",
  "foundingDate": "2026-07-19",
  "description": "Nabbly gathers new freelance briefs and remote roles from job boards and hiring communities onto one board, minutes after they post.",
  "sameAs": ["https://www.instagram.com/nabbly.co"]
}
```

`foundingDate` is a fact from the brief and it is exactly the kind of
unambiguous entity attribute that helps a model decide two mentions of "Nabbly"
are the same company. Add every other profile URL to `sameAs` as they come into
existence.

**Do not add** `aggregateRating` or `review` to the SoftwareApplication node
without real reviews. Fabricated ratings are a manual-action risk and a FEEL.md
violation twice over.

## 4.8 Smaller items

- **The homepage title uses an em dash.** FEEL.md section 7. Fixed by the
  rewrite in 1.4.
- **"25+ fields" in the homepage description.** Not supported by the CSV. Say
  "across two dozen fields" or drop the count. Numbers must be true at all
  times.
- **`og:image` is identical on all 26 pages.** Low priority, but per-field
  images would help both social sharing and AI Overview citation, which VERIFIED
  research puts at roughly 23% multimodal. Generate them from the existing radar
  motif per FEEL.md section 6 only when there is nothing better to do.
- **The deployed field pages are missing the Archivo `@font-face`** that the
  generator now emits. `about.html` has it, `freelance-design-jobs/index.html`
  does not. The generator is ahead of what is deployed. Harmless, but it means
  something did not rebuild when you thought it did.
- **`MIN_GIGS` flapping.** See 2.6, hysteresis.

## 4.9 What the rebuild should start doing differently

Concrete changes to `refresh-seo-pages.yml` and `make_field_pages.py`:

1. **Prune.** Delete `site/freelance-*-jobs/` directories this run did not
   write. See 2.6.
2. **Rebuild `/new-remote-jobs/` daily.** Everything else can stay weekly. Two
   schedules in one workflow file.
3. **Honest lastmod.** Hash-compare, only bump what changed. See 4.5.
4. **Print a build report.** Per-field gig counts and which fields crossed
   `MIN_GIGS` in either direction. The photography orphan existed for at least
   two builds without anybody knowing.
5. **Gate on similarity.** The code comment already measures body similarity
   between pages. Make it a hard failure above a threshold (start at 55%) so a
   future well-meant boilerplate paragraph cannot quietly push all 23 pages back
   toward doorway territory.
6. **Regenerate the homepage field block and the guides block** in the same
   pass, between marker comments. See 4.1.
7. **Do not add a sitemap ping step.** It 404s. See 4.5.

---

# Part 5. AI search

## 5.1 What is verified about how these systems choose

Everything in this subsection is from published 2026 research I read today.
Treat the exact percentages as the researchers' numbers, not mine, and note
that the studies disagree with each other by wide margins.

- Google AI Overviews appear on roughly 48% of searches as of February 2026, up
  from 31% a year earlier, and organic CTR drops by up to 61% when one triggers.
- The engines cite very different things. One 30-million-source analysis found
  only about 11% of domains cited by both ChatGPT and Perplexity.
- Perplexity leans hard on Reddit. Reported figures range from 24% of citations
  in January 2026 to 46.5% in March 2026 research. Wide spread, same direction.
- ChatGPT cites Reddit in something over 5% of responses and skews heavily
  encyclopedic. Gemini cites Reddit at around 0.1%.
- AI Overviews skew multimodal, with YouTube around 23% of citations and
  Wikipedia around 18%.
- Review directories matter. One study claims domains with active G2 or
  Capterra profiles show roughly 3x citation probability. Treat the multiple as
  directional.
- **llms.txt is not worth building.** Google's May 2026 AI optimisation guidance
  states explicitly that llms.txt is not needed for AI Overviews, AI Mode or any
  generative Search feature, and no major model provider has committed to
  reading it in production. One study found that removing llms.txt from a
  citation-prediction model actually improved accuracy. It has real use for
  agent-facing developer documentation. Nabbly is not that.

## 5.2 What Nabbly should do

**1. Confirm nothing is blocking the AI crawlers, then stop worrying about it.**
VERIFIED: `nabbly.co/robots.txt` is `User-agent: * / Allow: /`, which permits
GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot and Google-Extended. That is
already correct and it is the single highest-consequence item on this list,
because blocking OAI-SearchBot guarantees exclusion from ChatGPT's real-time
answers. Check that Cloudflare in front of the site is not bot-blocking them
independently of robots.txt, since that is where this usually breaks. Effort:
ten minutes. Do it first.

**2. Do not build llms.txt.** See above. Saves a day.

**3. Restructure the FAQ and every guide into question-then-answer.** The
extraction pattern these systems reward is a question-shaped heading followed
by a direct answer in the first one or two sentences, then the detail. Your
faq.html already does this and it is your most AI-friendly page. The guides do
not. `content.GUIDE_APPLY` uses statement headings. Converting them to
questions is a change in `content.py`, not in the generator, and it costs
nothing.

The per-field FAQ from 4.6(c) is the same move applied 23 times.

**4. Write one extractable paragraph that says what Nabbly is.** A model
answering "what is a good tool for finding freelance work fast" needs a block it
can lift. Put this near the top of about.html and keep it identical everywhere
it appears, because consistency across sources is what these systems read as
consensus:

```
Nabbly is a freelance and remote work board. It watches job boards and hiring
communities around the clock and gathers new gigs onto one board minutes after
they post, across two dozen fields. Browsing is free and includes a daily
digest. Pro is $12 a month and adds skill-ranked sorting, instant alerts, a
first reply drafted from the actual posting, and market rates.
```

Five sentences, every fact verifiable, no live counts, no source names, no
dashes. That is the paragraph you want quoted back at you.

**5. Accept that the no-sources rule costs you here, and price it in.** When
someone asks an AI which aggregator to use, the answer compares coverage:
"pulls from RemoteOK, WeWorkRemotely and 19 others". Nabbly will not say that,
for the reasons GOOGLE-JOBS.md sets out at length, and those reasons are
sound. The consequence is that Nabbly has to be differentiated on the three
things it *can* say: minutes not days, a drafted first reply, and a free tier
that browses everything. Those three need to appear together, in that order, in
the paragraph above and in every directory listing.

**6. Get on the directories, because that is where the answers are read from.**
G2, Capterra, AlternativeTo, Product Hunt. This overlaps with outreach and I am
not going to duplicate OUTREACH.md, but note that the AI-citation argument is a
*second, independent* reason to do it beyond the referral traffic, and it may be
the larger one.

**7. Reddit is the highest-leverage surface and the easiest to get wrong.**
Perplexity's citation mix means an honest, non-promotional presence in
r/freelance, r/forhire and r/digitalnomad plausibly matters more than any single
blog post. It also means a promotional one is worse than nothing, because the
thread that gets cited will be the one calling it spam. The realistic version:
answer the questions in Part 3 in threads where they are genuinely asked, using
the data, and mention the product only when it is the actual answer.

**8. Guides carry dates, and the dates get maintained.** Reported figures put
roughly 65% of AI bot hits on recently published or updated content, and
Perplexity in particular weights the last year heavily. The `dateModified` from
4.7 is not decoration. If the rates guides are rebuilt monthly, that date moves
monthly and honestly.

---

# Part 6. How to know whether any of this worked

The brief says analytics only started recording arrivals today, so there is no
baseline. Set one now.

- **Search Console, today.** Verify nabbly.co, submit sitemap.xml, and check
  Coverage for the photography orphan and anything else indexed that should not
  be. This is the only place you will see impressions, and impressions move
  months before clicks do.
- **The number to watch first is impressions on field pages, not clicks.** A
  one-month-old domain ranking at position 40 gets zero clicks and real
  impressions. Impressions rising is the leading indicator; clicks follow at
  position 10 or better.
- **Sixty-day checkpoints.** If `/new-remote-jobs/` and the architecture, QA and
  translation field pages have no impressions by late October, the problem is
  authority, not content, and the answer is outreach rather than more pages.
- **Watch which queries land on field pages.** If "freelance design jobs" brings
  nothing but "freelance architecture jobs" brings impressions, that confirms
  the difficulty read in 2.3 and tells you to write the low-difficulty fields
  properly before touching the hard ones.
- **Do not add more pages until 23 field pages plus 11 guides are all indexed
  and at least half have impressions.** The failure mode for a young domain is
  page count outrunning authority, which is the exact failure GOOGLE-JOBS.md
  section 4 already refused once.

---

# Part 7. One paragraph on Google for Jobs, as requested

Nothing I found changes the decision. The requirements have not moved,
`hiringOrganization` and `validThrough` are still mandatory, duplicate handling
still favours the original poster, and the two structural blockers in
GOOGLE-JOBS.md (naming sources, and not having real expiry data) are still
structural rather than fixable. One clarification worth writing down so it does
not get re-litigated from the other direction: the `ItemList` markup I recommend
in 4.7 is **not** a soft version of JobPosting. It is a name-only list
describing content already visible on the page, it carries no employer, no
date, no URL and no `JobPosting` type, and it does not make a page eligible for
the jobs box. If it ever starts being described internally as a step toward
Google for Jobs, that is the signal that it has been misunderstood and should
be removed.

---

# Sources

Autocomplete data pulled by me on 2026-08-25 from
`https://suggestqueries.google.com/complete/search?client=firefox&q=...`
(79 seeds; raw output in `autocomplete.txt`, `autocomplete2.txt`,
`autocomplete3.txt` in this directory).

Competitor HTML read directly on 2026-08-25:
[remotive.com](https://remotive.com/) ·
[weworkremotely.com](https://weworkremotely.com/) ·
[himalayas.app](https://himalayas.app/) ·
[solidgigs.com](https://solidgigs.com/) ·
[contra.com](https://contra.com/) ·
[wellfound.com/jobs](https://wellfound.com/jobs) ·
[workello.com](https://www.workello.com/) (down) ·
[jobboardsearch.com](https://jobboardsearch.com/)

Page structure analysis:
[contra.com/featured-jobs/freelance-design-jobs](https://contra.com/featured-jobs/freelance-design-jobs) ·
[remotesource.com/remote-jobs/posted-today](https://www.remotesource.com/remote-jobs/posted-today)

Google documentation and guidance:
[Sitemaps ping endpoint is going away](https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping) ·
[General structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) ·
[Breadcrumb (BreadcrumbList) structured data](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb) ·
[Google to deprecate Sitemaps ping endpoint](https://searchengineland.com/google-to-deprecate-sitemaps-ping-endpoint-later-this-year-428661)

Job board SEO practice:
[Job Board SEO: The Complete 2026 Guide, Job Boardly](https://www.jobboardly.com/blog/job-board-seo-vs-general-website-seo) ·
[Using Category Landing Pages for Job Board SEO, Niceboard](https://niceboard.co/learn/marketing/category-pages-for-job-board-seo) ·
[SEO for Job Boards, JBoard](https://jboard.io/blog/seo-for-job-boards) ·
[Programmatic SEO for Job Boards, Cavuno](https://cavuno.com/blog/programmatic-seo-for-job-boards)

AI search citation research:
[AI search engines cite Reddit, YouTube and LinkedIn most, Search Engine Land](https://searchengineland.com/ai-search-engines-cite-reddit-youtube-and-linkedin-most-study-473138) ·
[ChatGPT vs Perplexity vs Google AI: which cites B2B brands, Averi](https://www.averi.ai/how-to/chatgpt-vs.-perplexity-vs.-google-ai-mode-the-b2b-saas-citation-benchmarks-report-(2026)) ·
[Google AI Overviews statistics 2026, SEOProfy](https://seoprofy.com/blog/google-ai-overviews/) ·
[How ChatGPT, Google AI Overviews and Perplexity source information in 2026, Leapd](https://www.leapd.ai/blog/ai-visibility/how-chatgpt-google-ai-overviews-and-perplexity-source-information-in-2026) ·
[Should I create an llms.txt file, 2026 guide](https://www.getpassionfruit.com/blog/should-i-create-an-llms.txt-file-google-s-2026-guidance-explained) ·
[State of llms.txt 2026, Presenc AI](https://presenc.ai/research/state-of-llms-txt-2026)

Rate and market context used in Part 3:
[Freelance graphic design rates, Wave](https://www.waveapps.com/freelancing/freelance-graphic-design-rates) ·
[Graphic design price list 2026, ManyPixels](https://www.manypixels.co/blog/get-a-designer/graphic-design-price) ·
[The Global Freelance Hourly Rate Index 2026, Jobbers](https://www.jobbers.io/the-global-freelance-hourly-rate-index-2026-real-rates-by-skill-country-and-experience-level/) ·
[47 freelance rate statistics for 2026, WhatShouldICharge](https://whatshouldicharge.io/statistics/freelance-rates-2026) ·
[Best freelance writing jobs 2026, The Interview Guys](https://blog.theinterviewguys.com/best-freelance-writing-jobs/)

SERP composition read on 2026-08-25 for: freelance job boards · remote jobs
posted in the last 24 hours · freelance design jobs · how much to charge for
freelance graphic design · freelance developer jobs remote · how to find
freelance clients · freelance rates 2026 · freelance gigs / writing gigs.

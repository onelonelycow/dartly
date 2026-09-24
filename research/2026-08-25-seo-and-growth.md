# SEO and growth research — digest and verification

**Provenance.** A separate Claude session ran three parallel research agents on
2026-08-25 against the `nabbly-seo-handoff.zip` brief. That session had no repo, no
database and no analytics. Raw output (272KB, six files) is not in the repo; it lives in
`~/Downloads/nabbly-research.zip`. This file is the digest plus — the part that matters —
**independent verification against the real codebase and the live site**, done in this
session on 2026-08-25/26.

Nothing here has been applied. This is a reading list for the SEO phase, not a plan of
record.

---

## 1. What I verified myself

Every claim below was checked against the actual repo or fetched live. This is the part
to trust; the research session could not do it.

### Confirmed true

| Claim | Verified how | Result |
|---|---|---|
| `index.html` links to zero field pages and zero guides | `grep -c` on the file | **0 and 0** |
| `board.nabbly.co/robots.txt` has `Disallow: /gigs?*` | fetched live | confirmed |
| Field-page CTAs point at `/gigs?field=…` — i.e. at a blocked URL | read generator + robots | confirmed, **self-inflicted** |
| board `/` and `/gigs` both titled `Nabbly`, no canonical, no meta robots | fetched live | confirmed, 0 and 0 |
| `/freelance-photography-jobs/` exists but is absent from `sitemap.xml` | disk + grep | confirmed |
| `nabbly.co/guides/` returns 404 while the guide itself returns 200 | fetched live | confirmed |
| `MIN_GIGS = 150`, `SAMPLE = 16`, generator never prunes | read source | confirmed |
| Homepage says "25+ fields"; there are 24 | grep + `config.JOB_TYPES` | confirmed |
| Homepage title contains an em dash (breaks FEEL §7) | grep | confirmed |
| Sitemap stamps every URL with the same `lastmod` | all 28 read `2026-08-22` | confirmed |
| 23 field-page directories, 22 in the sitemap | `ls` + grep | confirmed, 1 orphan |

Five of these are outright bugs, not opinions. The CTA one is the sharpest: **every
field page's call to action points at a URL our own robots.txt blocks.**

### Deployed field pages are missing the new typeface

Found while checking their claim. I added Archivo to `make_field_pages.py` earlier today
but never regenerated the pages, so:

- generator emits `@font-face` Archivo — 2 occurrences
- **live `nabbly.co/freelance-design-jobs/` contains 0**

23 field pages are still on the old system font while the rest of the site is on Archivo.
One `make_field_pages.py` run fixes it. My gap, logged here so it isn't lost.

---

## 2. Where the research is wrong or out of date

Take these off the table before the SEO phase starts.

**Retention is 14 days, not 21.** The research repeats "21-day retention" throughout and
builds the urgency of its archiving argument on it. Actual: `db.STALE_DAYS = 14` and
`web/queries.py STALE_DAYS = 14`, changed 2026-08-24. This makes their argument
*stronger*, not weaker — the window is a week shorter than they thought.

**The Reddit legal exposure is close to moot.** Their data document calls the subreddit
collection question "the most serious thing in this document" and recommends spending a
billable lawyer hour on it. Checked:

- Method is `old.reddit.com/r/<sub>/search.rss` — a **public RSS feed, logged out, no
  account, no API key**. That is the *least* exposed configuration by their own analysis,
  not the worst.
- Reddit contributes **0 live gigs**. 269 ever, newest 2026-08-04. It has produced
  nothing in three weeks.

So the recommendation to consider dropping subreddits costs nothing — they are already
contributing nothing. The lawyer hour can wait. What survives from that section is the
**source register** idea, which is cheap and genuinely useful.

**"21 sources" hides extreme concentration.** True as a count, misleading as a fact:

| source | live gigs | share |
|---|---|---|
| himalayas | 31,686 | 62.6% |
| freelancer | 10,100 | 20.0% |
| arbeitnow | 5,953 | 11.8% |
| **top three** | **47,739** | **94.4%** |

The other 18 sources are 5.6% between them. This matters twice: the deck and site say
"21 sources" in a way that implies breadth, and the data-partnership plan assumes a
diversified dataset. A buyer's diligence will find this in ten minutes. Not a reason to
stop, a reason to say it accurately and to widen intake.

---

## 3. The time-sensitive item (not an SEO task)

Their handoff insists one chain comes before everything, and I think they are right:

    freeze field definitions -> start daily aggregate archiving

**Why it cannot wait.** History cannot be back-filled. Retention deletes the raw record
every 14 days. A daily aggregate snapshot — roughly 24 rows a day: per field, live count,
new-in-24h, budget quartiles where stated, remote/onsite split, urgency share — costs
about $5/month and one to two days of work, and it is the precondition for every
recurring report and every partnership conversation later. Everything else on their list
will still be there next week; this week's data will not.

**Freeze first, archive second.** Writing down what "Development / tech" includes today,
and versioning it when it changes, is what makes the archive comparable to itself. Two
hours. Without it the series has a silent discontinuity the first time a category shifts.

Note their "Management / Consulting merge" question is referenced in the handoff but
does not actually appear in the data document — treat it as an open question, not a
finding.

---

## 4. Tier 1: seven changes, ~3 hours, no open questions

All in `make_field_pages.py` and `index.html`. In their recommended order:

1. **Link field pages and the guide from the homepage** — generator-written
   `<!-- FIELDS:START/END -->` block. Highest severity item they found.
2. **Field page titles: "work" becomes "jobs"** — fixes 23 pages via one pattern.
   Autocomplete for all 24 fields completes to "freelance X **jobs**", never "work".
3. **Homepage title, description, H1** — proposed copy is in their doc; drops the em
   dash and puts a searched noun in the title.
4. **Six field pages repointed at the right noun**, including a 301 for the 9,238-gig
   development page → `freelance developer jobs` ("development" reads as *international
   development* in autocomplete).
5. **Generator prunes pages below `MIN_GIGS`** — `shutil.rmtree` anything the run didn't
   write. Fixes the photography orphan.
6. **Create `/guides/`**, add breadcrumb and Article schema.
7. **Decide the board robots.txt question** — they recommend noindex,follow on board
   routes plus a permissive robots.txt, so field-page CTAs stop pointing at blocked URLs.

Their proposed new page — `/new-remote-jobs/`, targeting "remote jobs posted today" — is
the one strategic idea worth weighing. It would give the 6,137-gig "Other / general"
bucket a crawlable surface, and recency is the one thing Nabbly genuinely wins on.
Requires a daily rebuild and a visible build date. **Never print a live count on it**
(FEEL §7).

---

## 5. What is estimated, not measured

Their own ledger is honest about this and it should be respected:

- **Every keyword volume band and difficulty rating is an estimate.** They had no Ahrefs,
  no Semrush, no Keyword Planner; Google Trends returned HTTP 429. What they *did* verify
  is autocomplete behaviour and SERP composition, which is why the "jobs beats work"
  finding and the six wrong-noun findings are solid while the A–F volume bands are not.
- `MIN_GIGS = 400` / `KEEP_GIGS = 250`, `SAMPLE = 24`, the 55% similarity gate — all
  judgment calls, and they say so. Their own note: 400 would kill Translation (395),
  which they separately call a top opportunity.
- All AI-search percentages come from third-party 2026 studies that "disagree with each
  other by wide margins."
- Every revenue figure in the data document beyond "today = $0" is low confidence.

Their legal analysis is the opposite: case holdings are cited precisely (*Feist*,
*Van Buren*, *hiQ* including the $500k judgment, *CV-Online*, *Ryanair*) and the useful
conclusion is durable — **aggregate statistics are legally cooler than republished
listings**, which is what the report products are built on.

---

## 6. Open questions for the founder

1. **Robots.txt on the board** — noindex+follow with permissive robots, or keep the
   current blocks and repoint the field-page CTAs at something crawlable?
2. **The recency page** — build `/new-remote-jobs/` or not? It is the biggest single
   idea in the SEO document.
3. **Which noun for Development** — accepting `freelance developer jobs` means a 301 on
   the largest field page.
4. **Pick a side on rate data** (their §4.7): publishing rate bands raises freelancers'
   floor; selling the same data to buyers of freelance labour lowers it. Same data,
   opposite effect. Worth deciding before the first report, not after.
5. **Sources: name them or not?** Their §8.2 is blunt — if the source list can never be
   disclosed to a buyer's compliance team, the commercial data path is closed. That is a
   legitimate choice, but it should be made deliberately.

---

## 7. Outreach research

See section 8 below — digested separately, including reconciliation against Nabbly's own
`brand/OUTREACH.md`, which the research session did not have when it started.

---

## 8. Outreach and distribution

The research session did **not** have `brand/OUTREACH.md` when it started, so it
re-derived a distribution plan from scratch and then had it reconciled afterwards. The
reconciliation is the most valuable part, because Nabbly's own playbook did a **verified
audit on 2026-08-18** — opening the actual pages — while the new research worked from
search results. Where they disagree on a fact about a specific site, **the existing
playbook usually wins**, and it is worth understanding why before overriding it.

### The constraint they call the month's biggest decision — already satisfied

Show HN's guidelines ask you to remove barriers, "ideally without barriers such as
signups or emails". They flag "confirm the board is browsable without an account" as the
single highest-priority product decision of the month. Checked:

- `board.nabbly.co/` signed out: **HTTP 200, 33 gig cards rendered, zero sign-in wall**
- `board.nabbly.co/gigs` signed out: **33 gig cards**

It is already open. That decision is closed, and Show HN is viable on that criterion.

### Ten contradictions with our own playbook — ours is better sourced

1. **r/forhire** — playbook lists it as a target; research says **no legal post format
   exists** (every post must be tagged `[For Hire]`/`[Hiring]`/`[Task]`, automod removes
   untagged). Research is right; update the playbook.
2. **r/digitalnomad** — playbook lists it; research says it bans self-promotion outright.
   Research is right.
3. **r/freelance** — research downgrades to high-risk, and names **r/SideProject** and
   **r/indiehackers** as the actual A-tier subreddits. Both are absent from our playbook.
   Worth adding.
4. **Hostinger, Useme, Flowlu** — research recommends pitching all three; **our playbook
   bans them by name** as publishers who run competing products. Ours was derived by
   opening the pages. **Keep ours.**
5. **Peak Freelance** — research names it one of two newsletters worth our single paid
   placement; **our playbook cut it on 2026-08-18** after finding it runs
   `jobs.peakfreelance.com` and lists it #1 in its own article. **Keep ours.** This is the
   clearest case of search-results research missing what page-opening found.
6. **Harlow** — research lists it as a roundup target; playbook says pitch Lettuce, not
   Samantha Anderl directly. **Keep ours.**
7. **JobBoardSearch dofollow** — research calls the free listing a "backlink"; our
   playbook quotes their own page: only *paid* listings are dofollow. **Ours is
   quoted from source.** Treat the free listing as audience, not a ranking signal.
8. **JobBoardSearch paid tier** — our playbook records $19 **auto-renewing every 30 days
   unless disabled**; research mentions a paid tier with no price and no renewal warning.
   Ours is the safer record.
9. **Product Hunt link value** — ours says launch-platform links are typically nofollow
   (audience play); research frames it as SEO via downstream scraping. Both partly true;
   don't budget for link equity.
10. **Which page to submit** — our playbook is specific (submit `nabbly.co/`, pitch the
    *field page* matching each article); the research pitches the homepage throughout and
    never mentions field-page targeting. **Ours is the better play**, especially once the
    field pages are fixed.

### What the research adds that we did not have

- **Reddit reality check**: across studies of 49–64 founder-facing subreddits, **58–61%
  ban self-promotion outright or gate it behind a 9:1 ratio**. Our playbook's "read the
  rules first" is right but understates how few venues are actually open.
- **r/SideProject and r/indiehackers** as the genuinely permissive A-tier.
- **Peerlist's zero-tolerance list** — DMing for upvotes, asking for upvotes in comments,
  excessive resharing all mean immediate suspension. Worth knowing before launching there.
- **HN specifics**: first 15–30 minutes of velocity dominate; "please don't ask friends to
  upvote" and ring detection means a domain ban is permanent. Never organise upvotes.
- **Directory tier list** with costs: AlternativeTo, JobBoardSearch, SaaSHub, Crunchbase,
  Peerlist, Product Hunt as the free A-tier; G2/Capterra deferred until ~200 paying users
  (G2 now ~$2,999/yr after acquiring Capterra, closed 2026-02-05).
- **A realistic day-30 expectation**: 8–12 listings live, **20–60 signups, and zero
  press** — press takes about three months. Stated bluntly, which is useful.
- **Spend nothing this month.** With one organic signup the constraint is retention, not
  reach. The two defensible buys later: a fixed-price technical SEO audit ($400–1,200)
  and 5–10 hours of freelance PR for a media list ($400–1,500).

### Their caveat, which should be respected

The research explicitly flags that **all Reddit rules came from third-party trackers**
because Reddit blocked its automated access, and that those trackers contradict each
other, most sharply on r/freelance. Open every sidebar before posting. Same for Uneed's
lane closure, BetaList's fee, and the Peak Freelance subscriber count.

---

## 9. How to use this in the SEO phase

1. Start the **freeze + archive** chain first. It is the only irreversible item.
2. Do Tier 1's seven site fixes — about three hours, no open questions, and item 1
   (homepage links to field pages) is the single highest-severity finding.
3. Regenerate the field pages while in there; they are still missing Archivo.
4. Treat every volume band as an estimate. The autocomplete findings are solid; the
   difficulty ratings are not.
5. On outreach, our own verified audit beats the new research wherever they disagree
   about a specific site — but take r/forhire, r/digitalnomad, r/SideProject,
   r/indiehackers and the Peerlist rules from the new work.

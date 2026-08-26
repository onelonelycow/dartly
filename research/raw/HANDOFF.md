# Handoff: SEO and growth research for Nabbly

Research run 2026-08-25 by three parallel agents in a separate Claude session, working
from the `nabbly-seo-handoff.zip` brief. That session had no access to the Nabbly repo,
so **nothing here has been applied**. Every change still needs making in the real
codebase.

**This file is the entry point and the ruling.** Where a numbered document below
disagrees with this file, this file wins, because it incorporates the founder's answers
and the reconciliation against `OUTREACH.md`, both of which happened after the research
finished.

## What is in this folder

| File | What it is | Length |
|---|---|---|
| `HANDOFF.md` | **This file. Start here.** Entry point, founder's answers, reconciliation, the corrected action list | 234+ lines |
| `00-MASTER-PLAN.md` | The three passes synthesised into one tiered sequence | ~19k chars |
| `01-seo-content.md` | Keywords per field, the head term, ten guides, technical pass, AI search | 10,700 words |
| `02-data-partnerships.md` | The data asset, buyers, alt-data reality, legal analysis, five report products | 1,336 lines |
| `03-outreach-representation.md` | Directories, community rules, creators and press, what to pay for, 30-day sequence | 927 lines |
| `04-OUTREACH-original.md` | **Nabbly's own pre-existing outreach file**, copied here unchanged so everything travels together. Not research output | 324 lines |

Read this file, then `00-MASTER-PLAN.md`. Go to the numbered documents only for the
detail behind a specific recommendation.

## One note before anything else

**The first three items in the corrected sequence are a chain, and the order inside it
is not negotiable.**

    decide the Management / Consulting merge
      -> freeze and version field definitions
        -> start daily aggregate archiving

The temptation is to skip past this and start on the site fixes, because those are
visible, quick, and feel like progress. The site fixes will still be there next week.
This week's data will not: the 21-day retention is deleting it continuously, and history
cannot be back-filled at any price.

The merge has to come first because merging fields after the archive has history means
either rewriting the archive or living with a discontinuity in your own trend series,
which is exactly what makes a dataset hard to publish from later. The freeze has to come
before archiving so the archive stays comparable to itself.

If only one thing in this entire folder gets done, make it this chain. Everything in the
data document, every recurring report, and every partnership conversation two years out
is gated on it. Two days of work is the option on all of it.

## How to use this

It is research, not a plan you are expected to adopt. It was produced by agents that had
never seen the codebase, the database, or the reasoning behind most product decisions.
**Take the verified findings as facts, argue with the judgment calls, and rewrite the
sequence to fit what you know.** The list of things worth arguing with is near the
bottom of this file.

Confidence is marked throughout the numbered documents. Where an agent verified
something by fetching a page or querying autocomplete it says VERIFIED. Where it
estimated, it says so and gives the method. **Do not treat an estimate as a measurement.**

## What was given to the research session

The zip contained `RESEARCH-BRIEF.md`, `FEEL.md`, `GOOGLE-JOBS.md`,
`make_field_pages.py`, `data/category-inventory-2026-08-25.csv`, `refresh-seo-pages.yml`,
and copies of `index.html`, `about.html`, `faq.html`, one field page and one guide.

It did **not** have: the repo, the database, `OUTREACH.md` (found later, reconciled
below), `outreach/DRAFTS.md`, or any analytics.

Constraints held throughout, and they were not re-litigated: the Google for Jobs
decision stands, no per-gig pages, sources are never named publicly, board.nabbly.co
is not the SEO surface, and all proposed copy follows FEEL.md section 7.

## The findings that were verified against the live site, not inferred

These came from actually fetching pages, so they should hold up:

1. `index.html`'s complete internal link set is `/`, About, FAQ, Privacy, Terms and
   three anchors. It links to **none** of the 23 field pages and **not** to the guide.
2. `board.nabbly.co/robots.txt` carries `Disallow: /gigs?*`, which blocks the field
   views the brief wants indexed. Every field page's amber CTA points at a blocked URL.
3. `board.nabbly.co/` and `/gigs` both return `<title>Nabbly</title>`, with no canonical
   and no meta robots on either.
4. `/freelance-photography-jobs/` returns 200 and is indexable but is absent from
   `sitemap.xml`. The generator writes pages and never prunes them.
5. `/guides/` returns 404.
6. Google autocomplete for all 24 fields completes to "freelance X **jobs**" and
   "remote X **jobs**", never "work". Raw autocomplete captures were kept.
7. `remote development jobs` autocompletes to nonprofit fundraising. `remote developer
   jobs` is clean across all ten suggestions.

Items 1 through 5 are bugs or contradictions, not opinions.

## What needs the repo, and so needs you

Tier 1 of the master plan is seven changes, roughly three hours total, all in
`make_field_pages.py` and `index.html`. None of them depend on any open question:

1. Link field pages and the guide from the homepage (30 min)
2. Field page title pattern: "work" becomes "jobs" (20 min, fixes 23 pages)
3. Homepage title, description and H1 (20 min)
4. Six field pages repointed at the right noun, including a 301 for the 9,238-gig
   development page (45 min)
5. Generator prunes pages that drop below `MIN_GIGS` (30 min)
6. Create `/guides/`, add breadcrumb and Article schema (1 hour)
7. Decide the board robots.txt question, Option A recommended (30 min)

Exact proposed copy for each is in `00-MASTER-PLAN.md` and, in more detail, in
`01-seo-content.md` parts 1, 2 and 4.

## What is time-sensitive and is not an SEO task

**Daily aggregate archiving** (`02-data-partnerships.md` section 3.5). One to two days
of work, about $5/month. It is the only irreversible item in the research. The current
21-day retention is destroying the record continuously, history cannot be back-filled,
and every recurring report and partnership downstream is gated on it. This should
probably be started before any of Tier 1, because Tier 1 will still be there next week
and this week's data will not.

**The subreddit collection question** (`02` section 4.4). One billable hour of counsel.
Reddit's terms require a negotiated commercial licence, and Reddit is currently
litigating against several parties over indirectly obtained scraping.

## Open questions: answered by the founder 2026-08-25

1. **Is board.nabbly.co browsable without an account? YES.** Show HN and r/SideProject
   are unblocked. No product change needed before launching.

2. **Data / analytics split: "probably a mix of both", not confirmed.** This is
   measurable rather than a judgment call, and the board has the answer. Run a count of
   the 2,409 Data gigs by title pattern, data entry terms versus analyst and analytics
   terms. If it is genuinely split, that is two pages rather than one, and
   `freelance data entry jobs` is the larger and easier term of the two. **Do this
   before writing either page.**

3. **Would disclose the full source list privately under NDA if the money is right.**
   The commercial data path stays open, which promotes one Tier 0 item from optional to
   important: **build the internal source register** (`02` section 4.5). A private
   record of every source and the rights it is collected under, maintained from now on.
   It is what makes an NDA disclosure possible in two years without reconstructing
   history from memory. Half a day, and like the archiving it only works if it starts
   early. Note the public no-sources rule is unaffected; this register is never
   published.

4. **`OUTREACH.md`: FOUND and reconciled 2026-08-25.** See the section at the end of
   this file. Short version: `OUTREACH.md` is the better document on targets and is
   ahead on execution. `03-outreach-representation.md` adds directories and verified
   community rules. Three conflicts, resolved below.

5. **Management / operations into Consulting: founder is in favour. Treat the research
   as weak support.** The suggestion in `01` section 2.2 was a one-line aside, not a
   researched recommendation. The evidence was only that `remote management j`
   autocompletes to "remote login vs remote management", so the phrase is contaminated
   by IT-admin meaning. It never checked whether the 1,651 management gigs and 1,714
   consulting gigs are actually similar work. Check that before merging.

   **Sequencing point the research missed:** Tier 0 calls for freezing and versioning
   field definitions before archiving begins, so the archive stays comparable to itself.
   **Any field merge must happen before that freeze.** Merging after six months of
   history means either rewriting the archive or accepting a discontinuity in your own
   trend series, which is exactly what makes a dataset hard to publish from later.
   Small decision now, annoying one in March.

## Two things worth arguing with

The research is confident about these and they are the kind of call that deserves a
second opinion from whoever knows the product better:

- **The digest, not the board, may be the thing to launch.** Remotive and Wellfound both
  started as email lists. See `03` section 6.
- **Selling the data is closed for two-plus years** on history requirements alone, and
  the recommendation is to publish an index instead. See `02` sections 0 and 3.3.

---

# Reconciliation: `OUTREACH.md` versus `03-outreach-representation.md`

`OUTREACH.md` was located 2026-08-25, after the research ran. The research session
never saw it. Both documents cover the same ground and **`OUTREACH.md` is the better
of the two on targets, because its list was tested rather than searched.**

Where they disagree, this section is the ruling.

## Already done, so drop it from the research plan

- **JobBoardSearch: submitted 2026-08-11**, free tier, feed field left empty as decided.
  `03` lists this as a week-1 task. It is done. Do not resubmit; the file says so.

## Where `OUTREACH.md` is right and the research is wrong

**The target list.** `03` built its outreach list from search results. `OUTREACH.md`
built one the same way on 2026-08-14, then opened all nine on 2026-08-18 and cut six
because they run the very thing they would be adding Nabbly to. Survivors:
**elnacain.com, magier.com, lettuce.co**, all verified to run no board and no gig
newsletter, with drafts in `outreach/DRAFTS.md`.

The rule it derived from that is the sharpest finding in either document:

> Sites that rank for "best job boards" usually rank *because* they run one. Look
> instead at agencies publishing career content, and at business-of-freelancing sites
> (tax, invoicing, contracts) which serve freelancers without competing for attention.

`03` found one instance of this (Millo owns SolidGigs) without generalising it. Treat
`OUTREACH.md`'s rule as the standing one, and apply it to every name in `03` section 3
before contacting anyone.

**Pitch the matching field page, not the homepage.** `OUTREACH.md` is right and `03`
is generic here. A writing roundup should get `/freelance-writing-jobs/`.

**Lead newsletters versus advice newsletters.** `OUTREACH.md` splits these correctly:
newsletters that curate and send gigs are competitors, not partners. Advice and
business-of-freelancing newsletters have no feed to protect. `03` does not make this
distinction and its section 3.1 list should be re-sorted against it.

**Paid links.** `OUTREACH.md` correctly notes that paying for a dofollow link is what
Google's link scheme guidance prohibits, and that JobBoardSearch's dofollow sits behind
the paid tier. `03` recommends several paid directory tiers without raising this. Take
free tiers.

## Where the research is right and `OUTREACH.md` should be corrected

**Reddit.** `OUTREACH.md` lists r/freelance, r/forhire and r/digitalnomad as targets
with "read the self-promotion rules first". The research read them:

- **r/forhire has no legal post format for a tool.** Every post must be
  [For Hire] / [Hiring] / [Task]. There is no valid way to post Nabbly there.
- **r/digitalnomad is a ban risk**, as is r/InternetIsBeautiful.
- Roughly 60% of founder-facing subreddits ban self-promotion outright.
- The legal, high-value set is **r/SideProject**, **one SHOW IH post on
  r/indiehackers**, **Indie Hackers Milestones**, and **Show HN**.

Caveat both ways: Reddit blocked automated access during the research and trackers
disagreed, most sharply on r/freelance. **Verify on each sidebar before posting.**

**AlternativeTo is missing from `OUTREACH.md` and is the research's top-ranked item.**
It is the exception to that file's "startup directories send founders, not freelancers"
rule, because its pages rank for "SolidGigs alternatives" and similar, which is a
freelancer query. Free. Create the account early, the age clock matters. Then add
Nabbly as an alternative on four competitor pages.

Also absent from `OUTREACH.md` and worth having: SaaSHub, Crunchbase, Peerlist
Launchpad, Fazier, MicroLaunch. All free tiers, all low effort.

## The one that is genuinely unresolved

**Peak Freelance.** `OUTREACH.md` cut it 2026-08-18 because it runs
jobs.peakfreelance.com. `03` week 3 says email them for single-issue sponsorship rates
($150 to $900 band). These are not the same action: the cut applies to free editorial
link pitching, and a competitor may still sell an ad slot. But `03` did not know they
run a board, so that recommendation is uninformed rather than wrong. **Ask for the rate
card, do not assume either answer.** Same question applies to Millo, which owns
SolidGigs.

## Sequencing conflict neither document could see alone

`OUTREACH.md`'s Tier 3 send-table points at `/freelance-development-jobs/`,
`/freelance-admin-jobs/` and `/freelance-video-jobs/`. Those are three of the six URLs
that `01-seo-content.md` section 2.2 says are aimed at the wrong noun and should move
to developer, virtual assistant and video editing.

**Do the URL renames before the outreach push.** Editorial links earned to a URL you
then 301 away from are worth less than links to the target, and you only get to pitch
elnacain.com once. Update the send-table and any drafts in `outreach/DRAFTS.md` at the
same time as the generator change.

## One number to settle

The JobBoardSearch submission description says "across 25 fields". The homepage says
"25+ fields". `RESEARCH-BRIEF.md` says 24. The CSV has 24 named categories plus an
"Other / general" bucket, so 25 is arguable rather than untrue, but it is now printed
in a live third-party listing and on the most important page on the site. FEEL.md
section 7 says numbers must be true at all times. **Pick one number, write down what it
counts, and use it everywhere.**

## Still to find

`OUTREACH.md` references `outreach/DRAFTS.md`, holding drafts for elnacain.com,
magier.com and lettuce.co. Not seen by the research session. Check it before writing any
new pitch.

---

# The corrected sequence

This supersedes the tiers in `00-MASTER-PLAN.md`. It folds in the founder's answers and
the `OUTREACH.md` reconciliation, both of which happened after the research finished.
Items removed here are removed because they are already done or were wrong, not because
they were deprioritised.

## Start now, in this order

| # | Do | Why now | Effort |
|---|---|---|---|
| 1 | **Decide the Management / Consulting merge** | Must precede the field-definition freeze, which must precede archiving. Cheap now, painful in March | 1 hr |
| 2 | **Freeze and version field definitions** | Makes the archive comparable to itself | 2 hrs |
| 3 | **Start daily aggregate archiving** | Only irreversible item in the research. Retention is deleting history daily | 1 to 2 days |
| 4 | **Build the internal source register** | Promoted, because the founder would sell under NDA. Never published | half day |
| 5 | **One lawyer hour on the subreddit question** | Largest unpriced risk. Gets worse the longer it runs unexamined | $300 to $600 |

Items 1 to 3 are one chain and the order inside it is not negotiable.

## Then the site fixes, about three hours total

All in `make_field_pages.py` and `index.html`. None depend on an open question.

| # | Do | Effort |
|---|---|---|
| 6 | Link field pages and the guide from the homepage. It currently links to neither | 30 min |
| 7 | Field title pattern: "work" becomes "jobs" across 23 pages | 20 min |
| 8 | Homepage title, description and H1 | 20 min |
| 9 | Repoint six fields at the right noun, 301 the development page to developer | 45 min |
| 10 | Generator prunes pages below `MIN_GIGS`, killing the orphaned photography page | 30 min |
| 11 | Create `/guides/`, add breadcrumb and Article schema | 1 hr |
| 12 | Board robots.txt: noindex on every route, permissive robots.txt (Option A) | 30 min |
| 13 | Update `OUTREACH.md`'s send-table and `outreach/DRAFTS.md` to the renamed URLs | 20 min |

**13 must happen with 9.** Outreach links pointing at URLs you are about to 301 are
worth less than links to the target, and elnacain.com can only be pitched once.

## Then measure two things before writing content

| # | Question | How |
|---|---|---|
| 14 | Are the 2,409 Data gigs analysis or data entry? | Count titles by pattern. If split, that is two pages, and data entry is the bigger easier term |
| 15 | Are management gigs and consulting gigs actually similar work? | Confirms or kills item 1 |

## Then content, which is also the press asset

| # | Do | Effort |
|---|---|---|
| 16 | `/new-remote-jobs/`, rebuilt daily with a visible build date | 3 hrs |
| 17 | Rate Bands, which is also SEO guide #1 "what design work actually pays" | 2 to 3 days |
| 18 | First Hour (arrival timing). Five weeks of data is enough for hour-of-day | 2 days |
| 19 | `nabbly.co/data/` plus a press email address | 1 day |

Every figure is a share or a band, never a live count, and every figure is stamped with
its measurement window. Rebuild monthly and restamp.

## Then distribution

Corrected against `OUTREACH.md`. **JobBoardSearch is done, do not resubmit.**

| # | Do | Note |
|---|---|---|
| 20 | AlternativeTo account today, submit later, add Nabbly on four competitor pages | Absent from `OUTREACH.md`, top-ranked by the research |
| 21 | SaaSHub, Crunchbase, Peerlist, Launching Next, Fazier, MicroLaunch | Free tiers only |
| 22 | Job Search Database, Job Board Fast | From `OUTREACH.md` Tier 1, still outstanding |
| 23 | Pitch elnacain.com, magier.com, lettuce.co with drafts in `outreach/DRAFTS.md` | Open each article first. Send the matching field page |
| 24 | Indie Hackers Milestones post, the honest one | Season the account first |
| 25 | r/SideProject, one SHOW IH post, Show HN | Show HN is unblocked, the board is browsable without an account |
| 26 | Ask Peak Freelance and Millo for rate cards | Both run competing boards. Ask, do not assume |
| 27 | Product Hunt, scheduled properly | Week 6 or 7, not on impulse |

**Not on this list, deliberately:** r/forhire (no legal post format for a tool),
r/digitalnomad and r/InternetIsBeautiful (ban risk), G2 and Capterra (need 10 to 20
reviews), BetaList (product is live, not beta), paid dofollow tiers anywhere, and
"best freelance job boards" as a content target.

## Do not do

- Contact a hedge fund, list on a commercial data marketplace, or attend an alt-data
  event. Buyers need 2 to 3 years of history; Nabbly has 37 days.
- Buy a PR retainer ($3k to $7k/mo) or MarketerHire ($5k/mo).
- Write "best freelance job boards". Listicle SERP, no product page ranks, and it
  requires naming sources.

The only two defensible spends: a fixed-scope technical SEO audit ($400 to $1,200) and
5 to 10 hours of freelance PR ($80 to $150/hr).

---

# What to argue with

These are judgment calls made by agents that had not seen the product. A second opinion
from someone who has is worth more than the research is.

1. **Launch the digest, not the board.** Remotive and Wellfound both started as email
   lists. Dutel wrote one post, collected 100+ emails, launched a month later as a
   newsletter and hit #1 on Product Hunt. Nabbly's digest is currently framed as a
   feature of the board.
2. **Selling data is closed for two-plus years**, so publish an index instead.
3. **Kill the Photography page** (185 gigs, intent is overwhelmingly local) and possibly
   Audio (100).
4. **"Gigs" is not a search term.** Sixteen of 24 field-plus-gigs probes came back
   polluted; "hr gigs" returns H.R. Giger for all ten suggestions. FEEL.md is right to
   keep "gigs" in the product; it should not be in page titles.
5. **The `/new-remote-jobs/` bet.** It assumes recency intent converts, which is
   unproven for this niche.

# Expectations, so the result is not misread

- SEO changes take 4 to 12 weeks to show. Nothing in items 6 to 13 moves a number this
  month, and that is expected rather than failure.
- Day 30 of distribution: 8 to 12 listings live, 20 to 60 signups total, zero press.
  Press takes three months and only if the data pitch lands.
- The signal that outreach is working is not traffic. It is field pages moving from
  Discovered to Indexed in Search Console, and impressions starting.

**The stopping rule:** if distribution produces signups but nobody returns the next day,
stop all of it and fix retention. Distribution is only worth buying for a product people
come back to.

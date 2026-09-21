# Nabbly — Handoff

Written 2026-09-16, updated 2026-09-21, from the repository, its commit history (603 commits since
2026-07-19), the docs in the repo, the Render and Supabase state as read that
day, and the working notes kept by the assistant who built most of it. Where a
number is given, it was measured on the date stated, not remembered. No
credentials appear here; each secret is named by what it is for.

---

## 1. Project overview

- **Name:** Nabbly (nabbly.co). Previously "Gig Radar", then "Dartly" — see §2.
- **One sentence:** A board that gathers freelance projects and remote jobs from
  ~20 public sources and shows them minutes after they post, with a drafted
  reply on every card and, for Freelancer.com, a bid you can place without
  leaving.
- **Problem:** The reply that lands first gets read. Freelance work is scattered
  across a dozen boards, most listings are hours old by the time anyone sees
  them, and a Freelancer project has ~30 bids within two hours of posting.
  Nabbly's measured detection latency is 2–6 minutes per source; the slow
  sources are their own feed delay, not ours.
- **Who it is for:** Individual freelancers and remote workers — designers,
  developers, writers, marketers, VAs — who want to see new work first and
  reply fast. Free tier is the whole board; paid tiers are about getting there
  first (alerts, ranking, drafted replies, market rates).
- **Why it exists:** The founder (Benjamin Steinhorn, Portland, US Pacific time;
  business/marketing background) wanted the "watch quietly, point at what
  matters" tool for the freelance market. The radar metaphor survives in the
  logo and in FEEL.md.

## 2. Backstory and history

**Origin (2026-07-17 to 07-19).** Started as "Demand Radar" / "Gig Radar" — a
Streamlit app that pulled hiring posts from a handful of RSS feeds and Reddit
`[Hiring]` threads and classified them. The repo directory is still named
`demand-radar` and the Render service for the original app is still named
`dartly`. Two adjacent ideas were researched and rejected in the same week:

- **Local service demand (landscaping etc.)** — about twenty sources tested;
  every open source was empty and every real one gated or litigious. Closed.
- **Permit radar for small residential contractors** — the permit is pulled by
  the contractor *after* the homeowner has hired them, so the signal means
  "this job is gone"; small contractors do not work cold lists. Closed.
  Full write-up: `RESEARCH-local-demand.md`, `ROADMAP.md` §"Closed".

**Rebrands.** Gig Radar → Dartly (2026-07-19) → Nabbly (2026-07-22), when the
nabbly.co domain and handle were secured. Brand kit in `brand/`.

**Product pivots, in order:**

1. **Per-person Nabbly (2026-07-22).** From one shared board to accounts,
   profiles, saved gigs, a 14-day Pro trial, then a "founding 50" perk.
2. **Durable data (2026-07-24).** Render wipes the disk on every deploy; the
   board moved to a Postgres mirror on Supabase so nothing resets.
3. **The FastAPI board (August).** The Streamlit app was slow, showed
   signed-out tabs it should not, and hosted Stripe. A second service,
   `nabbly-board` at board.nabbly.co, was built page by page — Gigs, Dashboard,
   Saved, Profile, Market, Plans, sign-in — and became the product. The
   Streamlit app (`app.nabbly.co`) is on a retirement path (`RETIRE-APP.md`);
  as of this writing it still serves the sign-out hop and nothing a member
   needs.
4. **Ingest moved onto the board service (late August).** The fetch loop used
   to run inside Streamlit, i.e. only while a browser was open. It now runs as
   a background thread on `nabbly-board` with a lease so two services cannot
   both ingest.
5. **Email cadence (2026-09-09/11).** Alerts had been firing hourly and spammed
   the founder; the weekly email became a "market-first" newsletter, sent
   7–9am Pacific, once a week. Rule adopted: never pick a number that reaches a
   real user without asking the founder.
6. **Quality over quantity (2026-09-11 onward).** The founder's framing: "not
   all the people in the world need THAT many jobs on here." Structured
   location and work-type at ingest, source-stated language, a measured
   classifier rewrite, and a "Projects only" filter followed. Diversifying
   supply by adding marketplaces was tried: of 12 evaluated, only Freelancer
   and PeoplePerHour are open and structured (`MARKETPLACES.md`).
7. **Apply from Nabbly (2026-09-10 to 09-16).** Freelancer OAuth connection,
   then the bid panel. Live on the real Freelancer as of 2026-09-16.

**Milestones:** first deploy 07-19; nabbly.co live 07-25; Supabase mirror
07-24; board service serving members 08-13; Stripe checkout on the board
08-30/31; first completed checkout 09-08 (a test account on the Alerts
tier — it proved the pipe, not the market); demo to "John" 09-11;
Freelancer bid live 09-16.

## 3. Current product

**Live on board.nabbly.co (the product):**

| Area | What it does |
|---|---|
| `/` Dashboard | Signed-in landing: hero, category groups, "fresh off the boards", a top-match card with a written reply. |
| `/gigs` Board | The full board, 25 per page. Rail filters: category groups + all 24 categories, Location (Everywhere / Remote I can take / On-site), **Kind of work (Anything / Projects only)**, Budget (Small/Medium/Large), Urgent. Search with typeahead. Sort: Newest, or Best match (Pro + profile). Cards carry category, budget, location, project/contract/full-time pills. |
| `/draft/{id}` Draft my reply | A reply written for the gig: template on Free, Claude-written on Pro. Copy, Save, Open in email (if the gig takes email), Apply on {source}. **On a Freelancer gig with a linked account: bid panel** (live budget, bids so far, bids left, price + days, Place bid, Retract). Fixed-price projects only. |
| `/saved` | Saved gigs. |
| `/market` | Where the work is: counts by category across the whole board; Pro adds typical budgets and the small/large split. |
| `/plans` | Free / Alerts $5 / Pro $15, Stripe checkout, trial, cancel, resume, switch. |
| `/profile` | Three tabs: **You** (name, country, skills, keywords, rate floor, resume upload), **Preferences** (alert channels: push/Telegram/Slack/Discord/SMS, cadence, urgent-only; language; forwarding address), **Account** (plan, **Connected accounts — Freelancer**, email opt-in, feedback, delete). |
| `/signin` | Email code (30-min TTL) or Google. No passwords. |
| `/unsubscribe` | One-click, with a way back on the profile. |
| Attribution | `?ref=` / `utm_source` on nabbly.co rides to the board, survives sign-in, is written to the member record; PostHog events (signup, draft_view, gig_click, trial_start, purchase, cancel…) carry `campaign`; internal accounts excluded. `tools/acquisition.py` reports signups → 7-day return → trials → paying by campaign. |
| Weekly email | Market summary + five fresh picks in the reader's languages, capped per source/company/budget tier. |
| Alerts | Instant pings on matching gigs via the member's chosen channels. |
| `nabbly.co` | Static marketing site: home, about, FAQ, pricing, privacy, terms, 23 SEO field pages ("freelance design jobs" etc.) regenerated from the live board. |

**In development:** nothing in flight at the moment of writing.

**Planned (see §11):** hourly-project bids; Guru if they answer; team accounts
(validated first); roundup outreach.

**Deprecated:** app.nabbly.co (Streamlit `dartly`). Reddit as a source (kept in
config for the `[Hiring]` classifier path; not enabled).

**Main user flow:** land on nabbly.co or a field page → Open the board (no
sign-in needed) → find a gig → Draft my reply → sign in with email code →
(founding grant: 60 days Pro) → copy reply / open source / place bid → save.

## 4. Technical architecture

- **Language:** Python 3.12 throughout. No JavaScript framework; a few inline
  scripts (copy button, bid confirm, async draft fetch).
- **Board service (`web/`):** FastAPI + Jinja2 + one uvicorn worker. Reads a
  local SQLite file (`board.db`) with FTS5 for search. Sessions via Starlette
  signed cookies (`AUTH_COOKIE_SECRET`). Server-rendered HTML; anonymous pages
  carry a 60s public cache header.
- **Streamlit app (`app.py`):** the original UI. Retirement path documented.
- **Ingest (`refresh.py` → `ingest.py` → `sources.py` → `classify.py` →
  `db.py`):** every ~2 minutes, fetch 42 feeds from 21 sites, clean, classify
  (category, budget tier, urgency), tag language/location/work-type, store in
  the ingest SQLite (`demand_radar.db`), push new rows to the mirror.
- **Mirror (`board_store.py`, `store.py`):** Supabase Postgres, table
  `nabbly_posts` (every gig ever seen; ~175k rows, ~107k not archived) and
  `nabbly_kv` (accounts, per-user files, analytics, snapshots, ops state).
  Local disks on Render are wiped per deploy; the mirror is the source of
  truth and everything rehydrates from it on boot.
- **Board sync (`web/sync.py`):** on boot pulls the whole board from the mirror
  (137–173s measured 2026-09-15), then incremental every 60s, reconcile every
  15 min, retention sweep daily (14-day window, ~53–55k rows steady state).
- **Auth:** email one-time codes (Resend) or Google OAuth; per-user data lives
  under a scope derived from the email (`paths.py`).
- **Billing (`billing.py`):** Stripe subscriptions, two prices; no webhook —
  the Plans page reconciles against Stripe on view and self-heals a checkout
  whose redirect never landed.
- **AI (`pitch.py`):** Claude (`claude-sonnet-5`) writes Pro drafts from the
  posting; template fallback on Free or when the key/balance is missing.
- **Freelancer (`freelancer.py`):** OAuth2 against accounts.freelancer.com,
  tokens encrypted at rest (Fernet keyed from the cookie secret), bid / retract
  / project / bids-left API calls. Sandbox by default; `FREELANCER_LIVE=1`
  switches to production.
- **Email (`mailer.py`):** Resend. Sign-in codes, welcome, weekly, alerts.
- **Alerts (`alerts.py`):** ntfy push, Telegram, Slack/Discord webhooks, Twilio
  SMS (Pro).
- **Telemetry (`telemetry.py`, `analytics.py`):** PostHog when keyed; events
  keyed to a rotating session id, never email.
- **Classifier (`classify.py` + `config.JOB_TYPES`):** keyword lists per
  category, scored (title ×3, word-count weight), last-resort words, fixed-set
  fallbacks. Fingerprinted; the board re-tags itself once when the rules change.
- **Key architecture decisions:** one process serves pages *and* ingests (with
  a lease) because it is the only always-on process; SQLite locally + Postgres
  durably because page queries are ~20ms and the mirror pull is the only
  row-dependent cost; no webhook for Stripe by choice (reconcile on view);
  every capacity decision keys off `boot_pull_s` on `/health`.

## 5. Infrastructure and connected services

**Render** (one workspace, region Oregon; all three defined in `render.yaml`,
Blueprint-synced — editing the YAML deploys):

| Service | Plan | What it is |
|---|---|---|
| `nabbly-board` (srv-d9v39pnavr4c73dgt4cg) | starter, 512MB | The product at board.nabbly.co. Serves pages, runs ingest, alerts, weekly email, retention. Health at `/health` (reports rows, ingest age, `boot_pull_s`, sweep). |
| `dartly` | standard | The Streamlit app at app.nabbly.co. To be retired. |
| `nabbly-site-static` | static | nabbly.co marketing site from `site/`. |

Builds: ~3m40s since 2026-09-14 (pip cache kept). Deploys are zero-downtime;
the new instance serves "still loading the board" for `boot_pull_s` seconds.
Memory: process trimmed after every ingest cycle since 2026-09-15 after an OOM
restart; watch the `mem:` log line.

**Supabase:** one project, Postgres only — no Supabase Auth, storage, edge
functions or cron are used. Tables: `nabbly_posts`, `nabbly_kv`. Schema
migrations are in code (`board_store._ADDED`, run on first connect).

**Stripe:** live mode; two recurring prices (Pro $15, Alerts $5); customer +
subscription ids stored on the account record. No webhook. `STRIPE.md` has the
operating rules (prices are immutable; test and live are separate).

**Resend:** transactional + weekly email from nabbly.co. **Google Cloud:**
OAuth client for "Continue with Google". **Anthropic:** API key for drafts.
**PostHog:** analytics (optional). **Twilio:** SMS alerts (optional).
**Freelancer.com:** registered app "Nabbly" on the live developer site (and a
sandbox one); redirect `https://board.nabbly.co/connect/freelancer/callback`;
scope `fln:project_manage` only.

**Domains:** nabbly.co (static), board.nabbly.co (board), app.nabbly.co
(Streamlit). GitHub: `onelonelycow/dartly`, branch `main` auto-deploys.

**Secrets (names only):** `DATABASE_URL`, `AUTH_COOKIE_SECRET`,
`STRIPE_SECRET_KEY`, `STRIPE_PRO_PRICE_ID`, `STRIPE_ALERTS_PRICE_ID`,
`RESEND_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID/SECRET`,
`FREELANCER_CLIENT_ID/SECRET`, `FREELANCER_LIVE`, `POSTHOG_API_KEY`,
`TWILIO_*`, `INBOX_*` (forwarding mailbox, off), `NABBLY_BLOCK_UA` (crawler
list override), `MALLOC_ARENA_MAX`.

## 6. Repository map

Single repo. Entry points: `web/main.py` (board, ~2,900 lines, every route),
`app.py` (Streamlit), `refresh.py` (ingest loop), `ingest.py` (one cycle).

| Where | What |
|---|---|
| `config.py` | Sources, `JOB_TYPES` keyword lists, category groups, signals, `PROJECT_SOURCES`, fallbacks. **Most product rules live here.** |
| `sources.py` | One fetcher per site + generic RSS; emits the 6+3 field contract (source, source_id, url, title, body, posted_at; remote, location, work_type, lang). |
| `classify.py` | Category / budget / urgency. `_job_type()` is the scorer. |
| `lang.py`, `location.py` | Language detection + reading-language rule; remote/on-site/restriction tagging. |
| `db.py` | Ingest SQLite schema, upsert, retention, reclassify. |
| `board_store.py`, `store.py` | Postgres mirror + KV. |
| `accounts.py` | Accounts, founding/trial/partner grants, sign-in codes, opt-out. Business rules for plans. |
| `billing.py` | Stripe. |
| `pitch.py`, `drafts.py` | Reply drafting and saved drafts. |
| `score.py`, `market.py` | Fit ranking; market statistics. |
| `weekly_digest.py`, `mailer.py`, `alerts.py` | Email and alert channels. |
| `freelancer.py` | OAuth + bid client. |
| `web/queries.py` | Every board query; `_filters()` is the one WHERE clause. |
| `web/sync.py` | Mirror → board.db, derive columns, retention. |
| `web/webauth.py`, `web/googleauth.py` | Sessions, codes, Google. |
| `web/templates/` | Jinja pages; `_card.html` is the gig card. |
| `site/` | Static marketing site + generated field pages (`tools/`). |
| `brand/` | Brand kit, captions, outreach plan, social posts. |
| `partners/` | NextNW proposal and intro email. |
| `tools/` | Classifier measurement scripts + fixtures, page generator. |
| Docs | `FEEL.md` (design rules), `ROADMAP.md`, `STRIPE.md`, `DEPLOY.md`, `DEPLOY_SEO.md`, `RETIRE-APP.md`, `MARKETPLACES.md`, `LOCATION.md`, `CLASSIFIER.md`, `RESEARCH-local-demand.md`. |

## 7. Current status (2026-09-16)

**Works:** everything in §3. Sign-in, board, filters, drafts (template and AI),
saved, market, plans/checkout/cancel/resume, weekly email in-window, alerts,
unsubscribe round trip, Freelancer connect and bid panel (the panel reads live
project data from the real Freelancer API — budget, bid count, bids-left all
confirmed on 2026-09-16; the *placing* of a bid is untested on the live site
by decision: the founder will place the first one on a project he actually
wants, not a test).

**Partially working / caveats:**
- Freelancer bids: fixed-price projects only; the "bids left" field shape was
  not confirmed in docs — the panel says "unknown" if Freelancer's response
  lacks it.
- Himalayas (57% of the board) cards only carry a full description for rows
  fetched after 2026-09-13; older rows show one sentence until they age out.
- Classifier: 70% exact / 80% by group on unseen rows. The judge itself is only
  high-confidence on ~60%. ~85% is the realistic ceiling for keywords.
- Weekly email picks are always projects with the top scores; a size cap now
  guarantees mixed budget tiers, but Small is still rare.

**Known operational facts:** memory was 485MB/512MB on 2026-09-15 before the
trim; after it 150→190MB over 35 hours (read 09-18), reset by every deploy.
Boot pull 137–255s (255s on 2026-09-21 as the fuller Himalayas bodies come in
— watch it; the lever is `RSS_BODY_CAP`). If either climbs, the levers
are `RSS_BODY_CAP` (sources.py), `STALE_DAYS` (db.py *and* web/queries.py,
together), or the standard plan ($25/mo).

**Technical debt:** `app.py` (Streamlit, ~6k lines) still deployed; `web/main.py`
is one large file; no automated test suite (measurement scripts and ad-hoc
TestClient sweeps instead); Stripe without webhooks; two copies of the
retention window.

**Blockers:** none technical. Growth is the blocker: 8 accounts, of which 5
are real members (all founding, signed up Aug 20 – Sep 7) plus the founder
and two internal test accounts. **Zero paying customers** — the one Alerts
subscription is a test account (corrected 2026-09-21; the 09-16 draft
counted it).

**Priorities:** see §15.

## 8. Product and business context

- **Customer:** solo freelancers and remote job seekers, English-first, US-led
  but the board is 8–9% non-English (German, Spanish, French, Indonesian…) and
  routes those to readers who can read them.
- **Pricing (live):** Free $0 — whole board, search, drafted reply (template).
  Alerts $5/mo — instant pings. Pro $15/mo — everything plus ranking,
  AI-written drafts, market rates, SMS. 14-day Pro trial (once); founding 50
  get 60 days Pro; partner grant (NextNW) 90 days.
- **Positioning:** "Every gig. The moment it drops." Speed and a written reply,
  not size — the site deliberately stopped selling on board size (2026-08-10).
- **Competitors:** the roundup articles ("best freelance job boards"), Remotive
  / RemoteOK / WWR (which are also sources), Upwork/Freelancer's own feeds,
  paid alert tools. Six of nine outreach targets turned out to be competitors
  (`brand/OUTREACH.md`).
- **Differentiators:** latency (minutes), one board across marketplaces *and*
  job boards, project-vs-job separation, reading-language routing, drafted
  reply from the actual post, bid-from-here on Freelancer.
- **Growth:** SEO field pages + roundup outreach (not started, highest leverage,
  no code); AI answer engines (ChatGPT, Claude, Perplexity, Gemini, Copilot
  allowed to read the board since 2026-09-13/14; a real visitor arrived from
  ChatGPT before that); partner groups (NextNW); Guru partnership email drafted.
- **Revenue model:** subscriptions. `ROADMAP.md` ranks team/agency accounts as
  the strongest next revenue line, with a validation plan before building.
- **Pitch:** demo walkthrough video and notes were prepared for a meeting with
  "John" on 2026-09-11; his feedback is pending.

## 9. Decisions already made — do not reopen without a strong reason

**Product:** one board, free forever; paid = getting there first. Weekly email
once a week, morning Pacific, market first, listings second. Projects and
salaried jobs both stay on the board, separated by a filter. Non-English posts
are routed, not translated (parked). Hourly Freelancer bids wait for verified
API semantics. Local-service demand and permit radar are closed (§2).

**Technical:** Render + Supabase + SQLite-locally; ingest on the serving
process with a lease; no Stripe webhook; sandbox-by-default for Freelancer;
crawler blocklist keeps training bots out and answer engines in; every change
that reaches a real user gets measured before it is called safe.

**Branding:** Nabbly, amber-on-dark, "calm, dark, warm, one amber thing at a
time" (FEEL.md). No trailing reassurance copy in UI; controls say what they do.

**Pricing:** $15 / $5 / free; founding 50 at 60 days; trial 14 days once.

**Legal/compliance:** privacy page promises a rotating session id and no
email in analytics — keep it true. Freelancer API T&Cs require encrypted
token storage — done. Unsubscribe must always work (legal), and now has a
way back. Crawler robots.txt hides filtered board, drafts, out-links.

**Working rules with the founder** (learned, and worth keeping): never pick a
number that reaches a real user without asking; measure before calling a
change safe; don't assert a mechanism you haven't measured; check the git
branch before every commit; all tool clocks are UTC, he is Pacific; push
fixes without asking, but ask before anything outward-facing.

## 10. Open questions

- **Product:** should Small-budget gigs get a guaranteed slot in the weekly
  email? Translate non-English postings? Show hourly-bid support once
  semantics are confirmed?
- **Business:** which regions after the US (Workana LatAm, Malt EU drafts are
  parked); team accounts — validate with real agencies first (`ROADMAP.md`
  §"Validating team accounts").
- **Technical:** retire `dartly` (phase plan exists); when does the board need
  the standard plan; automated tests.
- **UX:** John's feedback; the profile's three tabs were just reshuffled
  (2026-09-15) and need a real user's eyes.
- **Go-to-market:** five verified roundup targets drafted (two in Gmail,
  three contact forms), none sent; Guru email ready; NextNW intro unsent by
  design.
- **Before any paid ads (decisions, not code):** (1) approve the privacy-page
  correction — it still says "Nabbly does not currently take payments" and
  omits Stripe and Resend; proposed copy is in the 2026-09-21 session notes
  / commit `6871713`'s message; (2) whether one-word search terms may go to
  PostHog at all; (3) Meta Pixel or Conversions API means an advertising
  cookie or hashed emails to Meta — a privacy rewrite and a consent decision
  the page currently promises against.

## 11. Roadmap

- **Immediate:** founder places the first real Freelancer bid; read `boot_pull_s`
  and `mem:` on the next deploys; send the Guru message; John's feedback.
- **30 days:** roundup outreach (Tier 1); retire app.nabbly.co (phase 1 is
  billing on the board — done); re-measure the default board view (Oct 2);
  hourly bids if docs confirm; watch conversion of founding members as their
  60 days end (first cohort lapses mid-October).
- **90 days:** validate team accounts with three agencies before building;
  Guru fetcher if they say yes; second classifier pass only if a reader
  reports a wrong card; consider standard plan when memory or pull time say so.
- **Longer:** regional supply (LatAm, EU marketplaces), rate intelligence as a
  product once periods are stated on enough postings (`ROADMAP.md`).

## 12. Where a non-code assistant helps most

- **Outreach and partnerships:** `brand/OUTREACH.md` (roundups), the Guru
  message (in the founder's Gmail drafts), NextNW materials in `partners/`.
- **Product management:** turn John's feedback into a ranked list; own the
  "quality over quantity" measurement cadence; keep `ROADMAP.md` honest.
- **Marketing:** the site's copy is deliberately quiet — read `FEEL.md` first;
  social posts in `brand/posts/`; demo video in `brand/posts/demo/`.
- **Research:** which agencies to interview for team accounts; whether hourly
  bidding is worth the API work; conversion of founding members.
- **Financial modeling:** 5 real members, 0 paying; costs ≈ Render (~$32/mo for
  three services), Supabase free tier, Anthropic per draft, Resend, domain.
- **Pitch materials:** `brand/deck-alts`, the demo walkthrough, this document.
- **Documentation:** keep this file and `ROADMAP.md` current; retire
  `RETIRE-APP.md` when the app is gone.

## 13. Source references

- Repo: `github.com/onelonelycow/dartly` (main). Dashboards: Render
  `dashboard.render.com/web/srv-d9v39pnavr4c73dgt4cg`; Supabase project (one);
  Stripe live dashboard; Resend; PostHog.
- Live: https://nabbly.co · https://board.nabbly.co · https://board.nabbly.co/health
- Read first: `FEEL.md`, `ROADMAP.md`, `CLASSIFIER.md`, `MARKETPLACES.md`,
  `STRIPE.md`, `RETIRE-APP.md`, `brand/OUTREACH.md`, `partners/`.
- Code to skim: `config.py` (rules), `web/main.py` (routes), `web/queries.py`
  (`_filters`), `sources.py`, `classify.py`, `accounts.py`, `freelancer.py`,
  `weekly_digest.py`, `render.yaml`.
- Fixtures: `tools/classifier_sample_2026-09-13.csv`,
  `tools/classifier_validate_2026-09-13.csv`, `tools/classifier_compare.py`.

## 14. Recent changes (last 60 days, materially)

- **Aug:** board service built and became the product; filters with honest
  counts; mirror rehydration on boot; retention moved to the mirror; crawler
  blocklist after Meta pulled 4GB/day; predictive search; profile with tabs and
  account menu; PostHog scaffold; classifier keyword fixes; SEO field pages;
  Plans on the board with Stripe; cross-user data leak and checkout replay
  closed (08-09); founding badge; NextNW partner grants.
- **Sep 1–11:** uptime check fixed; ingest lease; alerts filter fix; cancel
  flow honesty; a Stripe `timeout=` bug that cost a payment (fixed, self-heal
  added); "Start free trial" was charging — fixed; structured location and
  work-type at ingest; PeoplePerHour added; weekly email rebuilt and windowed;
  sign-in code TTL 10→30 min; marketplaces evaluated; demo for John.
- **Sep 17–21:** five roundup-outreach targets verified and drafted
  (`outreach/READY-TO-SEND.md`); field pages regenerated English-only with a
  top CTA; single-category chip on the board; every pricing link now goes to
  the board's own Plans; nested-form bug in "Turn email back on" fixed;
  favicon route; sign-in email said 10 minutes (was 30); full attribution
  audit before a Meta ads test — session id and campaign now survive sign-in,
  outcome events added, purchase deduped, internal accounts excluded,
  `tools/acquisition.py` (see §15); Scoutify noted as a comparable.
- **Sep 12–16:** Projects-only filter; language from the source; French
  Himalayas leak fixed and fuller bodies (capped); unsubscribe way back;
  ChatGPT/Perplexity allowed; classifier measured and rewritten (58→70% exact
  on unseen rows, 2× faster); weekly email budget mix; boot pull instrumented
  and cut 406→~150s; build cache fixed (6m→3m40s); OOM restart diagnosed and
  trimmed; Freelancer connect moved to Account tab and live; bid panel shipped.

## 15. Handoff summary

**Current state in 10 bullets**
1. Product is the FastAPI board at board.nabbly.co; Streamlit app is legacy.
2. ~53–55k gigs on the board from 21 sites, 14-day window, minutes of latency.
3. 5 real members (all founding, 60-day Pro) plus the founder and two test
   accounts; 0 paying. Their Pro ends one at a time, Oct 19 – Nov 6; a
   "your Pro ends soon" email now goes 3 days before each.
4. Pricing live: Free / $5 Alerts / $15 Pro; Stripe on the board; checkout
   proven end to end by a test purchase on 2026-09-08. No customer purchase yet.
5. Freelancer bidding is live on the real site as of 2026-09-16 (fixed-price).
6. Classifier at 70% exact / 80% group on unseen rows; measured, with fixtures.
7. Weekly email: once a week, 7–9am Pacific, market first, reading-language
   aware, budget-tier mixed.
8. Infra: Render starter (512MB) + Supabase Postgres; boot pull ~150s, memory
   ~150MB after trim; builds ~3m40s.
9. Answer engines (ChatGPT, Claude, Perplexity, Gemini, Copilot) can read the
   four public pages; training crawlers cannot.
10. Every claim in the docs carries a measurement date.

**Top 5 priorities**
1. Send the five outreach emails (`outreach/READY-TO-SEND.md`) and the Guru
   message — drafted, verified, the site now backs every claim in them.
2. Approve the privacy-page correction before any ad spend.
3. The five founding members' Pro ends Oct 19 – Nov 6, one at a time; no
   "your Pro ends soon" email exists yet — the only conversion touch they
   will get. Build it before Oct 19.
4. First real Freelancer bid (founder's call, on a real project), then
   John's feedback → ranked list.
5. Read `boot_pull_s` (255s on 09-21) and the `mem:` line on each deploy;
   lower `RSS_BODY_CAP` if the pull passes ~270s.

**Top 5 risks**
1. Growth: five real members, zero paying, no channel has been worked yet.
   None of the five has a *recorded* return visit ≥7 days after signup — but
   `last_seen` was only reliably updated on some paths before 2026-09-21, and
   PostHog split every member into two identities until the same day, so this
   is "not measured", not "confirmed inactive". Re-read in October.
2. Memory/boot on a 512MB instance — instrumented, but the slope needs a week
   of reading.
3. Source fragility: Himalayas is 57% of the board; a feed change there is a
   product change.
4. Freelancer API assumptions (bids-left shape, hourly semantics) unverified
   against docs that could not be fetched.
5. One-person bus factor on the product side; this file and the commit
   messages are the mitigation.

**What not to waste time rediscovering**
- Local-service demand and permit radar: researched, closed (`ROADMAP.md`).
- Marketplaces beyond Freelancer/PeoplePerHour are walled (`MARKETPLACES.md`).
- "Default the board to remote" and "marketplace-only default" made the board
  worse — measured and rejected.
- Filtering "quality" by text signals (thin descriptions) is a source
  fingerprint, not quality.
- Render's `cache.profile: no-cache` is the page cache, not the build cache.
- Board size is not a reason to delete gigs; retention is the lever.
- The Stripe `timeout=` parameter is not a thing; prices are immutable.
- The founder's account is Pro for life by an owner check in `accounts.status`;
  its `pro_until` date in the database is dead data.
- The people-table campaign tags for the first five members are gone
  (predate the mirror); "(none)" in the acquisition report is permanent for
  them, not a bug.
- Nested `<form>` tags are dropped by browsers; the TestClient honours them.
  Secondary forms on the profile page sit outside the main form and are
  wired by `form=`.
- The weekly email cadence and window were the founder's call; ask before
  changing any number a member receives.

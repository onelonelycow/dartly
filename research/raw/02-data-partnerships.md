# Nabbly: the data asset

What it is worth, who would pay for it, what cannot legally be sold, and the play
that actually fits a five week old company.

Research date: 2026-08-25. Company age at time of writing: 37 days.
All external claims carry a URL. All estimates carry a confidence level.

**I am not a lawyer and section 4 is not legal advice.** It is a research summary
of publicly reported case law and published terms, written so that a real lawyer
can be asked the right questions in one billable hour instead of five.

**Confidence key**
- **High**: stated by the company or court itself, or by two independent sources.
- **Medium**: reported consistently by industry press or practitioner writeups.
- **Low**: my inference from adjacent facts. Treat as a hypothesis, not a number.

---

## 0. The verdict, before the evidence

Three answers, because there are three different questions hiding in "should we do
something with the data".

**Should Nabbly sell its data now? No.** Not "not yet as a matter of taste". The
buyers who pay real money for job posting data require a minimum of two to three
years of history and prefer five, and Nabbly has five weeks. That is not a
negotiating position, it is a disqualification at the screening stage. Every hour
spent pitching a data desk in the next twelve months is an hour not spent on the
thing that would actually work.

**Should Nabbly publish its data? Yes, and this is the highest value finding in
this document.** The exact same asset that is worthless as a product right now is
immediately valuable as marketing. Nabbly has one organic signup and no search
traffic. Proprietary data is the single most reliable way a company with no domain
authority earns links from publications that have plenty. Levels.fyi reached
roughly 4 million monthly visits on this mechanism with, by their own account,
zero advertising spend
([startupfounderstories.com](https://startupfounderstories.com/stories/levels-fyi-zuhayeer-musa),
[semrush](https://vi.semrush.com/website/levels.fyi/overview)). Ahrefs' single
best known data study holds over 3,500 referring domains
([BuzzStream analysis](https://www.buzzstream.com/blog/bootstrap-link-building-analysis/)).
Nabbly can start this month. Section 5 names five specific products.

**Should Nabbly keep the option open? Yes, and it costs almost nothing.** The one
thing that must happen now, this week, is to start archiving daily aggregate
snapshots in a form that will still be readable in three years. History cannot be
back-filled. A company that starts snapshotting on 2026-08-25 has a saleable
two-year history on 2028-08-25. A company that starts in 2027 does not. This is
the cheapest strategic option available and the only genuinely time-sensitive item
in this document. Details in section 3.5.

And one warning that runs through everything: **a meaningful part of Nabbly's
intake is legally hotter than the founder probably realises.** Not the job boards.
The subreddits. Section 4.4.

---

## 1. Who already does this

The category splits cleanly in two, and the split matters more than any individual
company, because it tells Nabbly which half it could ever plausibly join.

### 1.1 The raw-data sellers

These companies sell the dataset itself, under licence, to buyers who run their own
analysis. Enterprise contracts, custom pricing, long sales cycles, and every one of
them has years of history as the core of the pitch.

**Lightcast** (formerly Emsi Burning Glass; emsi merged with Burning Glass
Technologies in 2021)

- *What they sell*: labour market intelligence. Job posting data, skills taxonomies,
  career profiles, and government series, unified. The pitch is coverage: over 2.5
  billion job postings, 800 million career profiles, 100+ government sources, 160+
  countries ([lightcast.io](https://lightcast.io/), [education use case](https://lightcast.io/use-cases/education)).
- *To whom*: universities and community colleges (curriculum and program planning),
  economic development agencies, large enterprise workforce strategy teams, staffing
  firms. Their own positioning names "VP of Workforce Strategy or People Analytics
  Director at a 2,000+ employee enterprise" as the primary buyer
  ([GTM Directory profile](https://thegtmdirectory.com/tools/lightcast)).
- *Price*: not published. All three delivery modes (software, consulting, API) are
  custom quoted; software is an annual subscription, API is usage based
  ([Toolradar](https://toolradar.com/tools/lightcast)). Publicly visible institutional
  quotes in the education segment have historically sat in the five-figure annual
  range per institution. **Confidence: medium on the shape, low on any specific number.**
- *How they bootstrapped*: they did not bootstrap, they consolidated. Emsi grew out
  of economic modelling consulting for colleges and had government data as its spine
  from the start; Burning Glass built the posting-scrape and skills-extraction side
  since 2007. The merger bought coverage rather than earning it.
- *Read-across for Nabbly*: none, honestly. This is the end state of fifteen years and
  an acquisition. It is useful only as the answer to "what is the ceiling".

**Revelio Labs**

- *What they sell*: workforce intelligence built from job postings plus individual
  employee profiles. Their COSMOS product aggregates over 5 billion job postings from
  7 million-plus companies against 1.1 billion-plus profiles, and they have gone as far
  as publishing RPLS, an explicit private-sector alternative to BLS releases
  ([Integrity Research](https://www.integrity-research.com/revelio-labs-unveils-rpls-a-bold-alternative-to-bls-in-turbulent-times/),
  [Datarade profile](https://datarade.ai/data-providers/revelio-labs/profile)).
- *To whom*: institutional investors and hedge funds first, then corporate strategy,
  people analytics teams, and government labour agencies.
- *Price*: unpublished. Institutional workforce-data subscriptions in this tier
  commonly land in the $50k to $500k per year band depending on scope.
  **Confidence: medium**, from the general alt-data pricing evidence in section 3.
- *How they bootstrapped*: profile data at scale plus academic-grade methodology and
  a very visible research output. The RPLS move is the tell: they earned standing by
  publishing an index journalists could cite, then sold the underlying data.
- *Read-across for Nabbly*: **this is the closest thing to a roadmap in the whole
  document.** Publish the index first, sell the data later. Revelio did in a few years
  what Lightcast did in fifteen, largely by being the quotable source.

**LinkUp**

- *What they sell*: job listings scraped exclusively and directly from employer career
  pages. 350 million-plus global postings, indexed daily since 2007, from 86,000-plus
  companies across 195 countries ([linkup.com/data](https://www.linkup.com/data),
  [Datarade](https://datarade.ai/data-products/linkup-raw-job-market-data)).
- *To whom*: capital markets primarily. They market openly on alpha: signals derived
  from their listings "can potentially add 2% to 5% of alpha annually"
  ([LinkUp](https://www.linkup.com/use-cases/alpha-innovation-using-alt-jobs-data)).
  Distributed through Open:FactSet, Exabel, and Maiden Century's IDEA platform.
- *Price*: unpublished, capital-markets tier. See section 3.4 for the band.
- *How they bootstrapped*: **the single most instructive origin story here.** LinkUp
  deliberately does not touch job boards or LinkedIn. Only employer career pages. That
  choice is usually explained as a data-quality argument (no duplicates, no recruiter
  spam) and it is, but it is also a legal architecture. Scraping an employer's own
  careers page, logged out, is about the cleanest position available in this whole
  category. Compare that to Nabbly's position in section 4.
- *Read-across for Nabbly*: they had **fifteen years of history before this was an
  easy sale.** They also route through Dewey for academic access
  ([deweydata.io/data-partners/linkup](https://www.deweydata.io/data-partners/linkup)),
  which is a channel Nabbly can realistically reach far sooner than a hedge fund.

**Bullhorn**

- *What they sell*: staffing and recruitment software. The data is a byproduct, not a
  product; they monetise the CRM.
- *The data output*: the annual GRID Global Recruitment Insights and Data report,
  now in its 16th year, surveying roughly 2,300 recruitment professionals
  ([Bullhorn GRID 2026](https://www.bullhorn.com/news-and-press/press-releases/bullhorn-grid-report-staffing-firms-using-ai-see-stronger-growth-faster-placements/)).
- *Read-across*: GRID is mostly **survey** data, not platform telemetry. Worth noting
  because a survey is something Nabbly could run in a week and does not require years
  of history. See section 5.6.

### 1.2 The report and index publishers

These companies do not sell the data at all. The data is a distribution engine for
the actual business. **This is the half Nabbly belongs in.**

**Indeed Hiring Lab** ([hiringlab.org](https://www.hiringlab.org/))

The purest example in existence of the play recommended in section 5. Indeed's
economic research arm employs actual labour economists, publishes weekly from a
daily measurement system, and benchmarks its indicators against BLS and Eurostat
before publishing ([about](https://www.hiringlab.org/about/),
[Indeed newsroom](https://www.indeed.com/news/releases/indeed-turns-data-into-insights)).
Two details Nabbly should copy exactly:

1. **They publish the underlying series on GitHub.** The job postings tracker and the
   wage tracker are public repositories
   ([job_postings_tracker](https://github.com/hiring-lab/job_postings_tracker),
   [indeed-wage-tracker](https://github.com/hiring-lab/indeed-wage-tracker)). A CSV in
   a public repo is what turns a report into infrastructure. Researchers cite what they
   can download.
2. **Everything is code-checked and fact-checked internally before release, and
   benchmarked against outside datasets wherever possible.** That discipline is what
   makes a private index quotable next to a government one.

Price: free. Revenue: zero, directly. Value: Hiring Lab is why Indeed gets quoted in
every US labour market story, which is worth more than a data licence.

**Ashby** ([ashbyhq.com/talent-trends-report](https://www.ashbyhq.com/talent-trends-report))

The most directly copyable model for a small company, and worth studying closely.
Ashby is an ATS. It publishes Talent Trends Reports built from its own customer
telemetry: 54 million applications and 93,000 jobs in one report, 109 million
applications and 247,000 jobs in another, spanning January 2021 to March 2026
([recruiting operations benchmarks](https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends),
[recruiter productivity](https://www.ashbyhq.com/talent-trends-report/reports/2023-recruiter-productivity-trends-report)).

Note what the coverage actually looks like: HR Dive ran "Recruiters see job
applications triple, to more than 300 per role"
([HR Dive](https://www.hrdive.com/news/recruiters-see-job-applications-triple-to-more-than-300-per-role/820096/)).
That headline is **one number from one chart.** The report is the artifact; the
single striking number is the product. Also note that "median time to fill reached
56.7 days, up 37% since 2022" is the shape of claim that travels: a precise level,
plus a change, plus a baseline year.

Ashby also runs a subscribe-for-the-next-report email capture on the report hub. That
converts press-driven traffic into a list, which is the mechanism Nabbly needs most.

**ADP Research** ([adpresearch.com](https://www.adpresearch.com/), [workforcereport.adp.com](https://workforcereport.adp.com/))

The National Employment Report is built from anonymised weekly payroll data on more
than 26 million US private-sector employees, published monthly with the Stanford
Digital Economy Lab
([ADP release](https://mediacenter.adp.com/2026-05-06-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-109,000-Jobs-in-April-Annual-Pay-was-Up-4-4),
[methodology partnership](https://mediacenter.adp.com/2022-08-23-ADP-Research-Institute-and-Stanford-Digital-Economy-Lab-Unveil-New-Methodology-for-ADP-National-Employment-Report)).
It moves markets. Trading Economics carries it as a tracked release
([tradingeconomics](https://tradingeconomics.com/united-states/adp-employment-change)).

The lesson is the Stanford partnership. ADP borrowed academic credibility rather than
asserting its own. Section 6.4 proposes the small-scale version of exactly this.

**Gusto** ([gusto.com/research/economic-data](https://gusto.com/research/economic-data))

Payroll data from 300,000-plus SMBs, published as an Economic Trends Tracker aimed
explicitly at "business owners, researchers, policymakers, journalists, and workers"
([Gusto](https://gusto.com/resources/gusto-insights/introducing-gustos-economic-data-tracker)).
Their New Hires Pay Index is a named, recurring, single-number index. Naming the index
is the trick: an index has a value that changes, which gives journalists a reason to
write about it again next month.

**Payscale** ([payscale.com/research-and-insights](https://www.payscale.com/research-and-insights))

Sells compensation software; publishes a quarterly Labor Market and Wage Trends Report
off its Peer dataset ([report](https://www.payscale.com/featured-content/labor-market-wage-trends-report)).
Standard version of the model.

**Levels.fyi**

The one that proves a two-person company can do this. Verified compensation data,
self-reported and reviewed against offer letters and W-2s before publication, which
is the differentiator. No advertising, no SEO programme, no growth marketing, and
roughly 4 million monthly visits with sessions averaging over three and a half minutes
([founder story](https://startupfounderstories.com/stories/levels-fyi-zuhayeer-musa),
[traffic](https://vi.semrush.com/website/levels.fyi/overview)).

Two mechanics worth stealing:

- **Seasonal demand spikes.** Traffic surged every performance review and negotiation
  season. Nabbly's equivalent seasonality is the January and September freelance
  hiring cycles and the tax-year contractor rate-setting moment. Time the reports.
- **They became the reflex answer.** When someone asked "is this offer fair", the reply
  was "check Levels.fyi". Nabbly's target reflex is: someone asks "what should I charge
  for this", and the reply is "check Nabbly's rate bands". That is a distribution goal,
  not a revenue goal, and it is achievable.

**Upwork Research Institute** and **Fiverr**

Both publish, both are partly survey and partly platform telemetry, and both are
Nabbly's most direct comparators in the freelance lane specifically.

Upwork's 2026 Future Workforce Index surveyed 2,400 US workers in March and April 2026
and combined that with platform metrics: AI-related work categories, contract starts,
hourly earnings, YoY earnings trends
([Upwork investor release](https://investors.upwork.com/news-releases/news-release-details/upworks-future-workforce-index-2026-how-ai-redefining-value-work)).
Their headline claim was "over 1 in 3 skilled US knowledge workers now freelance, up
from roughly 1 in 4 a year ago". One sentence, enormous pickup.

Fiverr's Business Trends Index is the more copyable one because it is pure percentage
change by category: AI voice agents +49%, AI mobile app development +92%, Video and
Animation +278%, Programming and Tech +94%, Digital Marketing +62%
([Fiverr June 2026](https://www.fiverr.com/resources/guides/reports/business-trends-index-june-2026)).
Nabbly's CSV already has exactly this shape (live_gigs and new_this_week per field).
**Nabbly could produce the structural equivalent of the Fiverr index today.** The only
missing ingredient is a prior period to compare against, which is the archiving point
in section 3.5.

Fiverr also maintains a permanent statistics hub
([freelancing statistics](https://www.fiverr.com/resources/guides/reports/freelancing-and-future-of-work-statistics)),
which is the evergreen link-magnet format. Nabbly should have one of these.

**MBO Partners**

Fifteen consecutive years of the State of Independence report, and the most-cited
freelance headcount numbers in the US press: 72.9 million independents in 2025, or
79.2 million on the wider definition
([MBO](https://www.mbopartners.com/state-of-independence)). Note the two numbers from
one study. Journalists picked whichever suited the story, and MBO got cited twice.
Defining your own metric, publicly and precisely, is how you own it.

**Malt / Contra**: I found no substantial recurring data product from either. That is
a **gap in the European and the non-marketplace freelance segments.** If Nabbly ever
wants a co-published report with a named partner, Malt is an interesting candidate
precisely because it has the audience and not the recurring index. **Confidence:
medium**, based on absence of evidence in search rather than confirmed absence.

### 1.3 The split, stated plainly

| | Raw data sellers | Report and index publishers |
|---|---|---|
| Who | Lightcast, Revelio, LinkUp | Hiring Lab, Ashby, ADP, Gusto, Levels.fyi, Fiverr, Upwork, MBO |
| Sells | The dataset | Nothing. The report sells the real product |
| Needs | 2 to 5+ years of history, provenance audit, legal indemnities | A defensible method and one striking number |
| Nabbly today | Disqualified | Eligible immediately |
| Nabbly in 2028 | Plausible | Compounding |

---

## 2. Who would buy or trade for Nabbly's data

Ordered by how soon they will actually take the meeting. Read the "will they talk to
a five week old company" line first in each case; it is the only one that matters
right now.

### 2.1 Hedge funds and alternative data desks

**Will they talk to a five week old company? No.** Not with a polite maybe attached.
No.

- *Who*: the data-sourcing teams at Point72 (Aperio / market intelligence), Balyasny
  (data strategy group), Millennium, Citadel, Two Sigma, WorldQuant. The role title is
  usually "Head of Data Strategy" or "Alternative Data Sourcing".
- *What they want*: a panel with stable methodology, mapped to tradable tickers, with
  enough history to backtest. Nabbly's data maps to no tickers at all. Freelance gig
  postings from public boards do not attach to a company's revenue line the way LinkUp's
  employer-page postings attach to a named employer's headcount plans.
- *Format*: daily or weekly flat files or an S3 drop, point-in-time correct, with a
  documented restatement policy.
- *What they pay*: on average, buyers subscribe to about 20 datasets a year for about
  $1.6 million total, so roughly $80k per dataset; 84% of firms spend between $500k and
  $2.5m annually in total, and the top 20 funds spend $40m to $60m each
  ([Hedgeweek](https://www.hedgeweek.com/hedge-fund-alt-data-spending-set-to-surge-says-new-research/),
  [Paradox Intelligence](https://www.paradoxintelligence.com/blog/alternative-data-for-hedge-funds-complete-guide)).
  **Confidence: medium-high on the aggregate figures, and irrelevant to Nabbly for at
  least two years.**
- *How you get in the door*: via a broker (section 3), not cold. And it starts with a
  due diligence questionnaire about data provenance, which Nabbly currently cannot pass.
  See 4.6.
- *Honest read*: **this is the fantasy version of the opportunity and it should be set
  aside entirely until 2028 at the earliest.** The disqualifier is not size, it is
  history plus provenance plus ticker mapping, and two of those three cannot be fixed
  with effort.

### 2.2 Academic and economic researchers

**Will they talk to a five week old company? Yes. This is the single best real
opportunity in section 2.**

- *Who*: labour economists working on remote work, gig work, and AI's effect on task
  demand. Named and reachable:
  - **Nick Bloom (Stanford) and the WFH Research group** ([wfhresearch.com](https://wfhresearch.com/research-and-policy/)),
    which runs the SWAA survey covering over 900,000 respondents and already blends
    survey data with job posting evidence. Bloom advises Scoop's **Flex Index**, which
    explicitly builds from "employee surveys, manual culling of policies from company
    career websites, and job postings"
    ([Forbes](https://www.forbes.com/sites/jenamcgregor/2023/02/07/a-new-flex-index-is-collecting-companies-remote-work-policies-in-one-searchable-tool/)).
    Nabbly's remote/onsite split by field is directly complementary to what they build.
  - **Stanford Digital Economy Lab**, which co-produces ADP's NER methodology.
  - University economics departments generally, via the **Dewey Data** channel below.
- *What they want*: a clean panel, a documented methodology, and permission to cite.
  They care far less about length of history than a trader does, because a novel
  five-week series on a segment nobody measures is publishable in itself.
- *Format*: CSV or Parquet, a data dictionary, and a stable definition of each field.
- *What they pay*: usually nothing in cash. **They pay in citations, and a citation is
  the highest-quality backlink and credibility signal available.** An academic paper
  citing "data provided by Nabbly" is worth more to this company right now than $10k.
- *Route in*: **Dewey Data** ([deweydata.io](https://www.deweydata.io/)) is the
  concrete, low-friction path and by some distance the best-value item in this document.
  Researchers at 600-plus universities subscribe. Dewey does the listing work, accepts
  data in whatever format the partner has, and says listings go live in under two weeks
  with no engineering work required
  ([become a data partner](https://docs.deweydata.io/docs/become-a-data-partner)).
  Critically, they scope licences to academic-only, non-commercial, term-limited use
  with every researcher vetted, and they allow data minimisation, meaning fields can be
  redacted or restricted to protect IP. LinkUp is already a Dewey partner
  ([LinkUp on Dewey](https://www.deweydata.io/data-partners/linkup)), which both
  validates the channel for job-posting data and tells you the shape of the listing to
  copy. Dewey also offers partners collaboration on content, seminars and events.
  **Do this at 6 months of history. Cost: a few days of work. Confidence: high that
  the channel exists and is open; medium on whether Nabbly's five-week dataset is
  accepted today, high that a six-month one would be considered.**

### 2.3 Workforce and HR analytics vendors

**Will they talk to a five week old company? Some will, as a data supplement, not a
purchase.**

- *Who*: Lightcast, Revelio, Horsefly Analytics, Draup, TalentNeuron (Gartner spinout),
  Claro Analytics, Aura by Burtch Works.
- *What they want*: coverage of segments they miss. And here is Nabbly's genuinely
  differentiated angle: **every one of these vendors is built on permanent-employment
  postings from employer ATSs and large boards. Freelance, contract and gig demand,
  especially from community and non-ATS sources, is a real hole in their coverage.**
  Nabbly is small but it is small in a place they are blind.
- *Format*: API or bulk feed, mapped to a standard occupation taxonomy (O*NET/SOC) and
  a skills taxonomy. Nabbly's 24 fields would need mapping to SOC codes. That is
  perhaps two days of work and it materially increases the data's value to everyone in
  section 2. **Do it early.**
- *What they pay*: supplement feeds are typically low five figures to low six figures
  annually, or a data-swap with no cash. **Confidence: low on the number.**
- *Route in*: their partnerships or data-sourcing teams, usually via a
  "become a data partner" form. Lightcast publicises partner integrations openly
  (for example the uConnect partnership for college career centres,
  [Lightcast blog](https://lightcast.io/resources/blog/new-partnership-with-uconnect-brings-labor-market-insight-to-college-career-centers)).
- *Honest read*: a swap is far more likely than a cheque at this stage, and a swap is
  fine. Getting Nabbly's name into a Lightcast or Revelio methodology page is worth
  more than the licence fee they would offer.

### 2.4 Staffing and recruiting firms

**Will they talk to a five week old company? They will take the call and then ask for
candidates, not data.**

- *Who*: Robert Half, Aquent and Vitamin T (creative contract talent, closest fit to
  Nabbly's design and content fields), Toptal, Andela, Kforce, Insight Global.
- *What they want*: honestly, they want the supply side. They want freelancers. A rate
  benchmark is a nice-to-have; a pipeline of qualified contractors is the actual budget
  line.
- *What they pay*: for market rate benchmarks, $5k to $30k a year. For candidate flow,
  vastly more, but that is a different business and one Nabbly should think hard before
  entering, since it puts Nabbly's users on the other side of the table.
- *Honest read*: **the risk here is being pulled into becoming a recruiting company.**
  Recommend engaging only at the co-marketing level, not the data-sale level.

### 2.5 Edtech, bootcamps and course platforms

**Will they talk to a five week old company? Yes, at the content-partnership level.**

- *Who*: Coursera, Udemy, Springboard, CareerFoundry, Scrimba, Codecademy, Section,
  Maven, and the design and marketing course sellers who explicitly price against
  demand.
- *What they want*: evidence that the skill they teach is in demand and pays. They buy
  this from Lightcast today for curriculum and program planning
  ([Lightcast education](https://lightcast.io/use-cases/education)).
- *What they specifically want from Nabbly that they cannot get elsewhere*: **freelance
  demand, not employment demand.** A bootcamp selling "become a freelance designer"
  cannot currently prove there is freelance work. Nabbly can.
- *Format*: a quarterly PDF plus a couple of charts they can reuse with attribution.
  They do not want a feed.
- *What they pay*: for a co-branded report, $0 to $15k, mostly in kind. For a
  licensed data widget embedded in a course landing page, low five figures.
  **Confidence: low.**
- *Route in*: content and curriculum leads, not procurement. Offer a free co-branded
  chart first.

### 2.6 Freelancer tooling, payroll and contractor payment platforms

**Will they talk to a five week old company? Yes, and this is the second-best real
opportunity.** Fully covered in section 6, because the right deal here is a
partnership, not a sale.

### 2.7 Journalists and think tanks

**Will they talk to a five week old company? Yes, if the number is good. They do not
care how old you are, they care whether the stat is checkable.**

- *Outlets that reliably run this beat*: HR Dive, HR Brew, Fast Company, Business
  Insider, Worklife, Sifted (Europe), Quartz, The Hustle, Marketing Brew, Axios
  Closer, plus trade press per field (Creative Bloq for design, InfoWorld and The
  Register for dev).
- *Think tanks and orgs*: Brookings Metro, Aspen Institute Future of Work Initiative,
  Freelancers Union, Upwork's own research team (who will read a competitor's index),
  and the Bureau of Labor Statistics, which now openly discusses private data as a
  complement to official series (the Revelio RPLS launch was framed exactly this way,
  [Integrity Research](https://www.integrity-research.com/revelio-labs-unveils-rpls-a-bold-alternative-to-bls-in-turbulent-times/)).
- *What they want*: one number, a clear method, a named human to quote, and a chart
  they can screenshot. In that order.
- *What they pay*: nothing. They pay in links, which is the currency Nabbly is short of.
- *Route in*: Muck Rack ([hiringlab profile](https://muckrack.com/media-outlet/hiringlab)
  shows how a research arm is indexed there), plus direct email. Get a
  press@nabbly.co address and a permanent /data page before pitching anyone.

### 2.8 Government labour agencies

**Will they talk to a five week old company? No, and do not spend a day on it.**
BLS, state workforce boards, Eurostat and the ONS have procurement processes measured
in quarters and require multi-year series and audited methodology. This becomes
reachable only via the academic route in 2.2, which is how private data usually reaches
government in practice.

### 2.9 University career centres

**Will they talk to a five week old company? Not as a buyer. Possibly as a free pilot.**
They buy Lightcast-powered dashboards through their institutional research office
([APSU](https://www.apsu.edu/success-initiatives/lightcast.php),
[Cal State LA](https://www.calstatela.edu/institutionaleffectiveness/lightcast-labor-market-data),
[SJSU](https://careercenter.sjsu.edu/labor-market-insights/)), and those are annual
institutional contracts with existing vendors. The realistic version is: give one
career centre a free freelance-demand chart for their students, get a .edu link and a
quote. That is a marketing win, not a revenue one, and it is a good one.

---

## 3. The alternative data market reality

### 3.1 How the market actually works

The market is real and large. Alt data reached about $2.8 billion in 2025 after roughly
27% growth in 2024, with projections running to $14 billion by 2027 on one estimate and
$23 billion by 2030 on a bull case
([Kadoa](https://www.kadoa.com/blog/alternative-data-for-hedge-funds),
[Paradox Intelligence](https://www.paradoxintelligence.com/blog/alternative-data-for-hedge-funds-complete-guide)).
94% of surveyed buyers expect to increase spend in 2026
([Hedgeweek](https://www.hedgeweek.com/hedge-fund-alt-data-spending-set-to-surge-says-new-research/)).
Job postings specifically are one of the better-validated signal families, credited
with predicting revenue growth, M&A activity and strategic pivots ahead of earnings.

None of that helps Nabbly today, for the reasons in 3.3.

### 3.2 The channels, with real numbers

| Channel | What it is | Cost / take | Fit for Nabbly |
|---|---|---|---|
| **Datarade** ([list your data](https://datarade.ai/company/contact/list-your-data)) | Discovery layer, 2,000+ providers, 600+ categories. Routes buyer enquiries; delivery happens off-platform | Free tier exists at $0 membership. Paid tiers quote-based. Standard tier carries a **30% marketplace commission** on facilitated transactions | **Best first listing. Free, no engineering, and it is a passive lead capture.** Do it at 6 months |
| **AWS Data Exchange** ([provider financials](https://docs.aws.amazon.com/data-exchange/latest/userguide/provider-financials.html)) | Full marketplace with delivery and billing | Sellers keep the large majority; AWS takes a platform fee (reported around 30% in the general marketplace, lower for qualifying data products) | Requires real engineering and a subscription product. Not now |
| **Snowflake Marketplace** | Share data natively into buyers' warehouses | Snowflake platform fee reported at ~10% | Only if buyers are already Snowflake shops. Not now |
| **Eagle Alpha** ([data vendor](https://www.eaglealpha.com/platform/data-vendor/)) | Aggregator with buyer-side vetting and profiling tools; vendors can join **free** | Free to join | Worth a listing at 12+ months. Low cost, low probability |
| **BattleFin Ensemble + Discovery Days** ([battlefin.com](https://www.battlefin.com/)) | Curated events with pre-scheduled 15 to 25 minute one-to-ones between vetted providers and buy-side attendees, plus a standardised vendor scoring framework | Event participation typically costs money and requires vetting | **This is where deals actually start.** Also where a five-week dataset would be politely destroyed. 2028 at the earliest |
| **Nomad Data** | Search and sourcing layer for buyers describing a problem | Free listing | Cheap to list. Low expected value |
| **Dewey Data** ([partner docs](https://docs.deweydata.io/docs/become-a-data-partner)) | Academic-only marketplace, 600+ universities, vetted researchers, non-commercial term-limited licences, listings live in under two weeks, no engineering required | Revenue share, unpublished | **The one to actually pursue.** See 2.2 |

**Confidence on the percentage takes: medium.** These are reported figures from
secondary sources and marketplace terms change; verify against each provider agreement
before signing anything.

### 3.3 Due diligence, and the wall Nabbly hits

Buyers run a structured process, and there are three gates. Nabbly currently fails two
and a half of them.

**Gate 1: history.** This is the killer. Quants require **at least five years** for
backtesting at the depth they want. Under **two to three years** makes systematic
validation difficult ([The TRADE](https://www.thetradenews.com/thought-leadership/challenges-of-backtesting-alternative-data/),
[vBase](https://www.vbase.com/alternative-data/)). Nabbly has **37 days.** With 21-day
retention on the live board, even the raw record is short unless snapshots are archived.
**Confidence: high.** This is stated consistently everywhere and is the standard answer
from every data-sourcing team.

**Gate 2: provenance and legality.** Investment advisers must document that scraped data
was lawfully obtained, and the SEC has said explicitly that relying on a vendor's bare
representation is inadequate; buyers must understand the *basis* for the representation
and file supporting documentation
([Lowenstein Sandler](https://www.lowenstein.com/news-insights/publications/articles/key-considerations-for-alternative-data-and-ai-vendors-to-investment-firms-demonstrating-compliance-in-the-face-of-an-evolving-regulatory-environment),
[Akin](https://www.akingump.com/en/insights/alerts/sec-division-of-examinations-finally-speaks-on-alternative-data),
[SEC risk alert](https://www.sec.gov/files/code-ethics-risk-alert.pdf)).
Vendors are expected to have a standing Due Diligence Questionnaire and be able to
explain **every** source and the contractual rights around it. Read that sentence
against Nabbly's rule never to name sources publicly. See section 8.

**Gate 3: point-in-time correctness and stability.** Buyers need to know what the data
said on a given day, not what it says now after corrections. If Nabbly's board reclassifies
a field or changes its scraping cadence, the series breaks and the backtest is worthless.
This is a solvable engineering matter and it is worth solving now, cheaply, as part of 3.5.

**Gate 3 also has a hidden edge**: 21-day retention is a *product* decision that acts as
a *data* decision. It caps the observable lifetime of a gig at 21 days, which means
Nabbly can never measure how long a posting truly stays open. Snapshot the disappearance
events too; time-to-disappear is a genuinely interesting derived metric and nobody
publishes it for freelance work.

### 3.4 What Nabbly could realistically earn, and when

| Horizon | Channel | Realistic annual revenue | Confidence |
|---|---|---|---|
| Now (0 to 6 months) | Any data sale | **$0** | High |
| 6 to 12 months | Dewey academic listing | $0 to $5k, plus citations | Medium |
| 6 to 12 months | Co-branded report with an edtech or freelancer tool | $0 to $15k, mostly in kind | Low |
| 12 to 24 months | Datarade listing, inbound only | $0 to $25k | Low |
| 24 to 36 months | HR analytics vendor supplement feed | $20k to $80k | Low |
| 36 months+, only if much bigger | Capital markets, via a broker | $50k to $250k for a niche dataset | Low |

Set against sector benchmarks: the average alt-data buyer pays around $80k per dataset
across roughly 20 datasets ([Hedgeweek](https://www.hedgeweek.com/hedge-fund-alt-data-spending-set-to-surge-says-new-research/)),
processed data feeds commonly run $10k to $100k a year, and only category-defining sets
clear the high six figures.

**The blunt comparison**: Nabbly's Pro tier is $12/mo. The realistic 24-month data
revenue of $20k to $80k equals roughly 140 to 550 Pro subscribers. Building 140 to 550
subscribers is a known problem with a known playbook. Building a saleable data business
is a three-year detour with a low hit rate. **The data's job is to help acquire those
subscribers, not to replace them.**

### 3.5 The one thing to do this week

Archiving. Concretely:

1. **Daily aggregate snapshot, append-only, never mutated.** One row per field per day:
   date, field, live count, new-in-last-24h count, median and quartile budget where a
   budget was stated, share with a stated budget, remote/onsite/hybrid split, urgency
   flag share, size-tier mix. That is roughly 24 rows a day, which is nothing.
2. **Skill token counts.** Daily counts of a controlled vocabulary of skill terms
   appearing in postings per field. A controlled list beats free extraction because it
   stays comparable over time.
3. **Disappearance events.** When a gig leaves the board, record whether it aged out at
   21 days or vanished earlier. Early disappearance is the closest available proxy for
   "filled".
4. **Freeze the definitions and version them.** Write down what "Development / tech"
   includes today, and never silently change it. When it changes, bump a version number
   and keep both. This is the single discipline that separates a dataset from a pile.
5. **Store it somewhere boring and durable.** Daily Parquet or CSV to object storage,
   plus a copy in a private git repo. Cost: a few dollars a month.

Estimated effort: one to two days. Estimated value: it is the entire difference between
having a data asset in 2028 and not having one. **Confidence: high.**

---

## 4. The legal and ethical line

**Again: I am not a lawyer. This is a research summary, not advice.** But the shape of
the law here is unusually clear in a few places and unusually unclear in others, and
knowing which is which is most of the value.

### 4.1 The one distinction everything hangs on

**Republishing listings is legally hot. Publishing derived aggregate statistics is
substantially cooler.**

Under US law this follows from *Feist Publications v. Rural Telephone Service*,
499 U.S. 340 (1991)
([Justia](https://supreme.justia.com/cases/federal/us/499/340/)). The Supreme Court held
that facts are not copyrightable, and explicitly rejected the "sweat of the brow"
doctrine: no amount of labour in compiling facts creates a copyright in them. Copyright
extends only to an original *selection or arrangement*, and only to that selection or
arrangement, not to the underlying facts.

Applied to Nabbly:

- "There are 9,238 live development gigs and 4,990 arrived this week" is a **fact Nabbly
  measured**. It is not any source's expression. Nobody's copyright covers it.
- "Median stated budget for design gigs is $X" is a **statistic Nabbly computed**.
  Likewise.
- "Here is the full text of this posting from board Y" is **someone else's expression**,
  reproduced, and is where every legal problem in this document lives.

This is why section 5 recommends publishing statistics and section 4.5 recommends never
publishing listings. It is not a stylistic preference; it is the actual legal fault line.

**Settled: high confidence.** Facts and independently computed statistics are not
protected by US copyright. That part is not contested.

### 4.2 What is settled on scraping, and what is not

**Settled (US, and reasonably firm):**

- **The CFAA does not criminalise scraping public web pages.** *Van Buren v. United
  States* (2021) adopted the narrow "gates up or down" reading of "exceeds authorized
  access" ([Wikipedia](https://en.wikipedia.org/wiki/Van_Buren_v._United_States),
  [Nixon Peabody](https://www.nixonpeabody.com/insights/alerts/2021/06/10/van-buren-cfaa-ruling)).
  The Ninth Circuit then confirmed in *hiQ Labs v. LinkedIn*, 938 F.3d 985, on remand
  April 2022, that "without authorization" does not apply to public websites
  ([Justia](https://law.justia.com/cases/federal/appellate-courts/ca9/17-16783/17-16783-2022-04-18.html),
  [Fenwick](https://www.fenwick.com/insights/publications/hiq-labs-scrapes-by-again-the-ninth-circuit-reaffirms-that-data-scraping-does-not-violate-the-cfaa-1)).
  **Confidence: high.**

**Contested, and this is the part people get wrong:**

- **hiQ still lost.** This is the detail that almost every "scraping is legal now"
  summary omits. In December 2022 hiQ and LinkedIn settled with a **$500,000 judgment
  against hiQ**, an admission of liability under California common law trespass to
  chattels and misappropriation, spoliation sanctions, and a **permanent injunction
  requiring hiQ to stop scraping and delete all source code, data and algorithms**
  derived from LinkedIn
  ([Morgan Lewis](https://www.morganlewis.com/blogs/sourcingatmorganlewis/2022/12/linkedin-v-hiq-landmark-data-scraping-suit-provides-guidance-to-data-scrapers-and-web-operators),
  [Privacy World](https://www.privacyworld.blog/2022/12/linkedins-data-scraping-battle-with-hiq-labs-ends-with-proposed-judgment/),
  [ZwillGen](https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/)).
  hiQ won the CFAA question and was destroyed by contract and tort claims. **The lesson
  is that CFAA immunity is close to worthless on its own.** **Confidence: high.**

- **The contract question turns on whether you agreed to the terms.** *Meta Platforms v.
  Bright Data* (N.D. Cal., Judge Chen, January 2024) held that Meta's terms **did not
  prohibit logged-off scraping of publicly available data**, because Bright Data was not
  a "user" while logged out and therefore not bound. A factor that carried real weight
  was that Meta had removed 2009-era language binding all visitors, not just users.
  Meta dropped the case a month later
  ([Quinn Emanuel](https://www.quinnemanuel.com/the-firm/news-events/client-alert-meta-v-bright-data-significant-decision-for-web-scraping-industry/),
  [Farella Braun + Martel](https://www.fbm.com/publications/major-decision-affects-law-of-scraping-and-online-data-collection-meta-platforms-v-bright-data/),
  [Lowenstein](https://www.lowenstein.com/news-insights/publications/client-alerts/meta-v-bright-data-ruling-has-important-implications-for-webscraping-activities-by-investment-advisers-im)).
  One district court, not binding precedent, and it turned on the specific wording of
  Meta's terms. **Confidence: high that this is what the court held. Low that it
  generalises to any other site's terms.**

**The practical rule that falls out of hiQ + Bright Data**, and which Nabbly should
treat as an operating policy:

1. Do not create an account, and do not log in, to collect anything.
2. Do not click through or otherwise accept any terms.
3. Do not use an API key whose terms restrict what you may do with the output, unless
   you intend to comply with those terms exactly.
4. Respect robots.txt and rate limits, and identify the crawler honestly.
5. Stop immediately on a cease and desist, and keep the correspondence.

Number 3 is the one Nabbly is most likely to be violating right now, and number 1 is
the one that matters most for the subreddits.

### 4.3 Europe: the case that is literally about job listings

The EU position is different and there is a CJEU judgment **directly on Nabbly's exact
business model.**

***CV-Online Latvia SIA v Melons SIA*, C-762/19, 3 June 2021**
([EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62019CA0762),
[ipcuria](https://ipcuria.eu/case?reference=C-762%2F19),
[Bird & Bird analysis](https://www.twobirds.com/en/insights/2021/uk/cv-online-latvia-cjeu-complicates-the-enforcement-of-database-rights)).

CV-Online ran a Latvian job board. Melons ran KurDarbs.lv, a **search engine
specialising in employment notices that let job seekers search across several job
listing websites at once.** That is Nabbly, in 2019, in Latvia.

The Court held that a specialised search engine which copies and indexes the whole or a
substantial part of a freely accessible database **is** "extracting" and "re-utilising"
under Article 7 of the Database Directive (96/9/EC), and the database maker **may
prohibit it**, but only where those acts **adversely affect the maker's investment** in
obtaining, verifying or presenting the content.

Two things follow:

- **The bad news**: the sui generis database right applies to Nabbly's activity in the
  EU if a source board can show substantial investment in obtaining, verifying or
  presenting its listings, which most established boards can.
- **The good news, and it is real**: the Court added the harm requirement, which
  commentators noted **complicates enforcement** for database owners. A claimant must
  show a risk to redeeming its investment, not merely that copying occurred. It also
  reflects a competition-law sensitivity: the Court did not want database rights used to
  shut out aggregators that add value for users.

**Confidence: high on the holding. Medium on how a court would apply the harm test to
Nabbly specifically**, which will turn on whether Nabbly links traffic back to sources
(helping them) or substitutes for them (harming them). **This is a design decision with
legal consequences: linking out to the original posting is both the honest thing and
the legally safer thing.**

**And then the trap**: ***Ryanair Ltd v PR Aviation BV*, C-30/14, 15 January 2015**
([EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A62014CJ0030),
[Kluwer Copyright Blog](https://legalblogs.wolterskluwer.com/copyright-blog/ryanair-ltd-v-pr-aviation-bv-contracts-rights-and-users-in-a-low-cost-database-law/),
[Gowling WLG](https://gowlingwlg.com/en/insights-resources/articles/2015/ryanair-flying-high-at-the-cjeu/)).
PR Aviation screen-scraped Ryanair flight data for a comparison site. The Court held
that where a database does **not** qualify for Directive protection, the Directive's
user-protection provisions do not apply either, so **contract terms prohibiting
scraping are fully enforceable.** The perverse result, noted by every commentator: **a
database owner with no IP rights at all may end up with broader control, via contract,
than one with database rights.** **Confidence: high.**

Combined EU rule of thumb: **the terms of service are the real risk, not the database
right.** Which is exactly the same conclusion as hiQ, from the opposite direction. On
both continents, the case law converges on: contracts bind, and public facts do not.

### 4.4 The subreddit problem, which is the most serious thing in this document

Nabbly watches subreddits. This is materially riskier than watching job boards, and I
do not think it is currently priced in.

- Reddit's User Agreement prohibits accessing, searching or collecting data by automated
  means absent a separate agreement. Commercial use of the Reddit API requires a
  **separately negotiated commercial licence**, billed publicly at around $0.24 per
  1,000 API calls, and the standard terms prohibit using Reddit data in commercial
  products or for commercial redistribution at scale. Reddit's May 2026 policy
  clarification named unauthorised scraping as a Rule 8 violation and it is now enforced
  technically with 403 lockouts
  ([Prowlo summary of the Data API terms](https://prowlo.com/blog/reddit-data-api),
  [redditapis analysis](https://www.redditapis.com/blogs/is-scraping-reddit-legal-2026)).
  **Confidence: medium-high.** I could not fetch redditinc.com directly; verify against
  the primary terms at redditinc.com/policies/data-api-terms before acting.
- Reddit is litigating aggressively. It sued Anthropic in June 2025, and in October 2025
  sued Perplexity, SerpApi, Oxylabs and AWMProxy over what it called industrial-scale
  scraping obtained **indirectly via Google search results**
  ([CNBC](https://www.cnbc.com/2025/10/23/reddit-user-data-battle-ai-industry-sues-perplexity-scraping-posts-openai-chatgpt-google-gemini-lawsuit.html),
  [Search Engine Land](https://searchengineland.com/reddit-sues-perplexity-serpapi-scraping-google-463681)).
  **Note the SerpApi defendant carefully.** Reddit is going after the *intermediaries*
  and the *indirect* collectors, not only the end users. A small aggregator is exactly
  the profile of the second wave, and the theory does not require you to have touched
  reddit.com directly. **Confidence: high on the filings.**

**What I would do, in order:**

1. Establish precisely how Nabbly obtains subreddit content today: official API with a
   key, unauthenticated scrape, RSS, a third-party intermediary, or logged in. **Each
   has a different answer and the difference is large.** If any collection happens while
   logged in to a Reddit account, that is the highest-risk configuration in the whole
   pipeline, because the Bright Data logged-off defence evaporates.
2. Recognise that **Reddit is likely the source that cannot survive a data-licensing
   deal**, and possibly not a commercial product either. That is a product question, not
   just a legal one.
3. Consider whether the subreddit intake earns its risk. If subreddits contribute a
   small share of the roughly 4,200 daily gigs, the risk-adjusted answer may be to drop
   them. If they contribute the distinctive gigs nobody else has, the answer is a paid
   commercial licence, which is affordable at Nabbly's volumes: even 1 million calls a
   month is around $240.
4. **Never include Reddit-derived data in anything sold or licensed to a third party,**
   and never in an academic dataset, without a commercial licence in hand.

I want to be careful not to overstate: I found no case of Reddit suing a small job
aggregator, and none of this is a prediction that Nabbly will be sued. The point is
narrower and firmer. **The moment Nabbly tries to sell or license data, a buyer's due
diligence will ask exactly this question, and "some of it comes from subreddits" is an
answer that ends the conversation.** That is a commercial fact regardless of the legal
outcome.

### 4.5 Attribution terms, and the honest reading

The handoff already documents that RemoteOK's API terms ask for credit and a canonical
URL wherever listings are republished, and that this is the norm in the category
(GOOGLE-JOBS.md). Himalayas states the same expectation publicly: anyone may use the
API, but should link back to the URL found on Himalayas and mention Himalayas as the
original source
([Himalayas API](https://himalayas.app/api),
[docs](https://himalayas.app/docs/remote-jobs-api)).

Read carefully, **those terms are about republishing listings.** They are not obviously
triggered by publishing a statistic that no listing appears in. "The median stated
budget across development gigs was $X" contains no listing, no employer, no title and no
text from any source. Under *Feist* it is a fact Nabbly computed.

That said, two honest caveats:

- Some API terms restrict **derived works** or **any commercial use of the output**, not
  just republication. Those clauses would reach aggregate statistics. Every source's
  terms need reading individually against this specific question: *may I publish
  aggregate statistics derived from this feed?*
- In the EU, *Ryanair* means accepted terms bind regardless of whether database rights
  exist. If Nabbly clicked through or accepted terms to obtain an API key, those terms
  govern. **This is why the API-key sources are, counterintuitively, the legally
  constrained ones and the public logged-out pages are the free ones.**

**The practical output**: build a one-page internal source register listing, per source,
the collection method, whether terms were accepted, whether attribution is required,
whether derived works are restricted, and whether commercial use is restricted. It stays
internal, so it does not conflict with the no-naming rule. It is also **exactly the
document a Dewey listing or any future buyer will ask for**, and it takes an afternoon.

### 4.6 What is settled and what is contested, in one table

| Question | Status | Confidence |
|---|---|---|
| Are facts and computed statistics copyrightable in the US? | **Settled: no** (*Feist*) | High |
| Does scraping public pages violate the CFAA? | **Settled: no** (*Van Buren*, *hiQ* 9th Cir. 2022) | High |
| Does CFAA immunity protect you? | **Settled: no.** hiQ paid $500k and was enjoined on contract and tort grounds | High |
| Do ToS bind a logged-out, non-account scraper? | **Contested.** *Bright Data* said no on Meta's specific wording. One district court | Medium |
| Do EU database rights reach a job aggregator? | **Settled: yes in principle** (*CV-Online*), but only with proven harm to investment | High on holding, medium on application |
| Do contract terms bind even without database rights, in the EU? | **Settled: yes** (*Ryanair*) | High |
| Can Nabbly publish derived aggregate statistics? | **Very likely yes**, subject to per-source derived-works clauses | Medium-high |
| Can Nabbly republish listings at scale? | **No.** Already the settled internal answer (GOOGLE-JOBS.md), and the law agrees | High |
| Is the subreddit intake safe to commercialise? | **Likely not without a licence** | Medium-high |

### 4.7 The ethical line, separate from the legal one

Three things that are probably legal and that I would still not do:

1. **Do not publish anything that identifies an individual poster or a small employer.**
   A subreddit post is written by a person who did not expect to be a data point. Fields,
   bands and counts only. Never a quote, never a username, never a company small enough
   to be identified by its combination of attributes.
2. **Do not publish a statistic granular enough to reconstruct a source's inventory.**
   "Design gigs on the board: 3,639" is fine. Anything sliced finely enough that a
   source board could work out how much of its own catalogue Nabbly holds is both a
   business risk and the thing most likely to trigger a *CV-Online* harm argument.
3. **Do not let the data be used against the people who generate it.** Selling
   freelance rate data to staffing firms who use it to push rates down is a legitimate
   business and it is also directly adverse to Nabbly's own users. Nabbly's users are
   freelancers. Publishing rate bands **to freelancers** raises their floor. Selling the
   same data **to buyers of freelance labour** lowers it. Same data, opposite effect.
   Pick a side early and write it down, because the second cheque will make it harder.

---

## 5. The better play: data as marketing

### 5.1 Why this is the recommendation

Nabbly's actual problem is not monetising data. It is that the site has one organic
signup and no search traffic. Data is the fastest known fix for that specific problem,
for four reasons:

- **Original data is the top-performing digital PR format.** Over 90% of digital PR
  campaigns use data-led content or expert commentary, journalists are reported to be
  around 3.2x more likely to cite unique research, and data studies keep attracting
  editorial links for years after publication
  ([Search Engine Journal](https://www.searchenginejournal.com/achieving-links-that-matter-how-to-use-research-and-data-driven-journalism/474956/),
  [Siege Media](https://www.siegemedia.com/marketing/digital-pr-link-building),
  [Digital Applied](https://www.digitalapplied.com/blog/link-building-2026-digital-pr-outreach-guide)).
  **Confidence: medium** on the specific multipliers, which come from agency sources
  with an interest; **high** on the direction.
- **Nabbly's marginal cost is near zero.** Typical data campaigns cost $3,000 to $5,000
  because they are commissioned surveys, generating a reported 60 to 150 referring
  domains over 90 days. Nabbly's data already exists. **It gets the output of a $4,000
  campaign for the cost of a SQL query and a writeup.** That is a genuine structural
  advantage and it is being wasted every week it is not used.
- **Ahrefs' most-linked asset is a data study** with over 3,500 referring domains
  ([BuzzStream](https://www.buzzstream.com/blog/bootstrap-link-building-analysis/)), and
  data, stats and reports are their primary link acquisition method.
- **It compounds into the data asset from section 3.** Every published report is a
  timestamped public record of the series, which is free credibility for a future
  academic or commercial listing. The marketing play and the option value are the same
  work.

### 5.2 What actually makes a data report get picked up

From the Ashby, Gusto, Levels.fyi, Fiverr and Hiring Lab patterns above:

1. **One number, not twelve.** HR Dive took a single figure from a report of hundreds.
   Write the headline number first and build the report to support it.
2. **A level, a change, and a baseline.** "56.7 days, up 37% since 2022" travels.
   "Hiring is slower" does not.
3. **Name the index.** Gusto's New Hires Pay Index has a name, so it has a value, so it
   can change, so it is news again next month. An unnamed chart is news once.
4. **A stable cadence.** Monthly or quarterly, on a predictable date, forever. Journalists
   build a mental slot for recurring releases. The second edition is worth more than the
   first, and the sixth is worth more than the first five.
5. **Publish the numbers, not just the prose.** Hiring Lab puts the series on GitHub.
   A downloadable CSV converts a reader into a citer.
6. **A method note.** Not a source list. A method note: what was counted, over what
   period, what was excluded, and what the number does not mean.
7. **A named human.** Reporters need someone to quote. That means a founder byline and a
   real press email.
8. **Charts sized for screenshots.** Legible at 600px wide, with the source and date
   burned into the image, because the image will travel without the page.
9. **Honest limitations, stated by you.** Say what the data cannot show. It is the
   cheapest credibility available and it pre-empts the criticism.

### 5.3 The five products

All names fit the Nabbly vocabulary from FEEL.md (gigs, board, fields), avoid em dashes,
and avoid any claim that requires naming a source. All headline claims below are
**templates**, not assertions. Every number must be computed and true at publication.

---

#### 1. The Nabbly Demand Index

- **Cadence**: monthly, published the first Tuesday.
- **What it is**: each field's share of the board, and its change against the prior
  month and against the index baseline month. One named number: the Demand Index,
  which is total new gigs per day indexed to 100 at the baseline month.
- **Headline template**: "Freelance demand in [field] rose X% in [month], the fastest
  move on the board." Or on a flat month, which is also a story: "Freelance demand held
  flat in [month] while [field] fell for the third month running."
- **Why it works**: it is Fiverr's Business Trends Index applied to demand across the
  whole open market rather than one marketplace's inventory. Fiverr can only see Fiverr.
  **Nabbly can see across the market, and that is a genuinely better claim.**
- **Who covers it**: HR Dive, HR Brew, Fast Company, Quartz, Sifted, Business Insider,
  and trade press per field on the standout mover.
- **SEO target**: "freelance job market trends", "freelance demand [year]", "is
  freelancing growing".
- **Earliest possible**: needs one prior month. **First edition: early October 2026.**
- **Confidence it earns links**: medium-high after three or four editions. Low for the
  first one, and that is normal. Publish anyway; the sixth edition is the product.

---

#### 2. Rate Bands

- **Cadence**: quarterly.
- **What it is**: for each field, the distribution of budgets actually quoted in
  postings. Quartiles, not averages. Plus the share of postings that state a budget at
  all, which is itself a finding nobody publishes.
- **Headline template**: "Half of [field] gigs posted this quarter quoted between $X and
  $Y." And the more provocative one: "Only X% of freelance postings say what they pay."
- **Why this is the strongest of the five**: every existing rate guide is either a survey
  ("what freelancers say they charge", which is aspirational) or platform data
  ("what Upwork contracts settle at", which is one marketplace with its own selection
  effects). **Nabbly measures what clients are actually offering, in the open market,
  before negotiation.** That is a different and unoccupied measurement. It is also the
  most commercially useful number Nabbly could publish, and it feeds the Pro tier's
  market-rates feature directly.
- **Who covers it**: Fast Company, Business Insider, The Hustle, Creative Bloq,
  Marketing Brew, Freelancers Union, and near-certain pickup on r/freelance and Hacker
  News.
- **SEO target**: the highest-intent commercial queries Nabbly can reach.
  "freelance [field] rates", "how much to charge for [work]", "[field] freelance hourly
  rate 2026". These are queries with genuine purchase intent, and a permanently updated
  page beats a 2023 blog post.
- **Caveat to state honestly in the report**: stated budgets are what clients offer, not
  what freelancers accept. Say so, in the report, every time. It costs nothing and it is
  the difference between being cited and being picked apart.
- **Earliest possible**: **immediately**, as a launch edition with no comparison period.
  This is the one to publish first, in September 2026.
- **Confidence: high** that this earns links and search traffic. It is the best single
  idea in this document after the archiving.

---

#### 3. Skills on the Board

- **Cadence**: monthly, or quarterly if monthly is too thin.
- **What it is**: which named skills and tools appear in postings, and how the counts
  moved. Controlled vocabulary, counted consistently.
- **Headline template**: "[Tool] appeared in X% of development gigs this month, up from
  Y% in [month]." And the annual version: "The ten fastest-growing skills in freelance
  postings."
- **Why it works**: it is the most reliably picked-up format in this whole category
  because it maps to a decision a reader is making right now, which is what to learn
  next. It is also the format edtech partners in section 2.5 want most.
- **Who covers it**: InfoWorld, The Register, TechCrunch and dev newsletters for the
  tech cut; Marketing Brew and Search Engine Land for the marketing cut; Creative Bloq
  for design. Newsletter syndication (TLDR, Pointer, Dense Discovery) is realistic here
  and cheap to pitch.
- **SEO target**: "most in demand freelance skills", "what skills should I learn
  freelance", "[tool] freelance jobs".
- **Earliest possible**: needs two months. **First edition: November 2026.**
- **Confidence: medium-high.**

---

#### 4. The AI Line

- **Cadence**: quarterly.
- **What it is**: the share of postings in each field that mention AI tools or AI work,
  and whether AI-adjacent gigs quote higher budgets than their field's median.
- **Headline template**: "AI now appears in X% of freelance postings, up from Y% last
  quarter." And the one that gets the most coverage: "Gigs mentioning AI quoted budgets
  X% above their field median."
- **Why it works**: this is the single most-covered business story of 2026 and every
  outlet needs new numbers on it. Upwork's entire 2026 index was built on this angle and
  Fiverr's index leads with AI category growth
  ([Upwork](https://investors.upwork.com/news-releases/news-release-details/upworks-future-workforce-index-2026-how-ai-redefining-value-work),
  [Fiverr](https://www.fiverr.com/resources/guides/reports/business-trends-index-june-2026)).
  Nabbly's differentiator is again the cross-market view rather than one marketplace's
  inventory.
- **The angle only Nabbly has**: the *displacement* cut. Which fields' posting volumes
  are falling while AI mentions in that field rise. That is a genuinely newsworthy and
  genuinely uncomfortable finding, and if Nabbly finds it, it should publish it honestly
  rather than spinning it. **Note: this must be handled with care.** Posting-volume
  changes have many causes, and an overclaimed displacement story would be both wrong
  and, given the audience is freelancers, unkind. State it as an observed correlation in
  a five-month window and say plainly that it is not evidence of causation.
- **Who covers it**: essentially everyone. Business Insider, Fast Company, Axios, HR
  Dive, The Verge, plus every AI newsletter.
- **SEO target**: "is AI replacing freelancers", "AI freelance jobs", "AI impact on
  freelance work".
- **Earliest possible**: **immediately** for the level, one quarter for the trend.
- **Confidence: high** on pickup, **medium** on whether Nabbly's five-week window
  supports a defensible trend claim in the first edition. Publish the level first, wait
  for the trend.

---

#### 5. First Hour

- **Cadence**: twice a year, or as an evergreen page updated quarterly.
- **What it is**: the timing report. When gigs actually get posted, by hour and by day
  of week, by field. How long a gig stays on the board before it disappears. How much
  of a week's volume arrives in its busiest six hours.
- **Headline template**: "X% of freelance gigs are posted between [hour] and [hour]."
  "The average [field] gig disappears within X hours of going up."
- **Why this is the most defensible of the five**: **nobody else can produce this
  number.** Lightcast, Revelio and LinkUp all measure stock and flow at daily or weekly
  granularity. Continuous monitoring across many sources with minute-level arrival times
  is the specific thing Nabbly's architecture does and theirs does not. It is also
  perfectly on-message: Nabbly's entire pitch is speed, and this report is speed,
  quantified.
- **The honesty constraint**: "disappears from the board" is not "filled". Nabbly's
  21-day retention and source behaviour both affect it. **Say exactly that in the
  report.** Report it as time-to-disappear and define it precisely. Do not let a
  journalist turn it into "filled within X hours" without correcting them.
- **Who covers it**: Lifehacker, Fast Company, HR Brew, career and productivity
  newsletters, and it is the most socially shareable of the five.
- **SEO target**: "best time to apply for freelance jobs", "how fast do freelance jobs
  get filled", "when are jobs posted".
- **Earliest possible**: **immediately.** Nabbly has five weeks of arrival timestamps,
  and time-of-day patterns are stable enough that five weeks is genuinely sufficient for
  the hour-of-day cut. Say the window in the method note.
- **Confidence: high** that this is uniquely Nabbly's, **medium-high** on pickup.

---

#### 5.4 A sixth, cheap and fast: the survey

Bullhorn's GRID has run for sixteen years on roughly 2,300 survey responses, and
Upwork's headline 2026 finding came from 2,400 respondents. **A survey does not require
history.** Nabbly could run one this month, and the natural version is a survey of its
own free-tier list and the freelance subreddits it already understands. The pairing is
the interesting part: "freelancers say they charge X, and postings actually offer Y."
That gap is a story, and it is one only a company holding both sides can tell.
**Confidence: medium.** The constraint is that Nabbly's list is currently tiny, so this
is a 6-month item, after the reports have built a list.

### 5.5 The publishing mechanics

- Put everything under **nabbly.co/data/**, a permanent hub, styled to FEEL.md. This
  becomes the link target, and it is the page journalists bookmark.
- Every report gets a permanent URL that is **updated in place**, not replaced. The
  Demand Index lives at /data/demand-index/ forever, with an archive of prior editions.
  Links accumulate on one URL instead of scattering.
- **Publish the CSV.** Hiring Lab's GitHub repos are the model. A public repo at
  github.com/nabbly with the monthly series costs nothing and turns readers into citers.
  It also creates a public, timestamped record of the series, which is section 3.5's
  archiving requirement doing double duty.
- **Numbers on the report pages are as-of-date stamped, not live.** This satisfies
  FEEL.md's "true at all times" rule cleanly: a stamped historical figure stays true
  forever, where a live count on a static page does not.
- Email capture on every report, Ashby-style: "get the next one".
- A press email and a one-paragraph founder bio. Get listed on Muck Rack.

### 5.6 Realistic outcome

**Confidence: medium.** For a domain with no authority, publishing five recurring
products consistently for twelve months:

- First edition: 0 to 5 referring domains. Expect near silence, and do not read it as
  failure.
- By edition four to six: 10 to 40 referring domains per release if the numbers are
  genuinely novel, which Rate Bands and First Hour are.
- Twelve months in: 100 to 300 referring domains cumulatively, one or two tier-one
  pickups, and a small number of pages ranking for high-intent commercial queries.
- The realistic best case is one report going properly wide, which is worth more than
  the other eleven combined. Rate Bands and The AI Line are the two candidates.

This is not fast. It is, however, roughly the only reliable route from zero domain
authority to a ranking site that does not involve buying links, and it uses an asset
Nabbly already owns and currently throws away every 21 days.

---

## 6. Partnerships and integrations, without selling anything

### 6.1 Freelancer tooling: the demand layer inside someone else's product

The pitch is not "buy our data". It is: **you have freelancers in your product every
day and nothing to tell them about the market. We do. Put a small live panel in your
app, we both get attribution.**

| Company | Why they want it | Route in |
|---|---|---|
| **Bonsai** ([hellobonsai.com](https://agiled.app/blog/software-for-freelancers), $9 to $49/user/mo) | Contracts, proposals and invoicing. Their users set a rate inside the product and have nothing to check it against. Rate Bands solves that at the exact moment of need | Partnerships or content lead |
| **Moxie** ($10 to $32/mo) | Same, smaller, hungrier, and far more likely to say yes to a small partner | Founder to founder |
| **Indy** (free tier with 3 proposals/contracts/invoices) | Free-tier users are early-career freelancers, the exact audience for demand data | Founder to founder |
| **HoneyBook** ($29 to $109/mo) | Creative services heavy, matching Nabbly's design, video and photography fields | Partnerships team |
| **FreshBooks / Wave** | Larger, slower, more process. Wave's free tier reaches the widest freelancer base | Long shot, worth one email |

**The ask, in order of ambition**: (1) a co-published blog post using Nabbly's rate
bands with a link, (2) a newsletter swap, (3) an embedded widget or API panel showing
live demand in the user's field, (4) a bundle where their paying users get Nabbly Pro at
a discount.

Start at (1). It costs both parties an afternoon, and it is how (3) eventually happens.
**Confidence: medium-high** that several of these say yes to (1), **low** on (3) inside
twelve months.

### 6.2 Payments and contractor platforms

**Deel**, **Wise**, **Payoneer**, **Remote.com**. All publish content aimed at
contractors and all are competing on being the contractor's default account
([Deel comparison](https://www.deel.com/blog/best-global-payment-tools-for-contractors/),
[EOR HQ comparison](https://eorhq.com/guides/wise-vs-payoneer-vs-deel-vs-remote-contractor-payments/)).

They want the same thing Nabbly wants: to be useful to freelancers before the freelancer
has money to move. **The geographic cut of Nabbly's data is what they specifically
want**, because cross-border demand is their entire business model. "Which countries are
posting the most remote gigs" is a chart Deel's content team would take today.

Realistic ask: a co-published geographic report and a link. Deel and Payoneer both run
large content operations with a real appetite for partner data.
**Confidence: medium.** These are big companies with slow partnership processes, but
their *content* teams move fast and are the right door.

### 6.3 Complementary, non-competing API licensing

The rule: license to anyone who serves freelancers but does not aggregate gigs.
Portfolio hosts (**Contra**, **Read.cv** successors, **Dribbble**, **Behance**), time
trackers (**Toggl**, **Harvest**, **Clockify**), and community platforms.

Notably, **Contra** appears to have no recurring data product of its own, and it is
positioned as a commission-free freelance platform rather than a job aggregator. That
makes it complementary rather than competing, and a plausible co-publishing partner
rather than a rival. **Confidence: medium**, based on absence of a visible data product
in search.

### 6.4 The credibility partner, which is the highest-leverage relationship available

**ADP borrowed Stanford. Nabbly should borrow a university too.**

One labour economist or one PhD student, given free access to the archived aggregate
series in exchange for co-authoring the methodology note on the Demand Index. Cost:
zero. Value: the index stops being a startup's chart and becomes a jointly documented
measure, which is precisely the difference between a report journalists ignore and one
they cite.

Concrete targets: the **WFH Research** group around Nick Bloom
([wfhresearch.com](https://wfhresearch.com/research-and-policy/)), who already combine
surveys with job posting evidence and whose Flex Index collaboration shows an appetite
for private data partners; **Scoop's Flex Index** directly
([Forbes writeup](https://www.forbes.com/sites/jenamcgregor/2023/02/07/a-new-flex-index-is-collecting-companies-remote-work-policies-in-one-searchable-tool/));
and any labour economics department with a working paper on gig work. The approach is a
short email offering data, not asking for anything, with a link to the first published
report.

**Do this after the first two reports exist**, so there is something to point at.
**Confidence: medium** on getting a response, **high** on the value if one lands.

### 6.5 Affiliate and referral, briefly

Freelance tool affiliate programmes (Bonsai, FreshBooks, Deel) pay real commissions, and
a freelancer who just found a gig on Nabbly is at a natural moment to need a contract or
an invoice. This is legitimate revenue and it fits the product. **The caution from the
Stackyard work applies here**: verify each programme's actual policy on aggregator and
directory sites before building anything around it, since aggregator-style sites are
frequently excluded by affiliate networks even when the category looks like a match.
That lesson cost a rejection once already. **Confidence: medium** that several
programmes accept Nabbly; **high** that at least one will reject it on aggregator
grounds, so do not build a revenue plan on a single programme.

---

## 7. Sequenced, with honest costs

### Do now (weeks 0 to 8, five weeks of data)

| Action | Effort | Cost | Why now |
|---|---|---|---|
| **Start daily aggregate archiving** (3.5) | 1 to 2 days | ~$5/mo storage | Cannot be back-filled. Nothing else on this list is time-sensitive; this one is |
| **Freeze and version field definitions** | 2 hours | $0 | Makes the archive comparable to itself later |
| **Build the internal source register** (4.5) | Half a day | $0 | Answers the provenance question before anyone asks it, and it stays private |
| **Resolve the subreddit collection question** (4.4) | Half a day, plus a lawyer hour | ~$300 to $600 for one hour of counsel | The largest unpriced risk in the business |
| **Publish Rate Bands, launch edition** | 2 to 3 days | $0 | Best single report. Publishable today with no comparison period |
| **Publish First Hour** | 2 days | $0 | Uniquely Nabbly's, and five weeks is genuinely enough for hour-of-day |
| **Build nabbly.co/data/ and a press email** | 1 day | $0 | The permanent link target |
| **Map 24 fields to SOC/O*NET codes** | 2 days | $0 | Multiplies the data's value to every party in section 2 |

Total: roughly two weeks of work, under $1,000 including a lawyer hour.

**Explicitly do not do now**: contact any hedge fund, list on any commercial data
marketplace, or attend any alt-data event. It is not close.

### Do at 6 to 12 months of data

- Launch the **Nabbly Demand Index** monthly and **Skills on the Board** monthly.
- Publish **The AI Line** quarterly with a real trend rather than a level.
- **Apply to Dewey Data as an academic data partner** (2.2). Highest expected value of
  anything in section 2.
- Approach the **WFH Research / Flex Index** circle with a methodology co-author offer.
- Free **Datarade** listing as a passive lead capture.
- Co-published reports with two or three freelancer tools (6.1).
- Run the **survey** (5.4) against a list that by then exists.
- Public **GitHub repo** of the monthly series.

### Only if the company gets much bigger (2 to 3 years, and only with the archive intact)

- Commercial data licensing to HR analytics vendors as a freelance-segment supplement.
- A serious conversation with Eagle Alpha or a BattleFin Discovery Day, at which point
  the history requirement is met and the provenance register has three years of entries.
- Capital markets, and only with counsel, a full DDQ, a resolved subreddit position, and
  a ticker-mapping story that does not currently exist.

**Note what makes the third tier possible**: it is entirely gated on the first tier's
archiving item. Two days of work now is the option on everything in it. That is the
single highest leverage ratio in this document.

---

## 8. Conflicts with the standing rules, flagged explicitly

The brief asked for these to be named rather than routed around. Three real ones.

**8.1 The no-sources rule versus data credibility.** Every publisher in section 1.2 is
credible partly because its source is known and singular: Indeed's postings, ADP's
payroll, Gusto's payroll, Ashby's ATS. Nabbly cannot say what it measures without
either naming sources or being vague. **This is a genuine cost and it should be
acknowledged rather than argued away.**

The workable middle, and I think it holds: **describe the shape of the collection
without naming the members.** "Measured across 21 public job boards and hiring
communities, covering 24 fields, from [date] to [date]. Postings that appeared on more
than one source are counted once." That is a real method note. It says what was counted,
over what period, and how duplicates were handled, which is what a competent journalist
or referee actually needs. It never names a source.

Flex Index is the precedent worth citing: it publicly describes its collection as
employee surveys, manual culling of company career pages, and job postings, without a
member list, and Nick Bloom still calls it the best dataset he is aware of on the
question ([Forbes](https://www.forbes.com/sites/jenamcgregor/2023/02/07/a-new-flex-index-is-collecting-companies-remote-work-policies-in-one-searchable-tool/)).
Method transparency and source transparency are not the same thing, and only the first
is required. **Confidence: medium-high** that this survives journalistic scrutiny;
**low** that it survives a hedge fund DDQ, which is one more reason that path is closed
anyway.

**8.2 The no-sources rule versus commercial data sales.** This one does not have a
middle. Alt-data due diligence requires naming every source and documenting the rights
around each. That is a private disclosure under NDA rather than a public one, so it does
not technically breach the public rule, but the founder should decide in advance whether
he is willing to disclose the full source list to a buyer's compliance team. **If the
answer is no, the commercial data path is permanently closed, and that is a legitimate
choice.** It should be made deliberately rather than discovered in a meeting.

**8.3 "Numbers must be true at all times" versus recurring reports.** Resolved by
as-of-date stamping. "As of 25 August 2026, development gigs were 18% of the board" is
true permanently. It is only an unstamped or implied-live number that goes stale. Every
figure in every report carries its measurement window in the same visual unit as the
number, not in a footnote.

One addition: **state the observation window prominently in early reports.** "Measured
over five weeks" is a limitation, and publishing it is what makes the report credible
rather than what makes it weak. Readers forgive a short window that is disclosed. They
do not forgive one that is discovered.

---

## 9. The three things that matter, if only three get done

1. **Start archiving daily aggregate snapshots this week** (3.5). Two days of work.
   It is the only irreversible item on the list.
2. **Publish Rate Bands and First Hour in September** (5.3). Both are publishable with
   five weeks of data, both are uniquely Nabbly's, and both target queries with real
   commercial intent on a site that currently gets no search traffic at all.
3. **Answer the subreddit collection question with a lawyer** (4.4). One billable hour.
   It is the largest unpriced risk in the business and it gets more expensive to fix the
   longer the pipeline runs on an unexamined footing.

Everything else in this document is downstream of those three.

---

## Sources

**Labour market data companies**
- Lightcast: [lightcast.io](https://lightcast.io/) · [data overview](https://lightcast.io/products/data/overview) · [education](https://lightcast.io/use-cases/education) · [uConnect partnership](https://lightcast.io/resources/blog/new-partnership-with-uconnect-brings-labor-market-insight-to-college-career-centers) · [pricing model summary](https://toolradar.com/tools/lightcast) · [buyer profile](https://thegtmdirectory.com/tools/lightcast)
- Revelio Labs: [Datarade profile](https://datarade.ai/data-providers/revelio-labs/profile) · [RPLS launch](https://www.integrity-research.com/revelio-labs-unveils-rpls-a-bold-alternative-to-bls-in-turbulent-times/)
- LinkUp: [data products](https://www.linkup.com/data) · [alpha use case](https://www.linkup.com/use-cases/alpha-innovation-using-alt-jobs-data) · [Maiden Century](https://www.linkup.com/partners/maiden-century) · [Datarade listing](https://datarade.ai/data-products/linkup-raw-job-market-data) · [Dewey partnership](https://www.deweydata.io/data-partners/linkup)
- Indeed Hiring Lab: [hiringlab.org](https://www.hiringlab.org/) · [about](https://www.hiringlab.org/about/) · [data FAQ](https://www.hiringlab.org/indeed-data-faq-2/) · [job postings tracker repo](https://github.com/hiring-lab/job_postings_tracker) · [wage tracker repo](https://github.com/hiring-lab/indeed-wage-tracker) · [Indeed newsroom](https://www.indeed.com/news/releases/indeed-turns-data-into-insights)
- Ashby: [Talent Trends hub](https://www.ashbyhq.com/talent-trends-report) · [recruiting ops benchmarks](https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends) · [startup hiring](https://www.ashbyhq.com/talent-trends-report/reports/startup-hiring) · [HR Dive pickup](https://www.hrdive.com/news/recruiters-see-job-applications-triple-to-more-than-300-per-role/820096/)
- ADP: [ADP Research](https://www.adpresearch.com/) · [workforce report](https://workforcereport.adp.com/) · [May 2026 NER](https://mediacenter.adp.com/2026-05-06-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-109,000-Jobs-in-April-Annual-Pay-was-Up-4-4) · [Stanford methodology](https://mediacenter.adp.com/2022-08-23-ADP-Research-Institute-and-Stanford-Digital-Economy-Lab-Unveil-New-Methodology-for-ADP-National-Employment-Report)
- Gusto: [economic data](https://gusto.com/research/economic-data) · [tracker launch](https://gusto.com/resources/gusto-insights/introducing-gustos-economic-data-tracker)
- Payscale: [research and insights](https://www.payscale.com/research-and-insights) · [wage trends report](https://www.payscale.com/featured-content/labor-market-wage-trends-report)
- Levels.fyi: [founder story](https://startupfounderstories.com/stories/levels-fyi-zuhayeer-musa) · [traffic](https://vi.semrush.com/website/levels.fyi/overview)
- Upwork: [Future Workforce Index 2026](https://investors.upwork.com/news-releases/news-release-details/upworks-future-workforce-index-2026-how-ai-redefining-value-work) · [freelancing stats](https://www.upwork.com/resources/freelancing-stats)
- Fiverr: [Business Trends Index June 2026](https://www.fiverr.com/resources/guides/reports/business-trends-index-june-2026) · [freelancing statistics hub](https://www.fiverr.com/resources/guides/reports/freelancing-and-future-of-work-statistics)
- Bullhorn: [GRID 2026](https://www.bullhorn.com/news-and-press/press-releases/bullhorn-grid-report-staffing-firms-using-ai-see-stronger-growth-faster-placements/) · [2025 trends](https://www.bullhorn.com/grid/2025-industry-trends/)
- MBO Partners: [State of Independence](https://www.mbopartners.com/state-of-independence)

**Alternative data market**
- [Hedgeweek on 2026 alt data spend](https://www.hedgeweek.com/hedge-fund-alt-data-spending-set-to-surge-says-new-research/) · [Kadoa practical guide](https://www.kadoa.com/blog/alternative-data-for-hedge-funds) · [Paradox Intelligence guide](https://www.paradoxintelligence.com/blog/alternative-data-for-hedge-funds-complete-guide) · [Deloitte on discovery to integration](https://www.deloitte.com/us/en/insights/industry/financial-services/alternative-data-for-investors-from-discovery-to-institutionalization.html)
- Backtest history requirements: [The TRADE](https://www.thetradenews.com/thought-leadership/challenges-of-backtesting-alternative-data/) · [vBase](https://www.vbase.com/alternative-data/) · [Data Observatory](https://dataobservatory.substack.com/p/the-quagmire-of-backtesting-alternative)
- Marketplaces: [Datarade list your data](https://datarade.ai/company/contact/list-your-data) · [AWS Data Exchange provider financials](https://docs.aws.amazon.com/data-exchange/latest/userguide/provider-financials.html) · [Eagle Alpha vendor platform](https://www.eaglealpha.com/platform/data-vendor/) · [Eagle Alpha seller guide](https://www.eaglealpha.com/alternative-data-provider-complete-guide/) · [BattleFin](https://www.battlefin.com/) · [BattleFin Ensemble](https://www.battlefin.com/ensemble) · [Dewey](https://www.deweydata.io/) · [Dewey become a partner](https://docs.deweydata.io/docs/become-a-data-partner)
- Compliance: [Lowenstein Sandler on alt data vendor compliance](https://www.lowenstein.com/news-insights/publications/articles/key-considerations-for-alternative-data-and-ai-vendors-to-investment-firms-demonstrating-compliance-in-the-face-of-an-evolving-regulatory-environment) · [Akin on SEC exams](https://www.akingump.com/en/insights/alerts/sec-division-of-examinations-finally-speaks-on-alternative-data) · [SEC risk alert PDF](https://www.sec.gov/files/code-ethics-risk-alert.pdf) · [Morrison Foerster on MNPI deficiencies](https://www.mofo.com/resources/insights/220502-sec-deficiencies-investment-adviser-mnpi-compliance-practices)

**Legal**
- *Feist v. Rural Telephone*, 499 U.S. 340 (1991): [Justia](https://supreme.justia.com/cases/federal/us/499/340/)
- *Van Buren v. United States* (2021): [Wikipedia](https://en.wikipedia.org/wiki/Van_Buren_v._United_States) · [Nixon Peabody](https://www.nixonpeabody.com/insights/alerts/2021/06/10/van-buren-cfaa-ruling) · [EFF](https://www.eff.org/deeplinks/2021/06/van-buren-victory-against-overbroad-interpretations-cfaa-protects-security)
- *hiQ Labs v. LinkedIn*: [9th Cir. 2022 opinion](https://law.justia.com/cases/federal/appellate-courts/ca9/17-16783/17-16783-2022-04-18.html) · [Fenwick](https://www.fenwick.com/insights/publications/hiq-labs-scrapes-by-again-the-ninth-circuit-reaffirms-that-data-scraping-does-not-violate-the-cfaa-1) · [Morgan Lewis on the settlement](https://www.morganlewis.com/blogs/sourcingatmorganlewis/2022/12/linkedin-v-hiq-landmark-data-scraping-suit-provides-guidance-to-data-scrapers-and-web-operators) · [Privacy World](https://www.privacyworld.blog/2022/12/linkedins-data-scraping-battle-with-hiq-labs-ends-with-proposed-judgment/) · [ZwillGen lessons](https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/)
- *Meta Platforms v. Bright Data* (N.D. Cal. 2024): [Quinn Emanuel](https://www.quinnemanuel.com/the-firm/news-events/client-alert-meta-v-bright-data-significant-decision-for-web-scraping-industry/) · [Farella Braun + Martel](https://www.fbm.com/publications/major-decision-affects-law-of-scraping-and-online-data-collection-meta-platforms-v-bright-data/) · [Lowenstein](https://www.lowenstein.com/news-insights/publications/client-alerts/meta-v-bright-data-ruling-has-important-implications-for-webscraping-activities-by-investment-advisers-im)
- *CV-Online Latvia v Melons*, C-762/19 (CJEU 2021): [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62019CA0762) · [ipcuria](https://ipcuria.eu/case?reference=C-762%2F19) · [Bird & Bird](https://www.twobirds.com/en/insights/2021/uk/cv-online-latvia-cjeu-complicates-the-enforcement-of-database-rights) · [SCL](https://www.scl.org/12290-cjeu-search-engine-copying-of-databases-infringes-sui-generis-right-where-it-adversely-affects-database-maker-investment/)
- *Ryanair v PR Aviation*, C-30/14 (CJEU 2015): [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A62014CJ0030) · [Kluwer Copyright Blog](https://legalblogs.wolterskluwer.com/copyright-blog/ryanair-ltd-v-pr-aviation-bv-contracts-rights-and-users-in-a-low-cost-database-law/) · [Gowling WLG](https://gowlingwlg.com/en/insights-resources/articles/2015/ryanair-flying-high-at-the-cjeu/)
- EU database right generally: [European Commission](https://digital-strategy.ec.europa.eu/en/policies/protection-databases)
- Reddit: [Data API terms summary](https://prowlo.com/blog/reddit-data-api) · [legality analysis](https://www.redditapis.com/blogs/is-scraping-reddit-legal-2026) · [Reddit v Perplexity/SerpApi, CNBC](https://www.cnbc.com/2025/10/23/reddit-user-data-battle-ai-industry-sues-perplexity-scraping-posts-openai-chatgpt-google-gemini-lawsuit.html) · [Search Engine Land](https://searchengineland.com/reddit-sues-perplexity-serpapi-scraping-google-463681)
- Attribution norms: [Himalayas API](https://himalayas.app/api) · [Himalayas API docs](https://himalayas.app/docs/remote-jobs-api)

**Data as marketing**
- [Search Engine Journal on data-driven digital PR](https://www.searchenginejournal.com/achieving-links-that-matter-how-to-use-research-and-data-driven-journalism/474956/) · [Siege Media](https://www.siegemedia.com/marketing/digital-pr-link-building) · [Digital Applied 2026 guide](https://www.digitalapplied.com/blog/link-building-2026-digital-pr-outreach-guide) · [BuzzStream on Ahrefs' link sources](https://www.buzzstream.com/blog/bootstrap-link-building-analysis/)
- [Muck Rack, Hiring Lab as a media outlet](https://muckrack.com/media-outlet/hiringlab)

**Partnership candidates**
- [WFH Research](https://wfhresearch.com/research-and-policy/) · [Forbes on Flex Index](https://www.forbes.com/sites/jenamcgregor/2023/02/07/a-new-flex-index-is-collecting-companies-remote-work-policies-in-one-searchable-tool/) · [Flexos interview with Nick Bloom](https://www.flexos.work/learn/nick-bloom-stanford-media-hybrid-and-remote-work)
- [Freelancer software comparison, pricing](https://agiled.app/blog/software-for-freelancers) · [Deel contractor payment tools](https://www.deel.com/blog/best-global-payment-tools-for-contractors/) · [EOR HQ, Wise vs Payoneer vs Deel vs Remote](https://eorhq.com/guides/wise-vs-payoneer-vs-deel-vs-remote-contractor-payments/)

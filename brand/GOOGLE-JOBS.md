# Google for Jobs: the case, and why the answer is no for now

The question: should Nabbly publish each gig as its own indexed page carrying
`JobPosting` structured data, so listings can appear in Google's jobs box?

Short answer: no, and not because it is hard to build. It is a week of work.
The reason is that Google for Jobs requires publishing the two things Nabbly is
deliberately built to abstract away.

---

## The prize, stated fairly

The jobs box sits above the normal results for any query Google reads as a job
search. It is the single largest traffic source available to a board like this,
and it is why Indeed, Wellfound and We Work Remotely all invest in it. Nobody
should pretend it is small.

Entry requires, per Google's own guidelines:

- one crawlable page per posting, on nabbly.co
- `JobPosting` schema on each, including `title`, `description`,
  `datePosted`, `hiringOrganization` and `jobLocation`
- `validThrough`, and the page must stop being served once the role closes
- the posting must not be a duplicate of one already indexed elsewhere

Four requirements. Nabbly fails three of them structurally, not fixably.

---

## 1. It forces us to name sources and employers

`hiringOrganization` is required. There is no version of a `JobPosting` page
that does not say who is hiring.

On top of that, the source terms require their own credit. RemoteOK's API terms
ask that RemoteOK is credited wherever listings are republished, with the
canonical URL included so attribution is correct. That is a reasonable ask from
them and it is the norm across this category.

So publishing gigs as pages means either naming every source on every page, or
breaching the terms we collect under. Those are the only two options.

This is the whole thing. Every other surface in the product is careful never to
advertise sources: the FAQ answer was rewritten for it, the marketing FAQ block
was deleted over it, and the board screenshots on nabbly.co are cropped above
the "via" line for it. The reasoning has always been that the feed is the
product and where it comes from is plumbing, and a reader handed the list has
six other places to go instead of here.

Google for Jobs asks us to publish that list, at scale, on our own domain, as
the price of entry.

## 2. We do not have real expiry data

Google requires `validThrough` and penalises boards that serve listings for
roles already filled. Nabbly's 21-day retention is a freshness heuristic we
chose, not an expiry date any source gave us. We genuinely do not know when a
posting closes.

Publishing a guessed `validThrough` on tens of thousands of pages is
guaranteeing something we cannot know, to the one audience least forgiving of
it.

## 3. We would be the least authoritative copy

Google explicitly deprioritises duplicate postings. A gig on Nabbly already
exists on the source, and usually on three other aggregators. In a duplicate
contest between the original board and a domain with no history, we lose, and
we spend our crawl budget losing.

## 4. It would bury the pages that are working

The 21 field pages are unique, useful and were built carefully to avoid looking
like doorway pages. Adding 32,000 pages of other people's text next to them
changes what the domain looks like in aggregate: mostly thin, mostly
duplicated. That is the profile that attracts quality problems, and it would be
risking the thing that already works to chase the thing that probably will not.

---

## What would have to change for this to become a yes

Not "we got better at it". Something structural:

- **Nabbly hosts original postings.** If people post work directly to Nabbly,
  those listings are ours, expiry is known because the poster sets it, and
  `hiringOrganization` is a fact we are entitled to publish. That is a real
  product direction and it makes Google for Jobs a natural next step rather
  than a workaround.
- **A source relationship with explicit redistribution rights.** A written
  agreement with one board, covering republication and attribution terms we can
  live with. One partner is enough to test whether the traffic is worth it.

Both start from permission rather than around it.

---

## What to do instead, now

Everything in OUTREACH.md, which targets the same searches from the other
direction: rank the field pages, and get listed on the pages that already rank.
It is slower and it is smaller, and it does not require publishing anyone
else's work under our own name.

One related decision, already flagged: the JobBoardSearch submission form asks
for an RSS or API feed and offers to push those listings onward, including into
the Google for Jobs network. That is this same question wearing a disguise.
Leave the field empty and take the plain directory listing.

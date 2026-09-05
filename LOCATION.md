# Location on the board: what is wrong and what to do

Measured 2026-09-05 against the live API and the live board. Every number
below was read, not estimated; where something is a judgement it says so.

The short version: the board has a location filter whose underlying data was
never captured. It is not an Arbeitnow bug. It is a missing column.

---

## What was measured

One page of Arbeitnow's public API (`/api/job-board-api`), 250 jobs:

| | |
|---|---|
| Top locations | Paris 25, London 23, Berlin 16, Bordeaux 5, Düsseldorf 4, München 4 |
| `remote` flag set | **9 of 250** |
| "remote" present in location/title/tags | **19 of 250** |
| Genuinely remote, best estimate | **~19 — 7.6%** |
| `.co.uk` URLs | 75 of 250 (30%) |

So roughly **92% of what Arbeitnow supplies is an on-site job in a European
city**, and a fair share of the rest is German-language (`(m/w/d)`, `(gn)`,
"Remote Deutschland"). Nabbly sells "Freelance projects · Remote roles ·
Contract work". Those on-site roles appear in the default view.

## The actual defect

`posts` has **no location column and no remote column.** All ten fetchers in
`sources.py` emit exactly six keys — `source`, `source_id`, `url`, `title`,
`body`, `posted_at`. Nothing else survives ingest.

Arbeitnow returns `location` and `remote` per job. Both are discarded. The
board's `Everywhere / Remote I can take / On-site & local` facet then infers
"on-site" from free text (`app.py`, `_tags[...]["onsite"]`).

We are throwing away a structured answer and guessing a worse one. Only
`fetch_workingnomads` keeps location at all, and only by folding it into the
body string where it is searchable but not filterable.

## The `.co.uk` sub-issue, and why the obvious fix is wrong

Arbeitnow publishes UK roles on `www.arbeitnow.co.uk`, which sits behind an
aggressive Cloudflare challenge: `403` to any scripted request, and about ten
seconds in a real browser before the page appears. `www.arbeitnow.com` serves
in 0.27-0.46s with no challenge.

**Do not rewrite `.co.uk` to `.com`.** Tested on a live listing: the same path
on `.com` returns `410 Page not found`. The two domains hold different job
sets, so the rewrite swaps a slow page for a dead one. About a quarter of the
Arbeitnow gigs on the board at time of writing point at `.co.uk`.

## Options

1. **Capture what we already receive.** Add `location` and `remote` to `posts`
   and populate them in the fetchers that supply them. The existing filter
   becomes accurate with no UI change. Smallest change, largest effect.
   *Caveat: do not trust Arbeitnow's `remote` flag alone — it is set on 9 of
   the 19 genuinely-remote jobs and misses "Remote Deutschland" and "Germany -
   Remote" entirely. Use the flag OR a text match, not the flag alone.*
2. **Keep on-site out of the default view.** Independent of 1, and the change
   that actually stops a US freelancer being shown an on-site Munich role.
3. **Drop Arbeitnow.** Loses ~19 real remote gigs per 250 for free. Not
   recommended while 1 and 2 are undone — it treats a data gap as a supply
   problem.
4. **Badge `.co.uk` listings** the way `ACCOUNT_REQUIRED_SOURCES` is badged.
   Honest, but it advertises a defect rather than fixing one, and the
   underlying issue is the location data, not the domain.

## Recommendation

**1 then 2.** Keep the source; stop letting on-site roles into the default
view. A UK toggle is the wrong axis — a remote Berlin job is good for this
audience and an on-site London one is not, exactly as an on-site Boston one
is not. The axis is remote vs on-site, and that control already exists on the
board; it simply has nothing reliable behind it.

Leave `.co.uk` alone until 1 lands. Once location is a real column the
question answers itself, because almost every `.co.uk` job is on-site anyway
and will be filtered on its merits rather than its hostname.

## Not done, and why

Deferred on 2026-09-05: the founder had a demo and two source signups in
front of him, and this is an ingest change plus a re-tag of existing rows.
For the demo, `.com` gigs were verified clean and fast and one was picked by
hand.

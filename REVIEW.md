# Site review, and what to build next

Reviewed 2026-08-29 against the live surfaces, not the source. Every claim
below was checked in a browser or with a request; where something is a
judgement rather than a measurement it says so.

Nothing here is a redesign. The visual language is good and consistent, the
board is fast (190ms, 74KB, no external CSS or JS), and mobile has no
horizontal overflow. The problems are in the funnel and the seams between
three surfaces, not in how it looks.

---

## 1. The conversion leak that matters most

**"Draft my reply →" leads to a sign-in wall that never mentions the reply.**

It is the CTA on every card and the product's whole differentiator. Signed
out, it goes to `/signin`, which says *"Save your profile and picks, get
alerts, and keep your board across visits."* Nothing about the thing that was
just clicked.

Worse, nabbly.co promises the opposite. The Free column on the homepage reads
*"A drafted reply on every gig, ready to edit"*. So the site says free, the
button says sign in, and the sign-in page talks about something else.

Fix, in order of cost:
1. Carry the promise: `/signin?for=draft` renders "Sign in and your reply is
   waiting" instead of the generic line. One template branch.
2. Better: show the free template draft to a signed-out visitor and gate only
   the AI version. The free draft already exists in `pitch.py`. This turns the
   sign-in from a toll booth into a natural upgrade.

## 2. The price is not on the website

There is no `$` figure anywhere on nabbly.co. The homepage's Pricing nav is an
anchor to `#plans`, which lists Free and Pro features and no number. The board
footer's Pricing link points at `https://app.nabbly.co/?nav=pricing` — the
legacy Streamlit app, a different surface with a different shell.

$12/mo appears only inside `app.py`. Someone who wants to know what Pro costs
is sent out of the fast board into the old app to find out.

This is a small change with a real effect: put the number on `#plans`, and
point the board's Pricing link at nabbly.co rather than the app.

## 3. Three front doors, and the oldest one is still load-bearing

`nabbly.co` (static), `board.nabbly.co` (the product), `app.nabbly.co`
(Streamlit). The board is where the field pages send SEO traffic and where the
partner link lands — correct. But the app still owns the pricing page, and the
board links to it.

Until the app is either retired or explicitly framed as something else, every
link into it is a step backwards in speed and consistency for the user.
Decide which it is; the ambiguity is the cost.

## 4. Mobile has no navigation

The nav collapses to a single "Open the board" button. The Board / How it works
/ Forwarding / Pricing / FAQ links are all `display:none` with no menu control
of any kind — verified: five hidden links, zero visible, no burger, no
`<details>`. A phone visitor can only reach those sections by scrolling or via
the footer.

Given the audience is freelancers who will meet this on a phone, that is worth
a disclosure-triangle menu, which the codebase already uses elsewhere (the
board's mobile Filters toggle is exactly this pattern).

## 5. The board calls itself something else

The board footer reads **"OneLonelyCow · © 2026"**. The marketing site says
Nabbly. That is the GitHub handle showing through on the surface a customer
actually uses.

## 6. Market is a locked door with no window

Signed out, `/market` is one heading and an upsell. It is the answer to *what
should I charge*, which is a genuinely strong reason to pay — and a visitor
sees none of it.

A single real number visible to everyone (one field's median, this week) would
sell the page far better than a description of it does.

## 7. Smaller, verified

- All 30 sitemap URLs return 200; every homepage link resolves.
- Homepage is 42KB with 13KB inline CSS, 6KB inline JS, one lazy image. Fast.
- `/pricing.html` does not exist as a page — pricing lives at `#plans`. Fine,
  but it means there is no shareable pricing URL.

---

# The four revenue streams

`ROADMAP.md` already ranks these and its reasoning holds up. What follows is
that ranking checked against the data as it stands today, which changes two of
the four.

### Priority 1 — Team / agency accounts
**Most important. Not the easiest, and worth it anyway.**

The argument is the buyer, not the feature. A solo freelancer weighs $12
carefully; an agency owner compares it to a fraction of a recruiter's salary.
Same product, an order of magnitude more per account.

Cost is real: `accounts.py` is single-user throughout — no seats, no org, no
shared board, no routing. But only ~10 places check `pro` across both
services, so the gate itself is small.

**Before building it, ask the five questions in ROADMAP.md.** Two answers kill
it: if an agency pays for nothing today, the budget is theoretical; if they
route work by forwarding in Slack, the routing half has no value and this
collapses into several individual accounts they can already buy.

### Priority 2 — Alerts-only tier
**Easiest by a distance. Build it first even though it earns least.**

Alerts are built and working. There is exactly one Stripe price. This is a
second price plus a feature gate — not a new system.

Today the ladder is Free or $12, so everyone who finds $12 too much converts
to nothing. A cheaper rung catches them, and it can ship in days rather than
weeks. Do this while the team-account questions are still being asked.

### Priority 3 — Rate intelligence as a product
**Blocked on data, not on engineering. Do not schedule it yet.**

The Market page and the maths exist. The problem is underneath: **86% of
postings state an amount with no period at all.** An unmarked "$140" might be
hourly, a project total, or a week. Publishing only rates whose period is
stated leaves 6 of 25 fields with a 30+ sample hourly, 8 yearly — and
**per-project, the number freelancers most want, has twelve postings and not a
single field with a usable sample.**

So it can stay a Pro perk, where "indicative" is acceptable. It cannot yet be
a product someone buys for its accuracy.

Two things to fix first, in this order: extract periods from more postings, or
narrow the claim to the fields that do have samples. And settle the question
ROADMAP raises — selling data derived from other people's postings is a
decision to make deliberately, not to arrive at.

### Priority 4 — Dark demand / verified private demand
**Not a revenue stream. Take it off the revenue slide.**

ROADMAP is explicit: this belongs under defensibility, and *"do not put them
in a deck as monetization; it reads as padding and someone will notice."* The
deck currently lists it as revenue item 04.

It is genuinely valuable — a published count of work that reaches no public
board is the best answer to "why can't someone just build this?" But it is a
moat, and it needs forwarding volume before the number means anything.

---

## The order I would actually work in

1. **Fix the draft sign-in leak** — days, and it lifts every other number.
2. **Put the price on the site**, and point Pricing at nabbly.co not the app.
3. **Ship the alerts-only tier** — a price and a gate.
4. **Ask the agency questions.** Build team accounts only if the answers hold.
5. **Leave rate intelligence** until period extraction improves.
6. **Move dark demand** out of revenue and into the defensibility story.

1 and 2 are the cheapest work on this list and sit in front of every funnel
the others depend on.

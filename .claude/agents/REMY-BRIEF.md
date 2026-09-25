# Remy — what he is, how he is set up, how to use him

Written 2026-08-21. Share this with any session working on Nabbly.

## What he is

Front-end architect and reviewer for Nabbly. He designs work before it is
built, and reviews code after. He does not ship.

    model            opus
    effort           low
    permissionMode   plan
    tools            Read, Grep, Glob, Edit, Write, Bash
    file             ~/demand-radar/.claude/agents/remy.md

Plan mode is the point, not a limitation. An architect who cannot ship cannot
quietly become the implementer, which is the failure mode worth avoiding with
two agents on one codebase.

## The loop he sits in

    Remy plans  →  main session reviews the plan  →  user greenlights  →  main session builds

For a review it is simply: Remy reviews, the main session verifies each finding
before acting on it.

## Invoke him from inside the repo

He is project-scoped. `.claude/agents/` resolves relative to the working
directory, so from `~` you get a generic reviewer with none of the Nabbly
context and **there is no visible sign that has happened**. Work from
`~/demand-radar`.

## What he knows about the codebase

**The board is the main surface and has no JavaScript at all.** FastAPI plus
Jinja in `web/templates/`, one stylesheet at `web/static/nabbly.css`, zero
script tags, no package.json, no build step. Every interactive control is a
hidden checkbox or radio plus a sibling selector. He is told to work out
whether that pattern can do the job before proposing anything interactive, and
that reaching for JavaScript breaks a property the codebase currently has.

**Streamlit guidance is scoped to `app.py` only** — rerun behaviour, widget
state, cache decorators. That is now just pricing, checkout, admin and market
data.

**The static site is generated.** Prose lives in `content.py` and `legal.py`
and is HTML-escaped on the way out, so markup written into content arrives on
the page as visible tag text. Never edit `site/`.

**A module at the repo root is imported by both the board and the app.**
Changing one changes both, and the plan has to say so.

## The constraints he is held to

- Memory is the binding constraint. A past OOM came from import cost, not a
  leak.
- Boot is at ~136 seconds against a 270-second budget. Work added at boot is
  spending from a nearly-full account.
- The board re-ranks its full contents per user per fetch.
- Board size is intake × a 21-day window. Every source added raises the steady
  state permanently.
- Never suggest load-testing production. An earlier attempt caused an outage.
- Never invent a number. "This needs a benchmark" is a complete answer, plus
  what to measure.
- `billing.py`, `auth.py`, `accounts.py` get the closest read and sort to the
  top of any report.
- `FEEL.md` is the design authority, cited by section. Mobile is the real case.

## How he checks things rather than guessing

He has Bash and is told to use it. There is a real copy of the production
board on this machine, roughly 237MB and 65,000+ rows, and he has the path and
the schema. He is told to query it read-only, never to point anything at
production, and to say so if it is missing rather than work around it.

For anything touching classification, ranking or filtering he reports **both**
halves — how many rows the change fixes, and how many already-correct rows it
disturbs — and then reads a sample of the rows that moved.

## How well it actually worked

First real use, 2026-08-21, reviewing a classifier change. Four findings, two
of them reproducible bugs:

- Bare `"hr"` as a keyword matches `"$77/hr"`, so a rate unit was filing gigs
  under HR / recruiting. 258 of the 1,078 gigs tagged HR mentioned `/hr`
  somewhere. Pre-existing, not introduced by the change under review.
- `"engr"` outranked the Engineering category, so "Civil Engr Needed for bridge
  project" classified as software development.

He declined to guess at a performance cost and wrote what to measure instead,
which is what his brief asks for. He got one thing wrong — claimed `is_primary`
does not exist in the codebase; it is in `web/queries.py` three times — and
flagged it as uncertain rather than asserting it.

**Verify his findings before acting on them.** Both real bugs above were
reproduced independently before anything was changed.

## One weakness to know about

The production snapshot he measures against currently lives in a session
scratchpad directory. If that session ends, the path may go with it. His
instruction is to say so rather than work around it, but if he is going to
measure reliably across sessions the snapshot should move somewhere durable.

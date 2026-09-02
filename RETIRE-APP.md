# Retiring app.nabbly.co

Three surfaces exist: `nabbly.co` (static marketing), `board.nabbly.co` (the
FastAPI board, the actual product) and `app.nabbly.co` (the original Streamlit
app, `dartly` on Render). The board has long since overtaken the app on every
page a member uses. This is how the app goes away without breaking anything.

## Why bother

A visitor who lands on `app.nabbly.co` gets a slower app that shows Dashboard
and Saved tabs while signed out, which the board correctly hides. It looks
like the product and is not the product. Every "Upgrade" link walked members
into it, because that is where Stripe lived.

`dartly` also runs on Render's **standard** plan while the board runs on
**starter**, so the last phase is the one that stops paying for it.

## What still lives only in the app

Everything else — dashboard, gigs, market, saved, profile, sign-in, and the
legal pages — the board or nabbly.co already serves.

1. **Stripe checkout and redemption.** Barely a blocker: `/plans` on the board
   is already written to do both and falls back to linking at the app while
   `billing.enabled()` is False there.
2. **The admin panel** (`?nav=admin`). No board equivalent.
3. **Unsubscribe** (`?nav=unsubscribe&t=<token>`). THE SHARP ONE. It is in the
   footer of every email ever sent, those links are permanent, and breaking
   unsubscribe is a legal problem rather than a UX one.

Also `?nav=out&gid=…&e=…` in digests. The board has `/out/{gig_id}`, but it
identifies the reader by session; the email links carry an email token
instead, so they are not interchangeable.

## Phases

### 1. Native checkout on the board

Add to the **nabbly-board** service:

    STRIPE_SECRET_KEY         sk_live_…
    STRIPE_PRO_PRICE_ID       price_1UAWxFRbjGOdwPvoMHsnoYGH
    STRIPE_ALERTS_PRICE_ID    price_1UAWxARbjGOdwPvoMawtajZF

The Plans buttons stop bouncing to the app. Nothing else changes and it is
reversible by removing them again. This supersedes STRIPE.md's older note that
nothing goes on `nabbly-board`, which was true until `/plans` existed.

It does mean a live secret key on a second service. That is the right end
state — the board is where checkout belongs — but it is worth doing knowingly.

**This is also when the live purchase test finally happens**, which is still
the one link in the chain never exercised.

### 2. Make the board safe for email links

- Build `/unsubscribe?t=<token>` on the board, calling `accounts.unsubscribe`,
  the same one-click no-sign-in model the app uses.
- Build an email-token route for apply clicks, so a digest link can be
  attributed without a session.
- Then point `mailer.APP_URL` at `board.nabbly.co`.

New emails stop referencing the app. Old ones still need phase 4.

### 3. DECIDED 2026-09-01: sign-in and admin stay here

The app is not being retired. It keeps two jobs and forwards everything else,
which is phase 4 done early and phase 5 dropped.

Sign-in stays because the ?u= magic link in our emails is validated here and
THE APP CANNOT CREATE A BOARD SESSION: nb_session is set by the board's own
middleware and Streamlit sets no cookies, so forwarding a freshly signed-in
visitor to the board would land them signed out. That is the live consequence
of this decision — a welcome email lands somebody on this host, not on the
product — and it is the thing to revisit if it starts costing signups.

Moving it means the board accepting the emailed token, and that token is a
permanent reusable credential (accounts.by_token authenticates every request
with it), which is why accounts.email_token exists for every link that does
not need to sign anyone in. Putting it in board URLs would spread a standing
credential onto the surface being kept, so it is a build, not a redirect.

Admin stays because no board equivalent exists.

### 3b. The old plan for the admin panel

Either port the stats views to the board, or leave the app running and
unlisted: drop the `app.nabbly.co` custom domain and reach it at
`dartly.onrender.com`. Unlisting is one change and gets the same result for
visitors; porting is the only way to actually stop paying for the service.

### 4. Redirect, permanently

`app.nabbly.co` becomes a thin redirector mapping legacy `?nav=` values onto
board paths, and keeps serving `unsubscribe` and `out` itself. Not a temporary
shim — links already sitting in inboxes are permanent, so this is too.

### 5. Retire — NOT HAPPENING, see 3

Only once phase 4 has been live long enough that the logs show nothing but
redirects. Then the service can be suspended, and the standard-plan cost with
it.

## Order and risk

1 is independent and safe. 2 must land before 4, or the redirector has nothing
correct to point at. 3 is a judgement call that can happen any time. The only
real risk in the sequence is repointing `mailer` before the board can serve
what the emails ask for, which is why 2 is written as "build, then repoint"
rather than the other way round.

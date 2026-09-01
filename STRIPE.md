# Stripe setup

Two tiers are sold: **Pro $15/mo** and **Alerts $5/mo**. This is how the
plumbing goes together, and the handful of things about Stripe that will bite
you if you assume they work the way they look.

## The rules that decide everything else

**A price is immutable.** You cannot edit $12 into $15. You create a *new*
price and repoint the environment variable at it. The old one is archived, not
changed. This is why every price change below is "create, then repoint".

**Test and live are separate universes.** A `price_…` made in test mode does
not exist in live mode. Pasting a test id into production does not error
loudly — checkout just fails to build and the button quietly does not appear.

**Only one service needs these keys.** `app.py` (the `dartly` service) owns
checkout and redemption. The board (`web/`) never imports `billing` and reads
no `STRIPE_*` at all; it learns who is on what by reading the `plan` column
that `billing.confirm_session` writes. Setting Stripe vars on `nabbly-board`
does nothing.

**`STRIPE_ALERTS_PRICE_ID` unset is a working state.** The alerts tier is then
offered nowhere and everything behaves as it did before the tier existed. That
is deliberate: the code could ship before the price did.

---

## 0. Check which account production is on. FIRST.

**Resolved 2026-08-31.** `dartly` now runs the live key, both live prices are
set, and the old $12 price is archived. Kept here because it is the first
thing to check whenever checkout behaves strangely, and because of what it
cost: `dartly` was running a **sk_test_ key for the sandbox account**, and had
been since at least 5 August. Live checkout could never
have taken money. Six real upgrade attempts on 5-6 August created sessions in
the sandbox and died there; the zero subscribers and $0.00 MRR were never a
pricing or funnel problem.

There are TWO accounts, and every price id embeds which one it belongs to:

    acct_1U182N DulYXC8YrV   sandbox   ...prices look like price_...DulYXC8YrV...
    acct_1U182C RbjGOdwPvo   live      ...prices look like price_...RbjGOdwPvo...

So the check is one glance: in Render, `STRIPE_SECRET_KEY` must start with
`sk_live_`, and every price id must carry the LIVE account's suffix. A test
key with live price ids fails, and so does the reverse.

Do not paste a live secret key into a chat, a commit, or a ticket. Read it
once in the Stripe dashboard and paste it straight into Render.

## 1. Test first

Already done — test-mode prices exist and `.env` points at them:

    STRIPE_PRO_PRICE_ID       Pro $15/mo   (new price on product "Nabbly Pro")
    STRIPE_ALERTS_PRICE_ID    Alerts $5/mo (new product "Nabbly Alerts")

Run the Streamlit app locally and buy each tier with Stripe's test card
`4242 4242 4242 4242`, any future expiry, any CVC.

What to check, in order of what would hurt most if wrong:

1. **A $5 checkout grants `alerts`, not `pro`.** Sign in afterwards: the plan
   card should say **Alerts**, the Market page should still be a Pro upsell,
   and the Text-message field on the profile should be disabled with a PRO
   pill. If a $5 purchase turns anything Pro, stop — that is the one bug in
   here that costs real money.
2. **A $15 checkout grants `pro`**, and the Text-message field becomes usable.
3. **The alerts buy button disappears** once you are on the alerts tier.
   Nobody should be able to buy the same plan twice.
4. **The checkout page names the right product.** An alerts buyer should see
   "Nabbly Alerts", never "Nabbly Pro".

## 2. Live — DONE 2026-08-31

Verified in the dashboard: Nabbly Pro carries a single $15.00/month price,
Nabbly Alerts a single $5.00/month price, both `txcd_10103001` and Managed
Payments eligible, the $12 price archived, 0 subscriptions and $0.00 MRR.

    STRIPE_SECRET_KEY         sk_live_…   on dartly
    STRIPE_PUBLISHABLE_KEY    pk_live_…   on dartly
    STRIPE_PRO_PRICE_ID       price_1UAWxFRbjGOdwPvoMHsnoYGH   $15
    STRIPE_ALERTS_PRICE_ID    price_1UAWxARbjGOdwPvoMawtajZF   $5

The steps below are how it was done, kept for the next price change.

In the Stripe dashboard, **switch the Test/Live toggle to Live**. Everything
below is in live mode; if the toggle is wrong you will create the objects in
the wrong universe and nothing will work.

1. **Products → Nabbly Pro → Add another price.** Recurring, monthly, **$15**.
   Copy the `price_…` id.
   - If there is no live "Nabbly Pro" product yet, create it first.
2. **Products → + Add product.** Name **Nabbly Alerts**, recurring, monthly,
   **$5**. Copy the `price_…` id.
   - A separate product, not another price on Nabbly Pro: the product name is
     what Stripe prints on the checkout page and the receipt, so sharing one
     would show "Nabbly Pro" to somebody paying $5 for less.
3. **Render → `dartly` → Environment**, set all four. The first two are the
   ones that were wrong; changing only the price ids leaves you on the
   sandbox with live price ids, which fails outright:

        STRIPE_SECRET_KEY         sk_live_…   (was sk_test_, sandbox)
        STRIPE_PUBLISHABLE_KEY    pk_live_…
        STRIPE_PRO_PRICE_ID       price_1UAWxFRbjGOdwPvoMHsnoYGH   ($15, live)
        STRIPE_ALERTS_PRICE_ID    the $5 price on prod_VAhUkXT0IDS2n2

   Nothing goes on `nabbly-board`.
4. **Archive the old $12 price** so it cannot be checked out. Archiving does
   not touch anyone already on it — and today nobody is.
5. Redeploy `dartly`.

## 3. Verify live — STILL OUTSTANDING

The only link never exercised. Buy the $5 tier with a real card, confirm the
plan card says **Alerts** and not Pro, then refund yourself from the dashboard.

It cannot be done from the founder's account: `accounts.is_owner` makes that
account permanently Pro, and every upgrade control is hidden from anyone who
already pays. It needs a second, ordinary account.

Until this is done, "checkout works" is an assumption. Everything upstream of
the payment is confirmed; `billing.confirm_session` granting `alerts` rather
than `pro` is not.

---

## Notes

**The prices on the website are hand-written.** `site/index.html` says $0 / $5
/ $15, and `app.py` and `mailer.py` say $15 in their copy. Nothing reads the
figure back from Stripe. Change a price in Stripe and you must change it in
those files too, or the site advertises one number while the checkout charges
another.

**The buy button for the alerts tier deliberately carries no price.** The
amount lives in Stripe and Checkout shows it before anyone pays, so there is
one source of truth on the control that actually takes money.

**One `$12` in the admin panel is not a mistake.** It labels answers to a
survey that asked about $12, and it reads "asked pre-$15".

**Which price was paid decides which plan is granted** — read back off the
session in `billing.confirm_session`, never from anything the caller passed.
That is what stops a $5 checkout being redeemed as Pro. If you ever add a
third tier, add it to `_plan_for_price` or it will grant nothing at all, which
is the safe direction to fail.

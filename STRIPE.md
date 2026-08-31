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

## 2. Live

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
3. **Render → `dartly` → Environment**, set:

        STRIPE_SECRET_KEY         sk_live_…
        STRIPE_PUBLISHABLE_KEY    pk_live_…
        STRIPE_PRO_PRICE_ID       the new $15 price
        STRIPE_ALERTS_PRICE_ID    the new $5 price

   Nothing goes on `nabbly-board`.
4. **Archive the old $12 price** so it cannot be checked out. Archiving does
   not touch anyone already on it — and today nobody is.
5. Redeploy `dartly`.

## 3. Verify live

Buy the $5 tier with a real card, confirm the plan card says Alerts, then
refund yourself from the dashboard. There are no subscribers, so this is also
the first proof that live checkout works at all — which has never been
exercised.

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

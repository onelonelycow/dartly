"""
billing.py — Stripe checkout for Pro.

WHY THIS EXISTS: the trial and founding/partner grants get someone into Pro
for free; this is the door that keeps them there once that runs out. Kept
deliberately thin — Stripe's own hosted Checkout page takes the card, this
module only asks Stripe for a checkout link and, on the way back, confirms
the session actually paid before flipping the account to plan='pro'.

HOW IT'S WIRED: no public webhook endpoint, same constraint inbox.py has
(Streamlit has nowhere to put one). Checkout's success_url carries the
session id back to the app, which is retrieved and verified synchronously on
that page load — see the ?stripe_session= handler in app.py. Leave
STRIPE_SECRET_KEY / STRIPE_PRO_PRICE_ID unset and every call here is a
no-op, same convention as inbox.py and alerts.py.

NOT HANDLED YET: cancellations and failed renewals made outside the app
(e.g. from the Stripe customer portal, or a card that just expires) won't
un-set Pro until a reconciliation pass exists. Fine for now — nobody has a
subscription yet — but worth knowing before this has real subscribers.
"""
import os

import stripe

SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "").strip()

# The cheap rung. UNSET IS A WORKING STATE: with no price configured the tier
# is simply not offered anywhere, exactly as things were before it existed, so
# this can ship before the price exists in Stripe. Set it and the tier appears.
ALERTS_PRICE_ID = os.environ.get("STRIPE_ALERTS_PRICE_ID", "").strip()

# What each price buys. The map is the ONLY place a Stripe price becomes a
# plan: confirm_session reads back what was actually paid for and looks it up
# here, so a session can never grant more than its own price — that is what
# stops an alerts checkout being replayed as a Pro grant.
def _plan_for_price(price_id: str) -> str:
    if price_id and price_id == PRICE_ID:
        return "pro"
    if price_id and price_id == ALERTS_PRICE_ID:
        return "alerts"
    return ""


def price_for_tier(tier: str) -> str:
    return ALERTS_PRICE_ID if tier == "alerts" else PRICE_ID


def alerts_enabled() -> bool:
    """The alerts tier can be sold only when its own price is configured."""
    return bool(SECRET_KEY and ALERTS_PRICE_ID)

stripe.api_key = SECRET_KEY


def enabled() -> bool:
    return bool(SECRET_KEY and PRICE_ID)


def checkout_url(email: str, success_url: str, cancel_url: str,
                 tier: str = "pro") -> str | None:
    """A one-time Stripe Checkout link for this email, or None if billing
    isn't configured or Stripe can't be reached.

    tier defaults to "pro" so every existing caller keeps its behaviour.
    """
    price = price_for_tier(tier)
    if not SECRET_KEY or not price or not email:
        return None
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            customer_email=email,
            client_reference_id=email,
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
        )
        return session.url
    except Exception as e:
        print(f"  ! stripe checkout: {type(e).__name__}: {e}")
        return None


def confirm_session(session_id: str) -> tuple[bool, str]:
    """
    Verify a completed Checkout session and flip that account to Pro.

    Returns (ok, email). Called on the page load Stripe redirects back to —
    trusting the query params alone would let anyone forge a success by
    editing the URL, so this re-asks Stripe whether the session actually
    paid before touching the account.
    """
    if not enabled() or not session_id:
        return False, ""
    try:
        session = stripe.checkout.Session.retrieve(
            session_id, expand=["line_items"], timeout=15)
    except Exception as e:
        print(f"  ! stripe confirm: {type(e).__name__}: {e}")
        return False, ""
    if getattr(session, "payment_status", "") != "paid":
        return False, ""

    # A paid session stays retrievable from Stripe forever, so "payment_status
    # is paid" on its own is not proof of a CURRENT entitlement — it is proof
    # that money changed hands once. Re-opening the old success URL out of
    # browser history months after cancelling would otherwise hand back
    # lifetime Pro, free, as many times as you like. Three checks close that:

    # 1. It has to be the subscription product, not merely *a* paid session on
    #    this Stripe account. Without this, any future one-off purchase could
    #    be replayed here as a Pro grant.
    if getattr(session, "mode", "") != "subscription":
        return False, ""
    #    WHICH price also decides which plan is granted. Reading it back from
    #    the session rather than trusting anything the caller passed is what
    #    keeps a $ cheaper checkout from being redeemed as Pro.
    try:
        bought = {li.price.id for li in session.line_items.data if li.price}
        plan = ""
        for price_id in bought:
            got = _plan_for_price(price_id)
            if got == "pro":                 # Pro wins if both somehow appear
                plan = got
                break
            if got:
                plan = got
        if not plan:
            return False, ""
    except Exception:
        return False, ""      # can't prove what was bought -> don't grant

    email = (getattr(session, "client_reference_id", "") or
             getattr(session, "customer_email", "") or "").strip().lower()
    if not email:
        return False, ""

    # 2. The subscription behind it has to still be live. This is what a
    #    webhook would tell us; asking Stripe at redemption time gets the same
    #    answer without needing an endpoint Streamlit can't host.
    sub_id = getattr(session, "subscription", "") or ""
    if not sub_id:
        return False, ""
    try:
        sub = stripe.Subscription.retrieve(sub_id, timeout=15)
        if getattr(sub, "status", "") not in ("active", "trialing"):
            return False, ""
    except Exception as e:
        print(f"  ! stripe sub check: {type(e).__name__}: {e}")
        return False, ""

    # 3. One session grants Pro once. A replay of the same id is a no-op
    #    rather than a re-grant.
    import accounts
    if accounts.session_already_used(sub_id, session_id):
        return True, email

    accounts.set_plan(email, plan)
    accounts.set_stripe_ids(email, getattr(session, "customer", ""), sub_id)
    accounts.mark_session_used(email, session_id)
    return True, email

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

stripe.api_key = SECRET_KEY


def enabled() -> bool:
    return bool(SECRET_KEY and PRICE_ID)


def checkout_url(email: str, success_url: str, cancel_url: str) -> str | None:
    """A one-time Stripe Checkout link for this email, or None if billing
    isn't configured or Stripe can't be reached."""
    if not enabled() or not email:
        return None
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": PRICE_ID, "quantity": 1}],
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
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        print(f"  ! stripe confirm: {type(e).__name__}: {e}")
        return False, ""
    if getattr(session, "payment_status", "") != "paid":
        return False, ""
    email = (getattr(session, "client_reference_id", "") or
             getattr(session, "customer_email", "") or "").strip().lower()
    if not email:
        return False, ""
    import accounts
    accounts.set_plan(email, "pro")
    accounts.set_stripe_ids(email, getattr(session, "customer", ""),
                            getattr(session, "subscription", ""))
    return True, email

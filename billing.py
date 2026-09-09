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
        print(f"  ! confirm: billing disabled or no session id", flush=True)
        return False, ""
    try:
        session = stripe.checkout.Session.retrieve(
            session_id, expand=["line_items"])
    except Exception as e:
        print(f"  ! stripe confirm: {type(e).__name__}: {e}", flush=True)
        return False, ""
    ps = getattr(session, "payment_status", "")
    # "no_payment_required" IS A COMPLETED CHECKOUT. Stripe returns it when the
    # total came to zero -- a 100%-off promotion code, or a trial that collects
    # nothing today. Rejecting it meant any promotion would take the signup,
    # create a real subscription, and grant NOTHING: charged nothing and given
    # nothing, silently, which is the same shape as the alerts tier that
    # set_plan used to refuse. Every check below still runs, so a free checkout
    # earns a plan on exactly the same evidence a paid one does -- the right
    # price, a real subscription, and that subscription live.
    if ps not in ("paid", "no_payment_required"):
        print(f"  ! confirm: payment_status={ps!r} "
              f"(wanted paid or no_payment_required)", flush=True)
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
        print(f"  ! confirm: mode={getattr(session, 'mode', '')!r} "
              f"(wanted subscription)", flush=True)
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
            print(f"  ! confirm: prices {sorted(bought)} match no plan — check "
                  f"STRIPE_PRO_PRICE_ID / STRIPE_ALERTS_PRICE_ID on THIS "
                  f"service", flush=True)
            return False, ""
    except Exception as e:
        print(f"  ! confirm: could not read line items: {e!r}", flush=True)
        return False, ""      # can't prove what was bought -> don't grant

    email = (getattr(session, "client_reference_id", "") or
             getattr(session, "customer_email", "") or "").strip().lower()
    if not email:
        print("  ! confirm: no client_reference_id or customer_email on the "
              "session — nothing to grant to", flush=True)
        return False, ""

    # 2. The subscription behind it has to still be live. This is what a
    #    webhook would tell us; asking Stripe at redemption time gets the same
    #    answer without needing an endpoint Streamlit can't host.
    sub_id = getattr(session, "subscription", "") or ""
    if not sub_id:
        print(f"  ! confirm: no subscription on session for {email}", flush=True)
        return False, ""
    try:
        sub = stripe.Subscription.retrieve(sub_id)
        sst = getattr(sub, "status", "")
        if sst not in ("active", "trialing"):
            print(f"  ! confirm: subscription {sub_id} is {sst!r}", flush=True)
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
    # THE ONE EVENT THAT MATTERS, written down. This route took a real payment
    # and granted nothing, and every rejection above returned silently -- so
    # there was no way to tell a working checkout from a broken one.
    print(f"  billing: granted {plan} to {email} (sub {sub_id})", flush=True)
    return True, email


# ---------------------------------------------------------------------------
# Changing an EXISTING subscription. Never checkout.
#
# checkout_url() is for someone who is not paying yet. Pointing a current
# subscriber at it creates a SECOND subscription and bills them twice — $15
# and $5 at the same time — which is the whole reason these exist.
#
# Everything here works on the subscription id recorded by set_stripe_ids at
# checkout, and every one of them re-reads Stripe rather than trusting what
# this app believes about the account.
# ---------------------------------------------------------------------------
def plan_for_subscription(sub_id: str) -> tuple[str, str]:
    """
    What Stripe says this subscription currently is: (plan, status).

    plan is "pro" / "alerts" / "" and comes from the price actually on the
    subscription, through the same _plan_for_price map checkout redemption
    uses — so there is one place a price becomes a plan, not two.
    """
    if not SECRET_KEY or not sub_id:
        return "", ""
    try:
        sub = stripe.Subscription.retrieve(sub_id)
    except Exception as e:
        print(f"  ! stripe sub read: {type(e).__name__}: {e}", flush=True)
        return "", ""
    status = getattr(sub, "status", "") or ""
    plan = ""
    try:
        for item in sub["items"]["data"]:
            got = _plan_for_price(item["price"]["id"])
            if got == "pro":            # Pro wins if both are somehow present
                plan = got
                break
            if got:
                plan = got
    except Exception:
        return "", status
    return plan, status


def _single_item(sub):
    """The one subscription item, or None if this is not the shape we sell.

    Every subscription this app creates has exactly one line. Anything else
    was made by hand in the dashboard, and guessing which line to re-price is
    how somebody's billing gets quietly rewritten.
    """
    try:
        items = sub["items"]["data"]
    except Exception:
        return None
    return items[0] if len(items) == 1 else None


def switch_plan(sub_id: str, tier: str) -> tuple[bool, str]:
    """
    Move an existing subscription onto another price. (ok, error).

    Swaps the price ON the current subscription item, so there is one
    subscription before and one after. Stripe prorates: a downgrade leaves a
    credit against the next invoice, an upgrade bills the difference.
    """
    price = price_for_tier(tier)
    if not SECRET_KEY or not price or not sub_id:
        return False, "billing is not configured"
    try:
        sub = stripe.Subscription.retrieve(sub_id)
    except Exception as e:
        return False, f"could not read the subscription ({type(e).__name__})"
    if getattr(sub, "status", "") not in ("active", "trialing"):
        return False, "that subscription is not active"

    item = _single_item(sub)
    if item is None:
        return False, "this subscription has an unexpected shape"
    if item["price"]["id"] == price:
        return True, ""            # already there; nothing to do, not an error

    try:
        stripe.Subscription.modify(
            sub_id,
            items=[{"id": item["id"], "price": price}],
            proration_behavior="create_prorations",
            # A switch is a deliberate change of plan, not a renewal, and
            # should never be blocked behind a payment that needs a card
            # challenge. Stripe bills the difference on the next invoice.
            payment_behavior="allow_incomplete",
        )
    except Exception as e:
        print(f"  ! stripe switch: {type(e).__name__}: {e}", flush=True)
        return False, f"Stripe refused the change ({type(e).__name__})"
    return True, ""


def cancel_at_period_end(sub_id: str) -> tuple[bool, str]:
    """
    Stop the subscription renewing, keeping access to the end of the period.

    NOT stripe.Subscription.delete(). They have paid for this month; taking it
    away the moment they click is a refund problem dressed as a feature. The
    account keeps its plan until the period ends and reconcile_plan() moves it
    to free once Stripe reports the subscription gone.
    """
    if not SECRET_KEY or not sub_id:
        return False, "billing is not configured"
    try:
        sub = stripe.Subscription.modify(
            sub_id, cancel_at_period_end=True)
    except Exception as e:
        print(f"  ! stripe cancel: {type(e).__name__}: {e}", flush=True)
        return False, f"Stripe refused the cancellation ({type(e).__name__})"
    return True, ""


def period_end(sub_id: str) -> int:
    """
    Unix time this subscription's access actually runs out, or 0.

    READS cancel_at FIRST. On a subscription set to stop, Stripe puts the
    stopping time there, and that is the date a member needs -- it is when
    they lose the thing they paid for. Confirmed off the live object:
    cancel_at=1791501730, cancel_at_period_end=True, and NO current_period_end
    anywhere on the subscription or its items.

    Then the item periods, then the old top-level field, for a renewing
    subscription and for accounts pinned to an older API version.

    STRIPE OBJECTS ARE NOT DICTS. item.get() and sub.keys() both raise
    AttributeError -- "'keys' is a dict method, but a SubscriptionItem is not
    a dict" -- which is why the previous item-level read found nothing even
    where the field existed. to_dict() first, every time.
    """
    if not SECRET_KEY or not sub_id:
        return 0
    try:
        sub = stripe.Subscription.retrieve(sub_id)
    except Exception as e:
        print(f"  ! stripe period_end: {type(e).__name__}: {e}", flush=True)
        return 0

    at = int(getattr(sub, "cancel_at", 0) or 0)
    if at:
        return at

    ends = []
    try:
        for item in sub["items"]["data"]:
            d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
            ts = d.get("current_period_end")
            if ts:
                ends.append(int(ts))
    except Exception as e:
        print(f"  ! stripe period_end: items unreadable: {e!r}", flush=True)
    if ends:
        # The furthest out, so a mixed-interval subscription reports when
        # access actually stops rather than when its shortest line renews.
        return max(ends)

    top = int(getattr(sub, "current_period_end", 0) or 0)
    if top:
        return top

    try:
        sd = sub.to_dict() if hasattr(sub, "to_dict") else {}
        item_keys = sorted((sd.get("items") or {}).get("data", [{}])[0].keys())
        sub_keys = sorted(sd.keys())
    except Exception as e:
        item_keys, sub_keys = [f"<{e!r}>"], []
    print(f"  ! stripe period_end: {sub_id} has no date anywhere — "
          f"cancel_at={getattr(sub, 'cancel_at', None)!r} "
          f"cancel_at_period_end={getattr(sub, 'cancel_at_period_end', None)!r} "
          f"item_keys={item_keys} sub_keys={sub_keys}", flush=True)
    return 0


def cancelling(sub_id: str) -> bool:
    """
    Whether this subscription is set to stop at the end of the period.

    Reads cancel_at as well as cancel_at_period_end: Basil added enum values
    to cancel_at, and a subscription scheduled to stop by that route carries a
    timestamp rather than the boolean.

    Logs what Stripe actually returned when it says "no". Twice now the card
    has failed to show a cancellation that had definitely happened, and both
    times the reason was a field that had moved -- which is unfalsifiable
    without seeing the object.
    """
    if not SECRET_KEY or not sub_id:
        return False
    try:
        sub = stripe.Subscription.retrieve(sub_id)
    except Exception as e:
        print(f"  ! stripe cancelling: {type(e).__name__}: {e}", flush=True)
        return False
    flag = bool(getattr(sub, "cancel_at_period_end", False))
    at = getattr(sub, "cancel_at", None)
    if flag or at:
        return True
    ends = []
    try:
        for item in sub["items"]["data"]:
            ends.append(item.get("current_period_end"))
    except Exception:
        pass
    print(f"  ! stripe cancelling: {sub_id} reports no cancellation — "
          f"status={getattr(sub, 'status', None)!r} "
          f"cancel_at_period_end={flag!r} cancel_at={at!r} "
          f"item_period_ends={ends!r} "
          f"top_period_end={getattr(sub, 'current_period_end', None)!r}",
          flush=True)
    return False


# Statuses that mean the money has stopped. "past_due" is NOT here on purpose:
# Stripe is still retrying the card, and pulling the plan mid-retry punishes
# someone whose bank declined once.
_DEAD = ("canceled", "unpaid", "incomplete_expired")


def reconcile_plan(email: str, sub_id: str) -> str:
    """
    Make this account's plan match what Stripe actually says. Returns the plan
    it settled on, or "" if nothing was checked or changed.

    THIS IS THE PASS THE MODULE DOCSTRING SAYS DOES NOT EXIST, for one account
    at a time. It is what makes cancel_at_period_end honest: the subscription
    keeps running until the period ends, Stripe flips it to canceled, and the
    next time this runs the account drops to free. It also catches the case
    nobody chooses — a card that quietly expires.

    Still not a sweep. Someone who cancels and never comes back keeps a plan
    they are not paying for until they visit a page that calls this.
    """
    if not SECRET_KEY or not email or not sub_id:
        return ""
    plan, status = plan_for_subscription(sub_id)
    if not status:
        return ""                      # could not ask Stripe; change nothing
    import accounts
    if status in _DEAD:
        accounts.set_plan(email, "free")
        print(f"  billing: {email} -> free (stripe says {status})", flush=True)
        return "free"
    if status not in ("active", "trialing") or not plan:
        return ""
    acc = accounts.by_email(email)
    now = (accounts.status(acc) or {}).get("plan") or ""
    if now != plan:
        accounts.set_plan(email, plan)
        print(f"  billing: {email} {now or 'none'} -> {plan} (stripe)", flush=True)
        return plan
    return plan


def subscription_for_email(email: str) -> tuple[str, str]:
    """
    What Stripe says this ADDRESS is paying for: (subscription_id, plan).

    THE RECOVERY PATH, and the reason it exists: until now a payment became a
    plan in exactly one way -- the browser getting back to /plans with the
    Checkout session id on the URL. Close the tab, lose the query string, drop
    the connection, and the money was taken and nothing was granted, with no
    way back. That happened on the first real purchase.

    So this asks the question the other way round. It needs no session, no
    redirect and no stored id, which means it also heals an account whose
    confirm_session failed for a reason we have not thought of yet.

    Reads only. Grant decisions stay with the caller.
    """
    if not SECRET_KEY or not email:
        return "", ""
    try:
        # NO timeout= HERE. Stripe's LIST endpoints treat unrecognised keyword
        # arguments as query filters and reject them outright --
        # "Received unknown parameter: timeout" -- so the whole lookup failed
        # before it asked anything. retrieve() tolerates it, which is why the
        # calls above have carried it for months without complaint.
        customers = stripe.Customer.list(email=email.strip().lower(), limit=10)
    except Exception as e:
        print(f"  ! stripe customer lookup: {type(e).__name__}: {e}", flush=True)
        return "", ""
    best = ("", "")
    for cust in getattr(customers, "data", []) or []:
        try:
            subs = stripe.Subscription.list(customer=cust.id, status="all",
                                            limit=10)
        except Exception:
            continue
        for sub in getattr(subs, "data", []) or []:
            if getattr(sub, "status", "") not in ("active", "trialing"):
                continue
            plan = ""
            try:
                for item in sub["items"]["data"]:
                    got = _plan_for_price(item["price"]["id"])
                    if got == "pro":
                        plan = got
                        break
                    if got:
                        plan = got
            except Exception:
                continue
            if not plan:
                continue
            # Pro beats alerts if somebody somehow holds both, matching the
            # precedence confirm_session already applies within one session.
            if plan == "pro":
                return sub.id, plan
            best = (sub.id, plan)
    return best

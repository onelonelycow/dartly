"""
contact.py — find the address a gig actually wants you to write to.

Some postings don't have an apply button at all: they say "send your reel to
hello@studio.com" and that's the whole application. We already write the
reply; knowing where it goes turns a draft you copy-paste into a message you
can send.

No API key needed for any of this. Finding an email in text is a regex, not a
language model — this works on the free tier exactly as well as on Pro.

The hard part isn't matching an address, it's rejecting the wrong one. A job
post is full of addresses nobody should reply to: noreply@ senders, the
poster's own tracking pixels, support desks, example placeholders. A wrong
address is worse than none — it sends someone's application into a void and
they never know. So this errs heavily toward returning nothing.
"""
import re

# Deliberately not RFC 5322. That grammar allows quoted strings and comments
# that no job post uses, and the permissive version matches half a stylesheet.
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}\b")

# Local parts that are never a person waiting for an application.
_BAD_LOCAL = re.compile(
    r"^(noreply|no-reply|donotreply|do-not-reply|bounce|mailer-daemon|"
    r"postmaster|abuse|unsubscribe|privacy|legal|dmca|webmaster|"
    r"example|test|your|yourname|name|email|user|someone|firstname|"
    r"lastname|sample|demo|admin|root|info@example)$", re.I)

# Domains that mean "this is boilerplate", not "write to us here".
_BAD_DOMAIN = re.compile(
    r"^(example\.(com|org|net)|domain\.com|email\.com|yourcompany\.com|"
    r"company\.com|sentry\.io|wixpress\.com|sentry-next\.wixpress\.com|"
    r"\d+\.\d+|.*\.(png|jpg|jpeg|gif|svg|webp|css|js))$", re.I)

# Wording that marks the address as the one to APPLY to, rather than a
# support desk mentioned in passing. Scored, not required — plenty of posts
# just drop the address on its own line.
_APPLY_HINT = re.compile(
    r"(send|email|e-mail|apply|applications?|resume|résumé|cv|portfolio|reel|"
    r"submit|write to|get in touch|contact|reach out|enquir|inquir)", re.I)

# Scan the WHOLE body, not a prefix. This was 4,000 chars on the theory that
# "applications live near the end, this covers the tail" — measured against the
# real board, it missed 203 of 206 addresses, because "how to apply" is the last
# thing in a long posting and long postings run to 8,000+ characters. The regex
# is linear and bodies are capped at 2,000 chars in the feed frame anyway; there
# was never anything to save here.


def find(text: str) -> str:
    """
    The single best address to apply to, or ''.

    When a post names several, the one nearest apply-ish wording wins; ties go
    to the first, which is nearly always the one in the "how to apply" line.
    """
    if not text:
        return ""
    body = str(text)
    best, best_score = "", -1
    for m in _EMAIL.finditer(body):
        addr = m.group(0).strip(".,;:)]}>\"'")
        if not _plausible(addr):
            continue
        # How apply-ish is the sentence around it? 120 chars each way covers
        # "To apply, send your CV to x@y.com" without spanning the paragraph.
        window = body[max(0, m.start() - 120): m.end() + 120]
        score = len(_APPLY_HINT.findall(window))
        if score > best_score:
            best, best_score = addr, score
    return best


def _plausible(addr: str) -> bool:
    if addr.count("@") != 1:
        return False
    local, _, domain = addr.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if _BAD_LOCAL.match(local) or _BAD_DOMAIN.match(domain):
        return False
    # A local part that's a long hex run is a tracking/relay address, not a
    # person: "u9f3a2c1b8e7d@bounces.example".
    if len(local) > 24 and re.fullmatch(r"[0-9a-f]+", local, re.I):
        return False
    return True


# ---------------------------------------------------------------------------
# Reading the address off a job's own page
# ---------------------------------------------------------------------------
# Some boards keep the contact address on the posting page and out of the feed,
# so the only way to get it is to fetch the page. This is an ALLOWLIST, not a
# capability we point at everything, because testing it broadly showed exactly
# how badly a blanket version fails:
#
#   freelancer.com  -> "jane@freelancer.com", a placeholder in their own page
#                      template. Blanket fetching would have stamped one fake
#                      address onto 7,000+ gigs.
#   dribbble        -> "u003evonkretschmann@lotum.de", a JSON escape read as
#                      text.
#   himalayas       -> HTTP 403. nodesk -> 404. arbeitnow -> no address at all.
#
# A source earns a place here only after its pages have been checked by hand.
PAGE_SOURCES = {
    # python.org puts the employer's address in a mailto: link under
    # "E-mail contact", url-encoded, with the visible text broken up by
    # <span>@</span> to defeat scrapers. Its OWN jobs@python.org sits further
    # down the same page in boilerplate, which is why _SITE_GENERIC exists.
    "pythonjobs": "python.org",
}

# Addresses belonging to the board itself rather than to whoever is hiring.
_SITE_GENERIC = re.compile(
    r"^(jobs|info|hello|support|contact|help|admin|team|hi)@", re.I)

_MAILTO = re.compile(r'href=["\']mailto:([^"\'?>]+)', re.I)


def from_page(html_text: str, site_domain: str = "") -> str:
    """
    The employer's address from a posting page, or ''.

    Reads mailto: HREFS rather than running a regex over the visible text. A
    mailto link is an explicit "write to this person" affordance, where loose
    text matching picks up analytics addresses, template placeholders and
    escaped JSON. It also survives the common obfuscation of splitting the
    visible address with markup, since the href is intact underneath.

    Anything on the board's own domain is dropped: that's their support desk,
    not the person hiring.
    """
    if not html_text:
        return ""
    from urllib.parse import unquote
    site = (site_domain or "").lower().lstrip("www.")
    for raw in _MAILTO.findall(html_text)[:12]:
        addr = unquote(raw).strip().strip(".,;:)]}>\"'")
        if not _plausible(addr):
            continue
        domain = addr.partition("@")[2].lower()
        if site and site in domain and _SITE_GENERIC.match(addr):
            continue          # the board's own desk, not the employer
        return addr
    return ""


def mailto(addr: str, subject: str, body: str) -> str:
    """
    A mailto: URL that opens their mail client with the draft already in it.

    Percent-encoded via quote() with an empty safe list, because a subject
    line with an ampersand ("Design & brand refresh") would otherwise end the
    query string and silently truncate the message.
    """
    from urllib.parse import quote
    if not addr:
        return ""
    return (f"mailto:{quote(addr, safe='@')}"
            f"?subject={quote(subject or '', safe='')}"
            f"&body={quote(body or '', safe='')}")

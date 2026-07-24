"""
inbox.py — gigs that arrive by email.

WHY THIS EXISTS: the best demand in a lot of fields never reaches a public job
board. It goes out on a listserv, or lands in a members-only Slack. A test
client put it exactly: "for media and journalism I don't think you have the
good ones in the aggregator and some are like slack channels, so not sure how
you can automate that." Probing confirmed it — ProductionHUB, Mandy, Stage32,
Poynter, Idealist and Video Consortium publish nothing a crawler can read.

You cannot crawl a private inbox. But the person who receives it can forward
it. Each signed-in person gets their own forwarding address; anything sent
there is read, split into individual gigs, classified like any other source,
and filed on their board.

PRIVATE BY DEFAULT: forwarded gigs are scoped to the person who forwarded them
and never reach the public board. Many of these newsletters are paid
(Study Hall, Sonia Weiser's Opportunities of the Week), so republishing them to
everyone would be both rude and a licensing problem.

HOW IT'S WIRED: no public webhook endpoint, because Streamlit has nowhere to
put one. Instead one mailbox receives everything via plus-addressing
(gigs+<token>@…), and the background thread polls it over IMAP — the same loop
that already fetches the boards. Set INBOX_EMAIL / INBOX_PASSWORD /
INBOX_IMAP_HOST to switch it on; leave them unset and every call here is a
no-op.
"""
import email
import hashlib
import imaplib
import os
import re
from email.header import decode_header, make_header

IMAP_HOST = os.environ.get("INBOX_IMAP_HOST", "imap.gmail.com").strip()
INBOX_EMAIL = os.environ.get("INBOX_EMAIL", "").strip()
INBOX_PASSWORD = os.environ.get("INBOX_PASSWORD", "").strip()
# The address people forward to. Defaults to the mailbox itself, but a catch-all
# domain reads better on screen than a gmail address.
INBOX_DOMAIN = os.environ.get("INBOX_DOMAIN", "").strip()

MAX_PER_POLL = 25          # messages per pass; a backlog drains over a few passes
MAX_BODY = 12000           # plenty for a newsletter, keeps the model call cheap


def enabled() -> bool:
    return bool(INBOX_EMAIL and INBOX_PASSWORD)


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------
def token_for(user_email: str) -> str:
    """
    The tag in someone's forwarding address.

    Derived from their email so it's stable without storing another secret, and
    hashed so the address itself doesn't leak who they are.
    """
    return hashlib.sha256(
        f"nabbly-inbox:{(user_email or '').strip().lower()}".encode()
    ).hexdigest()[:10]


def address_for(user_email: str) -> str:
    """The address to forward newsletters to, e.g. gigs+3f9a2b1c04@nabbly.co."""
    if not user_email:
        return ""
    tag = token_for(user_email)
    if INBOX_DOMAIN:
        local = (INBOX_EMAIL.split("@")[0] or "gigs") if INBOX_EMAIL else "gigs"
        return f"{local}+{tag}@{INBOX_DOMAIN}"
    if not INBOX_EMAIL or "@" not in INBOX_EMAIL:
        return ""
    local, domain = INBOX_EMAIL.split("@", 1)
    return f"{local}+{tag}@{domain}"


_TAG_RE = re.compile(r"\+([0-9a-f]{10})@", re.I)


def _tag_from_headers(msg) -> str:
    """Find the +tag across the headers a forward might land on."""
    for field in ("Delivered-To", "X-Original-To", "To", "Cc", "X-Forwarded-To"):
        for raw in msg.get_all(field, []) or []:
            m = _TAG_RE.search(str(raw))
            if m:
                return m.group(1).lower()
    return ""


# ---------------------------------------------------------------------------
# Reading a message
# ---------------------------------------------------------------------------
def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


_TAGS = re.compile(r"<[^>]+>")
_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)


def _plain_text(msg) -> str:
    """Best-effort readable body: prefer text/plain, fall back to stripped HTML."""
    html_part = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition", "").startswith("attachment"):
                continue
            ctype = part.get_content_type()
            try:
                raw = part.get_payload(decode=True) or b""
                text = raw.decode(part.get_content_charset() or "utf-8", "replace")
            except Exception:
                continue
            if ctype == "text/plain" and text.strip():
                return text[:MAX_BODY]
            if ctype == "text/html" and not html_part:
                html_part = text
    else:
        try:
            raw = msg.get_payload(decode=True) or b""
            text = raw.decode(msg.get_content_charset() or "utf-8", "replace")
        except Exception:
            text = ""
        if msg.get_content_type() == "text/html":
            html_part = text
        elif text.strip():
            return text[:MAX_BODY]
    if html_part:
        stripped = _TAGS.sub(" ", _STYLE.sub(" ", html_part))
        return re.sub(r"\s+", " ", stripped).strip()[:MAX_BODY]
    return ""


# ---------------------------------------------------------------------------
# Turning a newsletter into gigs
# ---------------------------------------------------------------------------
_SCHEMA = {
    "type": "object",
    "properties": {
        "gigs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["title", "url", "summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["gigs"],
    "additionalProperties": False,
}

_SYSTEM = """\
You pull individual job and gig opportunities out of a newsletter or mailing \
list digest.

One entry per distinct opportunity. For each: the role as a title, the apply or \
read-more link if the email carries one (empty string if not), and a short \
summary in the sender's own words covering what the work is, who it's for, pay \
and deadline where stated.

Ignore anything that is not an opportunity: adverts, event notices, editorials, \
sponsor messages, subscription footers, "reply to unsubscribe". If the email \
contains no actual opportunities, return an empty list rather than inventing \
one. Never invent a link, a rate, or a deadline that isn't in the text.\
"""


def extract_gigs(subject: str, body: str) -> list[dict]:
    """
    Split one email into separate opportunities.

    Newsletters have no common shape — every listserv formats differently — so
    this is a language problem, not a parsing one. With no API key we fall back
    to filing the whole email as a single entry, which is honest: better one
    findable item than a bad guess at five.
    """
    body = (body or "").strip()
    if not body:
        return []
    try:
        import pitch          # reuses the same "is Claude available" check
        if pitch.ai_available():
            import anthropic
            import json
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=pitch.MODEL,
                max_tokens=4000,
                system=_SYSTEM,
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
                messages=[{"role": "user",
                           "content": f"Subject: {subject}\n\n{body}"}],
            )
            if resp.stop_reason != "refusal":
                text = next((b.text for b in resp.content if b.type == "text"), "")
                got = json.loads(text).get("gigs", []) if text else []
                return [g for g in got if (g.get("title") or "").strip()]
    except Exception:
        pass          # a model hiccup must not lose the email
    return [{"title": subject or "Forwarded opportunity",
             "url": "", "summary": body[:1500]}]


# ---------------------------------------------------------------------------
# The poll
# ---------------------------------------------------------------------------
def poll(max_messages: int = MAX_PER_POLL) -> dict:
    """
    Read unseen mail, file any gigs, mark the message seen. Never raises.

    Returns {"messages": n, "gigs": n, "skipped": n} so the background loop and
    the admin page can show whether it's actually doing anything.
    """
    out = {"messages": 0, "gigs": 0, "skipped": 0}
    if not enabled():
        return out
    import classify
    import db

    try:
        box = imaplib.IMAP4_SSL(IMAP_HOST)
        box.login(INBOX_EMAIL, INBOX_PASSWORD)
        box.select("INBOX")
        typ, data = box.search(None, "UNSEEN")
        ids = (data[0].split() if data and data[0] else [])[:max_messages]
        for num in ids:
            try:
                typ, raw = box.fetch(num, "(RFC822)")
                if not raw or not raw[0]:
                    continue
                msg = email.message_from_bytes(raw[0][1])
                tag = _tag_from_headers(msg)
                owner = _owner_for_tag(tag)
                out["messages"] += 1
                if not owner:
                    # Nothing to attach it to — leave it unread so a real person
                    # can look rather than silently binning someone's mail.
                    out["skipped"] += 1
                    continue
                subject = _decode(msg.get("Subject"))
                body = _plain_text(msg)
                sender = _decode(msg.get("From"))[:120]
                for g in extract_gigs(subject, body):
                    title = (g.get("title") or "").strip()[:300]
                    summary = (g.get("summary") or "").strip()
                    tags = classify.classify(title, summary, "inbox")
                    rec = {
                        "source": "inbox",
                        "source_id": hashlib.sha256(
                            f"{owner}|{title}|{g.get('url','')}".encode()).hexdigest()[:24],
                        "url": (g.get("url") or "").strip(),
                        "title": title,
                        "body": f"{summary}\n\nForwarded from: {sender}".strip(),
                        "posted_at": str(msg.get("Date") or ""),
                        "is_demand": 1,
                        "job_type": tags["job_type"],
                        "size_tier": tags["size_tier"],
                        "urgency": tags["urgency"],
                        "owner": owner,
                    }
                    if db.upsert_post(rec):
                        out["gigs"] += 1
                box.store(num, "+FLAGS", "\\Seen")
            except Exception:
                out["skipped"] += 1
        box.close()
        box.logout()
    except Exception as e:
        print(f"  ! inbox: {type(e).__name__}: {e}")
    return out


def _owner_for_tag(tag: str) -> str:
    """Which account owns this forwarding tag, as their storage scope."""
    if not tag:
        return ""
    try:
        import accounts
        import paths
        for acc in accounts.all_accounts():
            if token_for(acc["email"]) == tag:
                return paths.scope_for(acc["email"])
    except Exception:
        pass
    return ""

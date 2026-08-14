"""
textfmt.py — how a gig's text and dates are shown to a person.

SHARED, NOT COPIED. These moved out of app.py when the board service needed the
same formatting: "Posted 3h ago", the three-line body preview, the HTML
stripping that keeps a scraped description readable. Two implementations of
"how long ago was this" is two answers to the same question, and the one users
would notice is the one that disagrees between two pages of the same product.

Pure functions over strings and dates. No Streamlit, no database, no config —
so anything can import it, including a plain HTTP handler.
"""
import html as _html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


_HINT_SEP = "\x1f"

_BUDGET_TAIL = re.compile(
    r"\s*\$?[\d,.]+\s*[-–—]\s*\$?[\d,.]*\s*(?:[A-Z]{3})?\s*"
    r"(?:budget|/\s*year|/\s*yr|per\s+year)?\s*$", re.I)

_TAGLIKE = re.compile(r"^[A-Z][A-Za-z0-9+#./-]*$")       # "WordPress", "Make.com"

_TECHY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+#./-]*$")   # "n8n", "3D", "24/7"

_FEED_LOC = re.compile(r"^\s*(?:location|company)\s*:\s*[^\n]{0,60}?\s{2,}", re.I)

def _strip_feed_head(text: str) -> str:
    """
    Drop a leading 'Headquarters: …' metadata block.

    The "URL:" form is cut entirely — it ends at a known marker, so there's no
    guesswork. The bare form ("Headquarters: State College, PA <description>")
    has nothing separating the place list from the prose; a heuristic that
    guessed where the sentence began ate a real word ("At Nextcloud…" became
    "Nextcloud…") and missed several others, so we only remove the label and
    leave the location text alone. Losing copy is worse than a little noise.
    """
    m = _HQ_LABEL.match(text)
    if not m:
        return text
    rest = text[m.end():]
    u = _HQ_URL.match(rest)
    return rest[u.end():] if u else rest

_HQ_LABEL = re.compile(r"^\s*headquarters\s*:\s*", re.I)

_HQ_URL = re.compile(r".*?\burl\s*:\s*\S+\s*", re.I)

def _parse_dt(raw):
    """Parse the varied timestamp formats the boards send us."""
    raw = str(raw).strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass
    try:
        return parsedate_to_datetime(raw)  # RFC-822 (reddit / WWR RSS)
    except Exception:
        pass
    try:
        from dateutil import parser as _dp
        return _dp.parse(raw)
    except Exception:
        return None


def human_time(raw):
    """Friendly, low-precision time in the viewer's local timezone."""
    if not raw:
        return "recently"
    dt = _parse_dt(raw)
    if dt is None:
        return "recently"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()  # -> the machine's local timezone
    secs = max(0, (datetime.now(local.tzinfo) - local).total_seconds())
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    if secs < 7 * 86400:
        return f"{int(secs // 86400)}d ago"
    return local.strftime("%b ") + str(local.day)  # e.g. "Jul 16"


def is_recent(raw, hours=24):
    dt = _parse_dt(raw)
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) >= datetime.now(timezone.utc) - timedelta(hours=hours)


def smart_trim(text, target=230, hard=520):
    """Trim to a full sentence so a preview never trails off mid-thought."""
    text = (text or "").strip()
    if len(text) <= target:
        return text
    for i in range(target, min(len(text), hard)):
        if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1] in " \n"):
            return text[:i + 1]
    cut = text[:hard]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 0 else cut) + "…"


def _strip_tag_tail(text):
    """Peel a trailing run of skill tags: 'PHP Website Design WordPress n8n'."""
    words = text.split()
    i = len(words)
    while i:
        w = words[i - 1]
        if w.endswith((".", "!", "?", ",", ":", ";")):
            break  # real punctuation means we're back in prose
        taggy = _TAGLIKE.match(w) or (
            _TECHY.match(w)
            and any(c.isdigit() or c == "." for c in w)   # "n8n", "3D", "v2.0"
            and any(c.isalpha() for c in w))              # but never a bare number
        if not taggy:
            break
        i -= 1
    # Only a long run is a tag dump; a couple of proper nouns is just a sentence.
    return " ".join(words[:i]) if len(words) - i >= 5 else text


def _flip_spans(value: str) -> str:
    """
    Wrap each character so CSS can stagger a per-digit flip when it lands —
    the departure-board effect. Streamlit remounts this markup fresh on every
    rerun (it's not a persistent DOM node Python mutates in place), so a plain
    CSS `animation` replays on its own each time with no JS and nothing to
    orchestrate — see .gr-flip in the stylesheet.

    Each letter is its own inline-block, which is normally invisible — but it
    means the browser sees no difference between the gap AFTER a word and the
    gap between two letters INSIDE one: both are just boundaries between
    boxes, free to wrap at. Every stat here is a short number, where that
    never shows up. Market's "Hottest skill" puts a real phrase in this same
    slot ("Development / tech"), and on a narrow mobile stat card it wrapped
    mid-word — "Development/t" / "ech" — because nothing told the browser
    those letters belonged together. Grouping each word's letters inside one
    shared inline-block fixes that: the browser can now only wrap BETWEEN
    words, the same as plain text, while each letter still animates on its
    own inside its word.
    """
    i = 0
    words_html = []
    for word in value.split(" "):
        letters = "".join(
            f'<span class="gr-flip" style="animation-delay:{(i + j) * 35}ms">{ch}</span>'
            for j, ch in enumerate(word))
        i += len(word)
        words_html.append(f'<span style="display:inline-block">{letters}</span>')
    return " ".join(words_html)


def display_body(raw):
    """The half of a post a human should actually read (see sources._body)."""
    text = (raw or "").split(_HINT_SEP)[0].strip()
    # Rows fetched before sources._strip learned to drop it still carry
    # RemoteOK's "please mention the word …" scraper bait.
    # Imported here, not at module scope: sources pulls in requests,
    # feedparser and praw, and this module is imported by an HTTP handler that
    # has no business loading a Reddit client to format a paragraph.
    import sources
    text = sources.BOILERPLATE.sub("", text).strip()
    text = _strip_feed_head(text)
    text = _FEED_LOC.sub("", text, count=1).strip()
    for _ in range(3):  # a budget can sit behind the tags, so peel a few times
        before = text
        text = _strip_tag_tail(_BUDGET_TAIL.sub("", text))
        if text == before:
            break
    text = text.strip(" ·,-–—")
    # Several feeds hand us a preview that stops mid-word. Say so, rather than
    # pretending the sentence ended there.
    if text and text[-1] not in ".!?…\"')":
        text += "…"
    return text

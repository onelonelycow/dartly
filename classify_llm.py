"""
classify_llm.py — the second pass, for gigs the keywords cannot name.

classify.py is keyword rules over config.JOB_TYPES, and it is right about most
of the board for free. Where it fails it fails structurally: measured
2026-08-26, 6,164 of 50,496 gigs sat in "Other / general", and the commonest
words in that bucket were `manager` (1,311), `specialist` (914), `analyst`
(488) and `lead` (372). Those name a role's SHAPE, not its field. The field is
in the modifier — "Revenue Enablement Manager", "Learning Systems Analyst",
"Identity Trust and Fraud Intelligence Specialist" — and that modifier is
business jargon no keyword list can enumerate. Seventeen candidate phrases
tested against the live board rescued 460 of 6,164 between them, 7.5%, with the
best single phrase worth 183. That is the ceiling of the approach, not a gap in
the vocabulary.

So this asks a model, but ONLY where the rules already gave up.

THE BLAST RADIUS IS DELIBERATELY ONE-WAY. This never sees a gig the keywords
classified, and it can only return one of config.JOB_TYPES' existing names or
nothing. A row can therefore move OUT of "Other / general" and nowhere else: no
existing classification can be overwritten, no new field can be invented, and
no public URL changes as a result of anything decided here. The worst outcome
of a bad answer is a gig filed under the wrong existing field, which is the
same failure the keyword rules already have.

Batched, because a request per gig is mostly overhead: one call carries a page
of titles and returns a label per line.

Two outcomes that look alike are kept apart throughout. A gig the model READ and
declined to place stays in "Other / general" and is marked, so it is never sent
again. A call that did not happen at all — no key, no such model, no credit, a
timeout, an answer whose shape cannot be trusted — marks nothing and leaves the
whole batch for the next cycle. See label().
"""
import json
import os
import re

import config

# HAIKU, NOT OPUS. This picks one of 24 existing field names for a job title —
# it is not writing anything, and the blast radius of a wrong answer is a gig
# filed under the wrong existing field, which the keyword rules already get
# wrong sometimes. Opus was set here on the day drafting moved to Opus, which
# was a decision about REPLY QUALITY that should never have been applied to
# housekeeping: it ran uncapped on the most expensive model in the lineup and
# turned the API key off.
MODEL = os.environ.get("NABBLY_CLASSIFY_MODEL") or "claude-haiku-4-5-20251001"

# How many gigs one request carries. Twenty keeps the answer short enough to
# stay reliable and the prompt small enough that a single failure is cheap.
BATCH = int(os.environ.get("NABBLY_CLASSIFY_BATCH") or 20)

# Bodies are the tie-breaker, not the evidence: the title names the role and a
# long description mostly adds other people's skills mentioned in passing —
# the exact confusion classify.py's title-first rule exists to avoid.
BODY_CHARS = 400

FIELDS = list(config.JOB_TYPES.keys())
OTHER = "Other / general"

# Matched case-insensitively and without punctuation, so "design/creative",
# "Design / Creative" and "design creative" all resolve to the real name. A
# label that resolves to nothing is dropped rather than guessed at.
_CANON = {re.sub(r"[^a-z0-9]", "", f.lower()): f for f in FIELDS}

SYSTEM = (
    "You label freelance and remote job postings with one field each.\n\n"
    "The fields, and the only labels you may use:\n"
    + "\n".join(f"- {f}" for f in FIELDS)
    + "\n\nRules:\n"
    "- Reply with a JSON array of strings and nothing else. No prose, no code "
    "fence.\n"
    "- The array must have exactly one entry per numbered posting, in the same "
    "order.\n"
    "- Each entry is either one field name copied exactly from the list above, "
    'or the string "unknown".\n'
    '- Use "unknown" when no field fits, when the posting is too vague to '
    "place, or when it is not freelance or remote work at all. A wrong label is "
    'worse than "unknown".\n'
    "- Judge by the role being hired for, not by the industry of the employer. "
    'A finance company hiring a developer is "Development / tech".\n'
    "- Postings may be in any language. Label them the same way."
)


# Why the last call failed, in words. A background job that fails silently is
# indistinguishable from one that has nothing to do, and this one spent an
# afternoon looking like the latter while being the former.
LAST_REASON = ""


def enabled() -> bool:
    """Only when there is a key to spend and a client to spend it with."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False
    return True


def _prompt(gigs) -> str:
    out = []
    for i, g in enumerate(gigs, 1):
        title = (g.get("title") or "").strip()
        body = re.sub(r"\s+", " ", (g.get("body") or "")).strip()[:BODY_CHARS]
        out.append(f"{i}. {title}" + (f"\n   {body}" if body else ""))
    return ("Label each posting.\n\n" + "\n\n".join(out)
            + f"\n\nReturn a JSON array of exactly {len(gigs)} strings.")


def _parse(text: str, n: int):
    """
    The model's answer as a list of n labels, or None if it cannot be trusted.

    A short, long or unparseable array is rejected WHOLE rather than zipped up
    to whatever length matched. Truncation shifts every label after the missing
    one onto the wrong gig, which is silent and wrong everywhere, where a
    dropped batch is loud and wrong nowhere.
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|```$", "", text).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        got = json.loads(text[start:end + 1])
    except Exception:
        return None
    if not isinstance(got, list) or len(got) != n:
        return None
    out = []
    for label in got:
        # str() is NOT applied to a non-string: repr'ing ["Design / creative"]
        # strips down to the same key as the bare name, so a nested answer
        # would be accepted as if the model had returned the right shape. A
        # reply that is not a flat array of strings is a reply that misread the
        # format, and guessing what it meant is how a batch goes quietly wrong.
        if not isinstance(label, str):
            return None
        key = re.sub(r"[^a-z0-9]", "", label.lower())
        out.append(_CANON.get(key))          # None for "unknown" and for junk
    return out


def label(gigs, timeout: float = 60.0):
    """
    A list with a field name (or None) per gig, in order — or None if the call
    itself did not happen.

    THE TWO FAILURES ARE NOT THE SAME AND MUST NOT LOOK THE SAME. A list of
    Nones means the model read these gigs and could not place them, which is a
    real answer worth recording so they are never re-sent. A bare None means no
    answer exists: no key, no such model, no credit, a timeout. If those
    returned the same value the caller would mark the batch as checked, and one
    misconfigured deploy would silently burn the entire backlog — every gig
    marked read, none of them ever read, and nothing to retry because the mark
    is what stops the retry.

    `gigs` is a list of dicts with "title" and "body". Never raises: the caller
    is a background loop on a board that must keep serving.
    """
    global LAST_REASON
    gigs = list(gigs or [])
    if not gigs:
        return []
    if not enabled():
        LAST_REASON = ("no ANTHROPIC_API_KEY on this service"
                       if not os.environ.get("ANTHROPIC_API_KEY")
                       else "anthropic package not importable")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(timeout=timeout, max_retries=1)
        resp = client.messages.create(
            model=MODEL,
            # NOT 1000. Thinking tokens are drawn from max_tokens, and the
            # default model here thinks unless told otherwise, so a batch that
            # took a little deliberation spent the budget before writing its
            # answer. The reply came back truncated, _parse rejected it for the
            # right reason, and the whole batch was dropped — silently, since a
            # dropped batch marks nothing and simply retries later. Measured on
            # production: cycles were running every ~3 minutes and placing 20
            # gigs roughly one cycle in eight. Room to think AND answer.
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": _prompt(gigs)}],
        )
        stop = getattr(resp, "stop_reason", "")
        if stop == "refusal":
            LAST_REASON = "model declined the batch"
            return None
        if stop == "max_tokens":
            LAST_REASON = "ran out of max_tokens before finishing the answer"
            return None
        # Text blocks only: on a model that thinks by default the reply also
        # carries thinking blocks, which have no .text to join.
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        # _parse returns None for an answer whose shape cannot be trusted,
        # which is a failed call by any useful definition: nothing was learned,
        # so nothing should be marked.
        got = _parse(text, len(gigs))
        if got is None:
            LAST_REASON = (f"unusable answer (stop={stop}, {len(text)} chars): "
                           f"{text[:120]!r}")
        else:
            LAST_REASON = ""
        return got
    except Exception as e:
        LAST_REASON = f"{type(e).__name__}: {e}"[:200]
        print(f"  ! llm classify failed ({LAST_REASON})", flush=True)
        return None

"""
classify.py — the v0 "brain" for Nabbly.

Given a gig post's title + body, decide:
  - is this a real CLIENT hiring (demand)?  -> title tag [Hiring] / [Task]
  - what SKILL is it?                        -> job type
  - how big is the BUDGET?                   -> job size
  - is it URGENT?

Keyword rules only (no API key, no cost). We can upgrade to an AI classifier later.
"""
import re
import config

_MONEY = re.compile(r"[$£€]\s?([0-9][0-9,]*)")


def _contains_any(text, phrases):
    return any(p in text for p in phrases)


def _budget_amounts(text):
    out = []
    for m in _MONEY.findall(text):
        try:
            out.append(int(m.replace(",", "")))
        except ValueError:
            pass
    return out


def classify(title: str, body: str, source: str) -> dict:
    title_l = (title or "").lower()
    text = f"{title} {body}".lower()

    # --- Is this a client hiring (demand)? ---
    # Reddit gig posts must carry a [Hiring]/[Task] tag; job-board postings are
    # all real openings, so they count as demand automatically.
    if source == "reddit":
        is_demand = _contains_any(title_l, config.HIRING_TAGS)
    else:
        is_demand = True

    # --- Skill: prefer a match in the TITLE (names the real role); the body
    # often mentions other skills in passing, so only fall back to it. ---
    job_type = "Other / general"
    for skill, keywords in config.JOB_TYPES.items():
        if _contains_any(title_l, keywords):
            job_type = skill
            break
    else:
        for skill, keywords in config.JOB_TYPES.items():
            if _contains_any(text, keywords):
                job_type = skill
                break

    # --- Budget tier ---
    amounts = _budget_amounts(text)
    top = max(amounts) if amounts else None
    monthly = _contains_any(text, config.BIG_JOB_SIGNALS)
    small_sig = _contains_any(text, config.SMALL_JOB_SIGNALS)

    if monthly or (top is not None and top >= 800):
        size_tier = "Large"
    elif (top is not None and top <= 60) or (small_sig and not top):
        size_tier = "Small"
    elif top is not None:
        size_tier = "Medium"
    else:
        size_tier = "Medium"  # unknown budget -> middle by default

    urgency = "Urgent" if _contains_any(text, config.URGENT_SIGNALS) else ""

    return {
        "is_demand": 1 if is_demand else 0,
        "job_type": job_type,
        "size_tier": size_tier,
        "urgency": urgency,
    }

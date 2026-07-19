"""
profile.py — the user's saved profile (Free feature, powers everything else).

Stores who you are and what you want, in profile.json:
  - skills:     the skills you offer (used for fit scores + the daily digest)
  - rate_floor: your minimum acceptable budget (used for fit + lowball flags)
  - keywords:   comma-separated words you care about (used for fit scores)
  - name, portfolio: used to personalize drafted pitches
"""
import json

from paths import data_file

PATH = data_file("profile.json")
DEFAULT = {
    "name": "",         # for pitches
    "headline": "",     # e.g. "Brand & logo designer" — used in pitches
    "skills": [],       # fit scores + digest
    "rate_floor": 0,    # fit + lowball flags
    "rate_unit": "hr",  # "hr" or "project"
    "keywords": "",     # boost matches (comma-separated)
    "mute": "",         # hide gigs containing these (comma-separated)
    "portfolio": "",    # link, used in pitches
    "bio": "",          # one-line intro, used in pitches
    "country": "",      # for eligibility matching (US-only remote, etc.)
    "city": "",         # for surfacing local / on-site gigs near you
}

# Fields that count toward "profile completeness".
COMPLETENESS_FIELDS = ["name", "headline", "skills", "rate_floor",
                       "keywords", "portfolio", "bio"]


def load() -> dict:
    if PATH.exists():
        try:
            return {**DEFAULT, **json.loads(PATH.read_text())}
        except Exception:
            pass
    return dict(DEFAULT)


def completeness(p: dict) -> int:
    """Percent of key fields filled in (0-100)."""
    filled = sum(1 for f in COMPLETENESS_FIELDS if p.get(f))
    return round(100 * filled / len(COMPLETENESS_FIELDS))


def save(p: dict):
    PATH.write_text(json.dumps({**DEFAULT, **p}, indent=2))

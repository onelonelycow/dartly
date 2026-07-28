"""
location.py — where a gig can be done, and whether *you* can do it.

Most "remote" gigs are quietly geo-fenced ("US only", "EMEA", a timezone), and a
handful are hands-on / on-site. This reads each gig's text and tags:
  - remote:    can it be done remotely at all?
  - onsite:    does it need someone physically present?
  - worldwide: explicitly open to anyone, anywhere?
  - restrict:  region it's *limited* to (US / EU / UK / Canada / India), or None.

Then `eligible()` answers "can someone in <my country> actually take this?" and
`is_local()` answers "is this hands-on work in my city?". It's a keyword read, not
a legal check — approximate, but enough to stop showing people jobs they can't take.
"""
import re

# Regions a gig may be *restricted* to. Match the "…only / …based / must be in…"
# shapes, not a bare country mention (a company HQ isn't an eligibility rule).
_RESTRICT = [
    ("US",     r"u\.?s\.?a?[\s\-]?(?:only|based|residents?|citizens?)"
               r"|(?:must be|only)\s+(?:in|located in|based in|authorized to work in)\s+the\s+u\.?s"
               r"|us\s+candidates?\s+only|america[ns]?\s+only|\bus[\-\s]based\b"),
    ("EU",     r"\b(?:eu|eea)[\s\-]?(?:only|based|residents?)"
               r"|(?:must be|only)\s+(?:in|based in)\s+(?:the eu|europe)"
               r"|europe[\s\-]?only|emea\s+only"),
    ("UK",     r"\buk[\s\-]?(?:only|based|residents?)"
               r"|(?:must be|only)\s+(?:in|based in)\s+(?:the uk|england|britain)"),
    ("Canada", r"canad(?:a|ian)[\s\-]?(?:only|based|residents?)"),
    ("India",  r"\bindia[\s\-]?(?:only|based)\b|based in india"),
    ("Australia", r"australia[\s\-]?(?:only|based)|\banz\b\s+only"),
]

_ONSITE    = re.compile(r"on[\s\-]?site|in[\s\-]person|on location|on-location"
                        r"|must be (?:physically )?(?:present|on[\s\-]?site|local)"
                        r"|\bhybrid\b|local to |based in your area|no remote", re.I)
_REMOTE    = re.compile(r"\bremote\b|work from home|\bwfh\b|fully remote|100% remote"
                        r"|remote[\s\-]?(?:friendly|first|ok)", re.I)
_WORLDWIDE = re.compile(r"worldwide|anywhere in the world|any (?:location|country|timezone)"
                        r"|global(?:ly)?|remote\s*[\-–]\s*anywhere|open to all", re.I)

# What the profile's country dropdown offers, and how each maps to a region code.
COUNTRIES = ["United States", "United Kingdom", "European Union", "Canada",
             "India", "Australia", "Other / elsewhere"]
_COUNTRY_REGION = {
    "United States": "US", "United Kingdom": "UK", "European Union": "EU",
    "Canada": "Canada", "India": "India", "Australia": "Australia",
}


def country_region(country: str):
    """Map a profile country to the region code used in restrictions (or None)."""
    return _COUNTRY_REGION.get((country or "").strip())


def tag(gig: dict) -> dict:
    """Read a gig's text into location signals. Cheap enough to call per-render."""
    text = f"{gig.get('title','')} {gig.get('body','')}"
    tl = text.lower()
    restrict = None
    for code, pat in _RESTRICT:
        if re.search(pat, tl):
            restrict = code
            break
    onsite = bool(_ONSITE.search(tl))
    remote = bool(_REMOTE.search(tl))
    return {
        "remote": remote or bool(_WORLDWIDE.search(tl)),
        "onsite": onsite and not remote,          # "hybrid" leans remote-capable
        "worldwide": bool(_WORLDWIDE.search(tl)),
        "restrict": restrict,
    }


# ---------------------------------------------------------------------------
# City-locked gigs
# ---------------------------------------------------------------------------
# A title ending "… in New York City, NY" is a tell: that job wants someone in
# that metro, and showing it to everybody fills the board with work most people
# can't take. The anchor is a real US state / Canadian province code after a
# comma, or an explicit "onsite in <Place>" — not a bare capitalised word, which
# would match company names and wreck the board.
_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV "
    "WI WY DC AB BC MB NB NL NS ON PE QC SK"
).split()
_STATE_TAIL = re.compile(
    r",\s*(?:" + "|".join(_STATES) + r")\b(?:\s*,?\s*(?:USA|U\.S\.A?\.?|Canada))?\s*$",
    re.I)
_IN_PLACE = re.compile(r"\bin\s+([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3})"
                       r",\s*(?:" + "|".join(_STATES) + r")\b")
# Titles that end "in Remote" / "in Anywhere" are the opposite of city-locked.
_NOT_A_PLACE = re.compile(r"^(remote|anywhere|worldwide|global|usa?|uk)$", re.I)


def city_lock(gig: dict) -> str:
    """
    The city a gig is tied to, or '' if it isn't tied to one.

    Deliberately conservative: it only fires on a comma plus a real state or
    province code, because a false positive here HIDES a gig, and a board that
    quietly drops real work is worse than one showing a few it shouldn't.
    """
    title = str(gig.get("title") or "")
    # If the poster put "Remote" in the TITLE, take them at their word —
    # "Sr. Consultant | Remote, Vancouver, BC" is a remote job that happens to
    # name an office, not a job that needs you in Vancouver.
    if _REMOTE.search(title):
        return ""
    m = _IN_PLACE.search(title)
    if m:
        place = m.group(1).strip()
        if not _NOT_A_PLACE.match(place):
            return place
    if _STATE_TAIL.search(title):
        # "Company: Role — Austin, TX" with no "in"
        tail = title.rsplit(",", 1)[0]
        place = tail.rsplit("—", 1)[-1].rsplit("-", 1)[-1].rsplit(":", 1)[-1].strip()
        place = place.split()[-1] if place else ""
        if place and not _NOT_A_PLACE.match(place):
            return place
    return ""


def city_ok(gig: dict, user_city: str | None, allow_anywhere: bool = False) -> bool:
    """
    Should this city-locked gig be on THIS person's board?

    True when it isn't city-locked at all, when they've asked to see them
    regardless (they'd travel or relocate), or when it names their own city.
    """
    place = city_lock(gig)
    if not place or allow_anywhere:
        return True
    city = (user_city or "").strip().lower()
    if not city:
        return False
    hay = f"{gig.get('title','')} {gig.get('body','')}".lower()
    return city in hay


def label(t: dict) -> str:
    """Short pill text for a location tag. '' if nothing to say."""
    if t.get("onsite"):
        return "On-site"
    if t.get("restrict"):
        return f"{t['restrict']}-only"
    if t.get("worldwide"):
        return "Worldwide"
    if t.get("remote"):
        return "Remote"
    return ""


def eligible(t: dict, user_region: str | None) -> bool:
    """Could someone in `user_region` take this gig? Unknown region → assume yes."""
    r = t.get("restrict")
    if r and user_region and r != user_region:
        return False
    return True


_EU_CODES = {"DE", "FR", "ES", "IT", "NL", "IE", "PT", "BE", "AT", "SE", "DK",
             "FI", "PL", "CZ", "GR", "RO", "HU", "SK", "BG", "HR", "SI", "LT",
             "LV", "EE", "LU", "MT", "CY"}


def geo_from_ip() -> dict:
    """Best-effort {country, city} from this machine's public IP. Empty on failure.

    Note: on a hosted server this reads the *server's* location, not the visitor's —
    fine as a pre-fill the user can correct; a real deploy would use the browser instead.
    """
    import json
    import urllib.request
    try:
        url = "http://ip-api.com/json/?fields=status,country,city,countryCode"
        with urllib.request.urlopen(url, timeout=4) as resp:
            d = json.loads(resp.read().decode())
        if d.get("status") != "success":
            return {"country": "", "city": ""}
        cc = d.get("countryCode") or ""
        country = {"US": "United States", "GB": "United Kingdom", "CA": "Canada",
                   "IN": "India", "AU": "Australia"}.get(cc)
        if not country and cc:
            country = "European Union" if cc in _EU_CODES else "Other / elsewhere"
        return {"country": country or "", "city": d.get("city") or ""}
    except Exception:
        return {"country": "", "city": ""}


def is_local(gig: dict, user_city: str | None) -> bool:
    """Hands-on gig that names the user's city (rough 'near me' match)."""
    city = (user_city or "").strip().lower()
    if not city:
        return False
    text = f"{gig.get('title','')} {gig.get('body','')}".lower()
    return city in text

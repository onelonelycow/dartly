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


def label(t: dict) -> str:
    """Short pill text for a location tag (emoji + words). '' if nothing to say."""
    if t.get("onsite"):
        return "📍 On-site"
    if t.get("restrict"):
        return f"🌐 {t['restrict']}-only"
    if t.get("worldwide"):
        return "🌍 Worldwide"
    if t.get("remote"):
        return "🌍 Remote"
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

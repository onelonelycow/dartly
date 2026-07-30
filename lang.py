"""
lang.py — what language a gig is written in.

9% of the board arrives in German, Dutch, Spanish or French, because several
of the feeds we read are European. That's real work for someone who reads
those languages and pure noise for everyone else, so the board hides what you
can't read unless you say otherwise (Profile → "Show gigs in other languages").

Deliberately a stopword count, not a dependency. Language detection libraries
carry models worth tens of megabytes, and the memory ceiling on this instance
is the reason half of today's work exists. Function words are the strongest
cheap signal there is: three or more hits is decisive on job-post prose, and
anything below that stays English, which is the safe default — an unlabelled
English gig costs nothing, a wrongly hidden one costs someone the work.
"""
import re

# Function words, not vocabulary. "Design" and "Marketing" appear in every
# language's job ads; "und", "voor" and "buscamos" do not.
# NOTHING SHORTER THAN THREE LETTERS, and nothing that shows up inside a URL.
# The first draft of this included Portuguese "e|o|a" and Italian "e|i|il|la",
# which matched English prose on every line — it labelled 1,797 English gigs
# Portuguese, including "Toptal: Technical Project Manager". It also had "com",
# which \b-matches inside "example.com". Single letters and web-safe fragments
# are worthless as discriminators; only distinctive multi-letter function words
# earn a place here.
_SIGNALS = {
    "de": r"\b(und|oder|der|die|das|den|dem|für|mit|bei|wir|uns|unsere[nrs]?|"
          r"suchen|Ihre[nrs]?|Aufgaben|Kenntnisse|Erfahrung|Berufserfahrung|"
          r"Stelle|Mitarbeiter|Bewerbung|Deine|Deinen|m/w/d|w/m/d|"
          r"sowie|auch|nicht|sind|haben|werden|einen|eine|über|durch|zum|zur)\b",
    "nl": r"\b(het|een|voor|met|wij|jij|jouw|zoeken|ervaring|"
          r"functie|vacature|sollicitatie|werkzaamheden|"
          r"onze|niet|van|zijn|worden|binnen|waarbij|jaar)\b",
    "es": r"\b(los|las|una|para|nosotros|buscamos|experiencia|"
          r"conocimientos|trabajo|puesto|empresa|requisitos|desarrollo|"
          r"del|con|por|que|más|sobre|nuestra|nuestro|será|tus|sus|"
          r"equipo|puedes|tendrás)\b",
    "fr": r"\b(les|une|des|pour|avec|nous|vous|votre|recherche|"
          r"expérience|poste|entreprise|profil|travail|"
          r"dans|sur|est|sont|aux|notre|nos|vos|chez|ainsi|également|"
          r"missions|compétences)\b",
    # Portuguese was the thinnest list here and it showed: a real Brazilian
    # security post ("Analista Senior de Acessos e Identidades") matched only
    # "trabalho", twice, which is 2 hits against a threshold of 3 — so it sat
    # on the board in Portuguese. Enriched with the function words that
    # actually carry Portuguese prose, none of which collide with English.
    "pt": r"\b(uma|para|nós|procuramos|experiência|"
          r"conhecimentos|trabalho|vaga|empresa|desenvolvimento|"
          r"sobre|nossa|nosso|você|sua|seu|dos|das|pela|pelo|mas|"
          r"não|são|está|também|atuação|área|equipe|conhecimento|"
          r"remoto|vagas|requisitos|desejável)\b",
    "it": r"\b(una|per|noi|cerchiamo|esperienza|"
          r"conoscenze|lavoro|azienda|requisiti|sviluppo|"
          r"del|della|con|che|più|nostra|nostro|sono|anche|presso|"
          r"attività|competenze)\b",
}
_COMPILED = {k: re.compile(v, re.I) for k, v in _SIGNALS.items()}

NAMES = {"de": "German", "nl": "Dutch", "es": "Spanish", "fr": "French",
         "pt": "Portuguese", "it": "Italian", "en": "English"}

# Which language a profile country implies, so someone in Germany keeps their
# German gigs without having to find a setting.
COUNTRY_LANG = {
    "Germany": "de", "Austria": "de", "Switzerland": "de",
    "Netherlands": "nl", "Belgium": "nl",
    "Spain": "es", "Mexico": "es", "Argentina": "es",
    "France": "fr", "Portugal": "pt", "Brazil": "pt", "Italy": "it",
}

_MIN_HITS = 3
_SAMPLE = 500      # first N chars is plenty; job prose declares itself early


def detect(title: str, body: str = "") -> str:
    """
    Two-letter code, or 'en' when nothing else wins.

    English is the fallback rather than a detected class of its own: English
    function words ("and", "the", "for") appear inside plenty of German posts
    too, so scoring it would create ties. Absence of evidence for anything
    else is the signal.
    """
    text = f"{title or ''} {str(body or '')[:_SAMPLE]}"
    if not text.strip():
        return "en"
    best, best_hits = "en", 0
    for code, pat in _COMPILED.items():
        # DISTINCT words, not total occurrences. One word repeated is one piece
        # of evidence, not three: a German post that says "und" three times was
        # already caught, but an English post that happens to repeat a single
        # borrowed word ("una", "des", a "de" in a place name) used to be able
        # to clear the threshold on that word alone. Requiring three DIFFERENT
        # function words is what actually distinguishes prose in a language
        # from prose that mentions one of its words.
        hits = len({m.lower() for m in pat.findall(text)})
        if hits > best_hits:
            best, best_hits = code, hits
    return best if best_hits >= _MIN_HITS else "en"


def label(code: str) -> str:
    return NAMES.get(code, code.upper())

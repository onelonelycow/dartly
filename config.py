"""
config.py — the "settings" for Nabbly.

This is the ONE file you can safely edit yourself without knowing how to code.
It's just lists of words and source names. Add/remove between the quotes, keep commas.

Nabbly aggregates public "who's hiring" demand from MANY sources (freelance gig
boards + remote job boards), classifies each by SKILL and BUDGET, and surfaces the
freshest matching opportunities so a user can respond first.
"""

# ---------------------------------------------------------------------------
# SOURCES — turn each on/off by keeping/removing it from this list.
# Each is a public API or feed that needs no login or API key.
# ---------------------------------------------------------------------------
ENABLE_SOURCES = [
    # DISABLED 2026-08-13 — Reddit blocks anonymous RSS. It answers with HTTP
    # 200 and an HTML login wall ("Your request has been blocked by network
    # security"), so nothing errored and nothing parsed: measured 0 gigs from
    # all four subreddits, while spending 54 seconds of the 90-second cycle
    # budget on the deliberate 18s pauses between them. Sixty per cent of
    # every fetch cycle, returning nothing, pushing real sources past the
    # budget and into the next pass.
    #
    # To bring it back it needs the official API (praw is already a
    # dependency) and REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET. Re-enabling it
    # without those puts the same 54-second hole straight back.
    # "reddit",        # r/forhire & friends — freelance [Hiring] gigs
    "freelancer",      # Freelancer.com — many small fixed-price projects
    "remoteok",        # RemoteOK — remote jobs/contracts
    "remotive",        # Remotive — remote jobs
    "arbeitnow",       # Arbeitnow — remote/EU jobs
    "jobicy",          # Jobicy — remote jobs
    "weworkremotely",  # We Work Remotely — remote jobs
    "workingnomads",   # Working Nomads — curated remote jobs, direct outbound apply
    # Config-only boards (see RSS_SOURCES below)
    # DRIBBBLE CUT 2026-08-21. Its feed publishes titles and nothing else:
    # fetched live, 54 items, every single description zero characters long.
    # That is the feed, not our parser — sources.fetch_rss returns the same 54
    # rows with empty bodies. All 20 dribbble gigs on the board had a body
    # under 60 characters, which is 100% of them.
    #
    # A gig with no description cannot be classified beyond its title, cannot
    # have a budget read off it, and cannot have a reply drafted from it, which
    # is the thing Pro is sold on. It was 0.03% of the board and a
    # disproportionate share of the "about a third of listings are thin"
    # number that has to be defensible.
    #
    # Not fixable cheaply: the descriptions exist on Dribbble's own listing
    # pages, so recovering them means an HTTP fetch per item on a source
    # contributing twenty gigs.
    "himalayas", "realworkfromanywhere", "jobspresso", "pythonjobs",
    "larajobs", "wpjobs", "wwr_design", "wwr_devops", "wwr_support", "wwr_other",
    # vertical backfill
    "jobicy_health", "jobicy_legal", "jobicy_finance", "jobicy_edu",
    "jobicy_writing", "jobicy_hr", "jobicy_admin", "jobicy_support",
    "jobicy_design", "jobicy_pm", "jobicy_business", "jobicy_mgmt",
    "jobicy_marketing", "wwr_fullstack", "wwr_product",
    # unique boards filling thin verticals (3D, no-code, healthcare, events)
    "blenderartists", "threejs", "bubble", "nurserecruiter", "entcareers",
    "soundlister",     # Soundlister — audio/sound-design jobs; bespoke fetcher,
                        # its feed is weekly roundup posts, not one-item-per-job
    # ADDED 2026-08-20, after measuring the gap rather than guessing at it.
    # Sales / outreach was 9.4% of the board with NO dedicated source at all,
    # and management none either — both categories exist on We Work Remotely
    # and had simply never been wired up. Every feed below was fetched and its
    # titles compared against the 53,270 already on the board, so these are
    # ranked by work Nabbly does not already have, not by how busy they look:
    #   jobicy_dev      100 gigs a pass   the largest field on the board
    #   wwr_sales       123 gigs a pass   a field that had nothing
    #   wwr_management   43 gigs a pass
    #
    # NOT ADDED, and two of them are worth recording. jobicy_seo returned 2 new
    # of 9, not worth a fetch slot. remotive and nodesk measured well but are
    # AGGREGATORS: they re-list other boards, so they duplicate over time and an
    # /out/ click lands on a middleman rather than the source.
    #
    # AND TWO THAT LOOKED PERFECT AND WERE NOT JOBS AT ALL. authenticjobs and
    # codeable both scored 100% "new" against the board and both are BLOG
    # feeds — "How to Get a Design Job in 2026", "Codeable vs Toptal". They
    # scored perfectly BECAUSE they are articles: an article never matches a job
    # title already on the board, so the uniqueness check was measuring the
    # wrong thing and rewarding the worst possible result. Caught by reading the
    # parsed titles instead of trusting the count. Any future candidate gets the
    # same treatment: fetch it, print the titles, read them.
    "jobicy_dev", "wwr_sales", "wwr_management",
]

# ---------------------------------------------------------------------------
# Boards added by CONFIG rather than code.
#
# Every source above needed a bespoke fetcher, which does not scale to "a board
# for every career" — each new one is code to write and maintain. Anything that
# publishes an RSS feed can be switched on with one line here instead, so the
# bottleneck becomes finding good feeds rather than writing scrapers.
#
# Each entry was probed before being added; a feed that returned nothing or an
# article list instead of jobs was left out. "source" lets several feeds fold
# into one board (We Work Remotely publishes per-category feeds that carry rows
# its main feed misses; they dedupe against it because they share a source).
#
# WORTH KNOWING: the verticals people ask for most (media, journalism, video,
# nonprofit) publish no feeds at all — ProductionHUB, Mandy, Stage32, Poynter,
# Idealist and Video Consortium were all checked and none expose one. Their
# demand lives in Slack rooms and listservs, which no crawler can reach. That
# gap is an inbox problem, not a scraping one.
# ---------------------------------------------------------------------------
RSS_SOURCES = {
    "dribbble":   {"url": "https://dribbble.com/jobs.rss",
                   "label": "Dribbble"},
    "himalayas":  {"url": "https://himalayas.app/jobs/rss",
                   "label": "Himalayas"},
    # See the note in ENABLE_SOURCES for why these five and not the others.
    "jobicy_dev": {"url": "https://jobicy.com/?feed=job_feed&job_categories=dev",
                   "label": "Jobicy"},
    "wwr_sales":  {"url": "https://weworkremotely.com/categories/"
                          "remote-sales-and-marketing-jobs.rss",
                   "label": "We Work Remotely"},
    "wwr_management": {"url": "https://weworkremotely.com/categories/"
                              "remote-management-and-finance-jobs.rss",
                       "label": "We Work Remotely"},
    # General remote-jobs board, same shape as RemoteOK/Remotive above. Its
    # own listing page (not the feed link) carries the real employer apply
    # link with no login — confirmed on a live posting, an AshbyHQ link sat
    # right on the page — same one-extra-click pattern several sources here
    # already have, not a paywall.
    "realworkfromanywhere": {"url": "https://www.realworkfromanywhere.com/rss.xml",
                   "label": "Real Work From Anywhere"},
    "pythonjobs": {"url": "https://www.python.org/jobs/feed/rss/",
                   "label": "Python.org"},
    # Replaces nodesk (removed): checked two real listings and the actual
    # apply link sat behind a button reading "Subscribe to Apply" on both —
    # a paywall, not a job board. Jobspresso runs on WP Job Manager (same
    # plugin family as WordPress Jobs below) and its real apply mechanism,
    # confirmed on a live listing, is a direct email or a direct outbound
    # URL — no Jobspresso account of any kind.
    "jobspresso": {"url": "https://jobspresso.co/feed/?post_type=job_listing",
                   "label": "Jobspresso"},
    "larajobs":   {"url": "https://larajobs.com/feed",
                   "label": "LaraJobs"},
    "wpjobs":     {"url": "https://jobs.wordpress.net/feed/",
                   "label": "WordPress Jobs"},
    "wwr_design": {"url": "https://weworkremotely.com/categories/remote-design-jobs.rss",
                   "label": "We Work Remotely", "source": "weworkremotely"},
    "wwr_devops": {"url": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
                   "label": "We Work Remotely", "source": "weworkremotely"},
    "wwr_support": {"url": "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
                    "label": "We Work Remotely", "source": "weworkremotely"},
    "wwr_other":  {"url": "https://weworkremotely.com/categories/all-other-remote-jobs.rss",
                   "label": "We Work Remotely", "source": "weworkremotely"},

    # --- Vertical backfill (slow cadence; see sources._SLOW_EVERY) ------------
    # Healthcare, legal, finance, education, HR and admin barely appear in the
    # general boards. These category feeds are where those verticals actually
    # live, and they fold into their parent source so they dedupe against it.
    "jobicy_health": {"url": "https://jobicy.com/?feed=job_feed&job_categories=healthcare",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_legal": {"url": "https://jobicy.com/?feed=job_feed&job_categories=legal",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_finance": {"url": "https://jobicy.com/?feed=job_feed&job_categories=accounting-finance",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_edu": {"url": "https://jobicy.com/?feed=job_feed&job_categories=education",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_writing": {"url": "https://jobicy.com/?feed=job_feed&job_categories=copywriting",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_hr": {"url": "https://jobicy.com/?feed=job_feed&job_categories=hr",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_admin": {"url": "https://jobicy.com/?feed=job_feed&job_categories=admin",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_support": {"url": "https://jobicy.com/?feed=job_feed&job_categories=technical-support",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_design": {"url": "https://jobicy.com/?feed=job_feed&job_categories=design-multimedia",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_pm": {"url": "https://jobicy.com/?feed=job_feed&job_categories=project-management",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_business": {"url": "https://jobicy.com/?feed=job_feed&job_categories=business",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_mgmt": {"url": "https://jobicy.com/?feed=job_feed&job_categories=management",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "jobicy_marketing": {"url": "https://jobicy.com/?feed=job_feed&job_categories=marketing",
                   "label": "Jobicy", "source": "jobicy", "slow": True},
    "wwr_fullstack": {"url": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
                   "label": "We Work Remotely", "source": "weworkremotely", "slow": True},
    "wwr_product": {"url": "https://weworkremotely.com/categories/remote-product-jobs.rss",
                   "label": "We Work Remotely", "source": "weworkremotely", "slow": True},

    # --- Unique boards that fill verticals the big feeds barely touch --------
    # Each verified live (fresh 2026 items) before adding, and each is its own
    # board rather than another remote-jobs aggregator, so they diversify away
    # from Freelancer.com instead of duplicating it. All "slow": niche backfill,
    # not freshness-critical — fetched on the ~30-min cadence.
    "blenderartists": {"url": "https://blenderartists.org/c/jobs/paid-work/53.rss",
                   "label": "Blender Artists", "slow": True},      # 3D / animation, paid gigs
    "threejs": {"url": "https://discourse.threejs.org/c/jobs/9.rss",
                   "label": "three.js", "slow": True},             # 3D / WebGL, freelance-heavy
    "bubble": {"url": "https://forum.bubble.io/c/jobs-freelance/13.rss",
                   "label": "Bubble Forum", "slow": True},         # no-code app dev, freelance
    "nurserecruiter": {"url": "https://www.nurserecruiter.com/rss",
                   "label": "NurseRecruiter", "slow": True},       # healthcare, travel/contract RN
    "entcareers": {"url": "https://www.entertainmentcareers.net/ecnjcat124",
                   "label": "EntertainmentCareers", "slow": True}, # events / film / live production
}

# Subreddits where CLIENTS post gigs. slavelabour = small/micro paid tasks.
SUBREDDITS = ["forhire", "freelance_forhire", "jobbit", "slavelabour"]

# A Reddit post is real DEMAND if its title carries one of these tags.
HIRING_TAGS = ["[hiring]", "[task]"]


# NOT AN OPENING — postings that are not a job a person can apply to and be paid
# for. These are removed from the board, not merely ranked down, because showing
# one is the board saying something untrue: "Expression of Interest - Account
# Executive" has a body that reads "this is an expression of interest for future
# opportunities, not a live vacancy". FEEL.md §7 makes that a spec violation
# rather than a matter of taste.
#
# NOT A SIZE MEASURE. It removes about 190 rows from a 53,000-row board. The
# case for it is honesty, and any argument that starts with disk or memory is
# the wrong argument.
#
# MATCHED AGAINST THE TITLE ONLY, NEVER THE BODY. Measured 2026-08-22: "talent
# pool" appears in the BODY of 100 rows whose titles are clean, "candidate pool"
# in 29, "(unpaid)" in 29. Those are real jobs that mention a talent pool or an
# unpaid trial in passing. Matching the body would turn a 190-row fix into the
# deletion of 158 real openings.
#
# THREE TRAPS, ALL MEASURED, DO NOT ADD THEM BACK:
#   "pipeline"      54 hits, all false. It is a data-engineering word:
#                   "AWS EC2 Jenkins Pipeline", "AI Video Pipeline Build".
#   "survey"        a PROFESSION. "Quantity Surveyor", "Land Survey Drafter",
#                   "Regulatory Asbestos Survey Report Writing" are real gigs.
#                   Same shape as bare "hr" matching "$77/hr".
#   "do not apply"  catches the real test postings, but also "AI Film Trailer
#                   Creator MUST BE US BASED DO NOT APPLY IF NOT". Anchor on
#                   "test job"/"test posting" instead.
# Also excluded after measuring: "evergreen" (1 of 3 is a real agency role,
# 33% churn), "career fair" (1 row), "we are hiring" (1 row, a real gig).
#
# UNPAID IS INCLUDED, AND THE RULE IS POSITIONAL. "Volunteer Coordinator" is a
# PAID staff role that manages volunteers; "Marketing Manager (Remote,
# Volunteer)" is unpaid work. Volunteer-as-qualifier is parenthesised or trails
# the role noun; volunteer-as-object precedes it. So bare "volunteer",
# "volunteer coordinator" and "volunteer manager" are deliberately absent.
# All 20 matched rows were read individually: zero paid roles among them.
#
# German and Portuguese carry a third of the catch despite being 9% of the
# board, because "Initiativbewerbung" and "Banco de Talentos" are common
# posting types there. Spanish, French, Italian and Dutch equivalents measured
# near zero and are left out rather than carried dead.
#
# NO STEMS. Every phrase here must be whole words, unlike JOB_TYPES below which
# allows stems. The matcher whole-word-bounds anything alphanumeric at both
# ends, so a stem like "candidature spontan" compiles into a rule that can
# never match — the é that follows is a word character and the boundary
# refuses. That exact bug shipped and was caught in review; "opportunit*" needs
# both "future opportunity" AND "future opportunities" for the same reason
# (an optional trailing s cannot turn y into ies).
# What someone TYPES in the category box, mapped to the field the classifier
# files it under. Feeds the datalist typeahead on the board: typing "web dev"
# suggests and resolves to Development / tech. Hand-curated from JOB_TYPES
# keywords - English, reads as a job, unambiguous across fields. NO COUNTS
# ride along anywhere this is rendered (category tallies live on Market).
FIELD_ALIASES = {
    "web development": "Development / tech",
    "web dev": "Development / tech",
    "software engineer": "Development / tech",
    "full stack": "Development / tech",
    "front end": "Development / tech",
    "back end": "Development / tech",
    "mobile app": "Development / tech",
    "wordpress": "Development / tech",
    "data analyst": "Data / analytics",
    "data science": "Data / analytics",
    "data engineer": "Data / analytics",
    "machine learning": "Data / analytics",
    "civil engineer": "Engineering",
    "mechanical engineer": "Engineering",
    "electrical engineer": "Engineering",
    "software testing": "QA / testing",
    "quality assurance": "QA / testing",
    "help desk": "IT / support",
    "tech support": "IT / support",
    "graphic design": "Design / creative",
    "logo design": "Design / creative",
    "ui design": "Design / creative",
    "ux design": "Design / creative",
    "illustration": "Design / creative",
    "video editing": "Video / animation",
    "animation": "Video / animation",
    "after effects": "Video / animation",
    "audio engineer": "Audio / music",
    "music production": "Audio / music",
    "podcast editing": "Audio / music",
    "photo editing": "Photography",
    "product photography": "Photography",
    "3d artist": "Architecture / 3D",
    "3d model": "Architecture / 3D",
    "interior design": "Architecture / 3D",
    "cad drafting": "Architecture / 3D",
    "content writer": "Writing / content",
    "copywriting": "Writing / content",
    "blog writing": "Writing / content",
    "technical writing": "Writing / content",
    "ghostwriting": "Writing / content",
    "translation": "Translation / language",
    "transcription": "Translation / language",
    "subtitling": "Translation / language",
    "online tutor": "Teaching / tutoring",
    "course creator": "Teaching / tutoring",
    "social media": "Marketing / SEO",
    "seo": "Marketing / SEO",
    "email marketing": "Marketing / SEO",
    "google ads": "Marketing / SEO",
    "digital marketing": "Marketing / SEO",
    "lead generation": "Sales / outreach",
    "cold calling": "Sales / outreach",
    "account executive": "Sales / outreach",
    "business development": "Sales / outreach",
    "product manager": "Product / PM",
    "project manager": "Management / operations",
    "operations manager": "Management / operations",
    "virtual assistant": "Admin / VA",
    "data entry": "Admin / VA",
    "admin assistant": "Admin / VA",
    "bookkeeping": "Finance / accounting",
    "accountant": "Finance / accounting",
    "payroll": "Finance / accounting",
    "recruiter": "HR / recruiting",
    "talent acquisition": "HR / recruiting",
    "business analyst": "Consulting / strategy",
    "business plan": "Consulting / strategy",
    "customer service": "Customer support",
    "customer success": "Customer support",
    "contract review": "Legal",
    "paralegal": "Legal",
    "nurse": "Healthcare / medical",
    "medical billing": "Healthcare / medical",
    "clinical research": "Healthcare / medical",
}

NOT_AN_OPENING = {
    "open_application": [
        "general application", "open application", "open applications",
        "spontaneous application", "speculative application", "speculative cv",
        "unsolicited application", "general interest", "introduce yourself",
        "initiativbewerbung", "banco de talentos",
        "candidature spontanée", "candidature spontanee",
    ],
    "talent_pool": [
        "talent pool", "talent pooling", "talent community", "talent network",
        "candidate pool", "join our talent",
    ],
    "future": [
        "expression of interest", "register your interest", "future opening",
        "future opportunity", "future opportunities",
        "future consideration", "futuras oportunidades",
    ],
    "test_posting": [
        "test job", "test posting",
    ],
    "unpaid": [
        "(volunteer)", "(unpaid)", "(volunteer, unpaid)", "(unpaid/remote)",
        "(remote, volunteer)", "(volunteer / portfolio credit)",
        "volunteer position", "volunteer role", "unpaid internship",
        "- unpaid",
    ],
}

# ---------------------------------------------------------------------------
# SKILL (the "skill" toggles in the dashboard come from these)
# Each skill maps to words that signal it. First match wins, top to bottom.
# ---------------------------------------------------------------------------
# Matched as WHOLE WORDS, not substrings (see classify._skill_re), so short
# keywords like "api", "seo", "hr", "va", "bot" are safe now — "bot" no longer
# hits "both", "api" no longer hits "capital". Keywords are tried per category
# in this order, title first then body, so put the more specific categories
# above the broad ones. Stems (no trailing letters) still match the base word
# only: "illustrat" matches "illustrate"/"illustrator" but not partial words.
# Non-English terms below (DE/NL/ES/FR/PT/IT) exist because classify() sees
# every gig regardless of language, but until this was filled in, EVERY
# non-English category list except a handful of ad-hoc German/Spanish
# additions was empty — a German, Dutch, French, Portuguese or Italian post
# had nothing to match and fell through to "Other / general" by default,
# silently losing its real skill category for roughly 9% of the board (the
# same slice lang.py detects and can hide). Same discipline as the English
# list and lang.py's own function-word lists: compounds and full role nouns
# only, nothing short/generic enough to collide with an unrelated category.
JOB_TYPES = {
    "Video / animation": [
        "video edit", "video editor", "video editing", "animation",
        "animator", "motion graphic", "motion designer", "after effects",
        "premiere", "youtube", "shorts", "reels",
        "vfx", "videographer", "video producer", "videoeditor",
        "videoschnitt", "cutter", "trickfilmzeichner", "videomontage",
        "animatiefilm", "videobewerking", "editor de video", "edición de video",
        "monteur vidéo", "montage vidéo", "editor de vídeo", "edição de vídeo",
        "montaggio video", "editor video"
    ],
    "Design / creative": [
        "logo", "brand", "branding", "head of design",
        "graphic design", "graphic designer", "designer", "illustrator",
        "illustration", "figma", "ui/ux", "ui design",
        "ux design", "ux/ui", "photoshop", "packaging",
        "wordmark", "product design", "creative director", "art director",
        "web design", "grafikdesigner", "grafikdesign", "mediengestalter",
        "produktdesigner", "webdesigner", "grafisch ontwerper", "vormgever",
        "productontwerper", "diseñador gráfico", "diseño gráfico", "diseñador ux",
        "diseñador de producto", "designer graphique", "graphiste", "designer produit",
        "directeur artistique", "designer gráfico", "design gráfico", "designer de produto",
        "grafico", "designer grafico", "progettazione grafica"
    ],
    # Sits AFTER Design/Video on purpose: the classifier scans the body as a
    # fallback and takes the first category that matches, so a design or video
    # lead whose write-up merely mentions a photo stays put, and only gigs whose
    # own title/text is really about photography land here. Keywords are photo-
    # specific — never bare "photo", never "photoshop" (a designer's tool).
    "Photography": [
        "photographer", "photography", "photo editor", "photo editing",
        "photo retoucher", "photo retouching", "photoshoot", "photo shoot",
        "headshot", "headshots", "lightroom", "product photography",
        "real estate photography", "event photographer", "wedding photographer", "portrait photograph",
        "fotograf", "fotografie", "produktfotografie", "bildbearbeitung",
        "fotograaf", "productfotografie", "fotógrafo", "fotografía",
        "retoque fotográfico", "photographe", "photographie", "retouche photo",
        "fotografia", "fotografo", "ritocco fotografico"
    ],
    "QA / testing": [
        "quality assurance", "qa engineer", "qa tester", "tester",
        "test manager", "test engineer", "manual testing", "automation test",
        "qa analyst", "test automation", "qualitätssicherung", "qualitatssicherung",
        "qualitätsmanagement", "softwaretester", "testingenieur", "kwaliteitsborging",
        "testautomatisering", "control de calidad", "probador de software", "pruebas de software",
        "assurance qualité", "testeur logiciel", "test logiciel", "controle de qualidade",
        "testador de software", "testes de software", "controllo qualità", "tester software",
        "collaudatore"
    ],
    "Data / analytics": [
        "data analyst", "data analytics", "data science", "data scientist",
        "data engineer", "sql", "machine learning", "ml engineer",
        "ai engineer", "business intelligence", "power bi", "tableau",
        "analytics", "big data", "analista", "risk analyst",
        "quantitative", "datenanalyst", "datenanalytik", "datenwissenschaftler",
        "data-analist", "data-analyse", "datawetenschapper", "analista de datos",
        "ciencia de datos", "científico de datos", "analyste de données", "science des données",
        "analista de dados", "ciência de dados", "cientista de dados", "analista dati",
        "scienza dei dati", "ingeniero de datos", "bi analyst"
    ],
    # Non-software engineering: mechanical, electrical, civil, industrial. Sits
    # BEFORE Development/tech because that list contains a bare "engineer", which
    # was swallowing "Electrical Design Engineer" and the like. Every keyword
    # here is a compound or a German term, so "software engineer" can't match.
    "Engineering": [
        "mechanical engineer", "electrical engineer", "civil engineer", "chemical engineer",
        "process engineer", "structural engineer", "industrial engineer", "manufacturing engineer",
        "hardware engineer", "design engineer", "project engineer", "field engineer",
        "maintenance engineer", "electrician", "electrical design", "electrical installation",
        "pcb", "kicad", "cnc", "welding",
        "hvac", "ingenieur", "bauingenieur", "elektroniker",
        "elektriker", "konstrukteur", "maschinenbau", "haustechniker",
        "monteur", "montagearbeiten", "instandhaltung", "produktionsplanung",
        "werktuigbouwkundig ingenieur", "elektrotechnisch ingenieur", "installatietechniek", "ingeniero mecánico",
        "ingeniero eléctrico", "ingeniero civil", "electricista", "ingénieur mécanique",
        "ingénieur électrique", "ingénieur civil", "électricien", "engenheiro mecânico",
        "engenheiro elétrico", "engenheiro civil", "eletricista", "ingegnere meccanico",
        "ingegnere elettrico", "ingegnere civile", "elettricista"
    ],
    "Development / tech": [
        "developer", "software engineer", "programmer", "coding",
        "web dev", "python", "javascript", "typescript",
        "react", "node", "wordpress", "shopify",
        "full stack", "full-stack", "backend", "back end",
        "frontend", "front end", "devops", "api",
        "sdk", "software developer", "mobile app", "ios developer",
        "android developer", "engineer", "programming", "web developer",
        "bot", "softwareentwickler", "entwickler", "programmierer",
        "anwendungsentwickler", "cloud engineer", "platform engineer", "site reliability",
        "sre", "aws", "azure", "kubernetes",
        "administrador", "softwareontwikkelaar", "ontwikkelaar", "programmeur",
        "desarrollador", "ingeniero de software", "programador", "développeur",
        "ingénieur logiciel", "desenvolvedor", "engenheiro de software", "sviluppatore",
        "ingegnere software", "programmatore", "secops", "solutions architect",
        "software development", "integration engineer"
    ],
    "Writing / content": [
        "writer", "copywriter", "copywriting", "content writer",
        "content writing", "blog", "article", "ghostwriter",
        "ghostwriting", "proofreader", "proofreading", "editor",
        "scriptwriter", "seo writer", "technical writer", "content creator",
        "texter", "redakteur", "lektor", "tekstschrijver",
        "redacteur", "redactor", "redactor de contenidos", "corrector de textos",
        "rédacteur", "rédacteur web", "correcteur", "redator",
        "redator de conteúdo", "revisor de texto", "redattore", "correttore di bozze"
    ],
    "Marketing / SEO": [
        "marketing", "marketer", "seo", "social media",
        "ads manager", "google ads", "facebook ads", "paid ads",
        "ppc", "email marketing", "demand gen", "growth marketer",
        "growth marketing", "growth hacker", "content marketing", "brand manager",
        "media buyer", "marketingmanager", "onlinemarketing", "marketingassistent",
        "social-media-manager", "online marketing", "social media manager", "marketing digital",
        "gestor de marketing", "especialista en marketing", "responsable marketing", "chargé de marketing",
        "especialista em marketing", "marketing digitale", "responsabile marketing", "specialista marketing",
        "paid media", "demand generation", "lifecycle marketing", "paid social"
    ],
    "Sales / outreach": [
        "sales", "salesperson", "sales rep", "sales manager",
        "sales executive", "sales development", "account executive", "account manager",
        "cold caller", "cold call", "cold email", "outreach",
        "lead gen", "lead generation", "appointment setter", "business development",
        "closer", "sdr", "bdr", "vertrieb",
        "vertriebsmitarbeiter", "kundenberater", "außendienst", "verkoper",
        "accountmanager", "salesmedewerker", "representante de ventas", "ejecutivo de cuentas",
        "commercial", "représentant commercial", "chargé de clientèle", "representante de vendas",
        "executivo de contas", "rappresentante commerciale"
    ],
    "Customer support": [
        "customer support", "customer success", "support agent", "help desk",
        "customer service", "customer experience", "client success", "support specialist",
        "call center", "call centre", "kundenservice", "kundenbetreuung",
        "klantenservice", "klantondersteuning", "atención al cliente", "servicio al cliente",
        "soporte al cliente", "service client", "support client", "relation client",
        "atendimento ao cliente", "suporte ao cliente", "servizio clienti", "assistenza clienti",
        "client services", "member services", "customer engagement"
    ],
    "Product / PM": [
        "product manager", "project manager", "program manager", "scrum",
        "product owner", "scrum master", "delivery manager", "projektmanager",
        "projektleiter", "teilprojektleiter", "projektleitung", "productmanager",
        "projectmanager", "projectleider", "gerente de producto", "gerente de proyecto",
        "jefe de proyecto", "chef de produit", "chef de projet", "gerente de produto",
        "gerente de projeto", "responsabile di progetto", "product management", "product operations",
        "technical program"
    ],
    "Admin / VA": [
        "virtual assistant", "va", "administrative", "admin assistant",
        "data entry", "assistant", "scheduling", "office manager",
        "coordinator", "procurement", "operations manager", "receptionist",
        "back office", "sachbearbeiter", "verwaltungsfachkraft", "disposition",
        "büro", "sekretariat", "administratief medewerker", "receptioniste",
        "asistente virtual", "asistente administrativo", "auxiliar administrativo", "assistant administratif",
        "secrétaire", "assistant virtuel", "assistente virtual", "assistente administrativo",
        "assistente amministrativo", "segretaria"
    ],
    "Audio / music": [
        "voice over", "voiceover", "audio edit", "podcast",
        "music prod", "mixing", "sound design", "audio engineer",
        "music producer", "tonmeister", "toningenieur", "synchronsprecher",
        "geluidstechnicus", "audiomontage", "ingeniero de sonido", "locutor",
        "producción musical", "ingénieur du son", "monteur son", "voix off",
        "engenheiro de som", "produção musical", "tecnico del suono", "doppiatore",
        "produzione musicale"
    ],
    "Finance / accounting": [
        "accountant", "accounting", "bookkeeper", "bookkeeping",
        "quickbooks", "payroll", "invoicing", "tax",
        "financial analyst", "finance", "financial", "cfo",
        "controller", "auditor", "fp&a", "accounts payable",
        "accounts receivable", "steuerberater", "steuerfachangestellte", "buchhalter",
        "buchhaltung", "finanzbuchhaltung", "lohnbuchhaltung", "kreditsachbearbeiter",
        "bilanzbuchhalter", "steuerassistent", "boekhouder", "boekhouding",
        "financieel analist", "contador", "contabilidad", "analista financiero",
        "comptable", "comptabilité", "analyste financier", "contabilidade",
        "analista financeiro", "contabile", "contabilità", "analista finanziario",
        "loan officer", "loan manager", "underwriter", "billing specialist",
        "revenue cycle"
    ],
    "HR / recruiting": [
        "human resources", "recruiter", "recruiting", "recruitment",
        "talent acquisition", "headhunter", "sourcer", "people operations",
        "hr manager", "personalreferent", "personalwesen", "personalsachbearbeiter",
        "hr-medewerker", "personeelszaken", "reclutador", "recursos humanos",
        "selección de personal", "recruteur", "ressources humaines", "chargé de recrutement",
        "seleção de pessoal", "risorse umane", "selezione del personale", "benefits analyst",
        "compensation and benefits", "sourcing specialist", "benefits partner", "hr business partner",
        "hr operations", "hr systems", "hr generalist", "hr director",
        "hr coordinator", "hr specialist", "hr assistant", "hr lead",
        "hr advisor", "hr administrator", "hr analyst", "hris"
    ],
    "Legal": [
        "lawyer", "attorney", "paralegal", "legal",
        "counsel", "litigation", "compliance", "contract drafting",
        "legal drafting", "solicitor", "notary", "rechtsanwalt",
        "vertragsrecht", "advocaat", "juridisch medewerker", "abogado",
        "asesoría legal", "avocat", "droit des contrats", "advogado",
        "direito contratual", "avvocato", "diritto contrattuale"
    ],
    "Healthcare / medical": [
        "nurse", "clinical", "medical", "healthcare",
        "physician", "therapist", "caregiver", "pharmacist",
        "dental", "dentist", "health agency", "medical device",
        "clinical research", "pflegefachkraft", "pflegekraft", "krankenpfleger",
        "altenpfleger", "arzthelferin", "psychiatrist", "psychologist",
        "radiology", "radiographer", "sonographer", "ct tech",
        "veterinar", "physiotherap", "occupational therap", "paramedic",
        "midwife", "optometr", "verpleegkundige", "zorgverlener",
        "enfermero", "médico", "cuidador", "infirmier",
        "médecin", "aide-soignant", "enfermeiro", "infermiere",
        "medico", "operatore sanitario", "mental health", "behavioral health",
        "registered nurse", "lpn", "lvn", "lcsw",
        "lmft", "clinician", "patient care", "provider enrollment",
        "utilization review", "home health", "claims adjuster", "medical claims"
    ],
    "Architecture / 3D": [
        "architect", "interior design", "floor plan", "furniture design",
        "3d model", "3d artist", "rendering", "autocad",
        "revit", "blender", "cad", "landscape design",
        "sketchup", "architekt", "innenarchitekt", "3d-visualisierung",
        "interieurontwerper", "3d-visualisatie", "arquitecto", "diseño de interiores",
        "visualización 3d", "architecte", "architecte d'intérieur", "visualisation 3d",
        "arquiteto", "design de interiores", "visualização 3d", "architetto",
        "visualizzazione 3d"
    ],
    "IT / support": [
        "sysadmin", "system administrator", "it support", "network admin",
        "it technician", "helpdesk", "it-system", "technical support",
        "security engineer", "cybersecurity", "cyber security", "information security",
        "infosec", "soc analyst", "penetration test", "security analyst",
        "security specialist", "systemadministrator", "netzwerkadministrator", "systeembeheerder",
        "it-ondersteuning", "netwerkbeheerder", "administrador de sistemas", "soporte técnico",
        "administrador de red", "administrateur systèmes", "support informatique", "administrateur réseau",
        "suporte técnico", "administrador de rede", "amministratore di sistema", "supporto tecnico",
        "amministratore di rete", "systems administrator", "security operations", "service desk",
        "field service technician", "identity management"
    ],
    "Consulting / strategy": [
        "consultant", "strategy", "advisor", "founders associate",
        "management consultant", "business analyst", "strategist", "berater",
        "beraterin", "beratung", "unternehmensberatung", "head of strategy",
        "adviseur", "strategie", "consultor", "asesor",
        "estrategia", "conseiller", "stratégie", "assessor",
        "estratégia", "consulente", "consulenza", "strategia"
    ],
    "Teaching / tutoring": [
        "tutor", "teacher", "instructor", "curriculum",
        "lesson plan", "e-learning", "course creator", "teaching",
        "professor", "trainer", "coach", "lehrer",
        "nachhilfe", "dozent", "docent", "bijles",
        "leraar", "profesor", "clases particulares", "tuteur",
        "cours particuliers", "aulas particulares", "insegnante", "lezioni private"
    ],
    # Placed LAST on purpose. Anything with a real skill in the title — product
    # manager, sales manager, marketing manager — matches its own category
    # further up, so this only catches leadership roles that name no craft
    # ("Engineering Manager", "Manager Field Safety", "Head of Operations").
    # Those were the single biggest remaining lump in Other / general.
    "Management / operations": [
        "head of", "director", "vp of", "vice president",
        "chief", "general manager", "operations manager", "operations lead",
        "managing director", "office manager", "branch manager", "chief of staff",
        "geschäftsführer", "betriebsleiter", "abteilungsleiter", "teamleitung",
        "gruppenleiter", "leiter", "operationeel manager", "teamleider",
        "gerente de operaciones", "jefe de equipo", "responsable des opérations", "chef d'équipe",
        "diretor", "gerente de operações", "chefe de equipe", "responsabile operativo",
        "capo squadra", "business operations", "revenue operations", "operations specialist",
        "operations analyst"
    ],
    "Translation / language": [
        "translator", "translation", "localization", "interpreter",
        "bilingual", "subtitle", "subtitling", "proofreading spanish",
        "übersetzer", "übersetzung", "dolmetscher", "vertaler",
        "vertaling", "tolk", "traductor", "traducción",
        "intérprete", "traducteur", "traduction", "interprète",
        "tradutor", "tradução", "traduttore", "traduzione",
        "transcriber", "linguist", "linguistics", "interpreting",
        "audio transcription", "conversation transcription"
    ],
}

# ---------------------------------------------------------------------------
# CATEGORY GROUPS — a few BROAD buckets shown on the dashboard. Each maps to the
# granular JOB_TYPES above. Clicking a bucket filters the board to all its subs;
# users can then drill into a specific sub-category (or add subs to their profile).
# ---------------------------------------------------------------------------
CATEGORY_GROUPS = {
    "Tech & Data":        ["Development / tech", "Engineering", "Data / analytics", "QA / testing",
                           "IT / support"],
    "Design & Media":     ["Design / creative", "Video / animation", "Photography",
                           "Audio / music", "Architecture / 3D"],
    "Writing & Language": ["Writing / content", "Translation / language",
                           "Teaching / tutoring"],
    "Marketing & Sales":  ["Marketing / SEO", "Sales / outreach"],
    "Business & Support": ["Product / PM", "Management / operations", "Admin / VA", "Finance / accounting",
                           "HR / recruiting", "Consulting / strategy",
                           "Customer support", "Legal", "Healthcare / medical"],
}

# ---------------------------------------------------------------------------
# BUDGET (the "budget" slider uses these + parsed dollar amounts)
# ---------------------------------------------------------------------------
BIG_JOB_SIGNALS = ["/month", "per month", "monthly", "retainer", "ongoing", "long-term",
                   "long term", "full-time", "full time", "salary", "/year", "per year",
                   "annually", "k/yr", "revenue share"]
SMALL_JOB_SIGNALS = ["one time", "one-time", "quick", "small task", "gift card",
                     "per task", "small job", "$5", "$10", "$15", "$20", "$25"]

URGENT_SIGNALS = ["asap", "urgent", "immediately", "today", "right away", "start now",
                  "this week"]

# Boards that ONLY ever carry remote work. Their name already says it, so a
# "Remote" pill next to a source called RemoteOK is the same fact twice.
REMOTE_ONLY_SOURCES = {"remoteok", "remotive", "weworkremotely"}

# Boards where applying means creating a FREE account on THEIR site first —
# a real interruption to "reply first" that's worse if it's a surprise.
# Deliberately a short, confirmed list rather than a guess at every source:
# "weworkremotely" and "himalayas" per the founder's own reported experience
# clicking through real listings; "freelancer" because bidding on Freelancer.com
# requires an account by definition (it's a bid marketplace, not a job board);
# "bubble" and "blenderartists" are both Discourse forums (same /t/slug/id URL
# shape), where "applying" means replying to the thread, which every Discourse
# forum requires a free account for — that's how the software works, not a
# guess about their policy. Everything else stays off this list until it's
# actually been checked, not assumed — a wrong "no account needed" claim costs
# someone a surprise wall anyway, but a wrong "account needed" claim on a board
# that doesn't require one trains people to ignore the badge.
ACCOUNT_REQUIRED_SOURCES = {"weworkremotely", "himalayas", "freelancer",
                            "bubble", "blenderartists"}

# Distinct from the above on purpose: this isn't "make a free account," it's
# "pay money before you can even see the apply link." Nodesk was the one board
# that hit this (checked two real listings — the actual external application
# URL sat in a data attribute, but the visible button read "Subscribe to
# Apply" instead of "Apply Now" in the raw page, on both) and it's been pulled
# from ENABLE_SOURCES entirely rather than kept around and badged, so this
# starts empty. Gets its own badge with its own wording if it's ever needed
# again; conflating a paywall with a free signup would be dishonest about
# what's actually being asked of someone applying to a job.
SUBSCRIPTION_REQUIRED_SOURCES = set()

# Raw source keys are how we fetch; these are how a human should read them.
SOURCE_LABELS = {
    "remoteok": "RemoteOK",
    "remotive": "Remotive",
    "weworkremotely": "We Work Remotely",
    "arbeitnow": "Arbeitnow",
    "jobicy": "Jobicy",
    "freelancer": "Freelancer.com",
    "reddit": "Reddit",
    "soundlister": "Soundlister",
    "inbox": "Forwarded",     # a gig this person emailed in themselves
}


def source_label(key: str) -> str:
    """Pretty name for a source, falling back to the raw key."""
    key = (key or "").lower()
    if key in SOURCE_LABELS:
        return SOURCE_LABELS[key]
    spec = RSS_SOURCES.get(key)
    return (spec or {}).get("label") or key


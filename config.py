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
    "reddit",          # r/forhire & friends — freelance [Hiring] gigs + micro-tasks
    "freelancer",      # Freelancer.com — many small fixed-price projects
    "remoteok",        # RemoteOK — remote jobs/contracts
    "remotive",        # Remotive — remote jobs
    "arbeitnow",       # Arbeitnow — remote/EU jobs
    "jobicy",          # Jobicy — remote jobs
    "weworkremotely",  # We Work Remotely — remote jobs
    # Config-only boards (see RSS_SOURCES below)
    "dribbble", "himalayas", "nodesk", "pythonjobs", "larajobs", "wpjobs",
    "wwr_design", "wwr_devops", "wwr_support", "wwr_other",
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
    "nodesk":     {"url": "https://nodesk.co/remote-jobs/index.xml",
                   "label": "NoDesk"},
    "pythonjobs": {"url": "https://www.python.org/jobs/feed/rss/",
                   "label": "Python.org"},
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
}

# Subreddits where CLIENTS post gigs. slavelabour = small/micro paid tasks.
SUBREDDITS = ["forhire", "freelance_forhire", "jobbit", "slavelabour"]

# A Reddit post is real DEMAND if its title carries one of these tags.
HIRING_TAGS = ["[hiring]", "[task]"]

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
JOB_TYPES = {
    "Video / animation": ["video edit", "video editor", "video editing", "animation",
                          "animator", "motion graphic", "motion designer", "after effects",
                          "premiere", "youtube", "shorts", "reels", "vfx", "videographer",
                          "video producer"],
    "Design / creative": ["logo", "brand", "branding", "graphic design", "graphic designer",
                          "designer", "illustrator", "illustration", "figma", "ui/ux",
                          "ui design", "ux design", "ux/ui", "photoshop", "packaging",
                          "wordmark", "product design", "creative director", "art director",
                          "web design"],
    "QA / testing": ["quality assurance", "qa engineer", "qa tester", "tester",
                    "test manager", "test engineer", "manual testing", "automation test",
                    "qa analyst", "test automation"],
    "Data / analytics": ["data analyst", "data analytics", "data science",
                        "data scientist", "data engineer", "sql", "machine learning",
                        "ml engineer", "ai engineer", "business intelligence",
                        "power bi", "tableau", "analytics", "big data"],
    "Development / tech": ["developer", "software engineer", "programmer", "coding",
                          "web dev", "python", "javascript", "typescript", "react",
                          "node", "wordpress", "shopify", "full stack", "full-stack",
                          "backend", "back end", "frontend", "front end", "devops",
                          "api", "sdk", "software developer", "mobile app",
                          "ios developer", "android developer", "engineer", "programming",
                          "web developer", "bot"],
    "Writing / content": ["writer", "copywriter", "copywriting", "content writer",
                         "content writing", "blog", "article", "ghostwriter",
                         "ghostwriting", "proofreader", "proofreading", "editor",
                         "scriptwriter", "seo writer", "technical writer", "content creator"],
    "Marketing / SEO": ["marketing", "marketer", "seo", "social media", "ads manager",
                       "google ads", "facebook ads", "paid ads", "ppc",
                       "email marketing", "demand gen", "growth marketer",
                       "growth marketing", "growth hacker", "content marketing",
                       "brand manager", "media buyer"],
    "Sales / outreach": ["sales", "salesperson", "sales rep", "sales manager",
                        "sales executive", "sales development", "account executive",
                        "account manager", "cold caller", "cold call", "cold email",
                        "outreach", "lead gen", "lead generation", "appointment setter",
                        "business development", "closer", "sdr", "bdr"],
    "Customer support": ["customer support", "customer success", "support agent",
                        "help desk", "customer service", "customer experience",
                        "client success", "support specialist", "call center",
                        "call centre"],
    "Product / PM": ["product manager", "project manager", "program manager", "scrum",
                    "product owner", "scrum master", "delivery manager"],
    "Admin / VA": ["virtual assistant", "va", "administrative", "admin assistant",
                  "data entry", "assistant", "scheduling", "office manager",
                  "coordinator", "procurement", "operations manager", "receptionist",
                  "back office"],
    "Audio / music": ["voice over", "voiceover", "audio edit", "podcast", "music prod",
                     "mixing", "sound design", "audio engineer", "music producer"],
    "Finance / accounting": ["accountant", "accounting", "bookkeeper", "bookkeeping",
                            "quickbooks", "payroll", "invoicing", "tax", "financial analyst",
                            "finance", "financial", "cfo", "controller", "auditor",
                            "fp&a", "accounts payable", "accounts receivable"],
    "HR / recruiting": ["human resources", "recruiter", "recruiting", "recruitment",
                       "talent acquisition", "headhunter", "hr", "sourcer",
                       "people operations", "hr manager"],
    "Legal": ["lawyer", "attorney", "paralegal", "legal", "counsel", "litigation",
             "compliance", "contract drafting", "legal drafting", "solicitor",
             "notary"],
    "Healthcare / medical": ["nurse", "clinical", "medical", "healthcare", "physician",
                            "therapist", "caregiver", "pharmacist", "dental", "dentist",
                            "health agency", "medical device", "clinical research"],
    "Architecture / 3D": ["architect", "interior design", "floor plan", "furniture design",
                         "3d model", "3d artist", "rendering", "autocad", "revit",
                         "blender", "cad", "landscape design", "sketchup"],
    "IT / support": ["sysadmin", "system administrator", "it support", "network admin",
                    "it technician", "helpdesk", "it-system", "technical support"],
    "Consulting / strategy": ["consultant", "strategy", "advisor", "founders associate",
                             "management consultant", "business analyst", "strategist"],
    "Teaching / tutoring": ["tutor", "teacher", "instructor", "curriculum", "lesson plan",
                           "e-learning", "course creator", "teaching", "professor",
                           "trainer", "coach"],
    "Translation / language": ["translator", "translation", "localization", "interpreter",
                              "bilingual", "subtitle", "subtitling", "proofreading spanish"],
}

# ---------------------------------------------------------------------------
# CATEGORY GROUPS — a few BROAD buckets shown on the dashboard. Each maps to the
# granular JOB_TYPES above. Clicking a bucket filters the board to all its subs;
# users can then drill into a specific sub-category (or add subs to their profile).
# ---------------------------------------------------------------------------
CATEGORY_GROUPS = {
    "Tech & Data":        ["Development / tech", "Data / analytics", "QA / testing",
                           "IT / support"],
    "Design & Media":     ["Design / creative", "Video / animation", "Audio / music",
                           "Architecture / 3D"],
    "Writing & Language": ["Writing / content", "Translation / language",
                           "Teaching / tutoring"],
    "Marketing & Sales":  ["Marketing / SEO", "Sales / outreach"],
    "Business & Support": ["Product / PM", "Admin / VA", "Finance / accounting",
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

# Raw source keys are how we fetch; these are how a human should read them.
SOURCE_LABELS = {
    "remoteok": "RemoteOK",
    "remotive": "Remotive",
    "weworkremotely": "We Work Remotely",
    "arbeitnow": "Arbeitnow",
    "jobicy": "Jobicy",
    "freelancer": "Freelancer.com",
    "reddit": "Reddit",
}


def source_label(key: str) -> str:
    """Pretty name for a source, falling back to the raw key."""
    key = (key or "").lower()
    if key in SOURCE_LABELS:
        return SOURCE_LABELS[key]
    spec = RSS_SOURCES.get(key)
    return (spec or {}).get("label") or key


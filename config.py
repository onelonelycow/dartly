"""
config.py — the "settings" for Gig Radar.

This is the ONE file you can safely edit yourself without knowing how to code.
It's just lists of words and source names. Add/remove between the quotes, keep commas.

Gig Radar aggregates public "who's hiring" demand from MANY sources (freelance gig
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
]

# Subreddits where CLIENTS post gigs. slavelabour = small/micro paid tasks.
SUBREDDITS = ["forhire", "freelance_forhire", "jobbit", "slavelabour"]

# A Reddit post is real DEMAND if its title carries one of these tags.
HIRING_TAGS = ["[hiring]", "[task]"]

# ---------------------------------------------------------------------------
# SKILL (the "skill" toggles in the dashboard come from these)
# Each skill maps to words that signal it. First match wins, top to bottom.
# ---------------------------------------------------------------------------
JOB_TYPES = {
    "Video / animation": ["video edit", "video editor", "animation", "animator",
                          "motion graphic", "after effects", "premiere", "youtube",
                          "shorts", "reels", "vfx"],
    "Design / creative": ["logo", "brand", "graphic design", "designer", "illustrat",
                          "figma", "ui/ux", "ui design", "ux design", "photoshop",
                          "packaging", "wordmark", "label", "product design"],
    "QA / testing": ["quality assurance", "qa engineer", "qa tester", " tester",
                    "test manager", "test engineer", "manual testing",
                    "automation test", "analista de testes"],
    "Development / tech": ["developer", "software engineer", "programmer", "engineer",
                          "coding", "website", "web dev", "python", "javascript",
                          "react", "wordpress", "shopify", "full stack", "full-stack",
                          "backend", "frontend", "devops", "automation", "api", "bot"],
    "Data / analytics": ["data ", "analyst", "analytics", " sql", "machine learning",
                        " ml ", "ai engineer", "data scientist", "bi "],
    "Writing / content": ["writer", "copywrit", "content writ", "blog", "article",
                         "ghostwrit", "editor", "proofread", "script writ", "seo writ"],
    "Marketing / SEO": ["marketing", "seo", "social media", "ads manager", "google ads",
                       "facebook ads", "growth", "email marketing", "demand gen"],
    "Sales / outreach": ["sales rep", "sales develop", "cold caller", "cold call",
                        "outreach", "lead gen", "appointment setter", "account exec",
                        "business develop", "closer"],
    "Customer support": ["customer support", "customer success", "support agent",
                        "help desk", "customer service"],
    "Product / PM": ["product manager", "project manager", "program manager", "scrum",
                    "product owner"],
    "Admin / VA": ["virtual assistant", " va ", "administrative", "data entry",
                  "assistant", "scheduling"],
    "Audio / music": ["voice over", "voiceover", "audio edit", "podcast", "music prod",
                     "mixing", "sound design"],
    "Finance / accounting": ["accountant", "accounting", "bookkeep", "quickbooks",
                            "payroll", "invoic", " tax ", "financial analyst", "cfo",
                            "controller", "auditor"],
    "HR / recruiting": ["human resources", "recruiter", "recruiting",
                       "talent acquisition", "headhunt", " hr ", "sourcer",
                       "people operations"],
    "Architecture / 3D": ["architect", "villa", "interior design", "floor plan",
                         "furniture", "3d model", "rendering", "autocad", "revit",
                         "blender", " cad ", "landscape design"],
    "IT / support": ["sysadmin", "system administrator", "it support", "network admin",
                    "it technician", "helpdesk", "it-system"],
    "Consulting / strategy": ["consultant", "strategy", "advisor", "berater",
                             "founders associate", "management consult"],
    "Teaching / tutoring": ["tutor", "teacher", "instructor", "curriculum",
                           "lesson plan", "e-learning", "course creator", "teaching"],
    "Translation / language": ["translator", "translation", "localization",
                              "interpreter", "bilingual translat", "subtitl"],
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

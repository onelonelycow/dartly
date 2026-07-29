"""
pitch.py — writes the first reply to a gig, so you can answer fast AND well.

Two engines behind one function:

  * AI (Claude), when ANTHROPIC_API_KEY is set. It reads the client's actual
    post and answers what they actually asked for.
  * A template, when it isn't. Better than the old one, and still instant and
    free, but it cannot read the post, so it stays generic by construction.

That gap is the whole point. The old template only ever saw a gig's title and
budget tier and ignored the body entirely, which is why every draft came out
structurally identical. Send five of those and a client would notice. Nobody
pays for a mail merge.
"""
import hashlib
import json
import os
import re

import sources
import budget

# Sonnet, not Opus: a drafted reply is short, direct, everyday business
# writing (90-150 words, "here's why I fit this gig"), which is squarely
# Sonnet's strength — Opus's extra reasoning headroom isn't what this task
# needs. ~$15/mo at 3,000 drafts vs. ~$24 on Opus, same shape of output.
MODEL = "claude-sonnet-5"
_MAX_BODY = 2600          # plenty for a job post; keeps the prompt cheap


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
SYSTEM = """\
You write the opening reply a freelancer sends to a job post. The reply has one \
job: make the client want to answer THIS person. It is the first of many \
replies they will read, and most of the others are generic.

Write it as the freelancer, in first person, ready to send with no editing.

What makes it work:
- Show you read the post. Name something specific from it in the first two \
lines: the actual deliverable, their tool, their deadline, their industry, a \
constraint they mentioned. This is the single biggest thing.
- Lead with the part of their problem you have handled before. Use the \
freelancer's real background; never invent experience, clients, numbers, or \
credentials they did not give you.
- Ask at most two questions, and only about things the post genuinely does not \
answer. Asking about a detail they already stated proves you skimmed it.
- Match their register. A scrappy one-line post gets a short, human reply. A \
detailed corporate brief gets a more structured one.
- Be brief. Roughly 90 to 150 words. Short replies get read.

What kills it:
- Openers like "I hope this finds you well", "I am excited about", "I would \
love the opportunity", "I am the perfect fit".
- Restating their job back to them before saying anything useful.
- Listing every skill the freelancer has, rather than the ones this job needs.
- Praising the project ("what a great idea", "sounds like an exciting project").
- Em dashes, semicolons, or corporate filler. Write like a person types.
- Any placeholder such as [your name] or [link]. If a detail is missing, write \
around it.

Output only the message body. No subject line, no preamble, and no sign-off \
block beyond a simple first-name close.\
"""


# Reddit's RSS tail. Feeding "submitted by /u/x [link] [comments]" to the model
# is noise at best, and at worst it writes a reply addressed to the username.
_FEED_TAIL = re.compile(r"\s*submitted by\s*/u/\S+.*$", re.I | re.S)


def _clean_body(text: str) -> str:
    """The human-readable post, with our machine hints and scraper bait removed."""
    if not text:
        return ""
    human = str(text).split(sources.HINT_SEP)[0]
    human = sources.BOILERPLATE.sub("", human)
    human = _FEED_TAIL.sub("", human)
    human = re.sub(r"\n{3,}", "\n\n", human).strip()
    return human[:_MAX_BODY]


def _who(profile: dict, resume_text: str = "") -> str:
    """Everything true about the freelancer, as lines the model can draw from."""
    bits = []
    for key, label in (("name", "Name"), ("headline", "Does"),
                       ("bio", "Background"), ("portfolio", "Portfolio link")):
        v = (profile.get(key) or "").strip()
        if v:
            bits.append(f"{label}: {v}")
    skills = profile.get("skills") or []
    if isinstance(skills, list):
        skills = ", ".join(skills)
    if skills:
        bits.append(f"Skills: {skills}")
    kw = (profile.get("keywords") or "").strip()
    if kw:
        bits.append(f"Specific strengths: {kw}")
    floor, unit = profile.get("rate_floor"), profile.get("rate_unit") or "hr"
    if floor:
        bits.append(f"Rate floor: ${floor}/{unit} (do not state this unless the "
                    f"post asks for a rate)")
    # Optional and session-only (see resume.py) — a resume carries specific
    # projects, clients, years and tools that one bio line can't, which is what
    # turns a generic draft into one that names relevant work. Never invented:
    # the SYSTEM prompt's "never invent experience" rule already covers this
    # text the same as every other field here.
    if resume_text.strip():
        bits.append(f"Resume (use only what's actually in it):\n{resume_text.strip()}")
    return "\n".join(bits) or "No profile details on file."


def _user_prompt(gig: dict, profile: dict, resume_text: str = "") -> str:
    body = _clean_body(gig.get("body"))
    lines = [
        "THE FREELANCER",
        _who(profile, resume_text),
        "",
        "THE JOB POST",
        f"Title: {gig.get('title', '')}",
        f"Category: {gig.get('job_type', '')}",
        f"Budget tier: {gig.get('size_tier', '')}",
    ]
    if gig.get("urgency") == "Urgent":
        lines.append("The client flagged this as urgent, so they want a fast reply.")
    lines += ["", "What the client wrote:",
              body or "(The post has no body beyond the title. Work from the "
                      "title alone and keep the reply short.)"]
    if not (profile.get("name") or "").strip():
        lines.append("\nThe freelancer has no name on file, so end after the "
                     "last sentence with no sign-off.")
    if not (profile.get("portfolio") or "").strip():
        lines.append("\nThere is no portfolio link, so do not offer one or "
                     "leave a placeholder for it.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------
def ai_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _cache_key(gig: dict, profile: dict, resume_text: str = "") -> str:
    """Same gig plus same profile (and resume) means the same draft, so we only
    pay once. Hashed rather than embedded raw — a resume can run to thousands
    of characters and only its identity, not its content, needs to be in the
    key."""
    blob = json.dumps([gig.get("id"), gig.get("title"),
                       {k: profile.get(k) for k in
                        ("name", "headline", "bio", "portfolio", "skills",
                         "keywords", "rate_floor")},
                       hashlib.sha256(resume_text.encode()).hexdigest()],
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def draft_ai(gig: dict, profile: dict, resume_text: str = "",
             who: str = "") -> str:
    """
    A reply written from the client's actual words. Raises if the call fails so
    the caller can fall back, rather than showing an empty box.

    `who` is the caller's storage scope, used for the per-account daily cap.
    """
    import anthropic

    key = _cache_key(gig, profile, resume_text)

    # Cache first, and it's a real cache now (drafts.py, SQLite) rather than a
    # dict that emptied on every restart. A double-click, a page reload or a
    # Render redeploy used to mean paying for the same draft again.
    cached = budget.cached_ai(key)
    if cached:
        return cached

    # Only spend against the day's budget once we know we actually have to
    # call out. Checking before the cache would let a reload burn quota on a
    # draft we already hold.
    ok, why = budget.allow(who)
    if not ok:
        raise RuntimeError(f"budget: {why}")

    # No cache_control here on purpose: this system prompt is ~420 tokens and
    # a 4096-token prefix is needed before anything caches. Marking it would
    # look like an optimisation while doing nothing. The cache above is the
    # real saving, since it stops us paying twice for the same gig.
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=SYSTEM,
        messages=[{"role": "user", "content": _user_prompt(gig, profile, resume_text)}],
    )
    # Recorded here, not after the parsing below: the call was made and billed
    # the moment it returned, whether or not we liked the shape of the answer.
    budget.record(who)

    if resp.stop_reason == "refusal":
        raise RuntimeError("declined")
    text = "\n\n".join(b.text.strip() for b in resp.content
                       if b.type == "text" and b.text.strip()).strip()
    if not text:
        raise RuntimeError("empty draft")
    budget.cache_ai(key, text)
    return text


def draft_template(gig: dict, profile: dict | None = None) -> str:
    """
    The no-key fallback. It cannot read the post, so it does not pretend to:
    it opens on what the freelancer does, asks for the missing scope, and gets
    out of the way. Short and honest beats long and hollow.
    """
    profile = profile or {}
    name = (profile.get("name") or "").strip()
    portfolio = (profile.get("portfolio") or "").strip()
    bio = (profile.get("bio") or "").strip()
    title = gig.get("title", "this")
    skill = (gig.get("job_type") or "this work").lower()

    who = (profile.get("headline") or "").strip()
    if not who:
        skills = profile.get("skills") or []
        if isinstance(skills, list):
            skills = ", ".join(skills)
        who = skills or f"a {skill} freelancer"

    intro = f"I'm {who}."
    if bio:
        intro += f" {bio}."

    asks = ["What does done look like for you, and by when?"]
    if gig.get("size_tier") in ("Medium", "Large"):
        lead = "Two things would let me give you a real number rather than a range:"
        asks.append("Is there an existing setup I'd be working inside, or is "
                    "this from scratch?")
    else:
        lead = "One quick thing so I can scope it properly:"

    out = [f'Hi, I\'d like to help with "{title}".', "", intro, "", lead,
           "\n".join(f"  • {a}" for a in asks)]
    if portfolio:
        out += ["", f"Recent work: {portfolio}"]
    if name:
        out += ["", f"Thanks,\n{name}"]
    return "\n".join(out)


def draft_pitch(gig: dict, profile: dict | None = None, resume_text: str = "",
                who: str = "") -> str:
    """
    The best draft we can produce right now, without ever failing loudly.

    resume_text is optional and never persisted anywhere — see resume.py. The
    template engine can't use it (it has no model to read free text with), so
    it's only passed to the AI path; that's fine, the template was always the
    generic fallback.

    Hitting a daily cap raises inside draft_ai and lands in the same except as
    a dead key or a flat network — deliberately. Someone over the limit gets
    the template, which is a worse draft, not an error page. They are far more
    likely to be a script than a person, and a person who somehow drafted
    twenty replies today still gets something usable.
    """
    profile = profile or {}
    if ai_available():
        try:
            return draft_ai(gig, profile, resume_text, who=who)
        except Exception:
            pass          # capped, rate limited, no network, bad key: fall through
    return draft_template(gig, profile)

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
import style

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

Sound like a person typing, not a model generating. The tells to avoid:
- Use contractions. "I've", "I'd", "that's" — not "I have", "I would".
- Vary sentence length. Two long balanced sentences in a row reads as generated. \
A four-word sentence is allowed. So is a fragment.
- Do not explain their own business or trade back to them, and do not teach. \
Lines like "that usually comes down to..." or "the key here is..." are a \
consultant lecturing, not a peer replying.
- No lists of three. The rhythm of "X, Y, and Z" in every sentence is the \
single most recognisable generated cadence.
- Do not hedge. "I could potentially help with" is weaker than "I can do this".
- Skip transition scaffolding: "That said", "Additionally", "Furthermore".

What kills it:
- Openers like "I hope this finds you well", "I am excited about", "I would \
love the opportunity", "I am the perfect fit".
- Restating their job back to them before saying anything useful.
- Listing every skill the freelancer has, rather than the ones this job needs.
- Praising the project ("what a great idea", "sounds like an exciting project").
- Em dashes, semicolons, or corporate filler. Write like a person types.
- Any placeholder such as [your name] or [link]. If a detail is missing, write \
around it.

Output only the message body. No subject line and no preamble.

Sign off with the freelancer's first name on its own line at the end, when a \
name is given below. Just the first name, nothing under it: no title, no \
company, no contact block. If no name is given, stop after the last sentence.\
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


def _text(value) -> str:
    """
    Any stored field -> a stripped string, safely.

    `(x or "").strip()` looks like it covers this and doesn't: a pandas NaN is
    a float and it is TRUTHY, so it sails past the `or` and then blows up on
    .strip() with "'float' object has no attribute 'strip'". Profile and resume
    values reach here from a DataFrame, where an empty cell is exactly that
    NaN, which is how this crashed drafting in production.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        # NaN != NaN is the cheapest NaN test that needs no import.
        return "" if value != value else str(value).strip()
    return str(value).strip()


def _who(profile: dict, resume_text: str = "") -> str:
    """Everything true about the freelancer, as lines the model can draw from."""
    bits = []
    for key, label in (("name", "Name"), ("headline", "Does"),
                       ("bio", "Background"), ("portfolio", "Portfolio link")):
        v = _text(profile.get(key))
        if v:
            bits.append(f"{label}: {v}")
    skills = profile.get("skills") or []
    if isinstance(skills, list):
        skills = ", ".join(str(s) for s in skills)
    else:
        skills = _text(skills)
    if skills:
        bits.append(f"Skills: {skills}")
    kw = _text(profile.get("keywords"))
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
    _resume = _text(resume_text)
    if _resume:
        bits.append(f"Resume (use only what's actually in it):\n{_resume}")
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
    # Say what to do with the name in BOTH directions. The system prompt asks
    # for a first-name close, but only the no-name case was ever stated here,
    # so a draft for someone who HAD given a name often just stopped dead with
    # no sign-off at all.
    _name = _text(profile.get("name"))
    if _name:
        lines.append(f"\nEnd the message with \"{_name.split()[0]}\" on its own "
                     f"line as the sign-off. Nothing after it.")
    else:
        lines.append("\nThe freelancer has no name on file, so end after the "
                     "last sentence with no sign-off.")
    if not (profile.get("portfolio") or "").strip():
        lines.append("\nThere is no portfolio link, so do not offer one or "
                     "leave a placeholder for it.")
    # The Category line above names the JOB's field, and with an empty profile
    # that is the only occupation in the prompt — which is exactly how a model
    # ends up writing "I'm a designer" for someone who never said so. The
    # system prompt forbids inventing experience; this forbids the specific
    # inference, because the tempting wrong answer is right there in context.
    if not _who(profile, resume_text).strip().startswith(("Name", "Does",
                                                          "Background",
                                                          "Skills")):
        lines.append("\nNOTHING is known about this freelancer's field or "
                     "background. Do not state or imply what they do, and do "
                     "NOT borrow the job's Category as their profession. Ask "
                     "about the work instead of describing yourself.")
    examples = _style_examples()
    if examples:
        lines.append(examples)
    return "\n".join(lines)


def _style_examples() -> str:
    """
    Real (AI draft -> what they actually saved) pairs for whoever is signed
    in right now, so the next draft starts closer to where they'd end up by
    hand instead of relearning the same edit every single time. Reads
    style.py's per-account history, which is scoped the same implicit way
    profile.py and drafts.py already are — no account id passed in, because
    whichever account is signed in during this request is whichever
    account's edit history this reads.
    """
    edits = style.recent_edits(limit=2)
    if not edits:
        return ""
    blocks = [f"AI wrote:\n{e['original']}\n\nThis freelancer changed it to:\n{e['edited']}"
             for e in edits]
    return ("\n\nHOW THIS FREELANCER ACTUALLY EDITS DRAFTS\n"
            "Real examples of what they changed the last time a draft was "
            "written for them. Match the DIRECTION they moved things (shorter "
            "or longer, more or less formal, keeps or cuts the questions, sign-"
            "off habits) — not the exact wording, which was specific to that job.\n\n"
            + "\n\n---\n\n".join(blocks))


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
        # Stashed per THIS account even on a cache hit — the cache is shared
        # across everyone (see cache_ai's own note), but each account's own
        # "what did the AI first suggest me" record is scoped to them alone.
        style.stash_original(gig.get("id"), cached)
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
    style.stash_original(gig.get("id"), text)
    return text


def draft_template(gig: dict, profile: dict | None = None) -> str:
    """
    The no-key fallback. It cannot read the post, so it does not pretend to:
    it opens on what the freelancer does, asks for the missing scope, and gets
    out of the way. Short and honest beats long and hollow.

    Not reading the post is a real, permanent gap next to the AI path — that
    gap is the reason Pro exists. But nothing about that forces this to read
    like a form. The old version led with the same fixed sentence every time
    and turned its questions into a bulleted checklist, which reads as a mail
    merge even though the WORDS change per gig. This rotates a few honest
    openers and asks its question(s) as a sentence a person would actually
    type, picked deterministically off the gig id — same gig always drafts
    the same way (still cacheable, still consistent), but a results page full
    of drafts doesn't look like one template with the nouns swapped.
    """
    profile = profile or {}
    # _text, not `(x or "").strip()`: a NaN from an empty DataFrame cell is a
    # truthy float and crashes .strip(). Same bug this file hit in draft_ai.
    name = _text(profile.get("name"))
    portfolio = _text(profile.get("portfolio"))
    bio = _text(profile.get("bio"))
    title = gig.get("title") or "this"

    # NEVER falls back to the gig's own category. This used to end with
    # `who = skills or f"a {skill} freelancer"`, where `skill` is the JOB's
    # job_type — so someone with an empty profile got a draft that opened
    # "I'm a design / creative freelancer", an identity the app made up and
    # put in their mouth, under their name, to a stranger. Worse when the
    # classifier is wrong: an engineering role tagged Design/creative had
    # them introducing themselves as a designer to an engineering client.
    # If we don't know what they do, we say nothing about what they do.
    who = _text(profile.get("headline"))
    if not who:
        skills = profile.get("skills") or []
        if isinstance(skills, list):
            skills = ", ".join(str(s) for s in skills)
        else:
            skills = _text(skills)
        who = skills

    intro = f"I'm {who}." if who else ""
    if bio:
        intro = f"{intro} {bio}".strip() if intro else bio
        if not intro.endswith((".", "!", "?")):
            intro += "."

    # Deterministic, not random: a real per-account cache (drafts.py) can hold
    # this text, and it shouldn't change on a reload just because a fresh
    # random pick landed differently.
    openers = (
        f'Hi, "{title}" caught my eye.',
        f'Reaching out about "{title}".',
        f'I\'d like to help with "{title}".',
    )
    seed = hashlib.sha256(str(gig.get("id") or title).encode()).hexdigest()
    opener = openers[int(seed, 16) % len(openers)]

    if gig.get("size_tier") in ("Medium", "Large"):
        ask = ("A couple things that would help me give you a real number "
               "instead of a range: is there an existing setup I'd be "
               "working inside, or is this from scratch? And what does done "
               "look like for you, and by when?")
    else:
        ask = ("Before I quote anything, what does done look like for you, "
               "and by when?")

    # intro is omitted entirely when we don't know who they are, rather than
    # left as an empty line — otherwise the draft opens with a blank gap where
    # a sentence should be, which reads as broken rather than as brief.
    out = [opener, ""]
    if intro:
        out += [intro, ""]
    out += [ask]
    if portfolio:
        out += ["", f"Here's some recent work: {portfolio}"]
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
        except Exception as e:
            # Silent to the reader on purpose (a worse draft, not an error
            # page) but silent in the logs too used to mean the very first
            # real-key rollout had no way to see WHY it fell back. One line,
            # not the reader's problem, but ours to see.
            print(f"  draft_ai failed, falling back to template: {e!r}", flush=True)
    else:
        # ai_available() being False never reaches the except above at all —
        # this is the other, quieter way a key rollout goes unnoticed: the
        # env var isn't visible to this process, or `import anthropic` failed.
        print(f"  draft_pitch: AI not available "
              f"(key set: {bool(os.environ.get('ANTHROPIC_API_KEY'))})", flush=True)
    return draft_template(gig, profile)

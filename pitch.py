"""
pitch.py — drafts a first-response message for a gig so you can reply fast AND well.

v0 is a smart fill-in-the-blanks template (no API key, instant). It pulls the gig's
title, skill, and budget in so each draft is specific. Can be upgraded to an
AI-written pitch later.
"""


def draft_pitch(gig: dict, profile: dict | None = None) -> str:
    profile = profile or {}
    name = profile.get("name") or "[your name]"
    portfolio = profile.get("portfolio") or "[link to your work]"
    bio = (profile.get("bio") or "").strip()

    title = gig.get("title", "your project")
    skill = gig.get("job_type", "this")

    # Prefer a headline, else the profile's skills, else the gig's skill.
    who = profile.get("headline") or ""
    if not who:
        skills = profile.get("skills") or ""
        if isinstance(skills, list):
            skills = ", ".join(skills)
        who = skills or f"a {skill.lower()} freelancer"

    budget_line = {
        "Small": "Happy to keep this tight and quick to fit the scope.",
        "Medium": "I can scope this cleanly and give you a clear timeline up front.",
        "Large": "For a project this size I'll map out milestones so you always know where things stand.",
    }.get(gig.get("size_tier", ""), "")

    intro = f"I'm {who}"
    if bio:
        intro += f" — {bio}"

    return (
        f"Hi! I saw your post — \"{title}\".\n\n"
        f"{intro}. This is right in my wheelhouse. {budget_line}\n\n"
        f"A couple of quick questions so I can give you an accurate scope:\n"
        f"  • What's your ideal timeline?\n"
        f"  • Do you have any examples/references for the style you want?\n\n"
        f"Here's a sample of my work: {portfolio}\n"
        f"Happy to hop on a quick call whenever suits you.\n\n"
        f"Thanks,\n{name}"
    )

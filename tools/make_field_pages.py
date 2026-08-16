"""
make_field_pages.py — one crawlable page per field, built from the real board.

WHY THIS EXISTS: every gig Nabbly holds lives inside a Streamlit app, and a
crawler asking app.nabbly.co for HTML gets nine words and the title
"Streamlit". So the entire product — tens of thousands of postings, the only
text anyone actually searches for — is invisible to search engines. The
marketing site is one page. There is nothing for "freelance video editing
work" to match on.

These pages are the fix, and they are how job boards have always ranked: not
on the app, on a static page per category that a crawler can read.

THE RISK, AND WHAT KEEPS US ON THE RIGHT SIDE OF IT: twenty-odd pages that
differ only by a swapped noun are doorway pages, and Google demotes them on
purpose. So nothing here is templated filler — every page is built from facts
that are only true of its own field:

  * the curated vocabulary that classifies a gig INTO that field
    (config.JOB_TYPES), which is also, not by coincidence, the words people
    type when they search for that work
  * real, current titles from that field, so no two pages share a sentence
  * that field's own budget and urgency mix, described in words

TWO RULES INHERITED FROM THE REST OF THE SITE, both load-bearing:

  * NO SOURCE NAMES. Titles are shown, "via <board>" never is. The feed is the
    product; where it comes from is plumbing, and a visitor handed that list
    has somewhere else to go.
  * NO RELATIVE TIMESTAMPS. These are static files. "Posted 5 min ago" becomes
    a lie within the hour, and a page that lies about freshness is worse for
    trust than one that says nothing.

Run:  .venv/bin/python tools/make_field_pages.py
Out:  site/freelance-<slug>-jobs/index.html, one per field, plus a refreshed
      site/sitemap.xml
"""
import html
import re
import sqlite3
import sys
from urllib.parse import quote
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Pick up .env when running on a laptop, so a local run reads the same mirror
# CI does instead of silently falling back to the gitignored SQLite copy and
# writing pages from a stale board. Guarded because CI installs psycopg and
# nothing else, and sets DATABASE_URL directly, so python-dotenv is neither
# present nor needed there.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import config                                             # noqa: E402

DB = ROOT / "demand-radar.db" if (ROOT / "demand-radar.db").exists() \
    else ROOT / "demand_radar.db"
OUT = ROOT / "site"
BASE = "https://nabbly.co"
# WHERE THE CTAs SEND PEOPLE. This is the board that has to survive whatever
# outreach brings: measured at 100 concurrent in 0.15s, against the Streamlit
# app's 10.7s at 25 and outright failure at 50. Every field page funnels here,
# so pointing it at the app was pointing a firehose at the thing that cannot
# take one.
BOARD = "https://board.nabbly.co"

# A field needs enough behind it to be worth a page of its own. Below this a
# visitor lands on something nearly empty, which is exactly the thin-content
# result the whole exercise is trying to avoid.
MIN_GIGS = 150
SAMPLE = 16         # real titles shown per page. The single strongest
                    # thing separating one page from the next: no two
                    # fields share a posting, so this is where the
                    # uniqueness actually comes from. Eight left the
                    # pages at ~270 words, thin enough that the
                    # boilerplate outweighed the substance.

# Fields whose first word does not survive being lowercased into prose. Derived
# nouns are fine for most ("Design / creative" -> "design work"), and actively
# broken for three:
#
#   "IT / support"   -> "remote it work, the moment it posts"   <- pronoun
#   "HR / recruiting"-> "remote hr work"
#   "QA / testing"   -> "remote qa work"
#
# The IT one shipped live and read as a typo in the h1, the title tag and the
# meta description of a page we are about to point outreach at. Acronyms keep
# their case; anything else derives as before.
NOUN_OVERRIDES = {
    "it": "IT",
    "hr": "HR",
    "qa": "QA",
}


# "Design / creative" -> ("design", "design"). The slug drives the URL, the
# noun drives the prose, and both read better than the raw category label.
def slug_and_noun(field: str) -> tuple[str, str]:
    head = field.split("/")[0].strip().lower()
    head = re.sub(r"[^a-z0-9]+", "-", head).strip("-")
    noun = NOUN_OVERRIDES.get(head, head.replace("-", " "))
    return head, noun


def clean(title: str) -> str:
    """A gig title fit to print: no separator junk, no hiring boilerplate."""
    t = re.sub(r"\s+", " ", (title or "")).strip(" -–—|·")
    t = re.sub(r"\s*[-–—|]\s*(hiring|urgent|remote)\s*$", "", t, flags=re.I)
    return t


def read_board():
    """
    The live board, from Supabase when it is reachable, local SQLite otherwise.

    THIS HAS TO WORK WITHOUT THE LOCAL FILE. demand_radar.db is gitignored, so
    a scheduled run in CI has no copy of it and never will — and a generator
    that only reads a developer's laptop can only ever be run by hand, which is
    how "Recently on the board" quietly becomes a lie about work that closed
    weeks ago. Supabase holds the same board and is reachable from anywhere
    DATABASE_URL is set, so the pages can rebuild themselves on a schedule.

    Local SQLite stays as the fallback so running this on a laptop with no
    DATABASE_URL still does the obvious thing.
    """
    rows = []
    try:
        import board_store
        if board_store.enabled():
            rows = [r for r in board_store.pull()
                    if r.get("is_demand") and (r.get("title") or "").strip()]
            rows.sort(key=lambda r: str(r.get("posted_at") or r.get("fetched_at") or ""),
                      reverse=True)
            print(f"  board: {len(rows):,} gigs from the durable mirror")
    except Exception as e:
        print(f"  ! mirror unavailable ({type(e).__name__}), falling back to local")

    if not rows:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            "SELECT job_type, title, size_tier, urgency "
            "FROM posts WHERE is_demand = 1 AND COALESCE(title,'') != '' "
            "ORDER BY COALESCE(posted_at, fetched_at) DESC")]
        conn.close()
        print(f"  board: {len(rows):,} gigs from local sqlite")

    by = {}
    for r in rows:
        by.setdefault(r.get("job_type") or "", []).append(r)
    return by


# ── the page ────────────────────────────────────────────────────────────────
# Deliberately self-contained: no shared stylesheet to fetch, so each page is
# one request and renders instantly. The tokens are index.html's, copied, so
# the pages belong to the same site rather than merely linking to it.
CSS = """
:root{--bg:#121418;--bg2:#15181d;--panel:#171a20;--line:#262a31;--line2:#2f343d;
--ink:#F6F8FA;--ink2:#AEB4BE;--mute:#868D98;--amber:#E8933A;--amber-l:#F7B569;
--amber-d:#CB6F16;--radius:16px;--maxw:800px;
--sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}
header{border-bottom:1px solid var(--line)}
/* no flex gap here: the wordmark is "Nabb" + a coloured "ly" span, and a gap
   between flex children split the brand into two words. */
.nav{display:flex;align-items:center;height:64px;font-weight:650;font-size:19px;
letter-spacing:-.02em;text-decoration:none}
.amber{color:var(--amber)}
h1{font-size:clamp(30px,4.6vw,42px);font-weight:650;letter-spacing:-.02em;line-height:1.12;
margin:44px 0 0;text-wrap:balance}
.lead{color:var(--ink2);margin:18px 0 0;font-size:18px}
h2{font-size:21px;font-weight:650;letter-spacing:-.02em;margin:44px 0 0}
p{margin:14px 0 0}
.terms{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0;list-style:none}
.terms li{font-size:14px;color:var(--ink2);background:rgba(232,147,58,.07);
border:1px solid rgba(232,147,58,.16);padding:7px 13px;border-radius:100px}
.gigs{list-style:none;padding:0;margin:18px 0 0;border-top:1px solid var(--line)}
.gigs li{padding:13px 0;border-bottom:1px solid var(--line);font-size:15.5px;color:var(--ink2)}
.btn{display:inline-block;margin:26px 0 0;font-weight:600;font-size:16px;border-radius:11px;
padding:14px 24px;text-decoration:none;color:#2a1806;
background:linear-gradient(180deg,var(--amber-l),var(--amber-d))}
.more{display:flex;flex-wrap:wrap;gap:9px;margin:18px 0 0;padding:0;list-style:none}
.more a{font-size:14px;color:var(--ink2);text-decoration:none;background:var(--bg2);
border:1px solid var(--line);padding:8px 14px;border-radius:100px}
.more a:hover{border-color:var(--amber);color:var(--ink)}
footer{border-top:1px solid var(--line);margin-top:56px;padding:26px 0 48px;
color:var(--mute);font-size:13px}
footer a{color:var(--mute)}
.guidelink{margin-top:30px;font-size:15px;color:var(--mute)}
.guidelink a{color:var(--amber);text-decoration:none;font-weight:600}
.guidelink a:hover{text-decoration:underline}
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#121418">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Nabbly">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{base}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="/favicon.png">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"CollectionPage",
"name":{name_json},"description":{desc_json},"url":"{url}",
"isPartOf":{{"@type":"WebSite","name":"Nabbly","url":"{base}/"}}}}
</script>
<style>{css}</style>
</head>
<body>
<header><div class="wrap"><a class="nav" href="/">Nabb<span class="amber">ly</span></a></div></header>
<main class="wrap">
  <h1>{h1}</h1>
  <p class="lead">{lead}</p>

  <h2>What lands here</h2>
  <p>Nabbly reads {noun} briefs and roles from job boards and hiring
     communities around the clock, and puts each one on the board minutes after
     it posts. A gig reaches this page when it talks about work like this:</p>
  <ul class="terms">{terms}</ul>

  <h2>Recently on the board</h2>
  <p>Real {noun} postings Nabbly picked up. The live board carries far more,
     and it changes through the day.</p>
  <ul class="gigs">{gigs}</ul>
  <a class="btn" href="{BOARD}/gigs?field={cat}">See live {noun} work &rarr;</a>

  <h2>Why speed matters here</h2>
  <p>{speed}</p>

  <!-- One line, and it carries the field noun so it is not the same sentence
       twenty-one times. The first version of this was a 37 word paragraph
       repeated verbatim on every page, which pushed body similarity between
       pages from 40% to 45% - padding, by the standard the rest of this
       generator is held to. The link matters (these pages are the guide's
       only crawl path besides the sitemap); the paragraph did not. -->
  <p class="guidelink">Replying to {noun} briefs:
     <a href="/guides/how-to-reply-to-a-freelance-job-post/">what to put in the
     first two lines &rarr;</a></p>

  <h2>Other fields</h2>
  <ul class="more">{siblings}</ul>
</main>
<footer><div class="wrap">
  <a href="/">Nabbly</a> &middot; freelance and remote work from every board, in one place
  &middot; <a href="/privacy.html">Privacy</a> &middot; <a href="/terms.html">Terms</a>
</div></footer>
</body>
</html>
"""


def speed_line(noun, large, urgent, total):
    """
    A sentence about THIS field's own shape, not a slogan.

    Built from the field's real budget and urgency mix so no two pages argue
    the same way — a field where a third of the work is large-budget earns a
    different sentence from one that is mostly quick turnarounds. Nothing here
    claims a fast reply wins the work, which is a line the rest of the site
    deliberately does not make: early is the part you can control, not a
    guarantee.
    """
    big = round(100 * large / total) if total else 0
    urg = round(100 * urgent / total) if total else 0
    bits = []
    if big >= 25:
        bits.append(f"a good share of {noun} work here is posted at the larger "
                    f"end, and those briefs attract replies quickly")
    else:
        bits.append(f"most {noun} work here turns around fast, and a brief that "
                    f"sits unanswered tends to get filled by whoever saw it first")
    if urg >= 8:
        bits.append(f"roughly one in {max(2, round(100 / urg))} is posted with a "
                    f"deadline attached")
    bits.append("being early is the part you can actually control, which is the "
                "whole job of a board that updates every couple of minutes")
    return ". ".join(s[0].upper() + s[1:] for s in bits) + "."


def build(by=None):
    # Takes the board so __main__ can read it once and hand the same
    # snapshot to both the page builder and the recorder.
    by = by if by is not None else read_board()
    fields = []
    for field, rows in by.items():
        if not field or field.lower().startswith("other"):
            continue                      # nothing to search for, nothing to say
        if len(rows) < MIN_GIGS:
            continue                      # a page nobody should land on
        s, noun = slug_and_noun(field)
        if s:
            fields.append((field, s, noun, rows))
    fields.sort(key=lambda f: -len(f[3]))

    written = []
    for field, s, noun, rows in fields:
        terms = [t for t in config.JOB_TYPES.get(field, []) if len(t) > 2][:22]
        # PREFER TITLES THAT SAY WHAT THE FIELD SAYS. The sample used to take
        # the newest N that passed a length check, so the writing page led with
        # "Boost Google Reviews", "Transcribe Notes Into PDF" and "Draft
        # Dishwasher Damage Complaint" — a third of it not recognisably writing
        # work. That section is the page's own evidence, and it is exactly what
        # an editor skims when deciding whether the page is worth linking to;
        # classification noise there costs more than any paragraph of copy can
        # recover.
        #
        # The terms come from config.JOB_TYPES and are printed on the page
        # right above this list, so a sample drawn from them reads as
        # consistent rather than curated. Anything left over is filled from the
        # rest, in recency order, so a thin field still gets a full sample.
        low_terms = [t.lower() for t in terms]
        onpoint, spare, seen = [], [], set()
        for r in rows:
            t = clean(r["title"])
            k = t.lower()
            if not (12 < len(t) < 78) or k in seen:
                continue
            seen.add(k)
            (onpoint if any(w in k for w in low_terms) else spare).append(t)
            if len(onpoint) >= SAMPLE:
                break
        titles = (onpoint + spare)[:SAMPLE]
        if len(titles) < 4 or len(terms) < 3:
            continue                      # too thin to be worth indexing

        large = sum(1 for r in rows if r["size_tier"] == "Large")
        urgent = sum(1 for r in rows if r["urgency"] == "Urgent")
        url = f"{BASE}/freelance-{s}-jobs/"
        title = f"Freelance and remote {noun} work · Nabbly"
        desc = (f"New freelance {noun} briefs and remote {noun} roles from every "
                f"job board and hiring community, in one place, minutes after "
                f"they post.")
        page = PAGE.format(
            title=html.escape(title), desc=html.escape(desc), url=url, base=BASE,
            BOARD=BOARD,
            css=CSS, # quote(), not a naive space swap: every job_type here contains a slash
            # ("Design / creative"), and an unescaped one in a query value is at
            # best ambiguous and at worst truncates the filter.
            cat=html.escape(quote(field, safe="")), noun=html.escape(noun),
            name_json=repr(title).replace("'", '"'),
            desc_json=repr(desc).replace("'", '"'),
            h1=f"Freelance and remote {html.escape(noun)} work,<br>the moment it posts.",
            lead=(f"Every new {html.escape(noun)} brief and {html.escape(noun)} role "
                  f"Nabbly finds, from across the job boards and hiring communities "
                  f"it watches, gathered on one board you can read in a minute."),
            terms="".join(f"<li>{html.escape(t)}</li>" for t in terms),
            gigs="".join(f"<li>{html.escape(t)}</li>" for t in titles),
            speed=speed_line(html.escape(noun), large, urgent, len(rows)),
            siblings="",   # filled below, once every slug is known
        )
        written.append({"field": field, "slug": s, "noun": noun, "page": page,
                        "url": url, "n": len(rows)})

    # Sibling links last, so every page can point at every other one. Without
    # them each page is an orphan reachable only from the sitemap, which is a
    # weak signal; with them the set is a small connected site.
    for w in written:
        links = "".join(
            f'<li><a href="/freelance-{o["slug"]}-jobs/">{html.escape(o["noun"]) if o["noun"].isupper() else html.escape(o["noun"]).title()}</a></li>'
            for o in written if o["slug"] != w["slug"])
        w["page"] = w["page"].replace('<ul class="more"></ul>',
                                      f'<ul class="more">{links}</ul>')
        d = OUT / f"freelance-{w['slug']}-jobs"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(w["page"], encoding="utf-8")

    return written


def write_sitemap(written):
    today = date.today().isoformat()
    # app.nabbly.co is NOT listed. It answers a crawler with nine words and the
    # title "Streamlit" — everything it holds is rendered client side — so
    # pointing search engines at it hourly (which this file used to do, at
    # priority 0.9) spent crawl budget on an empty room and offered the domain
    # a thin page to judge it by.
    urls = [(f"{BASE}/", "daily", "1.0"),
            *[(w["url"], "daily", "0.8") for w in written],
            (f"{BASE}/about.html", "monthly", "0.6"),
            (f"{BASE}/faq.html", "monthly", "0.6"),
            (f"{BASE}/guides/how-to-reply-to-a-freelance-job-post/",
             "monthly", "0.7"),
            (f"{BASE}/privacy.html", "yearly", "0.3"),
            (f"{BASE}/terms.html", "yearly", "0.3")]
    body = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>{c}</changefreq>\n    <priority>{p}</priority>\n  </url>"
        for u, c, p in urls)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!--\n  Generated by tools/make_field_pages.py. Do not hand-edit; the\n"
        "  next run overwrites it. app.nabbly.co is deliberately absent - see\n"
        "  write_sitemap() for why.\n-->\n"
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n", encoding="utf-8")




# ── About and FAQ ───────────────────────────────────────────────────────────
# These existed only inside the Streamlit app, where a crawler sees nine words.
# ~500 words of the most searchable prose Nabbly has — "where do the gigs come
# from", "is it free", "are they verified" — was invisible. Both pages read
# from content.py, the same literal the app renders, so the copy cannot drift
# the way it did when the FAQ lived in two places.
import content                                            # noqa: E402

# Only the guide needs these: the two example replies sit side by side so the
# difference is visible before either is read.
GUIDE_CSS = """
.ex{background:var(--bg2);border:1px solid var(--line);border-left:3px solid var(--line2);
border-radius:0 var(--radius) var(--radius) 0;padding:16px 20px;margin:16px 0 0}
.ex-good{border-left-color:var(--amber)}
.ex-l{font-size:12px;font-weight:650;letter-spacing:.07em;text-transform:uppercase;
color:var(--mute)}
.ex p{margin:8px 0 0;font-size:15.5px;color:var(--ink2)}
.ex-good p{color:var(--ink)}
.close{margin-top:30px;padding-top:20px;border-top:1px solid var(--line);color:var(--mute)}
"""

PROSE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#121418">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Nabbly">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{base}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="/favicon.png">
{schema}
<style>{css}
dt{{font-weight:650;font-size:17.5px;letter-spacing:-.01em;margin:30px 0 0}}
dd{{margin:10px 0 0;color:var(--ink2)}}
</style>
</head>
<body>
<header><div class="wrap"><a class="nav" href="/">Nabb<span class="amber">ly</span></a></div></header>
<main class="wrap">
  <h1>{h1}</h1>
  <p class="lead">{lead}</p>
  {body}
  <a class="btn" href="{BOARD}/gigs">Open the board &rarr;</a>
  <h2>Browse by field</h2>
  <ul class="more">{siblings}</ul>
</main>
<footer><div class="wrap">
  <a href="/">Nabbly</a> &middot; freelance and remote work from every board, in one place
  &middot; <a href="/about.html">About</a> &middot; <a href="/faq.html">FAQ</a>
  &middot; <a href="/privacy.html">Privacy</a> &middot; <a href="/terms.html">Terms</a>
</div></footer>
</body>
</html>
"""


def write_prose_pages(written):
    sibs = "".join(
        f'<li><a href="/freelance-{w["slug"]}-jobs/">{html.escape(w["noun"]) if w["noun"].isupper() else html.escape(w["noun"]).title()}</a></li>'
        for w in written)

    # FAQPage schema is legitimate HERE and only here: every question below is
    # rendered visibly on the page. index.html carried this markup for a while
    # with no visible FAQ at all, which is what Google's guidelines forbid.
    import json
    faq_schema = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in content.FAQ]}, indent=None)

    faq_body = "<dl>" + "".join(
        f"<dt>{html.escape(q)}</dt><dd>{html.escape(a)}</dd>"
        for q, a in content.FAQ) + "</dl>"
    (OUT / "faq.html").write_text(PROSE.format(
        BOARD=BOARD,
        title="Frequently asked questions &middot; Nabbly",
        desc=("Where the gigs come from, how fresh they are, what is free and "
              "what Pro adds, and what Nabbly does with your data."),
        url=f"{BASE}/faq.html", base=BASE, css=CSS,
        schema=f'<script type="application/ld+json">{faq_schema}</script>',
        h1="Frequently asked questions",
        lead=("Everything people ask before they trust a board with their "
              "week's work."),
        body=faq_body, siblings=sibs), encoding="utf-8")

    about_body = "".join(
        f"<h2>{html.escape(h)}</h2><p>{html.escape(p)}</p>"
        for h, p in content.ABOUT)
    (OUT / "about.html").write_text(PROSE.format(
        BOARD=BOARD,
        title="About Nabbly &middot; freelance and remote work in one place",
        desc=("Nabbly gathers freelance projects and remote roles from every "
              "job board and hiring community into a single board, minutes "
              "after they post. What it does, and what it deliberately "
              "doesn't."),
        url=f"{BASE}/about.html", base=BASE, css=CSS, schema="",
        h1="About Nabbly", lead=html.escape(content.ABOUT_LEAD),
        body=about_body, siblings=sibs), encoding="utf-8")
    # ── the applying guide ──────────────────────────────────────────────
    # A directory rather than a flat .html because this is the first of a kind
    # and /guides/ is where the next one goes. Every rule on it is one the
    # drafter in pitch.py already follows, which is what makes it ours to
    # publish rather than advice reassembled from other people's blogs.
    ex = (f'<div class="ex"><div class="ex-l">The usual reply</div>'
          f'<p>{html.escape(content.GUIDE_APPLY_EXAMPLE_BAD)}</p></div>'
          f'<div class="ex ex-good"><div class="ex-l">A reply about their post</div>'
          f'<p>{html.escape(content.GUIDE_APPLY_EXAMPLE_GOOD)}</p></div>')
    guide_body = "".join(
        f"<h2>{html.escape(h)}</h2><p>{html.escape(b)}</p>"
        for h, b in content.GUIDE_APPLY)
    guide_body += ("<h2>What it looks like</h2>" + ex +
                   f'<p class="close">{html.escape(content.GUIDE_APPLY_CLOSE)}</p>')
    d = OUT / "guides" / "how-to-reply-to-a-freelance-job-post"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(PROSE.format(
        BOARD=BOARD,
        title=html.escape(content.GUIDE_APPLY_TITLE) + " &middot; Nabbly",
        desc=("What to put in the first two lines, how many questions to ask, "
              "how long to make it, and the tells that make a reply look "
              "pasted. With a worked example."),
        url=f"{BASE}/guides/how-to-reply-to-a-freelance-job-post/", base=BASE,
        css=CSS + GUIDE_CSS, schema="",
        h1=html.escape(content.GUIDE_APPLY_TITLE),
        lead=html.escape(content.GUIDE_APPLY_LEAD),
        body=guide_body, siblings=sibs), encoding="utf-8")

    return ["about.html", "faq.html",
            "guides/how-to-reply-to-a-freelance-job-post/"]


def record_snapshot(by):
    """
    Write down what the board looked like today, so a trend can exist later.

    NOTHING IN NABBLY RECORDS HISTORY. The live board holds 21 days by design,
    and once a gig ages out its row survives in the mirror but nobody ever
    counted what was there at the time. So the interesting claim — "the share
    of postings in this field grew" — cannot be made from current data however
    it is queried, and every week that passes without recording is a week of it
    lost permanently.

    One row per run, keyed by date, holding a count per field. Tiny, written to
    the same durable store as everything else, and it accumulates on its own
    once the weekly workflow runs. Twelve of these and a quarterly report
    becomes possible; without them it never does, however long we wait.

    Counts, not money, deliberately. What a gig pays cannot be published — the
    parser cannot tell an hourly rate from a project budget, so a median across
    both means nothing — but how many were posted is unambiguous.
    """
    try:
        import store
        if not store.enabled():
            print("  snapshot: no durable store configured, skipped")
            return False
        counts = {f: len(rows) for f, rows in by.items() if f}
        today = date.today().isoformat()
        ok = store.put("_board_snapshots", today,
                       {"date": today, "fields": counts,
                        "total": sum(counts.values())})
        print(f"  snapshot: {'recorded' if ok else 'FAILED'} {today} "
              f"({len(counts)} fields, {sum(counts.values()):,} gigs)")
        return ok
    except Exception as e:
        print(f"  ! snapshot failed ({type(e).__name__}: {e})")
        return False


if __name__ == "__main__":
    board = read_board()
    pages = build(board)
    prose = write_prose_pages(pages)
    write_sitemap(pages)
    record_snapshot(board)
    print(f"wrote {len(pages)} field pages, {len(prose)} prose pages, sitemap.xml\n")
    for w in pages:
        print(f"  /freelance-{w['slug']}-jobs/{'':<{max(0, 22 - len(w['slug']))}} "
              f"{w['n']:>6,} gigs   {w['field']}")

"""
make_legal.py — turn legal.py into static site/privacy.html and site/terms.html.

The app renders legal.py directly, but the marketing site is plain HTML, and a
static page is also what an OAuth reviewer or a regulator can actually read
without running JavaScript. Same source, so the two can't drift.

Run:  .venv/bin/python tools/make_legal.py
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT))          # legal.py lives at the project root

import legal  # noqa: E402


# One renderer, shared with the in-app pages, so the static site and the app
# can never drift apart in how they interpret the same source.
md_to_html = legal.to_html


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Nabbly</title>
<meta name="description" content="{desc}">
<link rel="icon" href="/favicon.png">
<meta name="robots" content="index, follow">
<style>
  :root{{--bg:#0B0D10;--card:#12151a;--ink:#ECEEF1;--mute:#98A0AB;--faint:#6C737E;
         --amber:#E8933A;--line:#232830}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);
    font:16px/1.75 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased}}
  .wrap{{max-width:760px;margin:0 auto;padding:0 22px}}
  header{{border-bottom:1px solid var(--line);padding:20px 0}}
  header .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px}}
  .brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);
    font-weight:700;font-size:20px;letter-spacing:-.3px}}
  .brand .ly{{color:var(--amber)}}
  .brand img{{width:30px;height:30px;border-radius:8px;display:block}}
  nav a{{color:var(--mute);text-decoration:none;font-size:14px;font-weight:600;margin-left:18px}}
  nav a:hover{{color:var(--amber)}}
  main{{padding:44px 0 20px}}
  h1{{font-size:34px;line-height:1.2;letter-spacing:-.6px;margin:0 0 6px}}
  h2{{font-size:22px;letter-spacing:-.3px;margin:38px 0 10px}}
  h3{{font-size:17px;letter-spacing:-.2px;margin:26px 0 6px;color:var(--ink)}}
  p,li{{color:#c9cfd8}}
  strong{{color:var(--ink)}}
  ul{{padding-left:20px}}
  li{{margin:6px 0}}
  a{{color:var(--amber)}}
  .back{{display:inline-block;margin:34px 0 8px;color:var(--mute);text-decoration:none;
    font-weight:600;font-size:14px}}
  .back:hover{{color:var(--amber)}}
  footer{{border-top:1px solid var(--line);margin-top:40px;padding:22px 0 46px;
    color:var(--faint);font-size:13.5px}}
  footer a{{color:var(--mute);text-decoration:none}}
  footer a:hover{{color:var(--ink)}}
  @media (max-width:640px){{h1{{font-size:27px}} h2{{font-size:19px}} main{{padding-top:30px}}}}
</style>
</head><body>
<header><div class="wrap">
  <a class="brand" href="/"><img src="/favicon.png" alt=""><span>Nabb<span class="ly">ly</span></span></a>
  <nav><a href="/privacy.html">Privacy</a><a href="/terms.html">Terms</a><a href="/">Home</a></nav>
</div></header>
<main><div class="wrap">
{body}
<a class="back" href="/">← Back to Nabbly</a>
</div></main>
<footer><div class="wrap">© 2026 Nabbly ·
  <a href="/privacy.html">Privacy</a> · <a href="/terms.html">Terms</a> ·
  <a href="/">nabbly.co</a>
</div></footer>
</body></html>
"""

for name, md, title, desc in (
    ("privacy.html", legal.PRIVACY, "Privacy Policy",
     "What Nabbly collects, why, and what we never do with it. No data selling, "
     "no advertising trackers."),
    ("terms.html", legal.TERMS, "Terms of Service",
     "The terms covering your use of Nabbly, including how job listings and "
     "drafted replies work."),
):
    body = md_to_html(md).replace(f"<h2>{title}</h2>", f"<h1>{title}</h1>", 1)
    (SITE / name).write_text(PAGE.format(title=title, desc=html.escape(desc), body=body))
    print("wrote", SITE / name)

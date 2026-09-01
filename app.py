"""
app.py — Nabbly.

Made for freelancers, by freelancers. An icon-navigated app: Dashboard (welcome +
your picks), Gigs (the whole board), Market (what work pays), Alerts, and Profile
(you + your plan).

Run:   streamlit run app.py
"""
import os
import re
import html
import uuid
import hashlib
import hmac
import secrets
import time
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import pandas as pd
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

import db
import config
import content
# Moved out of this file so the board service can format dates and bodies the
# same way — two implementations of "how long ago was this" is two answers to
# the same question, and users notice when two pages of one product disagree.
from textfmt import (_parse_dt, human_time, is_recent, smart_trim,
                     _strip_tag_tail, _flip_spans, display_body,
                     _HINT_SEP, _BUDGET_TAIL, _TAGLIKE, _TECHY, _FEED_LOC,
                     _HQ_LABEL, _HQ_URL, _strip_feed_head)
import ingest
import sources
import alerts
import pitch
import market
import score
import location
import lang
import resume
import budget
import contact
import drafts
import saved
import outcomes
import match_feedback
import style
import mailer
import refresh
import inbox
import legal
import analytics
import people
import paths
import auth
import accounts
import billing
import store
import profile as profile_mod

BASE = Path(__file__).parent
# Inlined rather than st.image() so the mark can be wrapped in a link home.
LOGO_SVG = (BASE / "assets" / "logo.svg").read_text()

# page_icon was a str(path). Streamlit treats a plain string as an emoji or
# shortcode first, so a filesystem path silently fell through to the stock
# Streamlit crown — confirmed by fetching app.nabbly.co/favicon.png and getting
# their 32x32 default back, not ours. Handing it a real image object is the
# unambiguous form. Pillow ships as a Streamlit dependency, so this adds
# nothing to the install.
def _page_icon():
    try:
        from PIL import Image
        return Image.open(BASE / "assets" / "favicon.png")
    except Exception:
        return "🧭"      # never let a missing asset break the whole page render


st.set_page_config(page_title="Nabbly", page_icon=_page_icon(), layout="wide",
                   initial_sidebar_state="collapsed")

# --- a little house style so cards/pills read as one cohesive, non-"code" look ---
st.markdown("""
<style>
/* ── Design tokens (FEEL.md §2) ─────────────────────────────────────────────
   The site (site/index.html) has carried a :root block since it was built; the
   app never did, so every colour here is a literal and they drift apart. These
   are the same names FEEL.md defines, so a change to the palette is one edit in
   two files rather than forty. New rules use the tokens; the older literals are
   left alone deliberately, so this stays a design pass and not a rename sweep. */
:root{
  --bg:#121418; --bg2:#15181d; --panel:#171a20;
  --line:#262a31; --line2:#2f343d;
  /* Headers/body/captions/dates sat too close together on brightness alone —
     each individually passed WCAG fine against --bg, but the STEPS between
     tiers were only ~1.4-1.6:1 apart, so a title and its own body copy read
     as barely different weights of the same gray. Widened every adjacent
     gap to ~1.6-2:1 (measured, not eyeballed — see the contrast numbers in
     the commit this landed in). --faint is untouched: it was already
     recalibrated earlier for its own WCAG fix, and .gr-body/.gr-posted sit
     on the same card relying on --mute and --faint staying genuinely
     different from each other. */
  --ink:#F6F8FA; --ink2:#AEB4BE; --mute:#868D98; --faint:#7d8590;
  --amber:#E8933A; --amber-l:#F7B569; --amber-d:#CB6F16;
  /* Vertical rhythm. The whole point is that these are DIFFERENT from each
     other — Streamlit ships one flat 16px between everything, which is why the
     page reads as undesigned no matter how good the individual pieces are. */
  --s-item:.5rem;      /* between parts of one thing (title, pills, body) */
  --s-group:1rem;      /* between sibling things (card to card) */
  --s-section:2.2rem;  /* before a new section heading */
}
/* --- How things respond to being touched --------------------------------
   There was NO global button styling at all: every button in the app was
   Streamlit stock, with no transition and no pressed state, so a click
   registered as a colour swap with nothing in between. That absence is most
   of what made the app read as unfinished — an interface feels expensive
   when it acknowledges the pointer, and cheap when it doesn't, and that is
   almost entirely hover and :active.

   Scoped to real controls, not "button", because Streamlit renders expanders,
   the "See more" toggle and various chrome as buttons too; sweeping them all
   would put a press animation on things that are not buttons to a reader.

   :active is the honest half of this. Hover is decoration on a mouse and
   nothing at all on a phone; the press is what a thumb actually feels. */
.stButton button,[data-testid="stFormSubmitButton"] button,
[data-testid="stDownloadButton"] button,.stLinkButton a{
  transition:transform .11s cubic-bezier(.2,.7,.3,1),
             border-color .16s ease,background .16s ease,box-shadow .16s ease}
.stButton button:hover,[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stDownloadButton"] button:hover,.stLinkButton a:hover{
  border-color:#3b4250}
/* The amber ones need their own hover: they have no visible border to shift,
   so the rule above does nothing for them. Brightness + a 1px lift is already
   the house treatment for a primary button on the marketing site
   (site/nextnw.html .btn-primary:hover), and it's the one transform FEEL.md §5
   explicitly allows. Deliberately NOT a background change — an earlier draft
   set one and it painted straight over the amber gradient, leaving dark text
   on dark grey.

   BOTH kind values, verified against the live DOM rather than assumed:
   st.button(type="primary") renders kind="primary", but a form's submit
   renders kind="primaryFormSubmit" — and the app's most prominent amber
   button (Search) is a form submit, so a rule matching only "primary" would
   have silently done nothing to the one button most people press. */
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover{
  filter:brightness(1.07);transform:translateY(-1px)}
button[kind="primary"]:active,button[kind="primaryFormSubmit"]:active{
  filter:brightness(1.02);transform:scale(.975)}
@media (prefers-reduced-motion:reduce){
  button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover,
  button[kind="primary"]:active,button[kind="primaryFormSubmit"]:active{
    transform:none}
}
.stButton button:active,[data-testid="stFormSubmitButton"] button:active,
[data-testid="stDownloadButton"] button:active,.stLinkButton a:active{
  transform:scale(.975)}
/* Keyboard users get the same affordance a mouse gets, and a visible ring
   rather than the browser's default outline, which the dark ground swallows. */
.stButton button:focus-visible,[data-testid="stFormSubmitButton"] button:focus-visible,
a.gr-title:focus-visible,a.gr-save:focus-visible,.gr-nav a:focus-visible,
a.gr-stat:focus-visible,a.gr-cat:focus-visible{
  outline:2px solid var(--amber);outline-offset:2px;border-radius:8px}
@media (prefers-reduced-motion:reduce){
  .stButton button,[data-testid="stFormSubmitButton"] button,
  [data-testid="stDownloadButton"] button,.stLinkButton a{transition:none}
  .stButton button:active,[data-testid="stFormSubmitButton"] button:active,
  [data-testid="stDownloadButton"] button:active,.stLinkButton a:active{
    transform:none}
}

/* Section headings speak the wordmark's language: the last word in amber, the
   way "ly" is amber in Nabbly. Replaces the scattered emoji prefixes so every
   heading reads as one family. */
.gr-accent{color:#E8933A}

/* --- Market's charts, hand-built instead of altair -----------------------
   altair costs 51MB just to import (measured 2026-08-01, up from the ~36MB
   the code used to say), and Market is a Pro feature — every trial and
   founding member has it, which is most of the launch cohort. That 51MB
   landing on top of an already-tight baseline is what tipped the app over
   its memory ceiling the night before send. Five charts, none of them need
   a charting library: two are sorted bar lists, two are three-slice donuts,
   one is a stacked bar. Real numbers still show on hover via `title`, same
   information altair's tooltip gave, just the browser's own mechanism
   instead of a second rendering engine's. */
.gr-hbars{display:flex;flex-direction:column;gap:13px}
.gr-hbar-top{display:flex;justify-content:space-between;align-items:baseline;
  font-size:13.5px;color:var(--ink2);margin-bottom:5px}
.gr-hbar-n{font-weight:700;color:#eaeef4;font-variant-numeric:tabular-nums}
.gr-hbar-track{height:9px;border-radius:5px;background:#1a1d23;overflow:hidden}
.gr-hbar-fill{height:100%;border-radius:5px 0 0 5px}
/* A full pill only when the bar is actually the max — otherwise the right
   edge stays square, which is what makes a bar read as "62% of the top one"
   instead of every bar looking like its own separate pill. */
.gr-hbar-fill.max{border-radius:5px}

/* Conic-gradient donut, a CSS circle standing in for an SVG arc chart. The
   hole is a smaller circle in the exact card background sitting on top —
   there's no native way to cut a ring out of a conic-gradient, so this fakes
   it by covering the center rather than actually being one. */
.gr-donut-wrap{display:flex;align-items:center;justify-content:center;
  gap:24px;flex-wrap:wrap;padding:8px 0}
.gr-donut{width:168px;height:168px;border-radius:50%;position:relative;
  flex:0 0 auto}
.gr-donut-hole{position:absolute;inset:29%;border-radius:50%;
  background:var(--bg)}
.gr-donut-legend{display:flex;flex-direction:column;gap:9px;font-size:13.5px;
  color:var(--ink2)}
.gr-donut-legend .sw{display:inline-block;width:10px;height:10px;
  border-radius:3px;margin-right:9px;vertical-align:-1px;flex:0 0 auto}
.gr-donut-legend .row{display:flex;align-items:center}
.gr-donut-legend b{color:#eaeef4;font-variant-numeric:tabular-nums;
  margin-left:auto;padding-left:16px}

.gr-stack{display:flex;flex-direction:column;gap:11px}
.gr-stack-row{display:grid;grid-template-columns:min(38%,190px) 1fr;
  align-items:center;gap:12px}
.gr-stack-lbl{font-size:12.5px;color:var(--ink2);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gr-stack-bar{display:flex;height:16px;border-radius:4px;overflow:hidden;
  background:#1a1d23}
.gr-stack-bar .seg{height:100%}
.gr-stats{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 4px;
  justify-content:center;max-width:none}
.gr-stat{flex:1;min-width:150px;background:#15181d;border:1px solid #262a31;
  border-radius:14px;padding:15px 16px 16px;position:relative;overflow:hidden}

/* ── the fields, for a signed-out first screen ─────────────────────────────
   Pills, not stat cards. Borrowed straight from nabbly.co's .vpill so the
   first thing a visitor sees here is the shape they just clicked away from,
   in the same amber wash and the same 100px radius.
   Reusing .gr-stat for these was wrong on two counts: it is a container built
   to hold a big number and a label, so a bare field name floated in a box
   sized for something else, and the names wrap at different lengths, which
   left "Tech & Data" a line shorter than "Marketing & Sales" beside it. A
   pill sizes to its own text, so five uneven names still make one clean row.
   Unlike the site's pills these ARE links, so they get a hover — the one
   thing worse than not being clickable is looking unclickable. */
.gr-cat{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:8px 0 0}
/* !important because Streamlit styles every markdown link amber and
   underlined, which turned the pills into five underlined amber phrases in
   boxes. Same override a.gr-save already needs, for the same reason. */
.gr-cat a{display:inline-block;font-size:14.5px;font-weight:600;letter-spacing:-.01em;
  color:var(--ink2)!important;background:rgba(232,147,58,.07);
  border:1px solid rgba(232,147,58,.18);padding:11px 19px;border-radius:100px;
  white-space:nowrap;transition:.15s;text-decoration:none!important}
.gr-cat a:hover{color:var(--ink)!important;border-color:var(--amber);
  background:rgba(232,147,58,.14);transform:translateY(-1px)}

/* Fresh and Urgent were two of the four counters this row replaced, and they
   were the two worth keeping — a way into the board, not a boast about its
   size. Back as filters, deliberately quieter than the fields above: what you
   do comes first, when it landed is a refinement of that. */
.gr-quick{display:flex;flex-wrap:wrap;gap:8px 20px;justify-content:center;
  margin:14px 0 2px;font-size:13.5px}
.gr-quick a{color:var(--mute)!important;text-decoration:none!important;
  transition:.15s;border-bottom:1px solid transparent;padding-bottom:1px}
.gr-quick a:hover{color:var(--amber-l)!important;border-bottom-color:rgba(232,147,58,.5)}
/* This is the one moment in the whole app that's actually worth celebrating
   — FEEL.md's one-amber-focal-point rule earns its keep here rather than
   fighting it. Sits between the live stats and the divider: after "here's
   the board" but before "here's what's new", since it's neither. */
/* Four saturated bars competing for attention read as noise. Keep the colour
   as a quiet cue, not a stripe: thinner, dimmer, shorter. */
.gr-stat .accent{position:absolute;left:0;top:18px;bottom:18px;width:2px;
  border-radius:0 3px 3px 0;opacity:.55}
.gr-stat .l{font-size:12.5px;color:#98a0ab;font-weight:500;margin:0 0 9px}
.gr-stat .n{font-size:31px;font-weight:600;color:#f2f4f7;line-height:1;
  font-variant-numeric:tabular-nums;perspective:240px;
  /* This is a number 99% of the time, but "Hottest skill" puts a category
     name here instead ("Development / tech"), and on a narrow 2-up mobile
     grid that's long enough to need a line break. Without this, it took
     the tightest break it could find — mid-word, "Development/t" / "ech" —
     instead of the space before "tech". Normal wrapping only breaks AT a
     space; worst case here is two short lines, never a word cut in half. */
  overflow-wrap:normal;word-break:normal}
.gr-stat .n.small{font-size:20px}
/* A departure-board flip when a number lands, instead of it just appearing —
   each digit rotates down into place, staggered left to right. `animation`
   (not `transition`) so it self-plays on mount with no JS: Streamlit hands
   this markup to the browser fresh on every rerun, which IS a mount as far as
   the DOM is concerned. `backwards` fill-mode holds the 0% frame during each
   span's own animation-delay, so digits don't flash their final value before
   their turn. */
.gr-stat .n span.gr-flip{display:inline-block;transform-origin:50% 100%;
  animation:gr-flip .38s cubic-bezier(.2,.7,.3,1) backwards}
@keyframes gr-flip{
  0%{transform:rotateX(75deg) translateY(-3px);opacity:0}
  55%{opacity:1}
  100%{transform:rotateX(0deg) translateY(0);opacity:1}}
@media (prefers-reduced-motion:reduce){
  .gr-stat .n span.gr-flip{animation:none}}
/* Real count-up, 0 to the true number — same feel as the marketing site's
   hero counter. First cut used a CSS @property counter trick (animate a
   registered integer custom property, print it live via counter()) — it
   worked in isolated testing, but this card re-renders on every Streamlit
   rerun (live_stats() re-reads the feed on a ~60s timer on its own), and a
   rerun landing mid-animation restarts it from a fresh mount. A slow,
   continuously-interpolated animation getting cut off and restarted over
   and over read as noise, not a climb.
   This version reuses the exact reel mechanism the digit-odometer already
   proved solid: real intermediate numbers (computed in Python with the
   same ease-out curve the marketing page's JS uses, not per-digit) stacked
   in a clipped column, revealed with steps() so each one SNAPS in rather
   than sliding — sliding differently-wide numbers vertically would look
   like a glitch. Short and step-based on purpose: fewer frames for a
   rerun to land on mid-flight, and if one does, the restart just looks
   like a quick re-tick, not a stall. */
.gr-count{display:inline-block;height:1em;overflow:hidden;vertical-align:top}
.gr-count-reel{display:flex;flex-direction:column;animation-fill-mode:forwards}
.gr-count-reel>span{height:1em;line-height:1em;white-space:nowrap}
@media (prefers-reduced-motion:reduce){.gr-count-reel{animation:none!important}}
/* Base applies only in the 640-641px gap: 16.5!important below, 18!important
   above. 18 so the gap matches desktop instead of inventing a third size. */
a.gr-title{font-size:18px;font-weight:600;color:#eaeef4 !important;
  text-decoration:none !important;line-height:1.35;letter-spacing:-.1px}
/* The save star. Dim until you go near it, so a column of sixty cards isn't
   sixty little icons competing with the titles they sit beside — it's there
   when you're deciding about THIS gig, invisible when you're scanning. */
/* #6b7482, not the #4d545e this shipped as. That measured 2.35:1 against the
   card — under the 3:1 WCAG needs for a UI control — and next to a bold white
   title it read as a rendering artifact rather than something you could press.
   It's the entry point to the entire Saved feature, so being nearly invisible
   defeated the feature. Still the quietest thing on the card at 3.81:1. */
/* padding+matching-negative-margin: expands the tappable hit area to ~32px
   (comfortably past the 24px WCAG minimum) without shifting the glyph's
   visible position or its spacing from neighbours — this was one gig-card
   icon among several sitting close together, exactly where a mis-tap on a
   phone is likely. */
a.gr-save{display:inline-block;margin:-8px -8px -8px 1px;padding:8px;
  font-size:16px;line-height:1;color:#6b7482!important;text-decoration:none!important;
  vertical-align:2px;transition:color .15s ease,transform .15s ease}
a.gr-save:hover{color:var(--amber-l)!important;transform:scale(1.18)}
a.gr-save.on{color:var(--amber)!important}
a.gr-save.on:hover{color:var(--amber-l)!important}
@media (prefers-reduced-motion:reduce){a.gr-save{transition:none}}
/* Same construction as .gr-save right above — a link, not a button, for the
   identical DOM-shape reason. Grayscale until it's actually been tapped, so
   an untapped card doesn't read as "you haven't won this one yet" (every
   card would say that); it earns color only once it's true. */
/* Let a multiselect show all of its chips. Streamlit caps this container at
   155.5px, and with every skill selected (which is the DEFAULT on the Gigs
   filters) the content is 170px — so the last row rendered sliced through the
   glyphs, "Management / oper…" cut in half. It scrolls, so it worked; it just
   looked broken the first time anyone opened the panel. Selector verified
   against the live DOM: the clipping element is the direct child div of
   [data-baseweb="select"], three levels inside stMultiSelect. */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div{
  max-height:none!important}
a.gr-title:hover{color:#E8933A !important;text-decoration:underline !important;
  text-decoration-color:rgba(232,147,58,.55);text-underline-offset:3px}
/* THE BADGE RAMP: eyebrow 10 (.gr-new, .gr-why .lead, .gr-matchfb .lead)
   -> chip 11 (.gr-why-chip, .gr-founding, .gr-ch-st) -> pill 12 (.gr-pill,
   .gr-feat span, .gr-plan-price span) -> check-label 12.5 (.gr-more-lbl).
   Four deliberate 1px rungs of uppercase chrome. NOT part of the text
   scale; do not flatten it into the label/meta steps. */
.gr-new{display:inline-block;font-size:10px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;color:#69d7a1;background:rgba(53,179,126,.13);
  border:1px solid rgba(53,179,126,.32);border-radius:6px;padding:1px 7px;
  vertical-align:2px;margin-right:9px}
.gr-pills{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 6px}
/* Pills are metadata, not controls. Outlined, they put four to six little boxes
   inside every card, and with sixty cards on screen the board reads as a grid of
   frames rather than a list of gigs. Tint only: the colour still carries the
   meaning, but nothing draws an edge except the card itself. (FEEL.md §9.4 —
   prefer background shifts over more outlines.) */
.gr-pill{font-size:12px;font-weight:500;padding:4px 11px;border-radius:999px;
  background:#1e222a;color:#aab2bd;border:0;line-height:1.55}
.gr-pill.match{background:rgba(232,147,58,.15);color:#eaa662}
.gr-pill.urgent{background:rgba(233,98,80,.15);color:#e8907e}
.gr-pill.low{background:rgba(232,147,58,.15);color:#eaa662}
.gr-pill.loc{background:rgba(76,141,255,.13);color:#89b0f5}
/* #35B37E is FEEL.md's actual documented green; a lighter #5EC478 had crept
   in here instead — same hue family, but a second, undocumented shade. */
.gr-pill.locnear,.gr-pill.remote{background:rgba(53,179,126,.14);color:#6bd19d}
.gr-pill.locoff{background:#1a1d23;color:#767c86}
/* Budget size, tinted by the same amber-ramp Market's charts already use
   for this exact tier (BUDGET_COLORS) — Small/Medium/Large as light-to-deep
   amber, not a new hue. This pill is on EVERY card (unlike match/urgent/loc,
   which are conditional), and it sat fully neutral gray until now — the
   single biggest reason a long list of cards read as flat monochrome
   despite the pill system underneath already carrying real color. */
.gr-pill.budget-sm{background:rgba(243,192,122,.13);color:#f0c896}
.gr-pill.budget-md{background:rgba(232,147,58,.15);color:#eaa662}
.gr-pill.budget-lg{background:rgba(168,93,27,.24);color:#d38a4f}
.gr-why{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 11px}
.gr-why .lead{font-size:10px;font-weight:600;letter-spacing:.8px;
  text-transform:uppercase;color:#6d747f;margin-right:2px}
.gr-why-chip{font-size:11px;font-weight:500;color:#caa06e;
  background:rgba(232,147,58,.07);border:1px solid rgba(232,147,58,.18);
  border-radius:999px;padding:2px 10px}
/* Same visual family as .gr-why right above — a quiet lead label plus small
   controls, not a second row of loud UI competing with the pills. */
.gr-matchfb{display:flex;align-items:center;gap:7px;margin:0 0 11px}
.gr-matchfb .lead{font-size:10px;font-weight:600;letter-spacing:.8px;
  text-transform:uppercase;color:#6d747f}
a.gr-thumb{display:inline-block;margin:-8px;padding:8px;font-size:14px;line-height:1;
  text-decoration:none!important;opacity:.4;filter:grayscale(1);
  transition:opacity .15s ease,filter .15s ease,transform .15s ease}
a.gr-thumb:hover{opacity:.85;transform:scale(1.15)}
a.gr-thumb.on{opacity:1;filter:none}
/* A grayscale 👎 still reads as a thumb, not as disapproval — only once
   pressed does it need to visibly mean "no." */
a.gr-thumb.on.down{filter:none}
@media (prefers-reduced-motion:reduce){a.gr-thumb{transition:none}}
.gr-founding{display:inline-flex;align-items:center;gap:5px;font-size:11px;
  font-weight:600;color:#eaa662;background:rgba(232,147,58,.12);
  border:1px solid rgba(232,147,58,.32);border-radius:999px;padding:2px 9px 2px 5px;
  vertical-align:2px;margin-left:7px;white-space:nowrap}
.gr-founding svg{flex-shrink:0}
.gr-hero{text-align:center;max-width:860px;margin:2px auto 6px;padding:14px 16px 6px;
  background:radial-gradient(ellipse 640px 260px at 50% -8%,rgba(232,147,58,.11),transparent 72%)}
@keyframes gr-ping{
  0%{box-shadow:0 0 0 0 rgba(55,198,137,.5)}
  70%{box-shadow:0 0 0 6px rgba(55,198,137,0)}
  100%{box-shadow:0 0 0 0 rgba(55,198,137,0)}}
.gr-h1{font-size:46px;line-height:1.06;font-weight:700;letter-spacing:-1.4px;
  color:#f5f7fa;margin:0 0 18px;text-wrap:balance}
.gr-h1 .accent{color:#E8933A}
/* Streamlit hangs a "#" deep-link off every markdown heading. That's a docs
   convention: here it reads as a stray icon welded to the end of the hero, and
   it points at an in-page anchor nobody can use, because the app navigates by
   tabs rather than by scrolling one long document. */
[data-testid="stHeaderActionElements"]{display:none!important}
.gr-sub{display:inline-block;font-size:17px;line-height:1.6;color:#99a1ac;
  max-width:600px;margin:0;text-align:center;text-wrap:pretty}
.gr-sub b{color:#ced4dc;font-weight:600}
/* Fill the content column so the stat row's edges line up with the feed cards
   below it, rather than sitting in a narrower band of its own. (Merged into the
   single .gr-stats rule above — this used to be a second declaration whose only
   live effect was overriding its own margin.) */
.gr-stat{transition:transform .15s ease,border-color .15s ease,background .15s ease}
.gr-stat:hover{transform:translateY(-3px);border-color:#3b4250;background:#181c22}
a.gr-stat{text-decoration:none;color:inherit;cursor:pointer;display:block}
.gr-stat .go{position:absolute;top:12px;right:14px;color:#5a616c;font-size:16px;
  opacity:0;transition:opacity .15s ease}
.gr-stat:hover .go{opacity:1;color:#E8933A}
.gr-qf{display:inline-block;font-size:13.5px;font-weight:500;color:#eaa662;
  background:rgba(232,147,58,.1);border:1px solid rgba(232,147,58,.28);
  border-radius:999px;padding:4px 13px}
.gr-cats{display:flex;flex-wrap:wrap;gap:9px;margin:2px 0 6px}
a.gr-cat{display:inline-flex;align-items:center;gap:8px;font-size:13.5px;font-weight:500;
  color:#cdd3dc!important;text-decoration:none!important;background:#191c22;
  border:1px solid #2b3039;border-radius:999px;padding:7px 8px 7px 14px;
  transition:border-color .14s ease,background .14s ease,color .14s ease}
a.gr-cat:hover{border-color:#E8933A;background:#22262e;color:#fff!important}
a.gr-cat .n{font-size:11.5px;font-weight:600;color:#8a919c;background:#0f1115;
  border-radius:999px;padding:1px 8px;line-height:1.5}
a.gr-cat:hover .n{color:#eaa662}
.gr-avatar{display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:50%;background:#22262e;border:1px solid #3a4150;
  color:#eaa662!important;font-size:15px;font-weight:600;text-decoration:none!important;
  cursor:pointer;transition:border-color .15s ease,background .15s ease;user-select:none}
.gr-avatar:hover{border-color:#E8933A;background:#2a2f38}
.gr-avatar.active{background:#E8933A;color:#141414!important;border-color:#E8933A}
.gr-acct{position:relative;display:inline-block}
/* The avatar used to be a real <a href> that also revealed this menu on
   :hover — fine with a mouse, broken on touch (hover barely exists there,
   and tapping a link just navigates immediately, no menu). It's a hidden
   checkbox + label now instead (same technique as .gr-more-cb elsewhere in
   this file): tapping the avatar toggles the menu open on any input type,
   no JS required. Desktop keeps the hover preview on top of that. */
.gr-acct-cb{display:none}
.gr-menu{position:absolute;right:0;top:48px;min-width:196px;background:#1b1e25;
  border:1px solid #2f3540;border-radius:12px;padding:6px;z-index:1000;
  box-shadow:0 14px 34px rgba(0,0,0,.5);opacity:0;visibility:hidden;
  transform:translateY(-6px);transition:opacity .14s ease,transform .14s ease,visibility .14s}
.gr-acct:hover .gr-menu,.gr-acct:focus-within .gr-menu,
.gr-acct-cb:checked ~ .gr-menu{opacity:1;visibility:visible;transform:translateY(0)}
.gr-menu-hd{padding:8px 10px 7px;color:#eaeef4;font-weight:600;font-size:14.5px;
  display:flex;flex-direction:column;line-height:1.55;text-align:left}
.gr-menu-hd span{color:#eaa662;font-weight:500;font-size:11.5px;letter-spacing:.02em}
.gr-menu a,.gr-menu .gr-mi{display:block;padding:8px 10px;border-radius:8px;text-align:left;
  color:#cdd3dc!important;text-decoration:none!important;font-size:13.5px;transition:background .12s}
.gr-menu a:hover{background:#262b34;color:#fff!important}
.gr-menu .gr-mi.muted{color:#6b7178!important;cursor:default}
.gr-menu a.gr-menu-pro{color:#eaa662!important;font-weight:600}
.gr-menu a.gr-menu-pro:hover{background:rgba(232,147,58,.12)}
.gr-menu-sep{height:1px;background:#2a2f38;margin:5px 4px}
/* --- Top bar: put the logo, the nav and the avatar on one line -----------
   Streamlit centres the three columns, but their contents drifted apart:
   an <iframe> is inline by default, so the nav reserved ~7px of descender
   space beneath it and rode high, while .gr-acct was an inline-block whose
   22px line box let the 38px avatar hang below. Both are boxes now. */
/* Scoped by what the row CONTAINS, not by position. ":first-of-type" also
   matched the first column row inside the profile form, which right-aligned
   and squashed its fields. :has() pins these rules to the top bar only. */
div[data-testid="stHorizontalBlock"]:has(.gr-home) iframe{display:block;margin:0}
/* The logo is a link home. line-height:0 stops the anchor's line box adding
   phantom height under the mark and knocking the bar out of line again. */
/* --- Top nav ---------------------------------------------------------------
   Plain links, deliberately. The old menu rendered inside an iframe, which put
   its CSS out of reach: at phone widths it stacked each icon above its label
   and set a ~117px floor under the header that nothing outside could fix.
   These are ordinary anchors using the same ?nav= routing the rest of the app
   already uses, so media queries reach them and the row stays one line. */
.gr-nav{display:flex;justify-content:center;align-items:center;gap:8px;
  flex-wrap:nowrap}
/* Streamlit paints markdown links its own accent colour, which washed out the
   active pill's label and made the inactive tabs read as links, so the colours
   here have to win outright. */
/* 15.5 here is navigation, deliberately larger than control — not the
   prose step even though it shares the value. */
.gr-nav a,.gr-nav a:link,.gr-nav a:visited{position:relative;font-size:15.5px;
  font-weight:600;color:#c3cad3!important;text-decoration:none!important;
  padding:10px 20px;border-radius:9px;white-space:nowrap;letter-spacing:-.1px;
  transition:background .18s ease,color .18s ease}
/* The active tab is marked by a RULE UNDER IT, not a solid amber slab behind
   the text. A filled pill was the single loudest element on a page whose whole
   job is to make gigs the loudest thing — and it fought the amber CTA buttons
   for the same attention. An underline reads as "you are here" without
   competing. ::after rather than border-bottom so it can animate width from
   the centre instead of appearing all at once. */
.gr-nav a::after{content:"";position:absolute;left:50%;right:50%;bottom:2px;
  height:2px;border-radius:2px;background:var(--amber);
  transition:left .22s cubic-bezier(.2,.7,.3,1),right .22s cubic-bezier(.2,.7,.3,1)}
/* The count rides inside the tab's own pill rather than floating over its
   corner: a corner badge on a text tab has nothing to anchor to and drifts as
   the label length changes. */
.gr-nav .gr-tabn{display:inline-block;margin-left:7px;min-width:18px;
  padding:1px 6px;border-radius:999px;font-size:11.5px;font-weight:700;
  line-height:1.5;text-align:center;color:#eaa662;
  background:rgba(232,147,58,.16);vertical-align:1px}
.gr-nav a.on .gr-tabn{color:#141414;background:var(--amber)}
.gr-nav a:hover{background:rgba(232,147,58,.09);color:#eaa662!important}
.gr-nav a:hover::after{left:30%;right:30%;background:rgba(232,147,58,.45)}
.gr-nav a.on,.gr-nav a.on:link,.gr-nav a.on:visited,.gr-nav a.on:hover{
  color:#F7B569!important;background:transparent}
.gr-nav a.on::after{left:18%;right:18%;background:var(--amber)}
@media (prefers-reduced-motion:reduce){
  .gr-nav a::after{transition:none}}
.gr-home{display:block;line-height:0;text-decoration:none!important;
  transition:opacity .14s ease}
.gr-home:hover{opacity:.8}
.gr-home svg{width:150px;height:auto;display:block}
/* The content sits in a centred column, but the TOP BAR spans the full width:
   the logo anchors the far-left corner and the avatar the far-right, the way a
   real app bar reads. It breaks out of the container's max-width with symmetric
   negative margins, then pads itself back off the very edges. */
div[data-testid="stHorizontalBlock"]:has(.gr-home){
  margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);
  width:100vw;max-width:100vw;box-sizing:border-box;
  padding:6px clamp(22px, 4vw, 64px) 12px;
  /* THE BAR IS ITS OWN SURFACE. It used to be the page's exact background
     with a 1px rule under it, which is why the header and the board read as
     one undifferentiated sheet: there was nothing there to see. It now sits a
     step above the page (--panel, already in the tokens and barely used) and
     STICKS, so the board scrolls beneath it. The blur is what sells that —
     content passing under frosted glass is the thing that makes a bar read as
     a layer rather than a stripe of colour.
     The gradient is deliberately near-invisible: opaque at the top where the
     logo and nav sit, easing to the panel colour at the rule, so the bar has
     a faint sense of depth instead of being one flat block. */
  background:linear-gradient(180deg,#181c22 0%,var(--panel) 100%);
  backdrop-filter:blur(14px) saturate(120%);
  -webkit-backdrop-filter:blur(14px) saturate(120%);
  border-bottom:1px solid #23272f;
  /* A shadow, not a second border. Two stacked lines under a bar is the look
     of a thing that has been bordered twice; a soft drop is how a real app bar
     separates itself from what's under it. */
  box-shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 10px 24px -14px rgba(0,0,0,.9)}
/* Streamlit's own toolbar sits above ours; without this the sticky bar slides
   under it and the logo clips on scroll. */
[data-testid="stHeader"]{background:transparent}
/* THE STICKY GOES ON THE WRAPPER, not on the bar itself. A sticky element can
   only travel inside its own parent's box, and Streamlit wraps this row in a
   stLayoutWrapper that is exactly the bar's height (measured: 64px for a 64px
   bar) — so `position:sticky` on the bar was honoured and had precisely zero
   room to move, scrolling away with the content. The wrapper's own parent is
   the full-length stVerticalBlock (~7,700px on the Gigs board), which is the
   travel room the bar needed. Scoped by :has(.gr-home) so it only ever hits
   this one row and not every layout wrapper on the page. */
[data-testid="stLayoutWrapper"]:has(.gr-home){
  position:sticky;top:0;z-index:900;
  /* Even with stHeader collapsed, this still rested 31.8px down: 20.8px from
     stMainBlockContainer's own padding-top (1.3rem, meant for the page
     CONTENT below, not this bar), plus an 11px flex gap the vertical block
     still applies before its first VISIBLE child — the injected <style>
     block ahead of it renders at zero height but still counts as a sibling
     for gap purposes. Pulling it up by that exact measured amount is what
     actually gets the panel color flush to the true top of the page,
     instead of leaving a sliver of raw page background above it. */
  margin-top:-31.8px}
/* Streamlit's three columns are ratios 2.0 / 4.9 / 1.3 (set in Python so the
   logo has room and the avatar doesn't), which measured out to the nav sitting
   50px right of the page's true centre — unequal flanks push the middle
   column's own centre off the bar's centre. A symmetric 1fr/auto/1fr grid
   fixes it regardless of what the flanks weigh: the same two-equal-tracks
   technique the mobile header already uses (below), just for desktop. */
@media (min-width:641px){
  div[data-testid="stHorizontalBlock"]:has(.gr-home){
    display:grid!important;grid-template-columns:1fr auto 1fr}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]{
    width:auto!important;min-width:0!important}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(1){
    justify-self:start}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(2){
    justify-self:center}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(3){
    justify-self:end}
}
/* 100vw includes the scrollbar, so clip the hair of overflow it would add. */
[data-testid="stAppViewContainer"],[data-testid="stMain"]{overflow-x:hidden}
/* The avatar's wrappers were pinned to a 22px line box, so a 38px avatar
   overflowed downward instead of the column growing to hold it. */
[data-testid="stColumn"]:has(.gr-acct)
  :is([data-testid="stElementContainer"],[data-testid="stMarkdown"],
      [data-testid="stMarkdownContainer"],[data-testid="stMarkdown"] > div){
  /* 45px = the logo's rendered height, which sets the bar height. Keeping the
     avatar's box the same means there is nothing left to centre. */
  height:100%!important;min-height:45px!important;align-self:stretch!important;
  display:flex!important;align-items:center!important;justify-content:flex-end!important;
  margin:0!important;padding:0!important;transform:none!important}
/* Streamlit centres a column by baking in a margin-top computed from the
   height it saw first (22px), which went stale once the box grew to 38px.
   Drop that margin, stretch the column to the full bar height, and centre the
   avatar inside it — no hard-coded offsets to drift out of date. */
[data-testid="stColumn"]:has(.gr-acct){
  margin-top:0!important;align-self:stretch;
  display:flex;align-items:center;justify-content:flex-end}
[data-testid="stColumn"]:has(.gr-acct) [data-testid="stVerticalBlock"]{
  height:100%!important;justify-content:center!important;align-items:flex-end!important}
.gr-acct{position:relative;display:flex;align-items:center;height:38px;
  margin-top:auto;margin-bottom:auto}   /* auto margins centre it in the bar */
section[data-testid="stSidebar"],div[data-testid="stSidebarCollapsedControl"]{display:none!important}
/* One centred content column for the whole app. Without a cap, the top (hero,
   search, stats) reads as a tidy column but the feed below sprawls edge-to-edge
   and loses the alignment — this keeps everything in the same ~1040px column so
   the page stays sharp all the way down, and the feed lines up with the stats. */
.block-container,div[data-testid="stMainBlockContainer"]{
  padding-top:1.3rem!important;max-width:1040px!important;
  margin-left:auto!important;margin-right:auto!important}
[data-testid="stMain"] hr{margin:4px 0 12px!important}
/* Measured on the live site: this was rendering at 60px, not the 0 the rule
   asked for — Streamlit sets its own height on this element with enough
   specificity to win over a plain, non-!important rule. That 60px, fully
   transparent, sat ABOVE the real header bar (.gr-home's wrapper starts
   lower down), showing raw page background through it — the "darker stripe
   above a lighter stripe" look. Everything this element used to hold
   (MainMenu, toolbar, deploy button, status widget) is already hidden
   below, so it has no remaining job; collapsing it for real removes the gap
   instead of trying to color-match two separate bars. */
header[data-testid="stHeader"]{height:0!important;min-height:0!important;background:transparent}
/* Hide Streamlit's own chrome so it reads as a real product, not a demo. */
#MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],.stDeployButton,[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],footer{display:none!important;visibility:hidden!important}
.gr-footer{max-width:980px;margin:52px auto 6px;padding:22px 16px 4px;
  border-top:1px solid #23262d;display:flex;flex-direction:column;
  align-items:center;gap:4px;text-align:center}
.gr-footer .brand{color:#eaa662;font-weight:700;font-size:14.5px;letter-spacing:.02em}
.gr-footer .tag{color:#8a919c;font-size:13.5px}
.gr-footer .foot-link{color:#8a919c;font-size:12.5px;font-weight:600;
  text-decoration:none;margin:2px 0}
.gr-footer .foot-link:hover{color:#eaa662}
.gr-footer .meta{color:#5a616c;font-size:11.5px}
/* --- Alert channel cards: name carries the weight, no emoji needed --- */
.gr-ch-h{font-size:17px;font-weight:650;color:#f2f4f7;letter-spacing:-.25px;margin:0 0 4px}
.gr-ch-s{font-size:12.5px;color:#98a0ab;line-height:1.5;margin:0 0 11px;min-height:38px}
.gr-ch-st{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  margin-top:9px;display:flex;align-items:center;gap:6px}
.gr-ch-st::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
.gr-ch-st.on{color:#69d7a1}
.gr-ch-st.off{color:#697080}
.gr-ch-st.warn{color:#e0a56a}
/* --- First run: pick a skill, watch the board re-sort around you ---------
   The old first-run experience was a banner telling you to go to another tab.
   This asks the one question that matters and answers it live, before you
   commit to anything. */
/* --- The one control on the front page -------------------------------------
   This used to be an amber banner with the input escaping full-bleed beneath
   it — two disconnected pieces, and the only element on the page not sharing
   the centre column. It's one quiet, centred control now: a small label and
   the field, both bounded to the same width as everything else. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-search-mark){
  max-width:620px!important;margin-left:auto!important;margin-right:auto!important;
  gap:6px!important}
.gr-search-lbl{text-align:center;font-size:13.5px;font-weight:600;color:#98a0ab;
  letter-spacing:.01em;margin:0 0 2px}
.gr-search-hint{text-align:center;font-size:13.5px;color:#7c838d;margin:8px 0 0}
.gr-search-hint a{color:#98a0ab!important;text-decoration:none!important;
  font-weight:600;border-bottom:1px solid rgba(232,147,58,.35)}
.gr-search-hint a:hover{color:#eaa662!important}
@keyframes gr-count{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

/* --- New gigs landing while you watch ------------------------------------
   A card carrying the "New" badge slides in rather than just appearing, so
   "every gig, the moment it drops" is something you see happen. */
/* NOTE: this targeted [data-testid="stVerticalBlockBorderWrapper"], which does
   not exist in Streamlit 1.59 — confirmed against the live DOM, the selector
   matched nothing and neither the slide-in nor the amber edge ever fired. The
   border lives on the stVerticalBlock itself (FEEL.md §8 says exactly this). */
@keyframes gr-land{from{opacity:0;transform:translateY(-9px)}to{opacity:1;transform:none}}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-new){
  animation:gr-land .5s cubic-bezier(.22,1,.36,1);
  border-color:rgba(232,147,58,.42)!important}
@media (prefers-reduced-motion:reduce){
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-new){
    animation:none}
}
/* --- The reply we already wrote ------------------------------------------
   This was the best thing in the product and it was hidden behind a collapsed
   row on every card, so nobody ever saw it. Shown, it's the moment people
   screenshot. */
.gr-draft{margin:2px 0 6px;border:1px solid rgba(232,147,58,.34);border-radius:16px;
  overflow:hidden;background:linear-gradient(180deg,rgba(232,147,58,.07),rgba(232,147,58,.02))}
.gr-draft-hd{padding:14px 18px 13px;border-bottom:1px solid rgba(232,147,58,.20);
  display:flex;flex-direction:column;gap:5px}
/* Monospace renders optically smaller at equal px — excluded from the
   scale by name, stays 10.5. */
.gr-draft-k{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  letter-spacing:.16em;text-transform:uppercase;color:#eaa662;font-weight:700}
.gr-draft-t{font-size:17px;font-weight:650;color:#f2f4f7;line-height:1.3;letter-spacing:-.2px}
.gr-draft-m{display:flex;gap:7px;flex-wrap:wrap;margin-top:2px}
/* Real paragraphs, not pre-wrap: the template's blank lines rendered as
   full-height gaps and the text ran the whole window. A message needs a
   readable measure, same as any other prose. */
.gr-draft-body{padding:16px 18px 17px;font-size:14.5px;line-height:1.62;color:#cbd2db;
  font-family:inherit;max-width:70ch}
.gr-draft-body p{margin:0 0 11px}
.gr-draft-body p:last-child{margin-bottom:0}
/* The free draft, inside the expander in gig_card — same body typography as
   the Pro showcase's .gr-draft-body, but a lighter container: the expander
   itself already draws a border, so a second amber-bordered box nested
   inside it would be one box too many. */
.gr-draft-body-free{background:#171a20;border-radius:12px;margin-bottom:10px}
@media (max-width:640px){
  .gr-draft-t{font-size:15.5px}
  .gr-draft-body{padding:14px 15px 15px;font-size:13.5px;line-height:1.6}
  .gr-draft-hd{padding:12px 15px 11px}
}
/* --- Trial / account strip -------------------------------------------------
   One quiet line telling you whose session this is and how long the trial has
   left. It sits above the fold on every page because "when does this stop
   working" is the question a tester will actually have. */
/* Deliberately not a flex row: `gap` treats every inline run as its own item,
   so a bolded phrase mid-sentence got 9px punched in before the next word and
   it read as "Nabbly Free ." */
.gr-trial{display:block;font-size:13.5px;line-height:1.5;padding:9px 16px;
  border-radius:11px;margin:0 0 6px;text-align:center;text-wrap:pretty;
  background:rgba(232,147,58,.08);border:1px solid rgba(232,147,58,.24);color:#c3cad3}
.gr-trial b{color:#E8933A;font-weight:700}
.gr-trial.over{background:rgba(233,98,80,.09);border-color:rgba(233,98,80,.32)}
.gr-trial.over b{color:#f2a08f}
.gr-trial.free{background:#15181d;border-color:#262b33;color:#9aa1ab}
.gr-trial.free b{color:#c8ced7}
@media (max-width:640px){.gr-trial{font-size:12.5px;padding:8px 12px}}
/* --- Early-access capture card --- */
.gr-cap{max-width:640px;margin:0 auto 14px;padding:20px 22px 18px;text-align:center;
  background:linear-gradient(180deg,rgba(232,147,58,.09),rgba(232,147,58,.03));
  border:1px solid rgba(232,147,58,.28);border-radius:16px}
.gr-cap.joined{background:linear-gradient(180deg,rgba(53,179,126,.10),rgba(53,179,126,.03));
  border-color:rgba(53,179,126,.32)}
.gr-cap.plain{background:#15181d;border-color:#262a31}
.gr-cap-h{font-size:19px;font-weight:650;color:#f2f4f7;letter-spacing:-.25px;margin-bottom:6px}
.gr-cap-s{font-size:14.5px;color:#98a0ab;line-height:1.55;max-width:52ch;margin:0 auto}
.gr-cap-s b{color:#eaa662}

/* --- Cohesive call-to-action / feedback cards -----------------------------
   The border wraps the WHOLE card (heading, copy, input, button) via a real
   st.container, instead of the old bordered box that held only the heading and
   left the form floating loose beneath it. Scoped by an invisible marker span
   so it never catches the many other bordered containers on the page (gig
   cards use the same wrapper). */
/* The bordered container is the stVerticalBlock that has our marker as a direct
   element-container child. Matching the marker anywhere via :has would also
   catch the column and page blocks that wrap it; the `>` pins it to the exact
   container so only that one card is styled. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-cta-mark){
  border:1px solid rgba(232,147,58,.30)!important;border-radius:18px!important;
  background:linear-gradient(180deg,rgba(232,147,58,.08),rgba(232,147,58,.02))!important;
  padding:6px 20px 14px!important}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-fb-mark){
  border:1px solid #262a31!important;border-radius:18px!important;
  background:#15181d!important;padding:6px 20px 14px!important}
.gr-cta-h{font-size:19px;font-weight:700;color:#f4f6f9;letter-spacing:-.3px;
  text-align:center;margin:8px 0 3px}
.gr-cta-s{font-size:13.5px;color:#98a0ab;line-height:1.5;text-align:center;
  max-width:44ch;margin:0 auto 13px}
.gr-cta-s b{color:#eaa662}
.gr-feat{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 7px;
  margin:2px auto 15px;max-width:430px}
.gr-feat span{font-size:12px;font-weight:500;color:#d3d9e1;
  background:rgba(232,147,58,.10);border:1px solid rgba(232,147,58,.22);
  border-radius:999px;padding:3px 11px;white-space:nowrap}
.gr-feat span::before{content:"✓ ";color:#eaa662;font-weight:700}
.gr-cta-fine{text-align:center;font-size:11.5px;color:var(--faint);margin:9px 0 6px}
.gr-updialog-hook{font-size:15.5px;line-height:1.55;color:#d3d9e1;text-align:center;
  max-width:46ch;margin:2px auto 18px}
.gr-mini{text-align:center;font-size:13.5px;color:#9aa1ab;margin:4px 0 8px}
.gr-mini b{color:#eaa662;font-weight:700}
.gr-dash-end{text-align:center;font-size:13.5px;color:#868d98;margin:6px 0 4px;
  padding:18px 0 6px}
.gr-dash-end a,.gr-dash-end a:link,.gr-dash-end a:visited{color:#eaa662!important;
  font-weight:600;text-decoration:none!important}
.gr-dash-end a:hover{text-decoration:underline!important}

/* --- Hero without the paragraph, and the quiet link to the story ---------- */
.gr-hero-tight{padding-bottom:6px}
/* Streamlit colours markdown links blue by default; force our muted grey so it
   doesn't fight the amber brand. */
.gr-about-link,.gr-about-link:link,.gr-about-link:visited{display:inline-block;
  margin-top:4px;font-size:13.5px;font-weight:600;color:#8a919c!important;
  text-decoration:none!important;letter-spacing:.01em;transition:color .15s}
.gr-about-link:hover{color:#eaa662!important}

/* --- Gig-list pager: quiet page controls, top and bottom of the list ------
   Same two ghost buttons every time, so paging feels like one continuous
   control rather than a different widget depending on where you are. */
.gr-page-n{text-align:center;font-size:13.5px;color:#969da7;line-height:1.3;
  font-variant-numeric:tabular-nums}
.gr-page-top{text-align:center;margin-top:3px}
.gr-page-top .gr-about-link{font-size:12.5px;margin-top:0}

/* --- About page ----------------------------------------------------------- */
.gr-about{max-width:680px;margin:6px auto 0;line-height:1.68}
.gr-about h2{font-size:26px;font-weight:750;letter-spacing:-.5px;color:#f4f6f9;
  margin:26px 0 10px;text-wrap:balance}
.gr-about h2:first-child{margin-top:6px}
.gr-about p{font-size:15.5px;color:#b8bfc9;margin:0 0 14px}
.gr-about p b{color:#e7ebf1;font-weight:600}
.gr-about .lead{font-size:18px;color:#dfe4ea;line-height:1.6}
.gr-about ol{margin:0 0 16px;padding-left:0;counter-reset:step;list-style:none}
.gr-about ol li{position:relative;padding:2px 0 12px 40px;font-size:15.5px;color:#b8bfc9}
.gr-about ol li b{color:#eef1f5}
.gr-faq-a{font-size:14.5px;color:#b8bfc9;line-height:1.65;padding:2px 2px 6px;
  max-width:70ch}

/* ── Long-form documents: Privacy, Terms ────────────────────────────────────
   These rendered as raw Streamlit markdown while About and FAQ had a proper
   type treatment, so they read like a different product. Same column width,
   colours and rhythm as .gr-about, but left-aligned headings and real list
   styling, because a policy is read top-to-bottom rather than scanned. */
.gr-doc{max-width:680px;margin:2px auto 0;line-height:1.68}
.gr-doc .gr-doc-title{font-size:31px;font-weight:700;letter-spacing:-.6px;
  color:#f4f6f9;margin:2px 0 4px;line-height:1.15}
.gr-doc .gr-doc-sub{font-size:13.5px;color:#7c828d;margin:0 0 26px;
  padding-bottom:18px;border-bottom:1px solid #262b33}
.gr-doc h2{font-size:22px;font-weight:650;letter-spacing:-.4px;color:#f2f4f7;
  margin:34px 0 10px;text-align:left;text-wrap:balance}
/* Section heads carry a short amber rule instead of sitting as plain bold
   text — the one piece of brand language these pages had none of, and it
   gives the eye something to catch when scanning a long policy. NOTE: these
   are h3, not h2: legal.py's markdown uses "## " only for the document title
   (which renders separately as .gr-doc-title) and "### " for every section,
   so styling h2 here targeted nothing at all. */
.gr-doc h3{font-size:18px;font-weight:650;letter-spacing:-.25px;color:#f2f4f7;
  margin:38px 0 12px;text-wrap:balance;
  padding-top:15px;border-top:1px solid #1e222a;position:relative}
.gr-doc h3::before{content:"";position:absolute;top:-1px;left:0;
  width:34px;height:2px;background:var(--amber);border-radius:2px}
.gr-doc p{font-size:15.5px;color:#b8bfc9;margin:0 0 15px}
.gr-doc strong{color:#eef1f5;font-weight:600}
/* Most paragraphs here open "**What we collect.** Then the explanation." Eight
   of those in a row reads as the text flickering between bold and not. Treated
   as a deliberate lead-in — its own colour, a hair of letter-spacing — the
   same pattern becomes structure instead of noise. */
.gr-doc p > strong:first-child{color:var(--amber-l);font-weight:650;
  letter-spacing:.005em}
.gr-doc ul{margin:0 0 16px;padding-left:20px}
.gr-doc li{font-size:15.5px;color:#b8bfc9;margin:7px 0;padding-left:2px}
.gr-doc li::marker{color:#E8933A}
.gr-doc a{color:#eaa662!important;text-decoration:none;
  border-bottom:1px solid rgba(232,147,58,.35)}
.gr-doc a:hover{border-bottom-color:#E8933A}
@media (max-width:640px){
  .gr-doc .gr-doc-title{font-size:25px}
  .gr-doc h2{font-size:19px;margin-top:28px}
  .gr-doc h3{font-size:16.5px;margin-top:30px}
  /* prose stays 15.5 at every width — line-height is the mobile lever,
     not a smaller size on the surface built for reading. */}
.gr-footer .foot-links{display:flex;gap:16px;align-items:center}
/* Keep the FAQ's heading and its rows in one column — the heading sat in a
   centred 680px block while the expanders ran the full width. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-faq-mark){
  max-width:680px!important;margin-left:auto!important;margin-right:auto!important}
.gr-about h2{text-align:center}
.gr-about ol li::before{counter-increment:step;content:counter(step);
  position:absolute;left:0;top:0;width:27px;height:27px;border-radius:8px;
  background:rgba(232,147,58,.14);border:1px solid rgba(232,147,58,.3);
  color:#eaa662;font-weight:700;font-size:13.5px;display:flex;align-items:center;
  justify-content:center;font-family:ui-monospace,Menlo,monospace}
/* Free vs Pro as two cards. The same information was a single paragraph of
   bolded fragments — you had to read it to compare two things that a reader
   wants to scan side by side. Pro carries the one amber edge on the page
   (FEEL.md §2: one focal point), Free stays neutral. */
.gr-ab-plans{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:6px 0 20px;
  align-items:start}
.gr-ab-plan{background:var(--bg2);border:1px solid var(--line);
  border-radius:14px;padding:18px 18px 6px;text-align:left;position:relative}
/* The card we actually want someone to pick — stronger border, a real glow
   instead of a tint, and a small lift so it reads as the featured option
   without a second accent colour entering the page (still one amber focal
   point, just a louder one). */
.gr-ab-plan.pro{border-color:rgba(232,147,58,.55);border-width:1.5px;
  background:linear-gradient(180deg,rgba(232,147,58,.10),rgba(232,147,58,.02));
  box-shadow:0 0 0 1px rgba(232,147,58,.08),0 22px 44px -22px rgba(232,147,58,.45);
  transform:translateY(-6px)}
@media (max-width:640px){.gr-ab-plan.pro{transform:none}}
.gr-ab-name{font-size:17px;font-weight:700;color:var(--ink);letter-spacing:-.2px}
.gr-ab-plan.pro .gr-ab-name{color:var(--amber)}
.gr-ab-sub{font-size:13.5px;color:var(--mute);margin:3px 0 10px}
.gr-about .gr-ab-plan ul{margin:0;padding-left:0;list-style:none}
.gr-about .gr-ab-plan li{font-size:14.5px;color:var(--ink2);margin:0 0 9px;
  padding-left:20px;position:relative;line-height:1.5}
.gr-about .gr-ab-plan li::before{content:"";position:absolute;left:2px;top:8px;
  width:6px;height:6px;border-radius:50%;background:var(--line2)}
.gr-about .gr-ab-plan.pro li::before{background:var(--amber)}
@media (max-width:640px){.gr-ab-plans{grid-template-columns:1fr}}
/* Forms lose Streamlit's chrome so the capture cards read as one block. NOTE:
   this must not constrain width — an earlier max-width here squeezed the
   profile form into the middle of the page and collided its labels. */
div[data-testid="stForm"]{border:0;padding:0}
/* In-copy links (e.g. URLs inside gig descriptions): on-brand amber + soft
   underline instead of Streamlit's default blue. Skips our own gr-* links. */
[data-testid="stMarkdownContainer"] a:not([class*="gr-"]){
  color:#e0a56a;text-decoration:underline;text-decoration-thickness:1px;
  text-decoration-color:rgba(232,147,58,.4);text-underline-offset:2.5px;
  transition:color .13s ease,text-decoration-color .13s ease}
[data-testid="stMarkdownContainer"] a:not([class*="gr-"]):hover{
  color:#E8933A;text-decoration-color:#E8933A}
/* ===========================================================================
   MOBILE (phones)

   Not a shrunk desktop. Three things were wrong at 375px and they're fixed as
   a system rather than one-off overrides:

   1. THE TOP BAR ate 152px — 19% of the screen — because Streamlit gives each
      column width:343px, so all three wrapped onto their own line (logo, then
      nav, then a lonely avatar). Content didn't start until y=222px, a quarter
      of the way down. It's a grid now: logo and avatar share row one, nav gets
      row two full-width.
   2. TYPE was still desktop-sized (h3 at 28px), so headings wrapped to two
      lines and everything felt oversized. There's a real mobile ramp below.
   3. TAP TARGETS were under 44px in places, and the Gigs location filter
      rendered as three ragged different-width rows.
   =========================================================================== */
@media (max-width:640px){

  /* --- 0. Vertical rhythm: reclaim the space above the fold ------------- */
  /* Streamlit ships desktop spacing: 20.8px of container padding, a 16px gap
     between every block, and 16px of margin on each divider. On a 812px-tall
     phone that's a lot of nothing before anything is read. */
  [data-testid="stMainBlockContainer"]{padding-top:.7rem!important;
    padding-left:1rem!important;padding-right:1rem!important}
  [data-testid="stVerticalBlock"]{gap:11px!important}
  hr{margin:2px 0 9px!important}

  /* --- 1. Top bar: three rows down to two ------------------------------- */
  /* Scoped by what the row CONTAINS. Never :first-of-type — that also matches
     the first column row inside the profile form and wrecks it. */
  div[data-testid="stHorizontalBlock"]:has(.gr-home){
    display:grid!important;
    grid-template-columns:1fr auto;
    grid-template-areas:"logo avatar" "nav nav";
    align-items:center;
    gap:10px 12px!important}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]{
    width:auto!important;min-width:0!important}   /* defeat Streamlit's 343px */
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(1){
    grid-area:logo}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(2){
    grid-area:nav}
  div[data-testid="stHorizontalBlock"]:has(.gr-home) > [data-testid="stColumn"]:nth-child(3){
    grid-area:avatar}
  .gr-home svg{width:124px;margin:0}
  .gr-acct{justify-content:flex-end}
  .gr-menu{top:44px;right:0}

  /* --- 2. Mobile type ramp ---------------------------------------------- */
  .gr-h1{font-size:26px!important;letter-spacing:-.6px!important;
    line-height:1.16!important;margin-bottom:11px!important}
  .gr-sub{font-size:14.5px!important;line-height:1.55!important}
  .gr-hero{padding:4px 2px 2px;margin-top:0}
    h3{font-size:21px!important;letter-spacing:-.5px!important;line-height:1.2!important}
  h4{font-size:17px!important;letter-spacing:-.3px!important}
  a.gr-title{font-size:16.5px!important;line-height:1.35}
  .gr-cap-h{font-size:17px}
  .gr-cap-s{font-size:13.5px}
  .gr-ch-h{font-size:16px}

  /* --- 3. Cards, controls, tap targets ---------------------------------- */
  .gr-stats{gap:9px;align-items:stretch}
  .gr-stat{min-width:calc(50% - 5px);padding:13px 13px 14px;
    display:flex;flex-direction:column;justify-content:space-between}
  .gr-stat .l{min-height:2.5em}          /* a wrapped label can't skew a row */
  .gr-stat .n{font-size:24px}
  .gr-cap{padding:17px 16px 15px}

  /* Anything you tap gets a thumb-sized target. Streamlit ships text inputs at
     36px and selects at 38px, which is fine with a mouse and fiddly with a
     thumb. (Tooltip "?" icons are left alone — they're markers, not targets.) */
  .stButton button, [data-testid="stFormSubmitButton"] button,
  [data-testid="stButtonGroup"] button[role="radio"],
  [data-testid="stRadioGroup"] label{min-height:44px!important}
  [data-testid="stTextInputRootElement"],
  [data-testid="stTextInputRootElement"] input,
  [data-testid="stNumberInputContainer"],
  [data-testid="stSelectbox"] > div > div{min-height:44px!important}
  [data-testid="stTextInputRootElement"] input{font-size:16px!important}  /* iOS
     zooms the page on focus for anything under 16px — this prevents that. */

  /* The Gigs location filter (st.segmented_control). Take two: the first
     mobile fix stacked the three options as full-width rows — even, but
     three rows of chrome on a page that already had seven. A swipeable chip
     row is one row, the pattern every phone user already knows from app
     stores and news apps. The gradient hints there's more to the right. */
  [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]){
    width:100%!important;align-self:stretch!important;position:relative}
  [data-testid="stButtonGroup"]{width:100%!important;max-width:none!important;
    overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
  [data-testid="stButtonGroup"]::-webkit-scrollbar{display:none}
  [data-testid="stButtonGroup"] > [role="radiogroup"]{
    display:flex!important;flex-wrap:nowrap!important;gap:7px!important;
    width:max-content!important;max-width:none!important}
  [data-testid="stButtonGroup"] button[role="radio"]{
    flex:0 0 auto;white-space:nowrap;justify-content:center}
  /* the label inside truncates at a fixed width — let it use the room */
  [data-testid="stButtonGroup"] button[role="radio"] > *{
    width:auto!important;overflow:visible!important;text-overflow:clip!important}
  /* THE GRADIENT THE COMMENT ABOVE PROMISED. It was never actually written:
     the container got position:relative to host it and nothing else, so the
     row just ended mid-word at the screen edge with no signal it scrolled.
     The founder read that as the layout bleeding off the page, which is the
     correct reading of a hard cut. A fade to the page ground says "there is
     more this way" the way every app-store shelf does. pointer-events:none so
     it can't eat a tap on the chip underneath it. */
  [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"])::after{
    content:"";position:absolute;top:0;bottom:0;right:0;width:34px;
    pointer-events:none;
    background:linear-gradient(90deg,rgba(18,20,24,0),rgba(18,20,24,.92))}

  /* Title row and pager keep their columns side by side. Streamlit stacks
     every stColumn full-width on phones, which turned "title + Refresh" into
     two bars and the pager into THREE (Prev / label / Next). Same technique
     as the top bar above: defeat the forced column width, put the row back. */
  div[data-testid="stHorizontalBlock"]:has(.gr-tools){
    display:grid!important;grid-template-columns:1fr auto;align-items:center;
    gap:8px!important}
  div[data-testid="stHorizontalBlock"]:has(.gr-tools) > [data-testid="stColumn"]{
    width:auto!important;min-width:0!important}
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-pg_"]){
    display:grid!important;grid-template-columns:1fr auto 1fr;
    align-items:center;gap:8px!important}
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-pg_"]) > [data-testid="stColumn"]{
    width:auto!important;min-width:0!important}
}

/* "New gigs arrived" nudge — a small, centred outline chip, not a full-width
   amber slab. Outline instead of fill, amber only in the text, so it invites a
   tap without breaking the calm of the page. Scoped to this one button by its
   key (Streamlit tags the container .st-key-arrivals). */
.st-key-arrivals{display:flex;justify-content:center;margin:0 0 12px}
.st-key-arrivals button{
  width:auto!important;min-height:0!important;
  background:#171a20!important;border:1px solid rgba(232,147,58,.28)!important;
  color:#e0a35f!important;border-radius:999px!important;
  padding:6px 15px!important;box-shadow:none!important;transition:.15s}
.st-key-arrivals button:hover{
  background:#1c2027!important;border-color:rgba(232,147,58,.55)!important;
  transform:none!important}
.st-key-arrivals button p{font-size:13.5px!important;font-weight:500!important;margin:0!important}

/* Sign-in page: the quiet "or" between email and Google */
.gr-or{display:flex;align-items:center;gap:12px;margin:14px 0 10px;color:#7c828d;
  font-size:12.5px;font-weight:600;letter-spacing:.03em}
.gr-or::before,.gr-or::after{content:"";flex:1;height:1px;background:#262b33}
/* Google's four-colour G in front of the "Continue with Google" label, drawn
   as an inline data-URI so nothing loads from a third party. */
.st-key-signin_google button p::before,
[class*="st-key-goog_"] button p::before{
  content:"";display:inline-block;width:17px;height:17px;margin:0 9px -3px 0;
  background:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="%23EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="%234285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="%23FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="%2334A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>') no-repeat center/contain}

/* ── Loading: a sweep, not a dimmer ──────────────────────────────────────────
   Streamlit's only "we're working" signal is fading the whole page down, which
   reads as the screen going dark for no reason rather than as progress. Two
   changes: keep the content at full brightness, and run a thin amber sweep
   across the top — the same radar language as the mark, and a pattern people
   already know from GitHub/YouTube. Driven by Streamlit's own
   data-test-script-state attribute, so it's exact rather than guessed timing. */
[data-testid="stApp"] [data-stale="true"]{opacity:1!important}
/* The bar is only CREATED while the script runs — no base rule to be overridden
   and left showing a static strip when idle. */
[data-testid="stApp"][data-test-script-state="running"]::before,
[data-testid="stApp"][data-test-script-state="rerunRequested"]::before{
  content:"";position:fixed;top:0;left:0;right:0;height:2.5px;z-index:99999;
  pointer-events:none;
  background-image:linear-gradient(90deg,
    rgba(232,147,58,0) 0%, rgba(232,147,58,.18) 28%,
    #F7B569 50%, rgba(232,147,58,.18) 72%, rgba(232,147,58,0) 100%);
  background-size:45% 100%;background-repeat:no-repeat;
  animation:nb-sweep 1.15s cubic-bezier(.45,.05,.35,1) infinite}
@keyframes nb-sweep{
  0%{background-position:-45% 0}
  100%{background-position:145% 0}}
@media (prefers-reduced-motion:reduce){
  [data-testid="stApp"][data-test-script-state="running"]::before,
  [data-testid="stApp"][data-test-script-state="rerunRequested"]::before{
    animation:none;background-position:50% 0}}

/* The page title, shared by Dashboard, Gigs, Market and Saved. Used to be a
   quiet "working title, not a billboard" on Dashboard (25px, its own class)
   while the other three tabs used the plain ### heading, which the type
   scale below renders at 30px — so the one place someone actually lands on
   was the SMALLEST title in the app. One shared, more prominent size now,
   applied consistently everywhere someone opens a main tab. */
.gr-page-head{margin:4px 0 22px}
.gr-page-head h2{font-size:36px;font-weight:700;letter-spacing:-.5px;color:#ECEEF1;
  margin:0 0 7px}
.gr-page-head p{font-size:15.5px;color:#8a919c;margin:0}
@media (max-width:640px){.gr-page-head h2{font-size:26px}}

/* ── Gigs page: make the controls read as ONE toolbar ───────────────────────
   Streamlit puts a 16px gap between every block, so six stacked control rows
   became six separate bars floating in space. Tightening the gap inside the
   toolbar region groups them, and the page reaches an actual gig far sooner.
   Scoped by a marker span so it can't touch the rest of the app. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-tools){
  gap:.55rem!important}
/* The "Narrow it down" expander was a heavy full-width bar competing with the
   search. Quieter border, tighter padding, so it reads as a secondary option. */
[data-testid="stExpander"]{border-color:#22262e!important;background:transparent!important}
[data-testid="stExpander"] summary{padding:7px 12px!important;font-size:13.5px!important}
[data-testid="stExpander"] summary p{font-size:13.5px!important;color:#98a0ab!important}

/* ── Gigs toolbar ───────────────────────────────────────────────────────────
   "Check for new gigs" was a full-width boxy button in its own half-width row
   above everything, and the "clear" buttons were parked at the far right edge,
   miles from the label they belong to. Both now read as quiet controls beside
   the thing they act on. */
.st-key-checknew button{
  min-height:0!important;background:#171a20!important;
  border:1px solid #2f343d!important;color:#c3cad3!important;
  border-radius:10px!important;padding:9px 14px!important;box-shadow:none!important}
.st-key-checknew button:hover{
  border-color:rgba(232,147,58,.55)!important;color:#eaa662!important;
  background:#1c2027!important;transform:none!important}
.st-key-checknew button p{font-size:13.5px!important;font-weight:600!important;margin:0!important}

/* The "clear this filter" chips: small, quiet, and adjacent to their label. */
[class*="st-key-clear"] button{
  min-height:0!important;background:transparent!important;
  border:1px solid #2f343d!important;color:#8a919c!important;
  border-radius:999px!important;padding:4px 12px!important;box-shadow:none!important}
[class*="st-key-clear"] button:hover{
  border-color:rgba(232,147,58,.5)!important;color:#eaa662!important;
  background:#181c22!important;transform:none!important}
[class*="st-key-clear"] button p{font-size:12.5px!important;font-weight:500!important;margin:0!important}

/* Streamlit's chart toolbar ships a "Show data" toggle that swaps the chart for
   a raw dataframe — internal column names and all (job_type, size_tier). That's
   our plumbing, not something a freelancer needs to see. Fullscreen stays, and
   the Market page offers a proper CSV export with readable headings instead. */
[data-testid="stElementToolbar"] button[aria-label="Show data"]{display:none!important}

/* Streamlit prints "Press Enter to apply / submit form" under every text box.
   It explains a convention people already know and leaves a line of grey noise
   under the search field. (Confirmed test id from Streamlit's own bundle.) */
[data-testid="InputInstructions"]{display:none!important}

/* ═══════════════════════════════════════════════════════════════════════════
   THE DESIGN PASS  (FEEL.md §9 — the four gaps against Linear/Vercel/Raycast)

   Measured against the live DOM before writing any of this. The finding that
   shaped it: three of the four "gaps" were not wrong values, they were surfaces
   we had never styled at all, still running Streamlit's stock defaults inside an
   otherwise hand-built app. Specifically, inside one gig card the title was
   19px, the body 16px and the "Posted…" line 14px — and the body and the
   caption were BOTH rgb(250,250,250), the same brightness as the title. Nothing
   receded, so nothing stood out. That is the whole "compressed scale" problem.
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── 1. Vertical rhythm ── Vercel's lesson ──────────────────────────────────
   Streamlit puts a flat 16px between every block on the page. The gap INSIDE a
   gig card was 16px and the gap BETWEEN two gig cards was also 16px, so a card
   read as four loose rows rather than one object. Sections, groups and items
   get three different distances now; that difference is the entire effect. */
/* Opt-in, not blanket. A page TITLE and a SECTION heading are both "###", so a
   global h3 margin pushed every view's first line 35px down the screen — and a
   :first-child reset can't catch it, because Streamlit leaves zero-height
   containers between the top bar and the title. A heading declares itself a
   section break instead; there are only two of them, and it can't drift. */
h3:has(.gr-sect){margin-top:var(--s-section)!important}
.gr-sect{display:none}
/* Sub-headings ("####") are always mid-page, so they always get the group gap. */
h4{margin-top:1.4rem!important}
/* A full-width rule immediately followed by a section gap is the same statement
   made twice, and the line is the weaker half. Space separates; the border just
   adds another edge to a page that already has too many (FEEL.md §9.4). */
[data-testid="stElementContainer"]:has(hr):has(+ [data-testid="stElementContainer"] h3:has(.gr-sect)){
  display:none}

/* ── 2. Type scale ── Linear's lesson ───────────────────────────────────────
   Widen the jump between display and body. Most of the compression is at the
   BOTTOM of the ramp (body and meta nearly matching the title), so pulling meta
   down and back does more work than pushing headings up. */
/* Desktop only. This block sits AFTER the mobile media query in the stylesheet,
   so an unscoped "!important" here would win the cascade on phones too and undo
   the mobile ramp — which is exactly what it did the first time round: h3 jumped
   from 21px back to 30px at 375px. Min-width keeps the two ramps independent. */
@media (min-width:641px){
  h3{font-size:30px!important;font-weight:700!important;letter-spacing:-.02em!important;
    line-height:1.2!important;color:var(--ink)}
  h4{font-size:20px!important;font-weight:650!important;letter-spacing:-.01em!important}
}

/* ── 3. The gig card ── Raycast's lesson ────────────────────────────────────
   Sixty near-identical blocks have to be skimmable, which means one dominant
   thing per row and everything else quietly below it. Scoped by what the block
   CONTAINS (never :first-of-type — that leaked into the profile form once). */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title){
  /* 4. …and the card finally gets the house border. It was the most repeated
     element on the site and the ONLY box still on Streamlit's stock
     rgba(250,250,250,.2) at 8px radius, while every hand-built card uses
     #262a31. That mismatch is why the board read as foreign. */
  border:1px solid var(--line)!important;border-radius:14px!important;
  background:#14171b!important;
  padding:15px 18px 13px!important;
  gap:var(--s-item)!important}          /* items inside < gap between cards */
/* A card lifts slightly under the pointer. Border-colour alone was too quiet
   to register as "this row is the one you're on" in a list of sixty, and the
   stat cards already lift 3px — this is the same idea at half the distance,
   because a gig card is much larger and a big element moving far reads as
   the page wobbling. The shadow is what actually sells it; the 1px is just
   enough to catch the eye. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title){
  transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title):hover{
  border-color:#3a414d!important;transform:translateY(-1px);
  box-shadow:0 10px 26px -18px rgba(0,0,0,.95)}
@media (prefers-reduced-motion:reduce){
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title){
    transition:none}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title):hover{
    transform:none}
}

@media (min-width:641px){
  a.gr-title{font-size:18px!important;font-weight:650!important;letter-spacing:-.2px}
}
a.gr-title{font-weight:650}
/* Body copy steps down and back. It is context for the title, not a peer. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title)
  > [data-testid="stElementContainer"] > [data-testid="stMarkdown"] p{
  font-size:14.5px;line-height:1.55;color:var(--mute)}
/* "Posted Jan 31" is the quietest thing in the card — it was 14px pure white. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title)
  [data-testid="stCaptionContainer"] p{
  font-size:12.5px!important;color:var(--faint)!important}

/* ── Card body: same height every time, expandable in place ────────────────
   Cards ran from two lines to twelve depending on the post, so a column of
   them looked ragged and unfinished. Three lines for everyone, with the rest
   one click away. The gap above sits here (not on the pills) so a card with
   NO description gets the identical gap before its date — that mismatch was
   what made the two card shapes look like different components. */
/* padding, NOT margin: this sits inside Streamlit's markdown wrapper, which
   collapses a child's top margin — the gap measured at exactly the card's 8px
   flex gap, i.e. the margin was doing nothing and the pills still sat right on
   top of the text. Padding can't collapse, so the separation is real.
   The number is empirical, not tidy: the pills row's own box overhangs the
   wrapper's top edge by ~2px, so the visible gap always lands a couple of
   pixels under whatever is set here. 18px measures as ~16px on screen. */
.gr-bodywrap{padding-top:18px}
/* A card with no description has no body box above the date, so it needs less
   padding to land on the same visible gap as one that does (item 10). */
.gr-bodywrap.gr-nobody{padding-top:9px}
.gr-body{font-size:14.5px;line-height:1.55;color:var(--mute);
  display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;
  overflow:hidden;white-space:pre-line}
.gr-more-cb{display:none}
.gr-more-cb:checked ~ .gr-body{-webkit-line-clamp:unset}
/* The label only earns its place when the text is actually cut off. We can't
   measure that in CSS, so it's always present but reads as a quiet link. */
.gr-more-lbl{display:inline-block;margin-top:5px;font-size:12.5px;font-weight:600;
  color:var(--mute);cursor:pointer;user-select:none;transition:color .13s}
.gr-more-lbl::after{content:"See more"}
.gr-more-cb:checked ~ .gr-more-lbl::after{content:"Show less"}
.gr-more-lbl:hover{color:var(--amber)}
/* Streamlit's own wrapper around this markdown block consistently under-
   reports its height by exactly 16px versus what actually renders here —
   verified on every card, not content-dependent (likely a stale auto-height
   measurement against the -webkit-box/line-clamp body above). Since the
   wrapper's reported height is what the flex `gap` to the next card row
   (the expander) is measured from, the real content spilled ~16px into it —
   worse on hover only because the expander's hover fill made the overlap
   visible; it was there unhovered too. Adding the missing 16px back as
   margin-bottom makes this element's own box match its real rendered size,
   which pulls the wrapper's reported height back in line with it. */
.gr-posted{font-size:12.5px;color:var(--faint);margin-top:9px;margin-bottom:16px}

/* "Send to hr@company.com" — the one place a draft turns into a sent message.
   Amber gradient because on a card where it appears, it IS the primary action
   (FEEL.md §4: one primary per screen; a gig card is that screen). */
a.gr-sendmail{display:block;margin:10px 0 2px;padding:11px 16px;border-radius:11px;
  text-align:center;font-size:14.5px;font-weight:650;letter-spacing:-.1px;
  color:#141414!important;text-decoration:none!important;
  background:linear-gradient(180deg,var(--amber-l),var(--amber-d));
  transition:filter .15s ease,transform .15s ease}
a.gr-sendmail:hover{filter:brightness(1.06);transform:translateY(-1px)}

/* ── Plan card ─────────────────────────────────────────────────────────────
   Replaces a stock st.success/st.info banner. Those use Streamlit's own green
   and blue, which are the only colours on the page that answer to nothing in
   FEEL.md §2 — a bright green slab in the middle of a near-black column read
   as someone else's component dropped into ours. */
/* "Coming soon" beside a section heading — same quiet amber chip the landing
   page uses, so a not-yet-live feature reads identically in both places. */
.gr-soon{display:inline-block;margin-left:10px;font-size:10px;font-weight:650;
  letter-spacing:.08em;text-transform:uppercase;color:var(--amber);
  background:rgba(232,147,58,.10);border:1px solid rgba(232,147,58,.26);
  border-radius:100px;padding:3px 9px;vertical-align:4px}
.gr-plan{background:var(--bg2);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px}

/* The one-time "just paid" reveal — plays exactly once, the render right
   after Stripe redirects back (see _pro_activated in plan_card). Perks tick
   in one at a time, then a longer pause before "Switch to Free" drifts in
   noticeably slower than the rest — a soft close, not another beat in the
   rhythm, so the last thing anyone sees isn't a big exit control. */
.gr-plan-anim{opacity:0;animation:gr-plan-in .4s ease-out .1s forwards}
.gr-unlocks{display:flex;flex-direction:column;gap:9px;margin-top:14px;
  padding-top:14px;border-top:1px solid var(--line)}
.gr-unlock{display:flex;align-items:center;gap:9px;font-size:13.5px;color:var(--ink2);
  opacity:0;transform:translateY(7px);animation:gr-rise-in .38s cubic-bezier(.22,.9,.35,1) forwards}
.gr-tick{width:16px;height:16px;border-radius:50%;flex:0 0 auto;
  background:rgba(84,185,90,.14);color:#54B95A;font-size:10px;font-weight:900;
  display:flex;align-items:center;justify-content:center;transform:scale(0);
  animation:gr-tick-pop .32s cubic-bezier(.3,1.6,.4,1) forwards}
.gr-unlock:nth-child(1){animation-delay:.55s}.gr-unlock:nth-child(1) .gr-tick{animation-delay:.63s}
.gr-unlock:nth-child(2){animation-delay:.73s}.gr-unlock:nth-child(2) .gr-tick{animation-delay:.81s}
.gr-unlock:nth-child(3){animation-delay:.91s}.gr-unlock:nth-child(3) .gr-tick{animation-delay:.99s}
.gr-unlock:nth-child(4){animation-delay:1.09s}.gr-unlock:nth-child(4) .gr-tick{animation-delay:1.17s}
@keyframes gr-plan-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes gr-rise-in{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
@keyframes gr-tick-pop{from{opacity:0;transform:scale(0)}to{opacity:1;transform:scale(1)}}
@keyframes gr-rise-in-slow{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
[data-testid="stElementContainer"]:has(.gr-downgrade-mark.anim)
  + [data-testid="stElementContainer"] button{
  opacity:0;animation:gr-rise-in-slow .7s ease-out 1.6s forwards}
@media (prefers-reduced-motion:reduce){
  .gr-plan-anim,.gr-unlock,.gr-tick{animation:none!important;opacity:1!important;transform:none!important}
  [data-testid="stElementContainer"]:has(.gr-downgrade-mark.anim)
    + [data-testid="stElementContainer"] button{animation:none!important;opacity:1!important}
}

/* Quick-jump row on Profile — the page grew to seven sections (details,
   resume, alerts, forwarding, plan, sign-in link, feedback) and finding
   "where's the plan card" meant scrolling past all of it. Same tinted-pill
   look as .gr-pill, real anchor links so a click is a plain browser scroll
   with no rerun. scroll-margin-top clears the sticky 64px top bar so a
   jumped-to heading doesn't land tucked underneath it. */
.gr-jump-row{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 22px}
a.gr-jump{font-size:12.5px;font-weight:500;padding:5px 13px;border-radius:999px;
  background:#1e222a;color:#aab2bd;border:0;text-decoration:none!important;
  transition:background .15s ease,color .15s ease,transform .12s ease}
a.gr-jump:hover{background:rgba(232,147,58,.14);color:#eaa662}
/* The click itself needed its own punch — a plain browser #anchor jump gives
   no feedback that anything happened before the page moves. :active covers
   mouse/touch, :focus-visible covers keyboard, both louder than hover alone
   since this is the only signal a click landed. */
a.gr-jump:active,a.gr-jump:focus-visible{background:rgba(232,147,58,.28);
  color:#f7b569;transform:scale(.94);outline:none}
.gr-jump-target{scroll-margin-top:76px;display:block}
/* Real scroll instead of an instant jump — the anchor is a plain browser
   navigation (no Streamlit rerun involved), so this is the whole fix. */
html{scroll-behavior:smooth}
/* Outside the media block on purpose: this was accidentally inserted INSIDE
   prefers-reduced-motion when it was added, so the settings link only styled
   for people who ask for reduced animation. Found by Remy dry-running the CSS
   extractor; the bug was in this source, not the extractor. */
.gr-settings-link{display:inline-block;padding:9px 16px;border-radius:10px;
  font-size:13.5px;margin-top:2px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}
  a.gr-jump{transition:none}
  a.gr-jump:active,a.gr-jump:focus-visible{transform:none}}

/* "Switch to Free" — a bordered stButton reads as the loudest thing on the
   card, which is wrong right after someone just paid; it's the exit, not a
   second call to action. Restyled down to quiet link text, same marker+:has
   technique as .gr-cta-mark elsewhere. */
[data-testid="stElementContainer"]:has(.gr-downgrade-mark)
  + [data-testid="stElementContainer"] button{
  background:transparent!important;border:none!important;box-shadow:none!important;
  color:var(--mute)!important;font-weight:400!important;font-size:13.5px!important;
  text-decoration:underline!important;text-underline-offset:2px!important;
  padding:2px 0!important;min-height:0!important}
[data-testid="stElementContainer"]:has(.gr-downgrade-mark)
  + [data-testid="stElementContainer"] button:hover{color:var(--amber)!important}
[data-testid="stElementContainer"]:has(.gr-downgrade-mark)
  + [data-testid="stElementContainer"]{display:flex;justify-content:center;margin-top:4px}

/* Signed-in confirmation. Was a stock st.success — Streamlit's own bright
   green, the one colour on the page that answers to nothing in FEEL.md §2,
   and the same reason the plan card above stopped being one. Quiet card,
   house palette, with a green dot carrying the "it worked" signal instead
   of a full green slab. */
.gr-confirm{display:flex;align-items:center;gap:11px;background:var(--bg2);
  border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.gr-confirm-dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto;
  background:#54B95A;box-shadow:0 0 0 3px rgba(84,185,90,.16)}
.gr-confirm-txt{font-size:14.5px;color:var(--ink2);line-height:1.45}
.gr-confirm-txt b{color:var(--ink);font-weight:650}
.gr-plan-top{display:flex;justify-content:space-between;align-items:flex-start;
  gap:16px;flex-wrap:wrap}
.gr-plan-name{font-size:17px;font-weight:650;color:var(--ink);letter-spacing:-.2px}
.gr-plan-note{font-size:13.5px;color:var(--mute);margin-top:3px;line-height:1.5}
.gr-plan-price{text-align:right;font-size:14.5px;font-weight:600;color:var(--amber);
  white-space:nowrap}
.gr-plan-price span{display:block;font-size:12px;font-weight:500;
  color:var(--faint);margin-top:3px}
@media (max-width:640px){
  .gr-plan-price{text-align:left;white-space:normal}}

/* ── 4. Fewer borders ───────────────────────────────────────────────────────
   "Draft my reply" was a bordered box inside a bordered card — a frame around a
   frame on every single row. Streamlit hangs that border on the inner <details>,
   not on [data-testid="stExpander"], which is why the existing border-color rule
   above it never did anything. It becomes a quiet row on a background shift. */
[data-testid="stExpander"] details{
  border:0!important;border-radius:10px!important;background:#191d23!important}
[data-testid="stExpander"] details summary:hover{background:#1e232a!important}
[data-testid="stExpander"] details summary p{color:var(--mute)!important}
/* The one place a real edge still earns its keep: an OPEN expander, where the
   draft needs to be visibly its own surface. */
[data-testid="stExpander"] details[open]{
  background:#171b21!important;box-shadow:inset 0 0 0 1px var(--line)}

/* ── The same system at 375px ───────────────────────────────────────────────
   Proportional, not a copy: the card breathes less because the screen is
   narrower, and the section gap shrinks because a phone scroll is cheap while
   a phone screen is not. */
@media (max-width:640px){
  :root{--s-section:1.5rem}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title){
    padding:13px 14px 11px!important;border-radius:12px!important}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title)
    > [data-testid="stElementContainer"] > [data-testid="stMarkdown"] p{font-size:14.5px}
  /* Refresh is styled quiet with min-height:0, which left it at 41.6px — under
     the 44px thumb target. Quiet is about colour and weight, not hit area. */
  .st-key-checknew button{min-height:44px!important}
}
</style>
""", unsafe_allow_html=True)

db.init_db()
accounts.init()

# --- Who is looking at this screen? -----------------------------------------
# This has to run before anything reads a profile, because which profile to
# read depends on the answer. Signed-in people are identified by a token in
# the URL; everyone else gets a scratch space unique to their browser session,
# so two strangers browsing at once never see each other's data.
# Key for the campaign-hint fingerprint below. Defined here, not inside the
# function, because _resolve_account() runs near the top of the script and SID
# does not exist yet at that point. Falls back to a per-process random value
# when AUTH_COOKIE_SECRET is unset: hints then stop matching across a restart,
# which is the right failure — a lost hint costs a longer grant, while a
# guessable key would let anyone claim one.
_FP_KEY = (os.environ.get("AUTH_COOKIE_SECRET", "").strip()
           or secrets.token_urlsafe(32)).encode()


def _client_fingerprint() -> str:
    """
    A short-lived, non-identifying handle for "this browser, right now".

    Exists only to carry a partner tag across a sign-in with Google, which
    destroys both st.session_state and the query string — see
    accounts.remember_campaign for the full story.

    HMAC of the client IP and user agent, never the raw values, so nothing
    stored can be read back as an address. Keyed on the app's own cookie
    secret when there is one; without it the key is per-process, which means
    hints stop matching after a restart. That is the correct failure: a lost
    hint costs a longer grant, and a guessable key would let anyone claim one.
    """
    try:
        h = st.context.headers or {}
    except Exception:
        return ""
    # Render terminates TLS and proxies, so the socket peer is the proxy.
    # Trust the first hop only; the rest of the chain is client-supplied.
    ip = (h.get("X-Forwarded-For", "") or "").split(",")[0].strip()
    ua = h.get("User-Agent", "") or ""
    if not ip and not ua:
        return ""
    return hmac.new(_FP_KEY, f"{ip}|{ua}".encode(),
                    hashlib.sha256).hexdigest()[:32]


def _resolve_account():
    # This is the FIRST thing that touches the database on every single render,
    # so an unhandled error here doesn't degrade one component — it replaces the
    # whole page with a traceback before anything has drawn. Both lookups below
    # can now raise StoreUnavailable (a busy/locked database, as opposed to "no
    # such account"), and both are caught: the visitor renders as a guest for
    # this one run and the NEXT rerun tries again. Crucially the token is left
    # in place when that happens — see the pop() below for why that matters.
    try:
        # Google first: it hands us an address it has already verified, so it
        # beats a link that anyone could forward and an email box nobody checked.
        gmail = auth.google_email(st)
        if gmail:
            # CAMPAIGN MUST BE PASSED HERE. This path had no campaign argument
            # at all, so it defaulted to "" and PARTNER_GRANTS never matched —
            # meaning a NextNW member who arrived on ?ref=nextnw and then chose
            # "Continue with Google" was created on FREE, with no 90-day Pro,
            # silently contradicting the offer the landing page just made them.
            # Google sign-in is live in production, so this was the likeliest
            # single way for the launch to go wrong.
            #
            # Read from session_state first (set during session init) and fall
            # back to the live query param, because THIS function runs before
            # that init block on a first load — the module-level CAMPAIGN
            # constant is defined further down the file and simply does not
            # exist yet at this point.
            _camp = st.session_state.get("_campaign", "")
            if not _camp:
                _camp = analytics.campaign_label(
                    st.query_params.get("ref", "")
                    or st.query_params.get("utm_source", ""))
            if not _camp:
                # BOTH of the above are empty on a Google sign-in, always.
                # session_state does not survive the navigation, and
                # Streamlit's callback ends at the app root with no query
                # string, so ?ref= is gone as well. Without this every NextNW
                # member arriving through Google got the founding-50 gift (60
                # days, and a slot) instead of their partner grant (90 days,
                # no slot). See accounts.remember_campaign.
                _camp = accounts.recall_campaign(_client_fingerprint())
            acc, _ = accounts.sign_in(gmail, source="google", campaign=_camp)
            if acc:
                return acc

        tok = st.query_params.get("u") or st.session_state.get("_tok") or ""
        if tok:
            acc = accounts.by_token(tok)
            if acc:
                st.session_state["_tok"] = tok
                return acc
            # Reached ONLY on a genuine miss, never on a database error. The
            # difference matters: this line signs someone out permanently, and
            # a moment of lock contention must never be what triggers it.
            st.session_state.pop("_tok", None)   # stale or forged token

        # Coming back from somewhere we deliberately did NOT hand the real
        # sign-in token to — Stripe Checkout is the only one today. ?e= is the
        # HMAC-derived email token, which identifies the account without being
        # a credential, so we resolve it here and restore the real session
        # server-side. Without this the redirect back from a successful
        # payment would land the payer on an anonymous page.
        etok = st.query_params.get("e") or ""
        if etok:
            acc = accounts.by_email_token(etok)
            if acc:
                st.session_state["_tok"] = acc["token"]
                return acc
    except accounts.StoreUnavailable:
        pass
    return None


# The account menu is raw HTML, so its "Sign out" can't call Python directly.
# It links back as ?signout=1 and we handle it here, before the account is
# resolved, so the cleared token actually takes effect on this run.
if st.query_params.get("signout"):
    _was_google = bool(auth.google_email(st))
    # Where to land afterwards. The board sends ?back= because its own cookie
    # clear is only half a sign-out — st.logout() below is the half that ends
    # the Google session, and only this app can call it. Carried in
    # session_state because st.logout() returns to the app root with no query
    # string. If it is lost, the sign-out still stands; only the ride home
    # goes missing.
    _sb = (st.query_params.get("back") or "").strip()
    if _sb.startswith("https://") or _sb.startswith("http://"):
        st.session_state["_signout_back"] = _sb
    st.session_state.pop("_tok", None)
    # Same reasoning as sign-in: cached-against-the-old-identity data has to go
    # with the identity. Without this the nav still shows "Saved 7" to whoever
    # sits down next on a shared machine.
    st.session_state.pop("_saved_set", None)
    st.session_state.pop("_rated", None)
    st.query_params.clear()
    if _was_google:
        st.logout()          # reruns on its own
    st.rerun()

# The ride home from a cross-surface sign-out. Runs BEFORE account resolution
# so a lingering Google session cannot sign the person back in on the very
# render that is supposed to be sending them away signed out.
if st.session_state.get("_signout_back") and not auth.google_email(st):
    _home = st.session_state.pop("_signout_back")
    st.markdown(
        f'<meta http-equiv="refresh" content="0; '
        f'url={html.escape(_home, quote=True)}">', unsafe_allow_html=True)
    st.caption("Signed out.")
    st.stop()

ACCOUNT = _resolve_account()
if ACCOUNT:
    paths.set_scope(paths.scope_for(ACCOUNT["email"]))
else:
    # Not signed in: a scratch space unique to this browser session, so two
    # people browsing at once still never see each other's data.
    if "_visitor" not in st.session_state:
        st.session_state["_visitor"] = "free-" + secrets.token_hex(8)
    paths.set_scope(st.session_state["_visitor"])

ACCESS = accounts.status(ACCOUNT)
PRO = ACCESS["pro"]

# The token for whoever is signed in by email, or "" — see ilink() below.
TOKEN = (ACCOUNT or {}).get("token", "") if ACCOUNT else ""
# The same person, identified by a value that is NOT a credential (HMAC of the
# sign-in token; see accounts.email_token). Used anywhere the identifier leaves
# our control and gets stored by someone else — Stripe's Checkout session
# objects being the case that matters: they're retained indefinitely and are
# readable from the Stripe dashboard, so the real sign-in token must never ride
# in a return URL. _resolve_account never accepts this value, so on its own it
# grants nothing.
EMAIL_TOKEN = accounts.email_token(TOKEN) if TOKEN else ""


def saved_ids() -> list:
    """
    This person's saved gig ids, newest first, read ONCE per session.

    Not a convenience: saved.has() goes through read_user_json(), which falls
    through to a Supabase round trip whenever the local file is missing — and
    for someone who has never saved anything, it is always missing. Calling it
    per card meant 25+ network round trips to draw one page of the board, and
    it never stopped, because the file that would end the fallback only exists
    once they save something. Measured at 26 calls for a single render.

    A list, not a set, because the Saved tab renders in the order things were
    saved — one cached source of truth for the stars, the tab count, and that
    page, instead of three reads that can disagree.

    The ?save= handler clears this, so a star still lights up immediately.
    """
    if "_saved_set" not in st.session_state:
        st.session_state["_saved_set"] = (
            saved.ids() if ACCESS["signed_in"] else [])
    return st.session_state["_saved_set"]




def my_ratings() -> dict:
    """{gig_id: 'up'|'down'} for this person, cached once per session — same
    reasoning as saved_ids()."""
    if "_rated" not in st.session_state:
        st.session_state["_rated"] = (
            match_feedback.my_ratings(ACCESS.get("email", ""))
            if ACCESS["signed_in"] else {})
    return st.session_state["_rated"]


def ilink(href: str) -> str:
    """
    An internal link that keeps a signed-in person signed in.

    Every <a href="?nav=..."> is a REAL browser navigation, not a Streamlit
    rerun, so each click starts a fresh session with empty session_state. That
    makes the query string the only thing that carries identity across a
    click — and a bare "?nav=gigs" replaces the whole query string, dropping
    the ?u= token that says who this is. The result was that anyone who
    signed up with an email was anonymous again the moment they clicked Gigs:
    signed in on the board, signed out one click later.

    Google sign-in never had this problem, which is why it went unnoticed —
    Streamlit's own auth is cookie-backed and survives navigation. Email
    sign-in has no cookie, so the token has to ride in the URL.

    Every internal link goes through here. Anything that doesn't will sign an
    email-signed-in person out when they click it.
    """
    if not TOKEN or "u=" in href:
        return href
    return f"{href}{'&' if '?' in href else '?'}u={TOKEN}"

prof = profile_mod.load()
ALL_SKILLS = list(config.JOB_TYPES.keys()) + ["Other / general"]

# Where the Gigs tab points. Empty = this app's own board page, which is what
# runs today. Set to https://board.nabbly.co on the dartly service to send
# Gigs to the fast board; clear it to come straight back.
BOARD_URL = os.environ.get("NABBLY_BOARD_URL", "").strip().rstrip("/")
FEED_CAP = 60
PAGE_SIZE = 25   # a couple of screens of scroll, not sixty cards in one column
# The dashboard showed five gigs and then stopped, which made a board of
# thousands feel thin — the point of the page is that there's always more.
DASH_FEED = 12
# How deep the cached "Picked for you" feed goes. 25 Load More clicks, which
# nobody reaches — and the Dashboard is a curated pick, not the full board;
# there's a link to that at the end of the list. Caching the whole matched
# board instead was costing tens of MB per signed-in person (see _dash_picks).
DASH_CACHE_ROWS = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------






def recent_count(data, hours=24):
    """How many gigs were actually posted within the last `hours` (real freshness)."""
    if data.empty:
        return 0
    return int(sum(is_recent(r, hours) for r in data["posted_at"]))




# Rows written before sources._body existed (including the bundled seed) have
# the machine hints glued straight onto the description. Trim the tell-tale
# tail: a run of capitalised skill tags, and a trailing budget/salary string.




# Job-board feeds open the description with the company's own metadata before a
# word of the actual role, which is pure noise in the card's most valuable spot
# (365 posts on the current board start this way). Two shapes:
#   "Headquarters: Brazil URL: http://x.com  <description>"   — clean to cut
#   "Headquarters: State College, PA  <description>"          — no delimiter








def _count_up_html(value: str, uid: str) -> str:
    """
    A real 0 -> N climb, matching the marketing site's hero counter — see
    .gr-count in the stylesheet for why this is a reel of real pre-computed
    numbers (the same ease-out curve the marketing page's JS ticks through
    live) rather than a live-animated CSS counter.

    `value` is the final, comma-formatted display text (e.g. "16,938");
    `uid` only needs to be unique among the stat cards sharing this page,
    so a slugified label is enough — it names this card's one-off
    @keyframes block.
    """
    n = int(re.sub(r"[^0-9]", "", value) or 0)
    if n <= 0:
        return html.escape(value)

    steps = 14
    frames = []
    for i in range(steps):
        t = i / (steps - 1)
        eased = 1 - (1 - t) ** 3  # fast start, gentle landing — same curve site/index.html uses
        frames.append(f"{round(n * eased):,}")
    frames[-1] = value  # land on the exact, correctly-formatted final text
    # Small n can round to the same value for several early steps in a row —
    # collapse those so the reel doesn't visibly "pause" repeating a frame.
    deduped = [frames[0]]
    for f in frames[1:]:
        if f != deduped[-1]:
            deduped.append(f)

    rows = "".join(f"<span>{html.escape(f)}</span>" for f in deduped)
    last = len(deduped) - 1
    kf = f"gr-cnt-{uid}"
    dur = "1.1s"
    return (
        f'<span class="gr-count">'
        f'<style>@keyframes {kf}{{from{{transform:translateY(0)}}'
        f'to{{transform:translateY(-{last}em)}}}}</style>'
        f'<span class="gr-count-reel" style="animation-name:{kf};'
        f'animation-duration:{dur};animation-timing-function:steps({last},end);'
        f'transform:translateY(-{last}em)">{rows}</span>'
        f'</span>'
    )


def founding_badge_html(rank: int | None) -> str:
    """
    A founding member's badge — their actual place in line, not a generic
    checkmark. The "#7" says something a stock icon can't: it's the one part
    of this badge that's unique to the person wearing it. The star is the
    one new shape here (the checkmark is already spoken for — it's the logo).

    ONE canonical spot for this: the account menu, since it's the only place
    that's visible on every page without a click. The plan card mentions
    "founding member" in plain text instead of repeating the badge — a
    second copy of the same graphic read as decoration, not signal.
    """
    if not rank:
        return ""
    return (
        f'<span class="gr-founding" title="One of the first {accounts.FOUNDING_LIMIT} '
        f'to sign up">'
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="#E8933A" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 2.5l2.9 6.4 7 .7-5.3 4.6 1.6 6.9-6.2-3.8-6.2 3.8 '
        '1.6-6.9-5.3-4.6 7-.7z"/></svg>'
        f'Founding member #{rank}</span>'
    )


def stat_cards(items):
    html = ('<div class="gr-stats" style="max-width:980px;margin-left:auto;'
            'margin-right:auto;justify-content:center">')
    for label, value, accent, *rest in items:
        cls = "n small" if "small" in rest else "n"
        href = next((x for x in rest if x and x != "small"), "")
        # Count-up is opt-in via "count" in rest — just the live-gigs total,
        # not every stat on the row. It's the one number that's genuinely
        # exciting to watch climb; Fresh/Urgent/Fields don't need the same
        # weight every single time someone lands on the page.
        if "count" in rest:
            uid = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            rendered = _count_up_html(value, uid)
        else:
            rendered = _flip_spans(value)
        inner = (f'<div class="accent" style="background:{accent}"></div>'
                 f'<div class="l">{label}</div>'
                 f'<div class="{cls}">{rendered}</div>')
        if href:
            html += (f'<a class="gr-stat" href="{ilink(href)}" target="_self">{inner}'
                     f'<div class="go">→</div></a>')
        else:
            html += f'<div class="gr-stat">{inner}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def pills(items):
    spans = "".join(f'<span class="gr-pill {v}">{t}</span>' for t, v in items)
    st.markdown(f'<div class="gr-pills">{spans}</div>', unsafe_allow_html=True)


def hbar_chart(rows, color: str, fmt=str, height: int | None = None):
    """
    A sorted horizontal bar list — Market's replacement for a two-line altair
    chart. `rows` is (label, value) pairs, already in the order to display;
    this doesn't sort them, because both callers want a specific order (one
    by count, one by rate) and re-deriving it here would be a second place
    that order lives. `fmt` renders the value shown beside the bar, e.g.
    `lambda v: f"${v:,}"` for a rate — the underlying number always drives
    the bar's width, so the visual and the label can't disagree.
    """
    if not rows:
        return
    top = max(v for _, v in rows) or 1
    items = "".join(
        f'<div class="gr-hbar">'
        f'<div class="gr-hbar-top"><span>{html.escape(str(lbl))}</span>'
        f'<span class="gr-hbar-n">{fmt(v)}</span></div>'
        f'<div class="gr-hbar-track">'
        f'<div class="gr-hbar-fill{" max" if v >= top else ""}" '
        f'style="width:{v/top*100:.1f}%;background:{color}" '
        f'title="{html.escape(str(lbl))}: {fmt(v)}"></div></div></div>'
        for lbl, v in rows)
    st.markdown(f'<div class="gr-hbars"{f" style=\"height:{height}px\"" if height else ""}>'
               f'{items}</div>', unsafe_allow_html=True)


def donut_chart(rows, colors: dict, fmt=lambda v: f"{v:,}"):
    """
    A three-ish-slice donut. `rows` is (label, value) pairs; `colors` maps
    each label to a hex. Built as a single conic-gradient circle rather than
    an SVG or a charting library — a plain CSS shape can't lose the browser
    the way importing a 51MB rendering library can.
    """
    total = sum(v for _, v in rows) or 1
    stops, pct = [], 0.0
    for lbl, v in rows:
        start, pct = pct, pct + v / total * 100
        stops.append(f"{colors.get(lbl, '#4C8DFF')} {start:.2f}% {pct:.2f}%")
    legend = "".join(
        f'<div class="row"><span class="sw" style="background:{colors.get(lbl,"#4C8DFF")}">'
        f'</span>{html.escape(str(lbl))}<b>{fmt(v)}</b></div>'
        for lbl, v in rows)
    st.markdown(
        f'<div class="gr-donut-wrap">'
        f'<div class="gr-donut" style="background:conic-gradient({", ".join(stops)})" '
        f'title="{"; ".join(f"{l}: {fmt(v)}" for l, v in rows)}">'
        f'<div class="gr-donut-hole"></div></div>'
        f'<div class="gr-donut-legend">{legend}</div></div>',
        unsafe_allow_html=True)


def stacked_hbar_chart(row_labels, seg_labels, values: dict, colors: dict):
    """
    A horizontal stacked bar per row_label, split across seg_labels.
    `values[(row, seg)]` gives that cell's count; missing keys are 0. The
    legend is drawn once above the rows rather than per-row, since every row
    shares the same segment set.
    """
    legend = "".join(
        f'<span class="row" style="display:inline-flex;margin-right:16px">'
        f'<span class="sw" style="background:{colors.get(s,"#888")}"></span>{s}</span>'
        for s in seg_labels)
    st.markdown(f'<div class="gr-donut-legend" style="flex-direction:row;'
               f'flex-wrap:wrap;margin-bottom:12px">{legend}</div>',
               unsafe_allow_html=True)

    rows_html = []
    for r in row_labels:
        cells = [(s, values.get((r, s), 0)) for s in seg_labels]
        row_total = sum(v for _, v in cells) or 1
        segs = "".join(
            f'<div class="seg" style="width:{v/row_total*100:.1f}%;'
            f'background:{colors.get(s,"#888")}" '
            f'title="{html.escape(str(s))}: {v:,}"></div>'
            for s, v in cells if v)
        rows_html.append(
            f'<div class="gr-stack-row">'
            f'<div class="gr-stack-lbl" title="{html.escape(str(r))}">{html.escape(str(r))}</div>'
            f'<div class="gr-stack-bar">{segs}</div></div>')
    st.markdown(f'<div class="gr-stack">{"".join(rows_html)}</div>',
               unsafe_allow_html=True)


def gig_pager(page: int, total_pages: int, key: str, show_top_link: bool = False):
    """
    Prev/next between chunks of the board, instead of one long scroll.

    Rendered twice around the same list: once above the first card (jump
    forward or back without scrolling up first) and once below the last (the
    moment you actually reach the bottom, keep going or bail back to the top —
    an ordinary anchor jump, not a rerun, so it's instant).
    """
    if total_pages <= 1:
        return
    c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="center")
    with c1:
        if st.button("‹ Prev", key=f"pg_{key}_prev", width="stretch",
                     disabled=(page <= 0)):
            st.session_state["gigspage"] = page - 1
            st.rerun()
    with c2:
        mid = f'<div class="gr-page-n">Page {page + 1} of {total_pages}</div>'
        if show_top_link:
            mid += ('<div class="gr-page-top">'
                    '<a href="#" class="gr-about-link">Back to top ↑</a></div>')
        st.markdown(mid, unsafe_allow_html=True)
    with c3:
        if st.button("Next ›", key=f"pg_{key}_next", width="stretch",
                     disabled=(page >= total_pages - 1)):
            st.session_state["gigspage"] = page + 1
            st.rerun()


def source_pill(src: str):
    """
    (text, css class) for a board's pill.

    Boards that are remote-only carry that fact in their name, so rather than
    adding a second "Remote" pill beside them we let the source pill say it:
    a globe and the same green the location pills use.
    """
    src = (src or "").lower()
    label = config.source_label(src)
    if src in config.REMOTE_ONLY_SOURCES:
        return label, "remote"      # the pill's own green tint says "remote"
    return label, ""


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------
def _build_feed(posts):
    """
    Rows -> a de-duplicated frame with the lowercased search columns.

    DELIBERATELY NOT CACHED. This was @st.cache_data(ttl=45, max_entries=64),
    which is the same shape as the bug that took the site down once already, one
    level further in:
      - cache_data HASHES its argument, and the argument was a list of ~13,000
        dicts, so every call walked the whole board just to build a cache key;
      - cache_data returns a COPY on every hit, so each call minted a fresh
        ~41MB frame even when nothing had changed;
      - max_entries=64 meant up to 64 board-sized frames could be resident.
    Caching belongs one level up, on the finished board, keyed by whether the
    board actually changed — see _public_feed().
    """
    if posts is None or len(posts) == 0:
        return pd.DataFrame(), 0
    df = posts.copy() if isinstance(posts, pd.DataFrame) else pd.DataFrame(posts)

    def _key(title):
        toks = [w for w in re.findall(r"[a-z0-9]+", str(title).lower()) if len(w) > 2]
        return " ".join(sorted(set(toks)))

    df["_key"] = df["title"].map(_key)
    before = len(df)
    # A TITLE THAT ISN'T LATIN HAS NO KEY, AND HAVING NO KEY IS NOT A REASON
    # TO BE THROWN OFF THE BOARD. _key() collects [a-z0-9] runs, so a posting
    # written in Arabic, Hindi, Chinese, Ukrainian, Japanese or Russian yields
    # nothing at all and lands on "". Dropping empty keys therefore deleted
    # those gigs outright rather than de-duplicating them — measured
    # 2026-08-16, 79 live postings, mostly Freelancer and Himalayas.
    #
    # They each get a unique key instead: kept, and unable to collapse into one
    # giant "" group where 78 of them would lose a coin toss to the 79th. The
    # board service has always done it this way (see sync.mark_primaries),
    # which is part of why the two surfaces disagreed.
    #
    # Whether a given reader SEES them is apply_language's decision, which is
    # the layer that actually knows what they read. Someone who set their
    # country to Ukraine should get the Ukrainian listings; nobody should have
    # them silently deleted upstream of that choice.
    blank = df["_key"] == ""
    if blank.any():
        df.loc[blank, "_key"] = [f"\x00{i}" for i in range(int(blank.sum()))]
    df = df.drop_duplicates(subset="_key", keep="first")
    # Lowercased text, computed once here rather than on every keystroke in
    # apply_filters, which used to re-lower ~9,000 titles and bodies per
    # character typed.
    df["_t"] = df["title"].fillna("").str.lower()
    df["_b"] = df["body"].fillna("").str.lower()
    # Which metro a gig is pinned to, if any. Computed once here because it's a
    # property of the POST, not of the reader — doing it per-render would mean
    # regexing 14,000 titles on every rerun for an answer that never changes.
    df["_city"] = [location.city_lock({"title": t}) for t in df["title"].fillna("")]
    # Same reasoning as _city: a gig's language is a property of the POST, so
    # it's computed once here rather than per render.
    df["_lang"] = [lang.detect(t, b) for t, b in
                   zip(df["title"].fillna(""), df["body"].fillna(""))]
    # Whether a gig is remote, on-site, or region-restricted is ALSO a property
    # of the post — location.tag() only ever reads the gig's own title and body.
    # It used to be called per row, per render, by both location_counts() and
    # apply_location(): 53,000 f-string concatenations of title+body and a
    # dozen regex passes over each, on every board load, for every visitor.
    # That was the second-largest per-request cost in the app after
    # skill_stats, and the reason 25 concurrent readers still peaked past 3GB
    # once skill_stats was fixed. Computed once here, it costs one pass per
    # board rebuild and turns both callers into vectorised boolean masks.
    _tags = [location.tag({"title": t, "body": b}) for t, b in
             zip(df["title"].fillna(""), df["body"].fillna(""))]
    df["_rem"] = [t["remote"] for t in _tags]
    df["_ons"] = [t["onsite"] for t in _tags]
    # "" rather than None: the eligibility test below compares this column
    # against a region code, and NaN would make every comparison false.
    df["_res"] = [t["restrict"] or "" for t in _tags]
    return df, before - len(df)


# Keyed on the board's fingerprint, not on a clock. A timer rebuilds the whole
# 41MB frame every N seconds whether or not a single gig arrived; ingest usually
# adds nothing, so nearly all of that work was churn. max_entries=1 is the point:
# the previous frame is evicted as the new one lands, so two can't be resident.
# The ttl is only a backstop for edits that don't move the fingerprint (the
# one-off reclassify at boot).
@st.cache_resource(max_entries=1, ttl=900, show_spinner=False)
def _public_feed_at(version):
    return _build_feed(db.posts_frame(demand_only=True, owner=None))


def _public_feed():
    """
    The public board, built ONCE and shared by every visitor.

    THIS CAUSED AN OUTAGE: it was previously cached per storage scope with
    max_entries=64. Every anonymous visitor gets a unique scratch scope, so each
    new browser session allocated its own ~29MB copy of the identical public
    board — up to 1.9GB against a 512MB instance, which tripped Render's memory
    limit and forced restarts. The public board is the same for everyone, so it
    is cached once, under one key.

    cache_resource rather than cache_data because it returns THE SAME object
    instead of a fresh copy per call, which is the other half of the saving.
    Safe because nothing mutates it: apply_filters and rank_by_relevance return
    new frames, and scored() copies before it writes.

    The board's fingerprint is the cache key, so this rebuilds when gigs
    actually arrive rather than every N seconds. board_version() is two integers
    off an index — cheap enough to ask on every rerun.
    """
    return _public_feed_at(db.board_version())


def _sort_key(df):
    """Newest first, matching the SQL COALESCE(posted_at, fetched_at)."""
    return df["posted_at"].fillna("").where(
        df["posted_at"].fillna("") != "", df.get("fetched_at", ""))


def load_feed():
    """
    The public board, plus anything this viewer forwarded to their own Nabbly
    address. Never anyone else's forwards.

    The common case returns the shared frame untouched — no copy, no extra
    memory. Only someone who has actually forwarded gigs pays for a merged
    frame, and they have a handful of rows, not thousands.
    """
    df, dropped = _public_feed()
    scope = paths.get_scope()
    # Anonymous scratch scopes can never own rows, so skip the query entirely.
    if not scope or scope.startswith(("free-", "guest-", "_")):
        return df, dropped
    owned = db.owned_posts(scope)
    if not owned:
        return df, dropped
    odf, _ = _build_feed(owned)
    merged = pd.concat([odf, df], ignore_index=True)
    return merged.assign(_s=_sort_key(merged)).sort_values(
        "_s", ascending=False, kind="stable").drop(columns="_s"), dropped


db.ensure_seeded()      # first run on a fresh deploy loads the bundled seed.db
# NOTE: rehydrate_board() used to run HERE, synchronously, before the first
# paint. On a cold start that meant pulling thousands of gigs from Supabase over
# the network while the visitor stared at a blank page. It now runs inside the
# background thread: the board renders immediately from the seed and fills in a
# moment later. Never put network work on the first-render path.
refresh.start(on_update=_public_feed)  # background fetcher: grows the feed while
                                        # the app is in use, and rebuilds the
                                        # cached board itself after each cycle
                                        # that adds gigs — see refresh._loop's
                                        # on_update comment for why
analytics.init()    # visit counting, in its own database file
people.init()       # who signed up, their profile, and their feedback
outcomes.init()     # gigs someone actually landed through the board
match_feedback.init()  # was the match score actually right

# Own-account visits never hit the counters. Checking on the product is the
# single most frequent kind of visit an owner account makes, and none of it
# is a real visitor — left in, every number on the Admin page is partly a
# measure of how often the founder opens their own site. Can only catch this
# while signed in as owner, so a signed-out check from the same person still
# counts; there's no way to tell those apart from a stranger's.
_OWNER_VISIT = ACCESS["signed_in"] and accounts.is_owner(ACCESS.get("email"))

# One id per browser tab. Streamlit reruns this script constantly, so without
# this every scroll and click would look like a brand-new visitor.
if "_sid" not in st.session_state:
    st.session_state["_sid"] = uuid.uuid4().hex[:12]
    _sid = st.session_state["_sid"]
    if not _OWNER_VISIT:
        analytics.track("session", "", _sid)
        # Where did they come from, and on what? Read once, from the request
        # that opened the session. We keep only the referring host and a
        # coarse device bucket — never the full URL, never anything
        # identifying.
        try:
            _h = st.context.headers or {}
            analytics.track("ref", analytics.referrer_label(_h.get("Referer", "")), _sid)
            analytics.track("device", analytics.device_label(_h.get("User-Agent", "")), _sid)
        except Exception:
            pass          # header access must never break a page load
        # A partner's own tag: ?ref=name (or utm_source=, which is what most
        # newsletter tools emit by default). Captured HERE, at session start,
        # because the nav dispatch calls st.query_params.clear() further down
        # — read it any later and it's already gone. Held in session state so
        # it survives to whenever they actually sign up, which is the only
        # moment that answers whether the collaboration worked.
        try:
            _tag = analytics.campaign_label(
                st.query_params.get("ref", "") or st.query_params.get("utm_source", ""))
            if _tag:
                st.session_state["_campaign"] = _tag
                analytics.track("campaign", _tag, _sid)
                # session_state alone is not enough: signing in with Google
                # navigates away and comes back to a bare app root, losing
                # both this and the ?ref= that set it. Park it server-side so
                # the grant still knows where they came from.
                accounts.remember_campaign(_client_fingerprint(), _tag)
        except Exception:
            pass
SID = st.session_state["_sid"]
CAMPAIGN = st.session_state.get("_campaign", "")


def note(event: str, detail: str = ""):
    """Record something the visitor did (once per session per thing). A no-op
    for the owner's own visits — see _OWNER_VISIT above."""
    if _OWNER_VISIT:
        return
    seen = st.session_state.setdefault("_seen_events", set())
    key = f"{event}:{detail}"
    if key in seen:
        return
    seen.add(key)
    analytics.track(event, detail, SID)


df, merged = load_feed()

# Every field market.skill_stats() reads, including through score.gig_amount().
# ADD TO THIS if skill_stats starts reading another one — a missing field
# silently becomes an empty string rather than raising.
_STAT_FIELDS = ("job_type", "source", "title", "body")


def _lazy_records(frame, fields):
    """
    A frame's rows as dicts, LAZILY, over only the columns asked for.

    THE PATTERN THAT MADE THE APP FALL OVER: `frame.to_dict("records")` builds
    every dict up front, so a whole-board call materialises 53,525 dicts of all
    22 columns before the caller reads one — measured at ~192MB of transient
    allocation, per call, per visitor. Sequential visitors freed it between
    renders and looked healthy; concurrent visitors each held their own, which
    is what put a 2GB instance on the floor at five people.

    Every caller here walks its rows exactly once and reads a handful of
    fields, so none of them ever needed a list. This yields the same dicts one
    at a time and the peak never forms.

    Use it for anything board-sized. `to_dict("records")` is correct for a
    single rendered page (25 rows), and nowhere else.
    """
    cols = [c for c in fields if c in frame.columns]
    if not cols:
        return iter(())
    return (dict(zip(cols, row)) for row in zip(*(frame[c] for c in cols)))


@st.cache_resource(max_entries=1, ttl=900, show_spinner=False)
def _skill_stats_at(version):
    """
    Demand and typical-budget stats per skill, built ONCE and shared.

    THIS WAS THE APP'S BIGGEST PER-REQUEST COST. It ran at module level, so
    every script run — every visitor, every rerun, every keystroke that
    triggered one — rebuilt the whole board as Python dicts to produce numbers
    that are identical for everybody. One call allocated ~192MB transiently.
    Sequential visitors freed it between runs and looked fine; concurrent
    visitors each held their own, which is what put a 2GB instance on the floor
    at five people. Measured: the filter chain that looked like the obvious
    suspect costs ~3MB for a hundred concurrent requests. This was the whole
    problem.

    Keyed on the board's fingerprint (same one _public_feed_at uses) so it
    rebuilds when gigs actually arrive, and cache_resource rather than
    cache_data so every caller shares one dict instead of unpickling a copy.
    Nothing mutates the result: market.lowball() only ever reads it.

    Computed from the PUBLIC board rather than load_feed()'s per-reader frame.
    A reader's own forwarded gigs used to be folded into these medians, which
    made "typical budget for this skill" mean something slightly different for
    each person — and a market rate shouldn't move because of what you
    forwarded yourself.
    """
    pub, _ = _public_feed()
    if pub.empty:
        return {}
    return market.skill_stats(_lazy_records(pub, _STAT_FIELDS))


stats = _skill_stats_at(db.board_version())


def apply_filters(data, skills, sizes, sources, urgent_only, keyword):
    if data.empty:
        return data
    mask = (data["job_type"].isin(skills) & data["size_tier"].isin(sizes)
            & data["source"].isin(sources))
    if urgent_only:
        mask &= data["urgency"] == "Urgent"
    t_l, b_l = _search_cols(data)
    if keyword:
        # EVERY word has to appear, in the title or the body, in any order.
        # This used to be one substring match on the whole phrase, so "figma
        # designer" found nothing unless those two words sat adjacent in that
        # exact order — which is why searching more than one word felt broken.
        for term in str(keyword).lower().split():
            esc = re.escape(term)
            mask &= (t_l.str.contains(esc, na=False, regex=True)
                     | b_l.str.contains(esc, na=False, regex=True))
    mutes = [m.strip().lower() for m in (prof.get("mute", "") or "").split(",") if m.strip()]
    if mutes:
        for m in mutes:
            esc = re.escape(m)
            mask &= ~(t_l.str.contains(esc, na=False, regex=True)
                      | b_l.str.contains(esc, na=False, regex=True))
    return data[mask]


def _search_cols(data):
    """
    The lowercased title/body columns, built by the feed cache. Falls back to
    computing them for any frame that didn't come through load_feed (the admin
    page builds its own), so callers never have to care.
    """
    t_l = data["_t"] if "_t" in data else data["title"].fillna("").str.lower()
    b_l = data["_b"] if "_b" in data else data["body"].fillna("").str.lower()
    return t_l, b_l


def rank_by_relevance(data, keyword: str):
    """
    Put the best matches first when someone searches.

    Results were returned newest-first, so a gig whose TITLE is exactly what you
    typed could sit below a hundred gigs that merely mention the word somewhere
    in the body. Scores title hits above body hits, whole words above fragments,
    and keeps recency as the tie-breaker (the frame arrives newest-first).
    """
    terms = [t for t in str(keyword or "").lower().split() if t]
    if not terms or data.empty:
        return data
    t_l, b_l = _search_cols(data)
    score = pd.Series(0, index=data.index, dtype="int32")
    for term in terms:
        esc = re.escape(term)
        word = r"(?<!\w)" + esc + r"(?!\w)"
        score += t_l.str.contains(word, na=False, regex=True).astype("int32") * 6
        score += t_l.str.contains(esc, na=False, regex=True).astype("int32") * 3
        score += b_l.str.contains(word, na=False, regex=True).astype("int32") * 2
    # A title that starts with the query is almost always the thing you meant.
    score += t_l.str.startswith(" ".join(terms)).astype("int32") * 5
    return data.assign(_score=score).sort_values(
        "_score", ascending=False, kind="stable").drop(columns="_score")


def location_counts(data):
    """(all, remote-I-can-take, on-site/local) counts for the location toggle."""
    if data.empty:
        return 0, 0, 0
    region = location.country_region(prof.get("country"))
    city = prof.get("city")
    if "_rem" not in data.columns:      # a frame that didn't come through _build_feed
        remote = local = 0
        for r in _lazy_records(data, ("title", "body")):
            t = location.tag(r)
            if t["remote"] and location.eligible(t, region):
                remote += 1
            if t["onsite"] or location.is_local(r, city):
                local += 1
        return len(data), remote, local
    rem, loc = _location_masks(data, region, city)
    return len(data), int(rem.sum()), int(loc.sum())


def _location_masks(data, region, city):
    """
    (remote-I-can-take, on-site/local) as boolean masks over a tagged frame.

    The vectorised twin of location.eligible() and location.is_local(), reading
    the _rem/_ons/_res columns _build_feed computed once for the whole board.
    Kept in one place because location_counts() and apply_location() have to
    agree exactly: the counts on the toggle are a promise about what the toggle
    gives you, and they were previously computed by two separate loops.
    """
    # eligible(): a gig with no restriction is open to everyone, and an unknown
    # reader region assumes yes — so only a KNOWN region excludes anything.
    rem = data["_rem"].fillna(False).astype(bool)
    if region:
        rem = rem & data["_res"].fillna("").isin(["", region])
    loc = data["_ons"].fillna(False).astype(bool)
    city = (city or "").strip().lower()
    if city:
        # is_local(): the reader's city named anywhere in the post. _t/_b are
        # already lower-cased by _build_feed, matching is_local's own .lower().
        esc = re.escape(city)
        loc = loc | (data["_t"].str.contains(esc, na=False)
                     | data["_b"].str.contains(esc, na=False))
    return rem, loc


def reading_languages():
    """
    Which languages this person's board should include.

    English always, plus whatever their country implies — someone in Germany
    keeps their German gigs without having to find a setting for it.
    """
    codes = {"en"}
    implied = lang.COUNTRY_LANG.get((prof.get("country") or "").strip())
    if implied:
        codes.add(implied)
    return codes


def apply_language(view):
    """
    Hide gigs written in a language this reader hasn't got.

    Nine percent of the board arrives in German, Dutch, Spanish or French
    because several feeds are European. That's real work for someone who reads
    those and unreadable clutter for everyone else. Off by default rather than
    on, and the detector falls back to English when unsure — a miss leaves a
    gig visible, which costs nothing, while a false positive would hide real
    work, which costs someone a job.
    """
    if view.empty or "_lang" not in view.columns:
        return view
    if prof.get("show_all_languages"):
        return view
    return view[view["_lang"].isin(reading_languages())]


def apply_city_lock(view):
    """
    Drop gigs pinned to a metro that isn't yours.

    A title like "… Senior Product Designer in New York City, NY" is work for
    someone in that metro; showing it to everyone fills the board with jobs
    most readers can't take. Off-limits gigs come back if you say you'd
    relocate (Profile), or if the post names your own city.
    """
    if view.empty or "_city" not in view.columns:
        return view
    if prof.get("open_to_relocate"):
        return view
    city = (prof.get("city") or "").strip().lower()
    locked = view["_city"].fillna("") != ""
    if not city:
        return view[~locked]
    # Their city named anywhere in the post keeps it, so "New York" still
    # matches "New York City".
    mine = view["_t"].str.contains(re.escape(city), na=False) | \
        view["_b"].str.contains(re.escape(city), na=False)
    return view[~locked | mine]


def apply_location(view, mode):
    """Filter the feed by where the work can be done, using the profile's country/city."""
    if view.empty or mode == "Everywhere":
        return view
    region = location.country_region(prof.get("country"))
    city = prof.get("city")
    if "_rem" not in view.columns:      # frame not built by _build_feed
        keep = []
        for r in _lazy_records(view, ("id", "title", "body")):
            t = location.tag(r)
            if (t["onsite"] or location.is_local(r, city)) if mode.startswith("On-site") \
               else (t["remote"] and location.eligible(t, region)):
                keep.append(r["id"])
        return view[view["id"].isin(keep)]
    # Same masks the toggle's own counts are built from, so the number on the
    # chip and the number of cards below it cannot drift apart. This used to
    # build a dict of all 22 columns for every row and call location.tag()
    # TWICE per gig on the remote branch.
    rem, loc = _location_masks(view, region, city)
    return view[loc if mode.startswith("On-site") else rem]


def scored(view, resume_text=""):
    """
    Fit scores, but ONLY when there is something to fit against.

    fit_score() gives every gig a flat +30 when the profile has no skills
    (score.py), so an empty profile produced the identical percentage on all
    sixty cards — "63% match" over and over, presented as personalisation for
    someone the app knows nothing about. A number that never varies isn't a
    match, and showing it teaches people the number means nothing. With no
    skills we return the view unscored, so no pill is drawn and the board
    keeps its newest-first order, which is the honest default.

    resume_text is an explicit param, never read from session_state in here,
    because this function also runs inside _dash_picks — an @st.cache_data
    function shared across every signed-in user with the same skills/sources.
    Reading session_state directly would bake whichever person's resume
    happened to populate that cache key into everyone else's Dashboard feed.
    Callers outside a cache (the Gigs page, draft_showcase) pass it through;
    _dash_picks deliberately doesn't, so the Dashboard's "Picked for you"
    just doesn't get the resume nudge — the same tradeoff apply_bias() makes
    for rating history, for the same reason.
    """
    if view.empty or not (prof.get("skills") or []):
        return view
    # Narrowed to the fields fit_score actually reads (score.FIT_FIELDS). The
    # board frame carries 18 columns and this used to build a dict of all of
    # them for every gig being ranked — 13,000 gigs for someone matching five
    # popular fields, on every cache miss, and the board's version changes
    # whenever new gigs land. Same scores, verified identical, ~19% quicker.
    sc = [score.fit_score(r, prof, resume_text=resume_text)
          for r in _lazy_records(view, score.FIT_FIELDS)]
    view = view.copy()
    view["_score"] = [s for s, _ in sc]
    view["_reasons"] = [r for _, r in sc]
    return view.sort_values("_score", ascending=False)


def apply_bias(view):
    """
    Nudge a scored() view by this person's OWN thumbs-up/down history.

    Deliberately separate from scored() rather than folded into it: scored()
    runs inside _dash_picks, which is @st.cache_data'd and SHARED across every
    signed-in user with the same skills/sources. Baking one person's bias into
    that result would leak into everyone else's cached feed. This runs after
    the cache, every render, on whichever view scored() already produced —
    cheap (a handful of category totals), and it's what makes "ranked by how
    well they fit you, and it keeps learning from what you rate" true
    everywhere that claim appears, not just on the Dashboard.
    """
    if not ACCESS["signed_in"] or view.empty or "_score" not in view.columns:
        return view
    _bias = match_feedback.my_category_bias(ACCESS["email"])
    if not _bias:
        return view
    view = view.copy()
    view["_score"] = [
        max(0, min(100, s + _bias.get(jt, 0)))
        for s, jt in zip(view["_score"], view["job_type"])
    ]
    return view.sort_values("_score", ascending=False)


def _prof_cache_key():
    """
    Every profile field that changes what _dash_picks returns.

    This exists because _dash_picks is @st.cache_data, and a cache_data cache
    is shared by EVERY visitor in the process — so anything the cached body
    reads that isn't in the key is served across users. The body reads this
    person's profile through five different helpers (mute in apply_filters,
    city/relocate in apply_city_lock, country/show_all in apply_language,
    keywords/rate_floor in scored), so all of it has to ride in the key.

    Fingerprinted rather than passed as one dict because cache keys must be
    hashable, and because listing the fields makes it obvious what has to be
    added here when a new profile field starts affecting the feed.
    """
    return (
        (prof.get("keywords") or ""),
        str(prof.get("rate_floor") or ""),
        (prof.get("mute") or ""),
        (prof.get("city") or ""),
        (prof.get("country") or ""),
        bool(prof.get("open_to_relocate")),
        bool(prof.get("show_all_languages")),
    )


@st.cache_data(ttl=180, show_spinner=False, max_entries=24)
def _dash_picks(version, scope, prof_key, skills, srcs):
    """
    The dashboard's "Picked for you" feed, cached. scored() alone measured
    ~90ms against a few thousand matched gigs — cheap once, but the
    dashboard was recomputing filter + scored from scratch on EVERY rerun,
    including every "Load more" click, even though neither the board nor
    the profile had actually changed since the last one. That's what made
    each successive load feel slower than the last, not the rendering.

    `scope` and `prof_key` ARE NOT USED IN THE BODY AND MUST NOT BE REMOVED.
    They exist purely to make the cache key identify a person. Without them
    this function was keyed on (version, skills, srcs) alone while its body
    read the current visitor's scope and profile — so two people who happened
    to share a skill set were served each other's frames: one person's
    privately forwarded gigs (load_feed pulls db.owned_posts for the current
    scope) and their profile keywords, which render as the visible "why"
    chips on every card. Anything this body reads that isn't an argument has
    to be added to _prof_cache_key().

    max_entries bounds the COUNT, and DASH_CACHE_ROWS bounds the SIZE. The
    count alone was not enough. This is keyed per person, so 24 entries means
    24 different people, and each one used to hold their whole filtered board:
    ~26MB for someone who picks five popular fields, 51MB for someone who
    picks all of them. Two dozen people on at once was 0.6-1.2GB of cache on
    top of a ~400MB baseline, to render twelve cards. That is the same shape
    of mistake that twice took the instance over its memory ceiling (see
    _public_feed), just wearing a bound that looked responsible.

    Returns (rows, total). The rows are capped; the total is the honest count
    of everything that matched, so the end of the list can tell the difference
    between "you have seen everything" and "you have seen the first 300".

    Keyed off the board's own version fingerprint (same one _public_feed_at
    uses), so it invalidates the moment real data changes rather than
    sitting stale on a timer. Loads the feed itself instead of taking `df`
    as an argument — load_feed() is already cheap (it just hits
    _public_feed's own cache) and a DataFrame is an expensive thing to hash
    as a cache key.
    """
    cur, _ = load_feed()
    cur = apply_language(apply_city_lock(
        apply_filters(cur, list(skills), ["Small", "Medium", "Large"],
                      list(srcs), False, "")))
    out = scored(cur)
    return out.head(DASH_CACHE_ROWS), len(out)


@st.cache_data(ttl=1800, show_spinner=False)
def _cached_free_draft(gid, title, body, size_tier, urgency, job_type,
                        name, headline, bio, portfolio):
    """
    pitch.draft_template() wrapped for caching — it's deterministic (same
    gig, same profile, same draft, on purpose, per its own docstring), but
    it was recomputing from scratch for every visible free-tier card on
    EVERY dashboard rerun, including every "Load more" click. Small per
    card (~1ms), but it compounds as the shown count grows with repeated
    Load More clicks, on top of whatever else made that rerun happen.

    Explicit primitive fields rather than the raw gig/profile dicts as the
    cache key — a DataFrame row's .to_dict() can carry pandas-specific
    values that don't hash as cleanly or predictably as plain strings.
    """
    gig = {"id": gid, "title": title, "body": body, "size_tier": size_tier,
           "urgency": urgency, "job_type": job_type}
    profile = {"name": name, "headline": headline, "bio": bio, "portfolio": portfolio}
    return pitch.draft_template(gig, profile)


def _free_draft_for(gig: dict, profile: dict) -> str:
    """Cache-key extraction for _cached_free_draft — see there for why."""
    return _cached_free_draft(
        gig.get("id"), gig.get("title"), gig.get("body"), gig.get("size_tier"),
        gig.get("urgency"), gig.get("job_type"),
        profile.get("name"), profile.get("headline"), profile.get("bio"),
        profile.get("portfolio"))


def _save_draft(gig_id, key):
    text = st.session_state.get(key, "")
    drafts.save(gig_id, text)
    # What they actually kept, compared to the AI's first attempt at this gig
    # — style.py filters out trivial edits on its own, so it's fine to call
    # this on every save rather than only the ones that look different.
    style.record_edit(gig_id, text)
    st.session_state[f"_saved_{gig_id}"] = True


def _regen_draft(gig, key):
    st.session_state[key] = pitch.draft_pitch(
        gig, prof, resume_text=st.session_state.get("_resume_text", ""),
        who=paths.get_scope())
    st.session_state[f"_saved_{gig['id']}"] = False




def gig_card(r, pro):
    with st.container(border=True):
        new = '<span class="gr-new">New</span>' if r.get("is_new") == 1 else ""
        title = html.escape(r.get("title") or "(no title)")
        # Routed through ?nav=out so an apply click can be logged (activity.py)
        # before the browser leaves — a direct href to the external URL has no
        # server round-trip to hook a count into. Falls back to the raw URL if
        # the row somehow has no id, so a click still goes somewhere.
        #
        # ilink() is what makes the logging actually happen. This opens in a NEW
        # TAB, and a new tab is a new Streamlit session with empty session_state,
        # so without the token in the URL the redirect route sees an anonymous
        # visitor and records nothing — the count the weekly digest reports would
        # sit at zero for everyone who signed in by email.
        gid = r.get("id")
        out_url = ilink(f"?nav=out&gid={gid}") if gid is not None else \
            html.escape(r.get("url") or "", quote=True)
        # The star is a LINK in the same markdown as the title, not an
        # st.button in a column beside it. A column would wrap the title in its
        # own stVerticalBlock, and the card's border rule keys off
        # `:has(> stElementContainer a.gr-title)` — so the column's block
        # matched it too and drew a second bordered card around just the
        # headline, while the real card lost its house border and fell back to
        # Streamlit's stock grey. Same ?param routing the nav and the stat
        # cards already use, so the card's DOM shape is exactly what the
        # stylesheet was tuned against.
        star = ""
        won = ""
        if gid is not None and ACCESS["signed_in"]:
            _on = str(gid) in saved_ids()
            # `from` so unsaving on the Saved tab returns to Saved, not Gigs.
            _from = (st.session_state.get("_active_tab") or "gigs").lower()
            star = (f'<a class="gr-save{" on" if _on else ""}" '
                    f'href="{ilink(f"?save={gid}&from={_from}")}" target="_self" '
                    f'title="{"Saved — click to remove" if _on else "Save for later"}">'
                    f'{"★" if _on else "☆"}</a>')
            # THE "I GOT HIRED" TAP IS GONE, and the reason is that nothing
            # could ever check it. Anyone could press it on any gig, so the
            # number it produced was unverifiable in principle rather than
            # merely unverified — and it was the number most likely to be
            # quoted to a partner or a board member, which is the worst place
            # for a figure you cannot stand behind. It was also self-selecting
            # in the honest direction: most people who land work never come
            # back to say so, so it undersold as well as being unprovable.
            #
            # outcomes.py and its table are left alone deliberately. Nothing
            # writes to them now, nothing is deleted, and the door stays open
            # for a version that can actually be evidenced.
            won = ""
        # rel is not optional on a target="_blank" we write by hand. noreferrer
        # stops the Referer header telling the poster which page on Nabbly the
        # click came from — that URL carries the filters, and on a signed-in
        # session it is the one place a token could ride along. noopener cuts
        # the opened tab's window.opener handle, without which the destination
        # can navigate the tab it came from somewhere of its own choosing.
        # Streamlit sets both on the links it renders itself; this anchor is
        # ours, so it has to say so.
        st.markdown(
            f'{new}<a class="gr-title" href="{out_url}" target="_blank" '
            f'rel="noopener noreferrer">{title}</a>{star}{won}',
            unsafe_allow_html=True)

        # Pills carry their meaning in colour (FEEL.md §2: match is amber,
        # urgent is red, low is amber-dim, location is blue/green, budget is
        # the same light-to-deep amber ramp Market's own charts use for size)
        # — an emoji prefix on top of a tinted pill was saying the same thing
        # twice. Budget shows on every single card, unlike the conditional
        # pills around it, so leaving it neutral (as it was) meant the one
        # pill guaranteed to appear every time carried no colour at all.
        badge_items = []
        if pro and r.get("_score") is not None:
            badge_items.append((f"{int(r['_score'])}% match", "match"))
        _src = (r["source"] or "").lower()
        _budget_cls = {"Small": "budget-sm", "Medium": "budget-md",
                       "Large": "budget-lg"}.get(r["size_tier"], "")
        # Source used to sit here as its own neutral-gray pill. It's logistics
        # (which board this came from), not a signal about whether the gig is
        # worth chasing — the same weight as "Urgent" or "83% match" for
        # information that isn't in the same league. It's still shown, just
        # as quiet text by the post date below, not competing for the eye.
        badge_items += [(r["job_type"], ""),
                        (f"{r['size_tier']} budget", _budget_cls)]
        # where can this be done — and can *you* take it?
        loc = location.tag(r)
        if location.is_local(r, prof.get("city")):
            badge_items.append((f"Near {prof.get('city')}", "locnear"))
        else:
            loc_lbl = location.label(loc)
            if loc_lbl:
                ok = location.eligible(loc, location.country_region(prof.get("country")))
                if not ok:
                    # geo-locked to a region you're not in — make that obvious
                    badge_items.append((f"{loc['restrict']}-only · can't apply", "locoff"))
                # A plain "Remote" pill beside a board called RemoteOK is the
                # same fact twice. Anything sharper (US-only, worldwide) still
                # earns its place.
                elif not (_src in config.REMOTE_ONLY_SOURCES
                          and loc_lbl.strip().lower().endswith("remote")):
                    badge_items.append((loc_lbl, "loc"))
        _lc = r.get("_lang") or "en"
        if _lc != "en":
            badge_items.append((lang.label(_lc), "locoff"))
        if r.get("urgency") == "Urgent":
            badge_items.append(("Urgent", "urgent"))
        if pro:
            lb, reason = market.lowball(r, stats, prof)
            if lb:
                badge_items.append((reason, "low"))
        # Apply-method last, on purpose: it's the one pill here that's
        # neutral-gray instead of carrying real signal color, so it reads as
        # a trailing note ("here's what applying involves") rather than
        # competing with match/budget/urgent for first-glance attention.
        if (r.get("apply_email") or "").strip():
            badge_items.append(("Apply by email", "match"))
        # The source name (below, by the post date) already says WHICH
        # board; this adds the one thing that doesn't say — that applying
        # means signing up there first. Said before the click, not
        # discovered after it. Two distinct facts on purpose: a free signup
        # and a paywall are not the same ask, and saying so honestly matters
        # more than keeping the badge list short.
        elif _src in config.SUBSCRIPTION_REQUIRED_SOURCES:
            badge_items.append(("Paid subscription to apply", "urgent"))
        elif _src in config.ACCOUNT_REQUIRED_SOURCES:
            badge_items.append(("Free account needed to apply", "locoff"))
        pills(badge_items)

        if pro and r.get("_reasons"):
            chips = "".join(f'<span class="gr-why-chip">{html.escape(x)}</span>'
                            for x in r["_reasons"])
            if chips:
                st.markdown('<div class="gr-why"><span class="lead">why</span>'
                            + chips + "</div>", unsafe_allow_html=True)

        # Right where the claim is made, not buried in a settings page or a
        # generic feedback box elsewhere — "73% match" is a specific promise,
        # and this is the cheapest way to find out if it was right. Only
        # shown alongside an actual score: without one there's no claim here
        # to rate. Same link+redirect construction as the star and 🎯 above.
        if pro and r.get("_score") is not None and gid is not None and ACCESS["signed_in"]:
            _mr = my_ratings().get(str(gid))
            _from2 = (st.session_state.get("_active_tab") or "gigs").lower()
            st.markdown(
                '<div class="gr-matchfb"><span class="lead">good match?</span>'
                f'<a class="gr-thumb{" on" if _mr == "up" else ""}" '
                f'href="{ilink(f"?rate={gid}&dir=up&from={_from2}")}" target="_self" '
                f'title="Yes, this was a good match">👍</a>'
                f'<a class="gr-thumb{" on down" if _mr == "down" else ""}" '
                f'href="{ilink(f"?rate={gid}&dir=down&from={_from2}")}" target="_self" '
                f'title="No, not really a match">👎</a></div>',
                unsafe_allow_html=True)

        # Body clamped to three lines so every card is the same height whether
        # its post is two sentences or twenty — a column of ragged cards is the
        # thing that made the board look unfinished. "See more" is a pure CSS
        # checkbox toggle rather than an st.button: a button would rerun the
        # whole script (25 cards, a full board rebuild) just to reveal a
        # paragraph that is already in the DOM.
        # A longer trim than the old 230-char preview: the CSS clamp now
        # controls how tall the card is, so the server no longer has to keep
        # the text short to keep the layout tidy. It also means "See more" has
        # something real to reveal instead of one extra sentence.
        body = smart_trim(display_body(r.get("body")), target=620, hard=1200)
        # Fall back to fetched_at exactly like the SQL sort does. Without it a
        # gig with no posted_at read "Posted recently" — which sounds like
        # "minutes ago" but actually means "we couldn't read a date", the least
        # useful thing to tell someone deciding whether a gig is worth chasing.
        # We always know when WE saw it, so say that instead.
        # Source moved here from the pill row above — see the badge_items
        # comment on why. Same quiet treatment as the date it now sits next
        # to: both are "how you'd act on this," not "should you care."
        posted = html.escape(
            f"Posted {human_time(r.get('posted_at') or r.get('fetched_at'))}"
            f" · via {config.source_label(_src)}")
        if body:
            cb = f"gm{r['id']}"
            st.markdown(
                f'<div class="gr-bodywrap">'
                f'<input type="checkbox" id="{cb}" class="gr-more-cb">'
                f'<div class="gr-body">{html.escape(body)}</div>'
                f'<label class="gr-more-lbl" for="{cb}"></label>'
                f'<div class="gr-posted">{posted}</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            # No description: the date still needs the same gap above it that a
            # card WITH a description gets, otherwise it rides up against the
            # pills and the two card shapes read as different components.
            st.markdown(f'<div class="gr-bodywrap gr-nobody">'
                        f'<div class="gr-posted">{posted}</div></div>',
                        unsafe_allow_html=True)

        gid = r["id"]
        saved_exists = drafts.has(gid)
        # Used to read "Draft my reply  ·  Pro" for everyone on Free — a
        # leftover from when the whole feature was a locked box. It isn't:
        # Free gets a real draft now (see the else branch below), so the
        # label shouldn't advertise a paywall that's no longer there. The
        # upsell still shows, just after opening it — "See what Pro unlocks".
        label = "Draft my reply"
        if pro and saved_exists:
            label += "  ·  draft saved"
        with st.expander(label):
            if pro:
                key = f"pitch_{gid}"
                # A saved edit is just a DB read — cheap, shows immediately.
                # A FRESH draft calls the real model (pitch.draft_pitch), which
                # used to run unconditionally the moment this card was seeded
                # into session_state — i.e. for every card on the board, the
                # instant it rendered, whether or not anyone opened it. On a
                # Dashboard with dozens of cards behind "Load more", that's
                # dozens of sequential API calls stacking up before the page
                # finishes — a card scrolling into view isn't the same as
                # someone asking for a reply to it. Now it's a deliberate
                # click, same shape as "Start fresh" below.
                if key not in st.session_state:
                    saved = drafts.load(gid)
                    if saved:
                        st.session_state[key] = saved
                if key in st.session_state:
                    st.text_area("Your draft", height=240, key=key,
                                 label_visibility="collapsed")
                    bc1, bc2 = st.columns(2)
                    bc1.button("Save draft", key=f"save_{gid}", width="stretch",
                               on_click=_save_draft, args=(gid, key))
                    bc2.button("Start fresh", key=f"regen_{gid}", width="stretch",
                               on_click=_regen_draft, args=(r, key),
                               help="Replace your edits with a new auto-draft")
                    # Some postings have no apply button at all — they just say
                    # "email us". For those we know the address, so the draft stops
                    # being something to copy somewhere and becomes something to
                    # send. Reads the CURRENT textarea, so any edit goes with it.
                    _to = (r.get("apply_email") or "").strip()
                    if _to:
                        _link = contact.mailto(
                            _to, f"Re: {r.get('title', '')}",
                            st.session_state.get(key, ""))
                        st.markdown(
                            f'<a class="gr-sendmail" href="{html.escape(_link, quote=True)}">'
                            f'Send to {html.escape(_to)}</a>', unsafe_allow_html=True)
                        st.caption("Opens your mail app with this draft already in it. "
                                   "Read it once before you send.")
                    if st.session_state.pop(f"_saved_{gid}", False):
                        st.caption("Saved — your edits will be here when you come back.")
                    elif saved_exists:
                        st.caption("Editing your saved draft. Tweak it, hit **Save**, and you're set.")
                else:
                    st.caption("Post-aware — written from this listing, not a template.")
                    st.button("Generate my draft", key=f"gen_{gid}", type="primary",
                              width="stretch", on_click=_regen_draft, args=(r, key))
            else:
                # A real draft, not just a paywall — see pitch.draft_template
                # for why this reads like a person and not a form. It just
                # can't read the post the way the Pro path can, which is the
                # actual, honest gap Pro closes. Cached (_free_draft_for) —
                # see _cached_free_draft for why.
                free_draft = _free_draft_for(r, prof)
                _body = "".join(
                    "<p>" + html.escape(block.strip("\n")).replace("\n", "<br>") + "</p>"
                    for block in free_draft.split("\n\n") if block.strip())
                st.markdown(f'<div class="gr-draft-body gr-draft-body-free">{_body}</div>',
                            unsafe_allow_html=True)
                if st.button("See what Pro unlocks", key=f"up_{r['id']}",
                              width="stretch"):
                    upgrade_dialog(f"draft_{gid}", pitch.free_draft_note(r))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
@st.fragment(run_every=60)
def live_stats():
    """Re-reads the feed every ~60s so the headline numbers climb on their own
    as the background fetcher pulls in new gigs — no click needed. (Kept a touch
    slower than the ~5-min fetch to avoid needless reruns.)"""
    # Same lens the rest of the app uses: the dashboard's own "Fresh off the
    # boards" list and the whole Gigs page both read through
    # apply_language(apply_city_lock(...)), so counting the raw frame here made
    # the tiles quote gigs no other surface would ever show. It read as the
    # number shrinking on click ("17,000+ on the board" landing on a page that
    # says 15,374), when nothing had actually gone anywhere. Count what the
    # viewer can actually reach. Both helpers no-op on an empty frame, so the
    # one guard below still covers the empty-board case.
    cur, _ = load_feed()
    cur = apply_language(apply_city_lock(cur))
    if cur.empty:
        return
    skills = prof.get("skills") or []
    # Signed in with skills → the numbers are about YOU: your matches, your
    # fresh ones, your urgent ones, with one card for whole-board context.
    # Signed out → the board at large, exactly as before.
    # The board total used to round down to a "15,000+" floor (fmt_floor,
    # FEEL.md §7) — that was about a HARD-CODED marketing figure going stale.
    # This one is never hard-coded, it's len(cur) read fresh on every load,
    # so there's no staleness to guard against; showing the exact count just
    # matches every other live number on this row now.
    if ACCESS["signed_in"] and skills:
        mine = cur[cur["job_type"].isin(skills)]
        stat_cards([
            ("Matching you", f"{len(mine):,}", "#E8933A", "?nav=gigs&qf=mine"),
            ("Fresh for you · 24h", f"{recent_count(mine, 24):,}", "#4C8DFF",
             "?nav=gigs&qf=mine"),
            ("Urgent for you", f"{int((mine['urgency'] == 'Urgent').sum()):,}",
             "#E96250", "?nav=gigs&qf=urgent"),
            ("On the whole board", f"{len(cur):,}", "#35B37E",
             "?nav=gigs", "count"),
        ])
    else:
        # SIGNED OUT: fields to click, not a scoreboard to admire.
        #
        # This used to be four counters — board total, fresh, urgent, fields
        # hiring. Two of those were filters worth having and two were vanity,
        # and all four answered "how big is this" for somebody who had not yet
        # been shown a single piece of work. A first-time visitor cannot act on
        # 32,194. They can act on "Design & Media".
        #
        # It also picks up the thing every other surface depends on: nothing
        # here ranks, alerts or drafts until we know what someone does, and the
        # first screen never asked. Now it does, and each answer is one click
        # into a filtered board (?group= is already handled at dispatch and
        # tracked, so we learn which fields people actually come for).
        category_cards(cur)


def category_cards(cur):
    """
    The broad fields, as links, for the signed-out dashboard.

    Same card shell as stat_cards so the row sits where the counters sat, minus
    the number: a field name and an arrow. Deliberately no per-field count —
    the point of this row is "which of these is you", and a tally next to each
    name turns a choice back into a leaderboard, which is what it replaced.

    Only fields that actually have gigs behind them are shown, so nobody clicks
    into an empty board. Ordered by volume, which is the one place size still
    earns its keep: it puts the likeliest match first without printing it.
    """
    if cur.empty:
        return
    counts = cur["job_type"].value_counts().to_dict()
    groups = [(g, sum(counts.get(s, 0) for s in subs))
              for g, subs in config.CATEGORY_GROUPS.items()]
    groups = sorted([(g, n) for g, n in groups if n], key=lambda x: -x[1])
    if not groups:
        return
    # `out`, not `html` — stat_cards gets away with that name because it never
    # needs the html module, and every group name here contains an ampersand.
    out = '<div class="gr-cat">'
    for g, _n in groups:
        out += (f'<a href="{ilink(f"?nav=gigs&group={quote(g)}")}" '
                f'target="_self">{html.escape(g)}</a>')
    out += "</div>"

    # Only offered when there is actually something behind them. "Urgent" that
    # lands on an empty board is worse than no link, and on a quiet night the
    # last 24 hours can genuinely be thin.
    quick = []
    if recent_count(cur, 24):
        quick.append(("Posted today", "?nav=gigs&qf=recent"))
    if int((cur["urgency"] == "Urgent").sum()):
        quick.append(("Urgent only", "?nav=gigs&qf=urgent"))
    if quick:
        out += '<div class="gr-quick">' + "".join(
            f'<a href="{ilink(h)}" target="_self">{t}</a>' for t, h in quick
        ) + "</div>"
    st.markdown(out, unsafe_allow_html=True)


def category_strip(col=None):
    """
    Pick a broad field to browse, with live counts.

    This was a wrapping row of chips. Five of them fit one desktop line but
    stacked into four ragged rows on a phone, and they pushed the first gig most
    of a screen further down — a whole block of chrome before any actual work.
    A select puts the same choice in one row beside the search, so the two
    controls read as one toolbar instead of two stacked bars.
    """
    if df.empty:
        return
    counts = df["job_type"].value_counts().to_dict()
    groups = [(g, sum(counts.get(s, 0) for s in subs))
              for g, subs in config.CATEGORY_GROUPS.items()]
    groups = sorted([(g, n) for g, n in groups if n], key=lambda x: -x[1])
    if not groups:
        return
    # No counts in the dropdown itself — picking one immediately shows
    # "N,NNN gigs for you" right under the search bar, so the number here
    # was saying the same thing twice, a beat apart.
    labels = ["All fields"] + [g for g, _ in groups]
    names = [""] + [g for g, _ in groups]
    current = st.session_state.get("groupfilter", "")
    target = col if col is not None else st
    pick = target.selectbox(
        "Browse by field", labels,
        index=names.index(current) if current in names else 0,
        key="groupsel", label_visibility="collapsed")
    chosen = names[labels.index(pick)]
    if chosen != current:
        st.session_state["groupfilter"] = chosen
        # Picking a field starts a fresh drill-down; a stale sub-category would
        # otherwise take precedence and show the wrong slice.
        st.session_state["catfilter"] = ""
        st.rerun()


def hero_search():
    """
    The front door: type what you're looking for.

    This was a skills dropdown, which is a filter wearing a search box's
    clothes — people type words, not categories. Free text searches every gig's
    title and body, so "figma" or "shopify" finds work no category could. The
    fixed categories are still there, as the browse chips below and as a filter
    on the Gigs page, which is where filtering belongs.
    """
    with st.container():
        st.markdown('<span class="gr-search-mark"></span>', unsafe_allow_html=True)
        with st.form("herosearch", clear_on_submit=False, border=False):
            c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
            with c1:
                q = st.text_input(
                    "Search gigs", label_visibility="collapsed",
                    placeholder="Search gigs — figma, shopify, copywriting…")
            with c2:
                go = st.form_submit_button("Search", type="primary", width="stretch")
        if go and q.strip():
            st.session_state["searchq"] = q.strip()
            st.session_state["_navidx"] = _TABS.index("Gigs")
            st.session_state["_profile"] = st.session_state["_about"] = False
            note("click", "search:text")
            st.rerun()
        # (The old "or tell us what you do" line lived here. Removed: people set
        # up their profile anyway, so it just cluttered the search area.)


@st.fragment(run_every=45)
def arrivals_pill():
    """
    "3 landed while you were reading" — the Twitter pattern.

    Polling the list and silently reordering it under someone's eyes is
    hostile; a pill they choose to tap is not. It also makes the live feed
    visible, which is the entire promise of the product.
    """
    cur, _ = load_feed()
    if cur.empty or "id" not in cur:
        return
    newest = int(cur["id"].max())
    if not st.session_state.get("_seen_max_id"):
        st.session_state["_seen_max_id"] = newest      # baseline on first view
        return
    newer = cur[cur["id"] > st.session_state["_seen_max_id"]]
    if prof.get("skills"):
        newer = newer[newer["job_type"].isin(prof["skills"])]
    n = len(newer)
    if not n:
        return
    # A quiet, centred chip (styled via .st-key-arrivals) rather than a bright
    # full-width bar. It should read as a gentle "there's more" nudge inside the
    # flow, not an alert shouting over the page.
    if st.button(f"Show {n} new gig{'s' if n > 1 else ''}",
                 key="arrivals", type="secondary"):
        st.session_state["_seen_max_id"] = newest
        note("click", "arrivals")
        st.rerun()


def draft_showcase(pro):
    """
    Show, don't tell.

    A ready-to-send reply, already written for a top-matching gig, sitting in
    the open. It was the strongest thing in the product and it lived behind a
    collapsed row on every card, which is where features go to die.

    Picks from the top 3 matches rather than always #1, so a daily regular
    doesn't see the identical card every visit — but the pick is seeded off
    the date and account, not random, so it holds still for the length of one
    sitting instead of changing on every unrelated rerun.
    """
    if df.empty or not prof.get("skills"):
        return
    srcs = sorted(df["source"].unique())
    top = apply_bias(scored(
        apply_filters(df, prof["skills"], ["Small", "Medium", "Large"], srcs, False, ""),
        resume_text=st.session_state.get("_resume_text", ""))).head(3)
    if top.empty:
        return
    seed = f"{datetime.now(timezone.utc).date()}-{paths.get_scope()}"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(top)
    g = top.iloc[idx].to_dict()
    gid = str(g["id"])
    pills_html = "".join(
        f'<span class="gr-pill {c}">{html.escape(str(t))}</span>' for t, c in [
            (f"{int(g['_score'])}% match", "match") if g.get("_score") is not None else ("", ""),
            (g.get("job_type", ""), ""), (f"{g.get('size_tier','')} budget", ""),
            source_pill(g.get("source")),
        ] if t)

    if not pro:
        # A real draft, not a locked box — see pitch.draft_template for why
        # this reads like a person and not a form. It can't read the post
        # the way Pro can; that's the actual, honest gap, so say that
        # instead of hiding the whole feature behind a lock icon. Cached
        # (_free_draft_for) — see _cached_free_draft for why.
        free_draft = _free_draft_for(g, prof)
        _body = "".join(
            "<p>" + html.escape(block.strip("\n")).replace("\n", "<br>") + "</p>"
            for block in free_draft.split("\n\n") if block.strip())
        st.markdown(
            '<div class="gr-draft"><div class="gr-draft-hd">'
            '<div class="gr-draft-k">Your draft, ready to edit</div>'
            f'<div class="gr-draft-t">{html.escape(g.get("title") or "")}</div>'
            f'<div class="gr-draft-m">{pills_html}</div></div>'
            f'<div class="gr-draft-body">{_body}</div></div>',
            unsafe_allow_html=True)
        _s1, _s2, _s3 = st.columns([1, 2, 1])
        with _s2:
            if st.button("See what Pro unlocks", key="up_showcase",
                          width="stretch"):
                upgrade_dialog("draft_showcase", pitch.free_draft_note(g))
        return

    # Same class of bug as the per-card fix above, different shape: this pick
    # is a single stable item (seeded per day+account, not per rerun), but
    # with no cache here it was still calling the real model fresh on EVERY
    # unrelated rerun on this page — a search, a save, anything — until the
    # day it happened to get saved. One session_state seed, same as before,
    # is the right fix for a single slot (it isn't the "load more grows
    # without bound" shape that made per-card caching wrong there).
    _sk = f"_showcase_pitch_{gid}"
    if _sk not in st.session_state:
        st.session_state[_sk] = drafts.load(gid) or pitch.draft_pitch(
            g, prof, resume_text=st.session_state.get("_resume_text", ""),
            who=paths.get_scope())
    text = st.session_state[_sk]
    body = "".join(
        "<p>" + html.escape(block.strip("\n")).replace("\n", "<br>") + "</p>"
        for block in text.split("\n\n") if block.strip())
    st.markdown(
        '<div class="gr-draft"><div class="gr-draft-hd">'
        '<div class="gr-draft-k">We already wrote your reply</div>'
        f'<div class="gr-draft-t">{html.escape(g.get("title") or "")}</div>'
        f'<div class="gr-draft-m">{pills_html}</div></div>'
        f'<div class="gr-draft-body">{body}</div></div>',
        unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        _gid = g.get("id")
        # ilink() for the same reason as gig_card's title: the redirect route
        # can only log the click if it can tell who is clicking.
        _out = ilink(f"?nav=out&gid={_gid}") if _gid is not None else (g.get("url") or "#")
        st.link_button("Open the gig  ↗", _out, width="stretch")
    with c2:
        if st.button("Edit this reply", width="stretch", key="showcase_edit"):
            st.session_state["_navidx"] = _TABS.index("Gigs")
            st.session_state["_profile"] = st.session_state["_about"] = False
            st.session_state["quickfilter"] = "mine"
            note("click", "showcase:edit")
            st.rerun()
    st.caption("Written from your profile and this exact gig. Edit it on the Gigs tab, "
               "or send it as it stands.")


def view_dashboard(pro):
    # The headline is a PITCH, and a pitch is only worth screen space to someone
    # who hasn't bought yet. Signed-out visitors may have landed here directly
    # without ever seeing nabbly.co, so they still get it. Signed-in members are
    # here to work: they get a quiet working header instead, which puts the
    # search ~124px higher and a second gig above the fold.
    if not ACCESS["signed_in"]:
        st.markdown(
            '<div class="gr-hero gr-hero-tight">'
            '<h1 class="gr-h1">Every gig, the moment it drops.<br>'
            'You just <span class="accent">reply first.</span></h1>'
            "</div>", unsafe_allow_html=True)
    else:
        _who = (prof.get("name") or "").strip().split(" ")[0]
        st.markdown(
            f'<div class="gr-page-head">'
            f'<h2>{"Welcome back, " + html.escape(_who) if _who else "Your board"}</h2>'
            f'<p>Search when you want. The rest comes to you.</p>'
            f'</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Nothing loaded yet. Pop over to **Gigs** and hit *Refresh* — "
                "we'll pull the latest for you.")
        return

    # The search sits right under the headline: pick what you do, and the
    # numbers below rearrange around you.
    hero_search()

    st.write("")
    live_stats()

    # Only shown once it's true. "You've landed 0 gigs" on every dashboard,
    # forever, until someone's first win, would be a worse look than saying
    # nothing — it would read as the board's own scoreboard sitting at zero
    # rather than as a thing waiting for THIS person's first tap.
    # The "you've landed N gigs" banner went with the tap that fed it. It read
    # as a verified count and was a tally of self-reports.

    # Category browsing moved to the Gigs page (where people are actually
    # looking), so the dashboard top stays a clean headline + search + stats.
    st.divider()
    arrivals_pill()
    draft_showcase(pro)
    # Picked for you IS the dashboard's whole identity — a fit-scored feed,
    # same shape as a social app's own For You page — not a second Gigs page,
    # so this deliberately doesn't get Gigs's full filter bar or pagination.
    # But a feed that just stops at a fixed 12 with no way to see more reads
    # as broken, not curated. "Load more" grows the SAME feed in place
    # (session_state, not a page nav) until it's genuinely exhausted — a
    # real, finite pool once someone's skills narrow it down — at which
    # point the honest next step is the full Gigs page, not more of this one.
    picked = bool(prof.get("skills"))
    if picked:
        st.markdown('### Picked for <span class="gr-accent">you</span>'
                    '<span class="gr-sect"></span>', unsafe_allow_html=True)
        srcs = sorted(df["source"].unique())
        top, matched_total = _dash_picks(
            db.board_version(), paths.get_scope(),
            _prof_cache_key(), tuple(prof["skills"]), tuple(srcs))
        top = apply_bias(top)
    else:
        st.markdown('### Fresh off the <span class="gr-accent">boards</span>'
                    '<span class="gr-sect"></span>', unsafe_allow_html=True)
        top = apply_language(apply_city_lock(df))
        # Not capped: this branch isn't cached, so it costs one frame for the
        # duration of the render rather than one per person held for 3 minutes.
        matched_total = len(top)

    if top.empty:
        st.caption("Nothing's clicking yet — try adding a few more skills on the Profile "
                   "tab. The board moves fast; there'll be more any minute.")
    else:
        shown = st.session_state.get("_dash_shown", DASH_FEED)
        for r in top.head(shown).to_dict("records"):
            gig_card(r, pro)

        if shown < len(top):
            # No count on the button — a curated "for you" feed showing
            # "14,286 more waiting" reads as an undifferentiated firehose,
            # not a pick. The number's still there for you in the code path
            # (len(top) - shown) if it's ever needed again, just not surfaced.
            if st.button("Load more", key="dash_more", width="stretch"):
                st.session_state["_dash_shown"] = shown + DASH_FEED
                st.rerun()
        else:
            _qf = "&qf=mine" if picked else ""
            # "That's everything" is only true when the list really ended. The
            # cached pick stops at DASH_CACHE_ROWS, so past that there are more
            # matches and saying otherwise would send someone away believing
            # the board was empty for them.
            _more = matched_total > len(top)
            _lead = (f"That's the top {len(top)} for you."
                     if _more else
                     f'That\'s everything {"matching you" if picked else "on the board"} right now.')
            st.markdown(
                f'<div class="gr-dash-end">{_lead} '
                f'<a href="{ilink(f"?nav=gigs{_qf}")}" target="_self">'
                f'See all gigs on the full board →</a></div>',
                unsafe_allow_html=True)

    # The feedback box used to sit here, directly under the gigs. A form asking
    # "what would make this better?" at the end of the reading path interrupts
    # the one thing someone came to do — read gigs. It lives on the Profile page
    # now, where settings and account things belong, and a quiet line points at
    # it from here instead.
    #
    # signup_card() only shows something here for people already signed in
    # (the trial offer, the keep-Pro ask, the pay-willingness question) — an
    # anonymous visitor's "sign in" prompt used to live here too, but sign in
    # is reachable from the account menu in the header now, so there's no
    # need to repeat it at the bottom of every scroll.
    if ACCESS["signed_in"] and ACCESS["plan"] != "pro":
        st.divider()
        signup_card("dashboard")


def view_gigs(pro):
    # The page used to open with SEVEN stacked control rows of different shapes
    # before a single gig appeared: heading, a boxy refresh button, search,
    # browse chips, location pills, a full-width expander, then the result count.
    # Refresh belongs with the title, not in the reading path — it's a
    # maintenance action, not something you do before every search.
    _h, _r = st.columns([3.4, 1], vertical_alignment="center")
    # Plain HTML now instead of a markdown "###" — the page-head div needs to be
    # the outer wrapper, and markdown only parses "###" at the very start of a
    # line, so a leading div would have turned it into literal text.
    _h.markdown('<div class="gr-page-head"><h2>The whole '
                '<span class="gr-accent">board</span></h2></div>'
                '<span class="gr-tools"></span>', unsafe_allow_html=True)
    with _r:
        if st.button("Refresh", key="checknew", width="stretch"):
            with st.spinner("Scanning the web for fresh gigs…"):
                ingest.run()
            _public_feed_at.clear()      # new gigs should show at once, not in 45s
            st.rerun()

    if df.empty:
        st.info("Nothing here yet — hit **Refresh** and we'll grab the latest.")
        return

    # Search and field sit on ONE row: they are the same decision ("what work?"),
    # so they belong together rather than as two stacked full-width bars.
    _sc, _fc = st.columns([3, 2], vertical_alignment="center")
    # A generation number baked into the widget's key, not a fixed "gigsearch".
    # Clear used to pop "gigsearch" from session_state and rerun, which is the
    # textbook way to reset a keyed widget — and it silently didn't work: the
    # results correctly went back to the whole board, but the box kept showing
    # the old query, because once a key has been typed into, Streamlit's
    # frontend treats it as user-owned and won't accept a fresh `value=` for
    # that SAME key on a later render. Changing the key itself sidesteps the
    # question entirely: the widget below is a widget Streamlit has never seen
    # before, so `value=` is honored because there's nothing to override.
    _skey = f"gigsearch_{st.session_state.get('_search_gen', 0)}"
    _sq = _sc.text_input("Search gigs", value=st.session_state.get("searchq", ""),
                         placeholder="Search gigs — figma, shopify, medical…",
                         label_visibility="collapsed", key=_skey)
    kw = (_sq or "").strip().lower()
    if kw != st.session_state.get("searchq", ""):
        st.session_state["searchq"] = kw

    category_strip(_fc)

    # Prominent location lens — the first cut most people want to make.
    # Counted through the same apply_language(apply_city_lock(...)) the view
    # below reads through (2189). Counting the raw frame here made every chip
    # promise gigs this reader can't be shown: "Everywhere · 17148" landing on
    # a page that says 15,375 gigs. A chip is a promise about what one tap
    # gives you, so it has to count the same board the tap lands on. Both
    # helpers no-op on an empty frame, and location_counts already handles it.
    _all, _rem, _loc = location_counts(apply_language(apply_city_lock(df)))
    _CITY = (prof.get("city") or "").strip()
    _onsite_lbl = "Near " + _CITY if _CITY else "On-site / local"
    _opts = [f"Everywhere · {_all}", f"Remote I can take · {_rem}",
             f"{_onsite_lbl} · {_loc}"]
    _pick = st.segmented_control("Where you can work", _opts, default=_opts[0],
                                 key="locseg", label_visibility="collapsed")
    loc_mode = ("Remote I can take" if _pick and "Remote" in _pick
                else "On-site / local" if _pick and _pick.startswith(_onsite_lbl)
                else "Everywhere")
    if loc_mode == "On-site / local" and not _CITY:
        st.caption("Showing hands-on gigs everywhere — add your **city** in Profile to pin "
                   "these to your area.")

    with st.expander("Narrow it down"):
        skills = st.multiselect("Skill", ALL_SKILLS, default=ALL_SKILLS, placeholder="")
        sizes = st.multiselect("Budget", ["Small", "Medium", "Large"],
                               default=["Small", "Medium", "Large"], placeholder="")
        srcs = sorted(df["source"].unique())
        sources = st.multiselect("Source", srcs, default=srcs, placeholder="")
        # A real filter, not a buried Profile checkbox: apply_language() hides
        # anything outside reading_languages() by default, which is the right
        # call for the Dashboard and other overview surfaces, but on the one
        # page whose whole job is "go find gigs," silently hiding ~9% of the
        # board is hiding real demand, not decluttering it. Same default
        # (home language only) so nobody's view changes unasked, but now it's
        # a visible, one-click choice right next to Skill/Budget/Source
        # instead of a setting most people will never find.
        _board_langs = (sorted(df["_lang"].dropna().unique())
                        if "_lang" in df.columns else ["en"])
        _lang_default = [c for c in _board_langs if c in reading_languages()] or _board_langs
        # Counts in the label, not just names — the point is to make the
        # non-English volume legible at a glance, not just technically
        # selectable.
        _lang_counts = df["_lang"].value_counts().to_dict() if "_lang" in df.columns else {}
        languages = st.multiselect(
            "Language", _board_langs, default=_lang_default,
            format_func=lambda c: f"{lang.label(c)} · {_lang_counts.get(c, 0)}",
            placeholder="")
        urgent = st.checkbox("Urgent only")
        if skills and set(skills) != set(ALL_SKILLS) and set(skills) != set(prof.get("skills") or []):
            if st.button("Save these as my skills", key="savefilterskills"):
                prof["skills"] = skills
                profile_mod.save(prof)
                note("click", "filter:saveskills")
                st.rerun()

    with st.spinner(f"Searching for “{kw}”…" if kw else "Loading the board…"):
        view = apply_filters(df, skills, sizes, sources, urgent, kw)
        view = apply_city_lock(view)
        if "_lang" in view.columns:
            view = view[view["_lang"].isin(languages)]
        view = apply_location(view, loc_mode)
        if pro:
            view = apply_bias(scored(view, resume_text=st.session_state.get("_resume_text", "")))
        if kw:
            # Best matches first — after scoring, so relevance to what they
            # actually typed wins over a generic fit score.
            view = rank_by_relevance(view, kw)

    # A search that comes up nearly empty is unmet demand saying so out loud —
    # someone typed a real skill or tool and the board had almost nothing for
    # it. note() already dedupes per session, so a person refining the same
    # bad query a few times only logs once. Threshold at 2, not 0: a single
    # stray match on a 16,000-gig board is functionally still "nothing here."
    if kw and len(view) <= 2:
        note("search_miss", kw)

    # Answer the search plainly, including when it finds nothing — an empty
    # board with no explanation reads as broken rather than as "no matches".
    if kw:
        sc1, sc2, _ = st.columns([3.1, 1, 5.9], vertical_alignment="center")
        sc1.markdown(f'<span class="gr-qf">▸ {len(view):,} result'
                     f'{"" if len(view) == 1 else "s"} for '
                     f'<b>{html.escape(kw)}</b></span>', unsafe_allow_html=True)
        if sc2.button("Clear", key="clearsearch", width="stretch"):
            st.session_state["searchq"] = ""
            # Bumping the generation, not popping "gigsearch" — see the comment
            # by _skey above for why popping the old key rendered the results
            # correctly but left stale text sitting in the box.
            st.session_state["_search_gen"] = st.session_state.get("_search_gen", 0) + 1
            st.rerun()
        if view.empty:
            st.info(f"Nothing matches **{kw}** right now. Try a broader word, or "
                    "browse by category from the dashboard.")

    # Quick-filter arriving from a Dashboard stat click
    qf = st.session_state.get("quickfilter", "")
    # "in your skills" with no skills on file filtered nothing — the pill said
    # the board was narrowed to them while showing all sixteen thousand gigs.
    # Say what actually happened and offer the fix, rather than claim a filter
    # that didn't run.
    if qf == "mine" and not (prof.get("skills") or []):
        st.info("Tell us what you do and this becomes your shortlist — right "
                "now it's the whole board. Add your skills on **Profile**.")
        qf = ""
        st.session_state["quickfilter"] = ""
    if qf:
        qlabel = {"recent": "posted in the last 24h", "mine": "in your skills",
                  "urgent": "urgent only"}.get(qf, qf)
        fc1, fc2, _ = st.columns([3.1, 1, 5.9], vertical_alignment="center")
        fc1.markdown(f'<span class="gr-qf">▸ {qlabel}</span>', unsafe_allow_html=True)
        if fc2.button("Clear", key="clearqf", width="stretch"):
            st.session_state["quickfilter"] = ""
            st.rerun()
        if qf == "urgent":
            view = view[view["urgency"] == "Urgent"]
        elif qf == "mine" and prof.get("skills"):
            view = view[view["job_type"].isin(prof["skills"])]
        elif qf == "recent":
            view = view[view["posted_at"].map(lambda r: is_recent(r, 24))]

    # A broad bucket (dashboard) or a specific sub-category drill-down
    cat = st.session_state.get("catfilter", "")
    group = st.session_state.get("groupfilter", "")
    if cat:
        cc1, cc2, _ = st.columns([3.1, 1, 5.9], vertical_alignment="center")
        cc1.markdown(f'<span class="gr-qf">▸ {html.escape(cat)}</span>',
                     unsafe_allow_html=True)
        if cc2.button("Clear", key="clearcat", width="stretch"):
            st.session_state["catfilter"] = ""
            st.rerun()
        view = view[view["job_type"] == cat]
    elif group and group in config.CATEGORY_GROUPS:
        subs = config.CATEGORY_GROUPS[group]
        # No "▸ Design & Media  [Clear]" row here any more: the field select
        # already shows the active field, and "All fields" already clears it.
        # Restating it underneath was a third control saying the same thing.
        view = view[view["job_type"].isin(subs)]
        # sub-category chips to narrow into a specific one
        vc = view["job_type"].value_counts().to_dict()
        subchips = "".join(
            f'<a class="gr-cat" href="{ilink(f"?nav=gigs&cat={quote(s)}")}" target="_self">'
            f'{html.escape(s)}<span class="n">{vc.get(s, 0):,}</span></a>'
            for s in subs if vc.get(s, 0)
        )
        if subchips:
            st.markdown('<div style="font-size:12px;color:#7c828d;margin:2px 0 5px">'
                        'Narrow to a sub-category:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="gr-cats" style="justify-content:flex-start">'
                        f'{subchips}</div>', unsafe_allow_html=True)

    # Named _caption, not `note`: assigning to `note` anywhere in this
    # function made EVERY `note` in it a local, so the analytics call at
    # the "Save these as my skills" button (further up) raised
    # UnboundLocalError and replaced the whole Gigs page with a traceback.
    _caption = f"**{len(view):,}** gigs for you"
    st.caption(_caption)

    if view.empty:
        # Only when a SEARCH hasn't already explained the emptiness. A no-match
        # search printed both this and "Nothing matches <term>", two empty
        # states stacked, the second contradicting the first by blaming
        # filters. The button is called Refresh, not "Check for new gigs" —
        # naming a control that isn't there sends people hunting for it.
        if not kw:
            st.info("Nothing matches those filters right now — try widening "
                    "them, or hit **Refresh** up top.")
        return

    # Reset to page 1 whenever the actual result set changes underneath the
    # reader. Without this, landing on page 3 of a broad browse and then
    # typing a narrow search would silently show an empty page instead of
    # the results that do exist — the same class of bug as a stale cache key.
    _fp = (kw, tuple(sorted(skills)), tuple(sorted(sizes)), tuple(sorted(sources)),
           urgent, loc_mode, qf, cat, group)
    if st.session_state.get("_gigs_fp") != _fp:
        st.session_state["_gigs_fp"] = _fp
        st.session_state["gigspage"] = 0

    pool = min(len(view), FEED_CAP)
    total_pages = max(1, -(-pool // PAGE_SIZE))    # ceiling division, no import
    page = min(st.session_state.get("gigspage", 0), total_pages - 1)
    st.session_state["gigspage"] = page

    gig_pager(page, total_pages, "top")
    start = page * PAGE_SIZE
    for r in view.iloc[start:start + PAGE_SIZE].to_dict("records"):
        gig_card(r, pro)
    gig_pager(page, total_pages, "bottom", show_top_link=True)


def view_saved(pro):
    st.markdown('<div class="gr-page-head"><h2>Gigs you '
                '<span class="gr-accent">saved</span></h2></div>',
                unsafe_allow_html=True)

    if not ACCESS["signed_in"]:
        st.info("Sign in and you can save gigs here to come back to. "
                "The board moves fast — saving pins one so it's still "
                "findable tomorrow.")
        return

    ids = saved_ids()
    if not ids:
        st.caption("Nothing saved yet. Hit the ☆ on any gig and it'll wait "
                   "for you here.")
        return

    # Read straight from the board, filtered to the saved ids, so a saved gig
    # shows whatever the board currently knows about it — the re-classified
    # tag, the backfilled apply address — instead of a copy frozen at save
    # time. The same reason saved.py stores ids and not rows.
    cur, _ = load_feed()
    if cur.empty:
        st.caption("The board is still loading. Give it a moment.")
        return
    have = cur[cur["id"].astype(str).isin(ids)]

    # Their save order, not the board's newest-first order: this page is a
    # list they built, so it should read in the order they built it.
    _rank = {gid: i for i, gid in enumerate(ids)}
    have = have.assign(_saved_rank=have["id"].astype(str).map(_rank)) \
               .sort_values("_saved_rank")

    # Anything saved that is no longer on the board — the posting was taken
    # down, or it aged past the 45-day cutoff. Said plainly rather than
    # silently showing fewer cards than the count implies, AND forgotten, so
    # the tab badge can't keep counting gigs nobody can see or remove.
    missing = _prune_saved_ghosts(ids, have)
    _n = len(have)
    st.caption(f"**{_n}** saved gig{'' if _n == 1 else 's'}" +
               (f"  ·  {missing} expired and cleared" if missing else ""))

    # NOT scored() here, deliberately. scored() ends with a sort by fit, which
    # threw away the save order this page is built around — so a Pro user (i.e.
    # everyone on a trial) saw their saved list shuffled into ranking order on
    # the one page whose whole premise is "the order you put them in". Match
    # pills come from _score, so Pro cards on this page simply don't carry one;
    # that's the right trade — the pill is available on every other surface,
    # and the ordering here is the feature.
    for r in have.to_dict("records"):
        gig_card(r, pro)


def _prune_saved_ghosts(ids, have) -> int:
    """
    Forget saved ids the board can no longer resolve, and report how many.

    Saved gigs age off the board continuously (archive_stale runs daily), and
    nothing ever removed their ids — so the tab badge counted them forever
    while the page could only render what still exists. Three months in that
    reads "Saved 31" against a page showing four. The star is the only remove
    control and it lives on a card that no longer renders, so a user could not
    clear them by hand either.

    Only prunes when the board is genuinely populated: an empty or
    still-loading board would otherwise look like "everything expired" and
    wipe a real list.
    """
    if have is None or len(ids) == len(have):
        return 0
    alive = set(have["id"].astype(str))
    gone = [g for g in ids if g not in alive]
    for g in gone:
        saved.remove(g)
    st.session_state.pop("_saved_set", None)
    return len(gone)


def view_market(pro):
    # NO altair import. It used to be lazy-imported right here — "only when
    # someone opens Market" — but Market is a Pro feature, so that meant "only
    # when a NextNW member does the thing the offer promised them." Measured
    # 2026-08-01 at 51MB, up from the ~36MB an old comment quoted, landing on
    # top of a baseline already tight against Render's ceiling — this is the
    # single most likely reason the app went down the night before send. Every
    # chart below is hand-built CSS instead: see hbar_chart/donut_chart/
    # stacked_hbar_chart above pills().
    st.markdown('<div class="gr-page-head"><h2>What gigs like yours are '
                '<span class="gr-accent">paying</span></h2></div>',
                unsafe_allow_html=True)
    # MOVED TO THE BOARD, 2026-08-22. Entering Streamlit cost every visitor
    # ~10s of JS bundle and websocket before the first pixel, and this page's
    # math was never the slow part. board.nabbly.co/market serves the same
    # numbers in ~0.2s, computed once per board change. Same pointer pattern
    # as view_profile; the full page below survives as the fallback when
    # BOARD_URL is unset, so clearing one variable cannot strand Pro members.
    if ACCESS["signed_in"] and BOARD_URL:
        st.caption("Market lives on the board now, where it loads instantly.")
        st.markdown(
            f'<a class="gr-jump gr-settings-link" href="{BOARD_URL}/market">'
            f'Open Market &rarr;</a>', unsafe_allow_html=True)
        return

    if not pro:
        st.info("This one's a **Pro** perk. See what work like yours actually pays, "
                "what's hot this week, and which posts are lowballing — pulled from "
                "everywhere at once. You can switch to Pro any time from your **Profile**.")
        return
    if not stats:
        st.info("Nothing to crunch yet — grab some gigs first.")
        return

    st.caption("Straight from the whole board — no guessing.")
    # Counted through the same lens as every other surface. `stats` is built
    # from the RAW feed (module level, ~line 1730) because the rate figures
    # below genuinely want every gig — a going rate shouldn't shrink because
    # you read one language. But the headline COUNT is the same number the
    # Gigs tab and the Dashboard show, and reading it off raw stats made
    # Market claim 17,882 while Gigs said 16,007 on the same board, in the
    # same session. Same fix as the dashboard tiles; Market was simply missed.
    _mv, _ = load_feed()
    _mv = apply_language(apply_city_lock(_mv))
    total = len(_mv)
    hottest = market.hot_skills(stats)[0]
    priced = [(s, d["typical"]) for s, d in stats.items() if d["typical"]]
    toprate = max(priced, key=lambda x: x[1]) if priced else ("—", 0)
    stat_cards([
        ("Gigs on the board", f"{total:,}", "#E8933A"),
        ("Skills tracked", f"{len(stats)}", "#4C8DFF"),
        ("Hottest skill", hottest[0], "#35B37E", "small"),
        ("Top typical rate", f"${toprate[1]:,}", "#B889F0"),
    ])
    # Sequential amber ramp for budget size (light = small, deep = large) —
    # the same three hex values the old alt.Scale used, so the recolour is
    # identical even though nothing here is Altair anymore.
    BUDGET_COLORS = {"Small": "#F3C07A", "Medium": "#E8933A", "Large": "#A85D1B"}
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**What's hot right now**")
        dd = (pd.DataFrame([{"Skill": s, "Gigs": d["count"]} for s, d in stats.items()])
              .sort_values("Gigs", ascending=False).head(8))
        hbar_chart(list(dd.itertuples(index=False, name=None)), "#E8933A")
        # A chart that tells you Development is busiest and then leaves you to
        # go find it is half an answer. These are the same rows, as links.
        # Deliberately NOT a click-on-the-bar handler: these are plain anchors
        # using the ?nav=gigs&cat= routing the category chips already use — no
        # new mechanism, and they work on a phone where a bar is a poor tap
        # target.
        _hot = "".join(
            f'<a class="gr-cat" href="{ilink(f"?nav=gigs&cat={quote(row.Skill)}")}" target="_self">'
            f'{html.escape(row.Skill)}<span class="n">{row.Gigs:,}</span></a>'
            for row in dd.itertuples())
        st.markdown('<div style="font-size:12px;color:#7c828d;margin:10px 0 6px">'
                    'Open one on the board:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="gr-cats" style="justify-content:flex-start">'
                    f'{_hot}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("**Typical budget by skill**")
        rr = (pd.DataFrame([{"Skill": s, "Budget": b} for s, b in priced])
              .sort_values("Budget", ascending=False).head(8))
        hbar_chart(list(rr.itertuples(index=False, name=None)), "#4C8DFF",
                  fmt=lambda v: f"${v:,.0f}")

    st.write("")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Budget mix** — how the board splits")
        bm = df["size_tier"].value_counts()
        donut_chart([(s, int(bm.get(s, 0))) for s in ("Small", "Medium", "Large")
                    if bm.get(s, 0)], BUDGET_COLORS)
    with c4:
        # This was a "Where the gigs come from" donut, which put every board we
        # read on screen with its share of the pie — a labelled map of exactly
        # where to go instead of us. Same rule that took the sources out of the
        # FAQ and the landing page (FEEL.md §7): the feed is the product,
        # provenance is plumbing. Urgency is the thing a freelancer can act on.
        st.markdown("**How fast you need to move**")
        urg = df["urgency"].fillna("").replace("", "Standard").value_counts()
        donut_chart([(p, int(urg.get(p, 0))) for p in ("Standard", "Urgent")
                    if urg.get(p, 0)],
                   {"Standard": "#4C8DFF", "Urgent": "#E96250"})

    st.write("")
    st.markdown("**Where the big budgets sit** — gigs by skill, split by budget")
    top_skills = df["job_type"].value_counts().head(8).index.tolist()
    sk = (df[df["job_type"].isin(top_skills)]
          .groupby(["job_type", "size_tier"]).size())
    stacked_hbar_chart(top_skills, ["Small", "Medium", "Large"],
                      {(jt, st_): int(n) for (jt, st_), n in sk.items()},
                      BUDGET_COLORS)
    # "Ballpark — budgets blend project & hourly figures across sources" was
    # three hedges and a mention of sources in one line. This says the one
    # thing a reader needs: treat it as a range, not a quote.
    st.caption("Treat these as a range to price against, not a fixed rate — "
               "posts quote by project and by hour, and both are counted here.")


def _channel(name, blurb):
    """An alert channel's heading. The name does the work, so no icon."""
    st.markdown(f'<div class="gr-ch-h">{name}</div>'
                f'<div class="gr-ch-s">{blurb}</div>', unsafe_allow_html=True)


def chan_ready(env_key: str) -> bool:
    """
    Is this channel actually usable on this deployment?

    A channel whose server-side credentials are missing can't deliver anything,
    so we don't show it at all rather than showing it with a "not set up"
    label. Advertising a switch that cannot be flipped is worse than an absent
    one: it reads as broken product rather than as a feature we haven't
    finished wiring.
    """
    return bool(os.environ.get(env_key, "").strip())


def alerts_section(pro):
    """
    Alert channels and cadence.

    This was its own top-level tab, which put a settings screen next to the
    three tabs that actually show gigs — and its own copy pointed people back
    to Profile to turn it on. It's a section of Profile now: one place for
    everything about you and your account.
    """
    st.markdown('#### We\'ll tap you on the <span class="gr-accent">shoulder</span>',
                unsafe_allow_html=True)
    if not pro:
        st.caption("A **Pro** perk. The moment a gig that fits you lands, we'll ping "
                   "you — so you're first to reply.")
        return
    st.caption("The faster you hear, the more you win. Switch on as many as you like — "
               "we hit every one the second a gig fits you.")
    p = alerts.load_prefs()

    # Only the channels this deployment can actually deliver on. SMS needs
    # Twilio keys, email needs SMTP, and the desktop pop-up only exists when
    # the local watcher is running — none of which a visitor can do anything
    # about, so a row of "not set up" chips was just telling people about
    # things that don't work. The status chips are gone with them: a field you
    # filled in is self-evidently filled in.
    sms = ntfy = webhook = tg_token = tg_chat = ""
    live = []
    if alerts.sms_ready():
        live.append("sms")
    live += ["ntfy", "chat"]          # ntfy and webhooks need nothing server-side

    _slots = [c for c in live]
    _cols = st.columns(2)
    _i = 0

    def _next_col():
        nonlocal _i
        col = _cols[_i % 2]
        _i += 1
        return col

    if "sms" in _slots:
        with _next_col():
            with st.container(border=True):
                _channel("Text message",
                         "A text the second a gig fits you. The only channel that reaches "
                         "you with no app open and the phone in your pocket.")
                sms = st.text_input("Mobile number", value=p.get("sms_to", ""),
                                    placeholder="+15551234567",
                                    label_visibility="collapsed")
                if sms.strip() and not alerts.valid_phone(sms):
                    st.caption("Use the +15551234567 format.")
    with _next_col():
        with st.container(border=True):
            _channel("Phone push",
                     "Free and instant, and it fires even with the site closed. Install "
                     "the ntfy app and subscribe to this exact topic.")
            ntfy = st.text_input("ntfy topic", value=p.get("ntfy_topic", ""),
                                 placeholder="a private topic, e.g. nabbly-alex-9f2",
                                 label_visibility="collapsed")
    with _next_col():
        with st.container(border=True):
            _channel("Discord or Slack",
                     "Drops matching gigs straight into a channel. Paste a webhook URL, "
                     "no password needed.")
            webhook = st.text_input("Webhook URL", value=p.get("discord_webhook", ""),
                                    label_visibility="collapsed",
                                    placeholder="paste your webhook URL")
    with _next_col():
        with st.container(border=True):
            _channel("Telegram",
                     "Message a bot you own. Create one with @BotFather, then paste its "
                     "token and your chat id.")
            tg_token = st.text_input("Bot token", value=p.get("telegram_token", ""),
                                     label_visibility="collapsed",
                                     placeholder="bot token")
            tg_chat = st.text_input("Chat ID", value=p.get("telegram_chat", ""),
                                    label_visibility="collapsed", placeholder="chat id")

    st.markdown("#### How often, and how many")
    st.caption("The difference between an edge and a nuisance. Start calm — you can "
               "always turn it up.")
    h1, h2, h3 = st.columns(3)
    with h1:
        _every_opts = {"As they land (2 min)": 2, "Every 15 minutes": 15,
                       "Every 30 minutes": 30, "Hourly": 60,
                       "Every 3 hours": 180, "Twice a day": 720, "Once a day": 1440}
        _cur = int(p.get("every_min") or 15)
        _names = list(_every_opts)
        _idx = next((i for i, k in enumerate(_names) if _every_opts[k] == _cur), 1)
        every_lbl = st.selectbox("How often at most", _names, index=_idx,
                                 help="Nabbly checks the boards every couple of minutes "
                                      "regardless. This only limits how often it pings you.")
        every_min = _every_opts[every_lbl]
    with h2:
        max_per = st.selectbox("Gigs listed per alert", [1, 3, 5, 10, 20],
                               index=[1, 3, 5, 10, 20].index(int(p.get("max_per_alert") or 5))
                               if int(p.get("max_per_alert") or 5) in (1, 3, 5, 10, 20) else 2,
                               help="Anything beyond this is still counted, and the alert "
                                    "links to the board so you can see the rest.")
    with h3:
        urgent_only = st.toggle("Only urgent gigs", value=bool(p.get("urgent_only")),
                                help="The quietest setting there is. Everything else "
                                     "still shows on the board.")

    _srcs = sorted({s for s in df["source"].unique()}) if not df.empty else []
    sources = st.multiselect(
        "Only alert me about these boards",
        _srcs, default=[s for s in (p.get("sources") or []) if s in _srcs],
        format_func=config.source_label,
        # Not blank like the others: here an empty box genuinely MEANS
        # something ("every board"), so the placeholder states it rather than
        # leaving you to guess whether the setting is off or unset.
        placeholder="Every board",
        help="Leave empty for every board. Narrowing this is the single most "
             "effective way to cut the noise.")

    crit = {"skills": prof.get("skills", []), "budgets": ["Small", "Medium", "Large"],
            "keyword": prof.get("keywords", ""), "discord_webhook": webhook.strip(),
            "ntfy_topic": ntfy.strip(), "telegram_token": tg_token.strip(),
            "telegram_chat": tg_chat.strip(), "sms_to": sms.strip(),
            "every_min": every_min, "max_per_alert": max_per,
            "urgent_only": bool(urgent_only), "sources": sources}

    cols = st.columns(2)
    with cols[0]:
        if st.button("Save my alerts", width="stretch"):
            alerts.save_prefs(crit)
            st.success("Saved — your alert preferences are set.")
    with cols[1]:
        if st.button("Send a test ping", width="stretch"):
            res = alerts.send_test(crit)
            if not res:
                st.warning("No channels are set up yet, so there was nothing to send to. "
                           "Add a phone-push topic above, or set one on the server.")
            else:
                worked = [k for k, v in res.items() if v]
                failed = [k for k, v in res.items() if not v]
                if worked:
                    st.success(f"Sent a test alert to **{', '.join(worked)}**. "
                               "It should land within a few seconds.")
                if failed:
                    st.error(f"Couldn't reach **{', '.join(failed)}**. Double-check the "
                             "topic, URL or keys for that channel.")

    st.caption("Alerts follow the skills & keywords you set above. Hit "
               "**Send a test ping** to confirm your channels are wired up.")


def resume_card():
    """
    A Pro-only nudge for better drafts: upload once, we draw on it when
    writing your reply. Session-only, on purpose — see resume.py. Nothing
    here ever calls profile_mod.save() or people.attach_profile(); the text
    lives in st.session_state and is gone when the tab closes.
    """
    st.markdown('#### Your <span class="gr-accent">resume</span>',
                unsafe_allow_html=True)
    # Names no vendor — the privacy policy still discloses the processor in
    # full, which is the right place for that. But it has to be true on ITS
    # OWN, without relying on someone having also read the policy: "used just
    # to write that one reply" went quiet on the fact that writing the reply
    # means the text leaves this server for a moment. "Processed to write your
    # reply" says that honestly without naming who does the processing.
    st.caption("Upload it once and your drafts can name real, specific work "
               "instead of reading like a form letter. **We don't store it** — "
               "processed only to write your reply, held in this browser tab, "
               "gone the moment you close it. Re-upload next time you visit.")
    up = st.file_uploader("Resume (PDF, Word, or .txt)",
                          type=["pdf", "docx", "txt"],
                          key="resume_upload", label_visibility="collapsed")
    if up is not None and up.name != st.session_state.get("_resume_name"):
        text = resume.extract_text(up)
        if text:
            st.session_state["_resume_text"] = text
            st.session_state["_resume_name"] = up.name
        else:
            st.warning("Couldn't read that file — try a text-based PDF "
                       "or Word file (not a scanned image), or a .txt instead.")
    if st.session_state.get("_resume_text"):
        words = len(st.session_state["_resume_text"].split())
        rc1, rc2 = st.columns([4, 1], vertical_alignment="center")
        rc1.caption(f"Loaded **{st.session_state.get('_resume_name', 'your resume')}** "
                    f"— about {words:,} words, held for this session only.")
        if rc2.button("Forget it", key="forget_resume", width="stretch"):
            st.session_state.pop("_resume_text", None)
            st.session_state.pop("_resume_name", None)
            st.rerun()


def inbox_card():
    """
    Someone's private forwarding address.

    The best work in a lot of fields never touches a job board — it goes out on
    a listserv or a paid newsletter that no crawler can reach. This is the way
    in: forward it once and the gigs land on your board like any other.
    """
    st.markdown('#### Forward your <span class="gr-accent">newsletters</span>',
                unsafe_allow_html=True)
    if not inbox.enabled():
        st.caption("Your own address for forwarding the mailing lists and "
                   "newsletters the job boards never see.")
        return
    if not ACCESS["signed_in"]:
        st.caption("Sign in and you'll get your own address. Forward it a "
                   "newsletter or listserv digest, and the gigs inside land "
                   "on your board — visible only to you.")
        return
    st.markdown("A lot of the best work goes out on a listserv or a paid "
                "newsletter, never a job board. Forward one here and we'll "
                "pull the gigs out of it for you.")
    st.code(inbox.address_for(ACCESS["email"]), language=None)
    mine = db.owned_posts(paths.get_scope())
    if mine:
        st.caption(f"**{len(mine)}** gig{'' if len(mine) == 1 else 's'} in from "
                   "your inbox so far, on your board only — nobody else sees them.")
    else:
        st.caption("Nothing forwarded yet. Send your next one through, or set a "
                   "rule in your mail app to forward them automatically. "
                   "Whatever arrives stays private to you.")


def _essentials_form():
    """
    The full profile form, kept for people WITHOUT an account.

    Everything on it — name, headline, skills, rate floor, keywords, location,
    portfolio, bio — is also on the board's own profile page, written to the
    same store through the same profile module. For a signed-in member that
    made two pages editing one set of settings, and only one of them was
    maintained. The board's page is now the single one.

    It survives here for guests only, and for a specific reason: the board's
    /profile answers 303 to anyone without an account, so deleting this
    outright would take away the try-before-you-sign-up path this form was
    deliberately built to be.
    """
    # Location pre-fill: detect once, the form below uses it as the default.
    geo = st.session_state.get("_geo", {})
    dcol, mcol = st.columns([1, 3], vertical_alignment="center")
    if dcol.button("Detect my location", width="stretch"):
        st.session_state["_geo"] = location.geo_from_ip()
        st.rerun()
    if geo:
        found = ", ".join(x for x in [geo.get("city"), geo.get("country")] if x)
        if found:
            mcol.markdown(f"**{found}**")
        else:
            mcol.caption("Couldn't place you automatically — just pick your country below.")

    # Everything past the three essentials lives in an optional section so a
    # fresh profile isn't a wall of ten inputs. It opens on its own for anyone
    # who already has details saved (or just detected their location), so we
    # never hide someone's own data from them.
    _has_extra = bool(geo) or any(prof.get(k) for k in
        ("rate_floor", "keywords", "mute", "portfolio", "country", "city", "bio"))

    with st.form("profile_form"):
        st.markdown("**The essentials**")
        f_name = st.text_input("Your name", value=prof.get("name", ""))
        f_headline = st.text_input("What you do", value=prof.get("headline", ""),
                                   placeholder="e.g. Brand & logo designer")
        # placeholder="" kills Streamlit's stock "Choose options" — a dropdown
        # already looks like a dropdown, so the hint was just grey noise.
        f_skills = st.multiselect("Your skills", ALL_SKILLS,
                                  default=prof.get("skills", []), placeholder="",
                                  help="The board sorts itself around these, so "
                                       "this is the one that matters most.")

        with st.expander("Fine-tune your matches   ·   optional",
                         expanded=_has_extra):
            rc1, rc2 = st.columns([2, 1])
            with rc1:
                f_floor = st.number_input("Won't work below ($)", min_value=0, step=25,
                                          value=int(prof.get("rate_floor") or 0))
            with rc2:
                f_unit = st.selectbox("per", ["hr", "project"],
                                      index=0 if prof.get("rate_unit", "hr") == "hr" else 1)
            f_keywords = st.text_input("Nudge these to the top",
                                       value=prof.get("keywords", ""),
                                       placeholder="logo, figma, brand")
            f_mute = st.text_input("Never show me", value=prof.get("mute", ""),
                                   placeholder="unpaid, commission only, crypto")
            lc1, lc2 = st.columns(2)
            with lc1:
                _country = prof.get("country") or geo.get("country") or "Other / elsewhere"
                _opts = location.COUNTRIES
                f_country = st.selectbox("Where are you based?", _opts,
                                         index=_opts.index(_country) if _country in _opts else len(_opts) - 1,
                                         help="Used to hide remote gigs locked to other regions.")
            with lc2:
                f_city = st.text_input("Your city (for local, hands-on gigs)",
                                       value=prof.get("city") or geo.get("city", ""),
                                       placeholder="e.g. Portland")
            f_relocate = st.toggle(
                "Show gigs tied to other cities",
                value=bool(prof.get("open_to_relocate")),
                help="Off by default: a gig posted as \"… in Austin, TX\" wants "
                     "someone in that metro, so it stays off your board unless "
                     "it names your city. Turn this on if you'd travel or move.")
            f_alllang = st.toggle(
                "Show gigs in other languages",
                value=bool(prof.get("show_all_languages")),
                help="Around one gig in eleven is posted in German, Dutch, "
                     "Spanish or French. English (and your country's language) "
                     "always show; this adds the rest.")
            f_portfolio = st.text_input("Where's your work?",
                                        value=prof.get("portfolio", ""),
                                        placeholder="your portfolio link")
            f_bio = st.text_area("A line about you (we'll use it in your replies)",
                                 value=prof.get("bio", ""),
                                 placeholder="10+ yrs designing brand identities for small businesses.")

        if st.form_submit_button("Save", width="stretch"):
            _saved = {
                "name": f_name.strip(), "headline": f_headline.strip(),
                "skills": f_skills, "rate_floor": f_floor, "rate_unit": f_unit,
                "keywords": f_keywords.strip(), "mute": f_mute.strip(),
                "portfolio": f_portfolio.strip(), "bio": f_bio.strip(),
                "country": f_country if f_country != "Other / elsewhere" else "",
                "city": f_city.strip(),
                "open_to_relocate": bool(f_relocate),
                "show_all_languages": bool(f_alllang),
            }
            profile_mod.save(_saved)
            # If they've signed up, keep a copy against their email, so what we
            # have is a person and their craft, not just an address.
            _who = st.session_state.get("_signed_up_email", "")
            if _who:
                people.attach_profile(_who, _saved)
            st.session_state.pop("_geo", None)
            st.session_state["_profile_saved"] = True
            st.rerun()


def view_profile(pro):
    st.markdown('### Tell us about <span class="gr-accent">you</span>',
                unsafe_allow_html=True)
    st.caption("The more we know, the better the gigs we surface for you.")

    # The jump chips were a symptom: five anchors because the page was too long
    # to scroll. A member's page is now four short cards, so there is nothing to
    # jump past. Guests still see the long form, so they still get the chips.
    if not (ACCESS["signed_in"] and BOARD_URL):
        _jumps = [("#alerts", "Alerts"), ("#forwarding", "Forwarding"),
                  ("#plan", "Plan"), ("#feedback", "Feedback")]
        st.markdown(
            '<div class="gr-jump-row">' +
            "".join(f'<a class="gr-jump" href="{h}">{t}</a>' for h, t in _jumps) +
            "</div>", unsafe_allow_html=True)
    # A flash flag, not a toast shown right before the rerun below that follows
    # a save: st.success() immediately followed by st.rerun() throws away its
    # own message before a human ever sees it — the rerun aborts THIS script
    # run and starts a fresh one where that success() line never executes
    # again. Same pattern the draft-reply "Saved" caption already uses
    # correctly (see _saved_{gid} above): set a flag, rerun, then read and
    # clear the flag on the run that actually renders.
    if st.session_state.pop("_profile_saved", False):
        st.success("Got it — we've tuned things to you.")

    # No "Signed in as …" line and no Sign out button up here: the account menu
    # in the top bar already shows both, and repeating them at the top of the
    # page pushed the actual form down for no new information. Sign out now
    # sits at the very bottom, where a destructive action belongs. The setup
    # progress bar went with them — a percentage on an optional form reads as
    # homework, and every field on it is already optional by design.
    if not ACCESS["signed_in"]:
        st.caption("We'll use this right away. Sign in from the **Dashboard** to "
                   "keep it for next time.")

    # ONE PLACE TO EDIT ONE SET OF SETTINGS. This page used to carry the whole
    # profile form and a 148-line alerts section, both writing the same stored
    # profile the board writes — not a similar one: the same module, the same
    # keys, checked field by field. The board's page is the better of the two,
    # so this points at it rather than competing with it.
    #
    # Falls back to the form if NABBLY_BOARD_URL is unset, the same way the
    # Gigs tab does. Without that guard, clearing one dashboard variable would
    # leave a member with no way to edit their profile at all.
    if ACCESS["signed_in"] and BOARD_URL:
        st.markdown("**Your feed settings live on the board**")
        st.caption("What you do, the words that lift or bury a gig, where you "
                   "are, how your replies read, and where alerts go. All on "
                   "one page there.")
        # A PLAIN ANCHOR, NOT st.link_button, WHICH ALWAYS OPENS A NEW TAB and
        # has no parameter to stop it. The board is the same product on a
        # sibling subdomain and the session cookie is scoped to .nabbly.co, so
        # opening a second tab makes an internal navigation look like leaving
        # the site — the same reasoning the Gigs tab link already carries.
        st.markdown(
            f'<a class="gr-jump gr-settings-link" href="{BOARD_URL}/profile">'
            f'Open feed settings &rarr;</a>', unsafe_allow_html=True)
    else:
        _essentials_form()

    # EVERYTHING BELOW IS ON THE BOARD NOW. Resume, forwarding, plan, the
    # sign-in link and feedback all moved there when settings became one page,
    # so for a signed-in member this page would otherwise be a second copy of
    # all of it — the exact split this was meant to close. Guests still get the
    # lot, because the board's /profile answers 303 without an account.
    if ACCESS["signed_in"] and BOARD_URL:
        return

    if pro:
        st.divider()
        st.markdown('<span id="resume" class="gr-jump-target"></span>', unsafe_allow_html=True)
        resume_card()

    if not (ACCESS["signed_in"] and BOARD_URL):
        st.divider()
        st.markdown('<span id="alerts" class="gr-jump-target"></span>',
                    unsafe_allow_html=True)
        alerts_section(pro)

    st.divider()
    st.markdown('<span id="forwarding" class="gr-jump-target"></span>', unsafe_allow_html=True)
    inbox_card()

    st.divider()
    st.markdown('<span id="plan" class="gr-jump-target"></span>', unsafe_allow_html=True)
    plan_card()

    st.divider()
    signin_link_card()

    st.divider()
    st.markdown('<span id="feedback" class="gr-jump-target"></span>', unsafe_allow_html=True)
    feedback_card("profile")

    # Sign out lives at the very bottom: it's the one destructive control on
    # the page, and nothing below it competes for the click.
    if ACCESS["signed_in"]:
        st.divider()
        _so, _ = st.columns([1, 3])
        with _so:
            if st.button("Sign out", width="stretch", key="signout"):
                # Drop our own session first, then Google's if it owns this
                # login, otherwise st.logout() reruns and we never get here.
                st.session_state.pop("_tok", None)
                st.session_state.pop("_saved_set", None)   # see ?signout= above
                st.session_state.pop("_rated", None)
                st.query_params.clear()
                if auth.google_email(st):
                    st.logout()
                st.rerun()


def alerts_offer(email: str, where: str, has_alerts: bool = False):
    """
    The cheap rung, offered exactly where somebody has just declined $15.

    The ladder was Free or Pro, so everyone who found Pro too much converted
    to nothing. This is shown after the Pro button rather than beside it: it
    is the fallback for a no, not a competing option, and putting it level
    with Pro would talk people out of the more valuable plan.

    NO PRICE IN THE LABEL. The amount lives in Stripe. A number typed here
    would be a second source of truth that disagrees silently the first time
    the price changes, and this one sits on a button that takes money.
    Checkout shows the real figure before anyone pays.

    Renders nothing at all when STRIPE_ALERTS_PRICE_ID is unset, which is how
    this ships before the price exists.
    """
    # Already on it. A lapsed trial still reads as "trialed", so without this
    # an existing alerts subscriber is shown the buy button again and Stripe
    # will happily sell them a SECOND subscription for the thing they already
    # pay for. Pro is covered separately: both call sites are unreachable
    # while pro is true.
    if has_alerts or not billing.alerts_enabled() or not email:
        return
    url = billing.checkout_url(
        email,
        success_url=f"{mailer.APP_URL}/?from={where}&stripe_session={{CHECKOUT_SESSION_ID}}&e={EMAIL_TOKEN}",
        cancel_url=f"{mailer.APP_URL}/?nav={where}&e={EMAIL_TOKEN}",
        tier="alerts")
    if not url:
        return
    st.markdown('<div class="gr-cta-fine">Not ready for Pro?</div>',
                unsafe_allow_html=True)
    st.link_button("Just the alerts \u2014 a cheaper plan", url, width="stretch")


def plan_card():
    """
    What you're on, what it costs, when it renews, and the way out.

    This was a coloured st.success/st.info banner — Streamlit's stock alert
    styling, which is the one surface on the page that ignores the house
    palette entirely. It's a real card now, and it answers the three questions
    a plan screen exists to answer (what am I on, when am I next charged, how
    do I leave) instead of only the first.
    """
    st.markdown('#### Your <span class="gr-accent">plan</span>',
                unsafe_allow_html=True)

    days = ACCESS.get("days_left") or 0
    renews = ""
    if ACCESS["pro"] and days:
        # The real deadline off the account, not now+days_left — days_left is
        # rounded up, so rebuilding the date from it overshoots by a day.
        _when = ACCESS.get("ends") or (datetime.now(timezone.utc)
                                       + timedelta(days=days))
        # Both the countdown and the date. "How long have I got" is the thing
        # people actually want off this card, and a date alone makes them work
        # it out against today's; a countdown alone is vague about which day it
        # actually stops. "Ends", never "renews": nothing is charged today, and
        # implying a billing date we don't have would be the kind of claim
        # FEEL.md §7 exists to prevent.
        _left = "1 day left" if days == 1 else f"{days} days left"
        renews = f"{_left} · ends {_when.strftime('%-d %B %Y')}"

    if ACCESS["plan"] == "pro" and not days and ACCESS.get("paid"):
        name, price, note = ("Pro", "$15/mo",
                             "Renews automatically. Cancel anytime.")
    elif ACCESS["plan"] == "pro" and not days:
        name, price, note = "Pro", "On the house", "Thanks for backing us."
    elif ACCESS["pro"] and ACCESS.get("founding"):
        # The badge itself lives in the account menu only (see
        # founding_badge_html) — this card says the same thing in plain
        # text rather than repeating the graphic a second time on the same
        # page load.
        # NOT "60 days" as a constant. A founding member who buys the Alerts
        # tier has that window cut to accounts.FOUNDING_DAYS_ALERTS, so the
        # hardcoded number promised twice what some of them actually have.
        # days_left is the real remaining figure, already rounded up by
        # accounts.status.
        _d = ACCESS.get("days_left") or 0
        if ACCESS.get("plan") == accounts.ALERTS_PLAN:
            name = "Pro · founding member, on Alerts"
            price = f"Pro free for {_d} more day{'s' if _d != 1 else ''}"
            note = ("Your $5 Alerts plan carries on after that. "
                    "Upgrade any time to keep the rest.")
        else:
            name = "Pro · founding member"
            price = (f"Free for {_d} more day{'s' if _d != 1 else ''}" if _d
                     else "Free while your founding window runs")
            note = "Our thank-you to the people who backed it first."
    elif ACCESS["pro"]:
        name, price, note = ("Pro · trial", "Free for 14 days",
                             "You drop back to Free when it ends, not charged.")
    elif ACCESS.get("alerts"):
        # Paying, but not for Pro. Falling through to the Free card below told
        # a subscriber they were on the free plan.
        name, price, note = ("Alerts", "Instant pings",
                             "Cancel anytime. Upgrade to Pro whenever you want "
                             "the rest.")
    else:
        name, price, note = ("Free", "$0 — the whole board",
                             "Every gig, every field, search and browse.")

    # Plays once — the render right after Stripe redirects back. Every render
    # after that (this session or a future visit) is the plain card below.
    _activated = st.session_state.pop("_pro_activated", False) and ACCESS.get("paid")

    if _activated:
        st.markdown(
            f'<div class="gr-plan gr-plan-anim">'
            f'<div class="gr-plan-top">'
            f'<div><div class="gr-plan-name">{html.escape(name)}</div>'
            f'<div class="gr-plan-note">{html.escape(note)}</div></div>'
            f'<div class="gr-plan-price">{html.escape(price)}'
            + (f'<span>{html.escape(renews)}</span>' if renews else "")
            + '</div></div>'
            '<div class="gr-unlocks">'
            '<div class="gr-unlock"><span class="gr-tick">✓</span>Ranked picks</div>'
            '<div class="gr-unlock"><span class="gr-tick">✓</span>Post-aware drafts</div>'
            '<div class="gr-unlock"><span class="gr-tick">✓</span>Instant alerts</div>'
            '<div class="gr-unlock"><span class="gr-tick">✓</span>Market rates</div>'
            '</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="gr-plan">'
            f'<div class="gr-plan-top">'
            f'<div><div class="gr-plan-name">{html.escape(name)}</div>'
            f'<div class="gr-plan-note">{html.escape(note)}</div></div>'
            f'<div class="gr-plan-price">{html.escape(price)}'
            + (f'<span>{html.escape(renews)}</span>' if renews else "")
            + '</div></div></div>', unsafe_allow_html=True)

    if not ACCESS["pro"]:
        st.caption("**Pro** adds instant pings, post-aware drafts, picks ranked for "
                   "you, and what-it-pays market rates.")
        if ACCESS.get("can_trial"):
            if st.button("Try Pro free for 14 days", type="primary", key="trial_profile"):
                ok, msg = accounts.start_trial(ACCESS["email"])
                if ok:
                    st.rerun()
                st.warning(msg)
        elif ACCESS.get("trialed"):
            if billing.enabled():
                _url = billing.checkout_url(
                    ACCESS["email"],
                    success_url=f"{mailer.APP_URL}/?from=profile&stripe_session={{CHECKOUT_SESSION_ID}}&e={EMAIL_TOKEN}",
                    cancel_url=f"{mailer.APP_URL}/?nav=profile&e={EMAIL_TOKEN}")
                if _url:
                    st.link_button("Upgrade to Pro — $15/mo", _url,
                                   type="primary", width="stretch")
                else:
                    st.warning("Checkout's briefly unavailable — try again in a moment.")
            else:
                st.caption("Your 14-day Pro trial has been used. We'll email you "
                           "the moment paid Pro opens.")
        # OUTSIDE the if/elif, so it reaches BOTH branches. It used to sit in
        # the lapsed-trial arm only, which meant somebody who had never started
        # a trial was shown "Try Pro free" and never learned the cheap tier
        # existed — the people most likely to want it were the only ones who
        # could not see it.
        alerts_offer(ACCESS["email"], "profile", ACCESS.get("alerts", False))
        return

    # The way out. Owner accounts are permanently Pro (accounts.status), so
    # there's nothing to downgrade and the control would do nothing.
    if not accounts.is_owner(ACCESS.get("email")):
        _dg_cls = "gr-downgrade-mark anim" if _activated else "gr-downgrade-mark"
        st.markdown(f'<span class="{_dg_cls}"></span>', unsafe_allow_html=True)
        if st.button("Switch to Free", key="downgrade"):
            st.session_state["_confirm_downgrade"] = True
        if st.session_state.get("_confirm_downgrade"):
            st.caption("You'll keep the whole board, search and your profile. "
                       "You'd lose ranked picks, post-aware drafts, market rates "
                       "and instant alerts.")
            _c1, _c2, _ = st.columns([1, 1, 2])
            with _c1:
                if st.button("Yes, switch", key="downgrade_yes", width="stretch"):
                    accounts.downgrade(ACCESS["email"])
                    st.session_state.pop("_confirm_downgrade", None)
                    st.rerun()
            with _c2:
                if st.button("Keep Pro", key="downgrade_no", width="stretch"):
                    st.session_state.pop("_confirm_downgrade", None)
                    st.rerun()


def _send_signin_code(email: str) -> tuple[bool, str]:
    """Mint a code and mail it. Returns (ok, message)."""
    code, err = accounts.issue_code(email)
    if err:
        return False, err
    subject, html_body, text_body = mailer.signin_code_email(code)
    if not mailer.send(email.strip().lower(), subject, html_body, text_body):
        # Never leave someone staring at a code entry box for an email that
        # was never sent.
        return False, "We couldn't send that email. Try again in a minute."
    return True, ""


def _signin_email_step():
    st.markdown('<span class="gr-cta-mark"></span>'
                '<div class="gr-cta-h">Welcome</div>'
                '<div class="gr-cta-s">Your board, saved and sorted to you.'
                '</div>', unsafe_allow_html=True)
    if not mailer.enabled():
        # Without mail there is no way to prove the address, and signing
        # someone in on an unverified address is the exact hole this replaced.
        st.warning("Email sign-in isn't available right now."
                   + (" Use Google below." if auth.enabled() else ""))
    else:
        with st.form("signin_page_form", clear_on_submit=False, border=False):
            email = st.text_input("Email", placeholder="you@example.com",
                                  label_visibility="collapsed")
            sent = st.form_submit_button("Email me a code", type="primary",
                                         width="stretch")
        if sent:
            ok, msg = _send_signin_code(email)
            if ok:
                st.session_state["_code_email"] = email.strip().lower()
                st.rerun()
            st.warning(msg)
        st.markdown('<div class="gr-cta-fine">Works with any email · we send a '
                    'six digit code, no password to remember</div>',
                    unsafe_allow_html=True)


def _signin_code_step(email: str):
    st.markdown('<span class="gr-cta-mark"></span>'
                '<div class="gr-cta-h">Check your email</div>'
                f'<div class="gr-cta-s">We sent a six digit code to '
                f'<b>{html.escape(email)}</b>.</div>', unsafe_allow_html=True)
    with st.form("signin_code_form", clear_on_submit=False, border=False):
        code = st.text_input("Code", placeholder="123456",
                             label_visibility="collapsed", max_chars=6)
        ok_click = st.form_submit_button("Sign in", type="primary", width="stretch")
    if ok_click:
        ok, err = accounts.check_code(email, code)
        if ok:
            # Only NOW does the account get created or resolved. Before the
            # code is proven there is deliberately no account touched at all.
            good, msg = sign_in_here(email, "signin")
            if good:
                st.session_state.pop("_code_email", None)
                # Straight to the board — see the note in sign_in_here. The tab
                # index is set directly rather than via ?nav= because the ?nav
                # dispatch clears the query string, which would wipe the ?u=
                # token that keeps them signed in.
                st.session_state["_navidx"] = 0      # Dashboard
                st.session_state["_page"] = ""
                st.rerun()
            st.warning(msg)
        else:
            st.warning(err)
    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("Send a new code", width="stretch", key="resend_code"):
            ok, msg = _send_signin_code(email)
            st.warning(msg if not ok else "New code sent.")
    with _c2:
        if st.button("Use a different email", width="stretch", key="change_email"):
            st.session_state.pop("_code_email", None)
            st.rerun()


def signin_link_card():
    """
    The passwordless answer to "reset my password".

    There is no password on a Nabbly account — being signed in IS holding the
    token in your address bar. So the honest version of a password reset is
    "put that link somewhere I can get to it from my phone", which is this.
    Says so plainly rather than borrowing the words of a password flow that
    doesn't exist here, because a "Reset password" button that resets nothing
    is worse than no button.
    """
    st.markdown('#### Getting back <span class="gr-accent">in</span>',
                unsafe_allow_html=True)
    if not ACCESS["signed_in"]:
        st.caption("Sign in first and you can send yourself a link from here.")
        return
    st.caption("There's no password on your account. The link in your address "
               "bar is what signs you in, so here's a copy for your inbox, for "
               "a new phone or a different browser.")
    if not mailer.enabled():
        # Never claim to have sent something we structurally cannot send.
        st.caption("Email isn't switched on for this site yet.")
        return
    _l, _c, _r = st.columns([1, 1.6, 1])
    with _c:
        if st.button("Email me my sign-in link", width="stretch",
                     key="send_signin_link"):
            subject, html_body, text_body = mailer.signin_link_email(
                (prof.get("name") or "").strip(), ACCOUNT["token"])
            if mailer.send(ACCESS["email"], subject, html_body, text_body):
                st.session_state["_signin_link_sent"] = True
            else:
                st.session_state["_signin_link_sent"] = False
            st.rerun()
    _sent = st.session_state.get("_signin_link_sent")
    if _sent is True:
        st.markdown(
            f'<div class="gr-confirm"><span class="gr-confirm-dot"></span>'
            f'<span class="gr-confirm-txt">Sent to '
            f'<b>{html.escape(ACCESS["email"] or "")}</b>. Check your inbox.'
            f'</span></div>', unsafe_allow_html=True)
    elif _sent is False:
        st.warning("That didn't send. Try again in a minute.")


# ---------------------------------------------------------------------------
# Early access: an email, then the only question that really matters
# ---------------------------------------------------------------------------
def sign_in_here(email: str, where: str):
    """
    Sign someone in and put their token in the URL. Lands them on Free.

    The token in the address bar is what makes them the same person tomorrow.
    We tell them to keep the link rather than pretending a cookie will hold.
    Starting Pro is a separate, deliberate choice (accounts.start_trial), so
    signing in never drops anyone into a trial they didn't ask for.
    """
    try:
        acc, is_new = accounts.sign_in(email, source=where, campaign=CAMPAIGN)
    except accounts.StoreUnavailable:
        # Their address was fine; we just couldn't write it down this second.
        # Saying so plainly beats "that doesn't look like an email address",
        # which would send someone off retyping a perfectly good address.
        return False, "We couldn't reach your account just then. Try once more."
    if not acc:
        return False, "That doesn't look like an email address."
    st.session_state["_tok"] = acc["token"]
    st.query_params["u"] = acc["token"]
    # Whoever this session was a moment ago, it isn't them now — drop anything
    # cached against the old identity. Critically this includes the saved set:
    # the nav badge calls saved_ids() on EVERY render including signed-out
    # ones, so by the time someone finishes signing in it has already cached
    # []. Leaving it means their stars all render hollow, and clicking one on
    # a gig they had genuinely saved reads the real store and TOGGLES IT OFF —
    # they press save and it silently deletes. Exactly the path anyone who
    # lost their link and signed in again would take.
    st.session_state.pop("_saved_set", None)
    st.session_state.pop("_rated", None)
    note("signup" if is_new else "signin", where)
    return True, ""


_FEAT = ('<div class="gr-feat"><span>Ranked picks</span><span>Post-aware drafts</span>'
         '<span>Market rates</span><span>Instant alerts</span></div>')


def signup_card(where="dashboard"):
    """
    The sign-in / trial / upgrade card. One cohesive, on-brand block whose look
    adapts to where the person is: not signed in (sign in, free), signed in on
    Free (an optional Pro trial they can start), on a trial (a quiet day-count
    plus the one willingness-to-pay question), or trial over (a clean Pro
    upsell). Pro members see nothing here; there's nothing to sell them.
    """
    a = ACCESS
    # On Pricing, the Free/Pro comparison lists just rendered a few pixels
    # above this card — repeating the same four items here as a pill row
    # read as the same sentence twice. Everywhere else (Dashboard etc.) this
    # is the first and only place someone sees the Pro feature list, so it
    # stays.
    _feat_html = "" if where == "pricing" else _FEAT
    if a["signed_in"] and a["plan"] == "pro":
        if st.session_state.pop("_pro_activated", False):
            st.markdown(
                '<div class="gr-confirm"><span class="gr-confirm-dot"></span>'
                '<span class="gr-confirm-txt">You\'re on <b>Pro</b>. Ranked picks, '
                'post-aware drafts and instant alerts are all live now.</span></div>',
                unsafe_allow_html=True)
        return

    # On an active trial: they already have everything, so no hard sell. Ask the
    # single research question once, then just show days remaining, quietly.
    if a["signed_in"] and a["pro"]:
        if not st.session_state.get("_pay_answered"):
            with st.container(border=True):
                st.markdown(
                    '<span class="gr-cta-mark"></span>'
                    '<div class="gr-cta-h">Quick one while you\'re here</div>'
                    '<div class="gr-cta-s">When your Pro ends, would you pay '
                    '<b>$15/mo</b> to keep ranked picks, post-aware drafts and '
                    'instant alerts?</div>', unsafe_allow_html=True)
                a1, a2, a3 = st.columns(3)
                for col, label, val in ((a1, "Yes", "yes"), (a2, "Maybe", "maybe"),
                                        (a3, "No", "no")):
                    with col:
                        if st.button(label, key=f"pay_{val}_{where}",
                                     width="stretch"):
                            people.set_pay(a["email"], val)
                            st.session_state["_pay_answered"] = True
                            note("click", f"pay:{val}")
                            st.rerun()
        else:
            d = a["days_left"]
            _lbl = "of founding Pro left" if a.get("founding") else "of Pro left on your trial"
            st.markdown(f'<div class="gr-mini"><b>{d} day{"s" if d != 1 else ""}</b> '
                        f'{_lbl}</div>', unsafe_allow_html=True)
        return

    # Signed in, on Free, never trialed: offer Pro as a choice, not a default.
    # Low-key — one button, no countdown, and an explicit "keep browsing free".
    if a["signed_in"] and a.get("can_trial"):
        with st.container(border=True):
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Want to try Pro?</div>'
                        f'{_feat_html}'
                        '<div class="gr-cta-s">Free for 14 days, whenever you like. '
                        'No card, nothing charged, and you drop back to Free on your '
                        'own if you don\'t upgrade.</div>', unsafe_allow_html=True)
            _t1, _t2, _t3 = st.columns([1, 2, 1])
            with _t2:
                if st.button("Try Pro free for 14 days", type="primary",
                             width="stretch", key=f"trial_{where}"):
                    ok, msg = accounts.start_trial(a["email"])
                    if ok:
                        note("click", f"trial_start:{where}")
                        st.rerun()
                    else:
                        st.warning(msg)
            st.markdown('<div class="gr-cta-fine">Or keep browsing on Free — the '
                        'whole board is yours either way</div>', unsafe_allow_html=True)
            # Under the trial offer, not beside it: the free trial is still the
            # better first step, and this is the answer for someone who has
            # already decided they do not want the whole thing.
            alerts_offer(a["email"], where, a.get("alerts", False))
        return

    # Signed in with a lapsed trial → keep-Pro interest. Not signed in → sign in
    # (which lands on Free; the trial above is where Pro gets chosen).
    signed = a["signed_in"]
    with st.container(border=True):
        if signed:
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Keep Pro after your trial</div>'
                        f'{_feat_html}', unsafe_allow_html=True)
            if billing.enabled():
                _u1, _u2, _u3 = st.columns([1, 2, 1])
                with _u2:
                    _url = billing.checkout_url(
                        a["email"],
                        success_url=f"{mailer.APP_URL}/?from={where}&stripe_session={{CHECKOUT_SESSION_ID}}&e={EMAIL_TOKEN}",
                        cancel_url=f"{mailer.APP_URL}/?nav={where}&e={EMAIL_TOKEN}")
                    if _url:
                        st.link_button("Upgrade to Pro — $15/mo", _url,
                                       type="primary", width="stretch")
                    else:
                        st.caption("Checkout's briefly unavailable — try again "
                                   "in a moment.")
                st.markdown('<div class="gr-cta-fine">Cancel any time from your '
                            'plan page</div>', unsafe_allow_html=True)
                alerts_offer(a["email"], where, a.get("alerts", False))
            # Billing not configured (e.g. local dev): fall back to recording
            # interest so the ask still means something.
            elif st.session_state.get("_upgrade_noted"):
                st.markdown('<div class="gr-mini">Noted — we\'ll email you the '
                            'moment Pro opens. <b>Thanks.</b></div>',
                            unsafe_allow_html=True)
            else:
                _u1, _u2, _u3 = st.columns([1, 2, 1])
                with _u2:
                    if st.button("I want Pro", type="primary",
                                 width="stretch", key=f"up_{where}"):
                        people.set_pay(a["email"], "yes")
                        st.session_state["_upgrade_noted"] = True
                        note("click", f"upgrade:{where}")
                        st.rerun()
                st.markdown('<div class="gr-cta-fine">$15/mo when it launches · '
                            'nothing charged now</div>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Sign in to save your board</div>'
                        '<div class="gr-cta-s">Keeps your profile and picks for next '
                        'time. No cost to sign in, and Pro\'s there to try whenever '
                        'you\'re ready.</div>', unsafe_allow_html=True)
            # Email first — any provider, their choice — with Google as a
            # one-tap option beneath when it's configured.
            with st.form(f"signup_{where}", clear_on_submit=False, border=False):
                c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
                with c1:
                    email = st.text_input("Email", placeholder="you@example.com",
                                          label_visibility="collapsed")
                with c2:
                    sent = st.form_submit_button("Send code", type="primary",
                                                 width="stretch")
            if sent:
                # Goes through the emailed code like every other door. This card
                # used to call sign_in_here() straight from the address, which
                # would have left the impersonation hole wide open on the busiest
                # surface in the app while the sign-in page was locked down.
                # Hands off to the sign-in page for the code step rather than
                # growing a second code UI here.
                ok, msg = _send_signin_code(email)
                if ok:
                    st.session_state["_code_email"] = email.strip().lower()
                    st.session_state["_page"] = "signin"
                    st.rerun()
                st.warning(msg)
            if auth.enabled():
                _g1, _g2, _g3 = st.columns([1, 2, 1])
                with _g2:
                    if st.button("Continue with Google", width="stretch",
                                 key=f"goog_{where}"):
                        note("click", f"google:{where}")
                        st.login("google")
            st.markdown('<div class="gr-cta-fine">No card · no password · any '
                        'email works</div>', unsafe_allow_html=True)


@st.dialog("Never start from a blank page")
def upgrade_dialog(where: str, hook: str = "Pro drafts every reply for you."):
    """
    The soft nudge: opened by an explicit click on a real, working button
    ("See what Pro unlocks" and the like) — never shown unprompted, so it
    never reads as a paywall jumping out at someone. One short benefit line
    up top, then signup_card underneath for the actual ask: same copy, same
    real actions (start a trial, register interest, sign in) as everywhere
    else that card lives, so wiring this onto a new page is one call, not a
    new pitch to write and keep in sync.

    First cut led with a full paragraph explaining the mechanism on top of
    signup_card's own headline and subtext — two pitches stacked in one
    modal. Cut to a single line on purpose, closer to how Linear or
    Superhuman's own upgrade prompts read: say the benefit once, briefly,
    and get out of the way.

    `hook` defaults to the generic line but the draft touchpoints pass
    pitch.free_draft_note(gig) instead — this used to sit as a permanent
    caption under every single draft on the page, which got noisy across a
    results page of cards. The specific, per-gig reasoning is worth more at
    the one moment someone's actually asking what Pro does than as
    something everyone scrolls past on every card.
    """
    st.markdown(
        f'<div class="gr-updialog-hook">{hook}</div>',
        unsafe_allow_html=True)
    signup_card(where)


def view_legal(which: str):
    """
    The privacy policy or the terms.

    Rendered through legal.to_html() into the shared .gr-doc treatment — the
    same column width, colours and rhythm as About and FAQ — rather than as raw
    Streamlit markdown, which made these two pages look like a different site.
    """
    body = legal.PRIVACY if which == "privacy" else legal.TERMS
    title = "Privacy Policy" if which == "privacy" else "Terms of Service"
    # The source starts with its own "## Title" and a "Last updated" line; both
    # are re-set here as the page header, so drop them from the body.
    trimmed = "\n".join(
        ln for ln in body.strip().splitlines()
        if not ln.startswith("## ") and not ln.startswith("**Last updated"))
    st.markdown(
        f'<div class="gr-doc">'
        f'<div class="gr-doc-title">{title}</div>'
        f'<div class="gr-doc-sub">Last updated {legal.UPDATED}</div>'
        f'{legal.to_html(trimmed)}'
        f'</div>', unsafe_allow_html=True)
    st.divider()
    _b1, _b2, _b3 = st.columns([1, 1.4, 1])
    with _b2:
        if st.button("← Back to the board", width="stretch", key=f"back_{which}"):
            st.query_params["nav"] = "dashboard"
            st.rerun()


def view_unsubscribe():
    """
    One click, no sign-in needed — same token-in-URL model as everywhere else
    in the app. Reached from the unsubscribe link at the bottom of every
    email (mailer.py's _shell()). Turns off ALL email for the account, not
    just whichever one carried the link — see accounts.unsubscribe()'s note
    on why there's one opt-out, not one per email type.
    """
    import accounts
    token = st.session_state.get("_unsub_token", "")
    ok = bool(token) and accounts.unsubscribe(token)
    st.markdown('### You\'re <span class="gr-accent">unsubscribed</span>'
                if ok else
                '### That link didn\'t <span class="gr-accent">work</span>',
                unsafe_allow_html=True)
    if ok:
        st.markdown(
            '<div class="gr-confirm"><span class="gr-confirm-dot"></span>'
            '<span class="gr-confirm-txt">You won\'t get the welcome email or '
            'the weekly digest again. The board itself is still there '
            'whenever you want it.</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<p class="gr-doc-sub">This link has expired or isn\'t valid. '
            'If you\'re still getting email you don\'t want, the feedback '
            'box on your profile goes straight to us and we\'ll take care '
            'of it by hand.</p>',
            unsafe_allow_html=True)
    st.write("")
    _b1, _b2, _b3 = st.columns([1, 1.4, 1])
    with _b2:
        if st.button("← Back to the board", width="stretch", key="back_unsub"):
            st.query_params["nav"] = "dashboard"
            st.rerun()


def view_signin():
    """
    A focused sign-in page. The account menu's "Sign in" used to point at the
    dashboard, where the actual sign-in card sits far down the page — so it read
    as "nothing happened, back to home". This gives the click a real destination.
    """
    if ACCESS["signed_in"]:
        # Nothing to show someone who is already signed in — the account menu
        # in the header already says who they are. Land them on the board
        # instead of a page whose only content is a fact they know and a
        # button to leave it.
        st.session_state["_navidx"] = 0          # Dashboard
        st.session_state["_page"] = ""
        st.rerun()

    st.markdown('### Sign in to <span class="gr-accent">Nabbly</span>',
                unsafe_allow_html=True)
    st.caption("Save your profile and picks, get alerts, and keep your board "
               "across visits. No password.")
    _l, _c, _r = st.columns([1, 2, 1])
    with _c:
        with st.container(border=True):
            # Two steps: address, then the code we mail to it. The second step
            # is the whole point — typing an address used to be enough to BE
            # that person, so the only thing standing between a stranger and
            # someone's profile, drafts and resume was knowing their email.
            _pending = st.session_state.get("_code_email", "")
            if _pending:
                _signin_code_step(_pending)
            else:
                _signin_email_step()
            if auth.enabled():
                st.markdown('<div class="gr-or"><span>or</span></div>',
                            unsafe_allow_html=True)
                if st.button("Continue with Google", width="stretch",
                             key="signin_google"):
                    note("click", "google:signin")
                    st.login("google")
                st.markdown('<div class="gr-cta-fine">We only see your email &amp; '
                            'name</div>', unsafe_allow_html=True)


def view_about():
    """
    The company story, moved off the front page so the hero can stay a headline.

    This is where the "freelancing's enough of a hustle" explanation lives now,
    told properly: the problem and how Nabbly works. The Free/Pro breakdown
    used to live here too, as two cards in the middle of a story someone reads
    top to bottom — fine the first time, useless the second time they come
    back just to check what Pro includes. That comparison is its own page now
    (view_pricing) and this just points there.
    """
    st.markdown(
        '<div class="gr-about">'
        '<h2>The fastest reply usually wins.</h2>'
        '<p class="lead">Freelancing is enough of a hustle without refreshing ten '
        'job boards all day. The work is out there, scattered across boards, '
        'subreddits and communities, and the person who answers a good post '
        '<b>first</b> is usually the one who gets it.</p>'

        '<p>So Nabbly watches all of it for you, around the clock, and puts every '
        'gig in one place the moment it drops, from a quick $20 task to a full '
        'project. No more tab-hopping, no more finding the perfect job a day '
        'after it was filled.</p>'

        '<h2>How it works</h2>'
        '<ol>'
        '<li>We <b>watch every board and community</b> continuously, so you '
        'don\'t have to keep a single tab open.</li>'
        '<li>Each gig is <b>sorted by skill, budget and urgency</b>, then matched '
        'against what you do, so your board is yours.</li>'
        '<li>When something fits, you get an <b>instant alert</b> on whichever '
        'channel you like, before the crowd shows up.</li>'
        '<li>We even <b>draft the first reply</b> for you, so you answer in '
        'seconds instead of staring at a blank message — from the actual '
        'post on Pro, from a smart template on Free.</li>'
        '</ol>'

        '<p>Every gig, every field, is free to search and browse forever — no '
        f'catch. <a class="gr-about-link" href="{ilink("?nav=pricing")}" '
        'target="_self">See the full Free vs. Pro breakdown →</a></p>'

        # Was "built in the open by one person … goes straight to them" — third
        # person about ourselves, which reads oddly and ages badly the moment
        # anyone else joins.
        '<h2>Where we\'re headed</h2>'
        '<p>We built Nabbly because we were tired of losing good work to '
        'whoever happened to be online at the right minute. It\'s early, and '
        'we\'d rather ship it and hear from you than polish it in private. If '
        'something\'s missing, wrong, or just annoying, tell us straight — the '
        'feedback box on your profile comes to us, and we read all of it.</p>'
        '</div>', unsafe_allow_html=True)

    _b1, _b2, _b3 = st.columns([1, 1.4, 1])
    with _b2:
        if st.button("← Back to the board", width="stretch"):
            st.query_params["nav"] = "dashboard"
            st.rerun()


def view_pricing():
    """
    Free vs. Pro, on its own page.

    Used to be two cards in the middle of the About page's story — fine for a
    first read, but anyone coming back later just to check what Pro includes
    had to skim a whole company narrative to find two <ul>s. This is that
    comparison alone, plus the actual next step (signup_card), since knowing
    the difference and doing something about it belong on the same screen.
    """
    st.markdown(
        '<div class="gr-about">'
        '<h2>Free, and Pro</h2>'
        '<p class="lead">Everyone gets the whole board, free, forever. Pro gets '
        'you there first — ranked picks, faster drafts, real-time alerts. No '
        'seats, no contracts.</p>'

        '<div class="gr-ab-plans">'
        '<div class="gr-ab-plan">'
        '<div class="gr-ab-name">Free</div>'
        '<div class="gr-ab-sub">The whole board, no catch</div>'
        '<ul>'
        '<li>Every gig, every field</li>'
        '<li>Search and browse it all</li>'
        '<li>Your profile, so the board sorts around you</li>'
        '<li>Fresh gigs, minutes after they\'re posted</li>'
        '<li>A drafted reply on every gig, ready to edit</li>'
        '<li>Forward newsletters into your private board</li>'
        '</ul></div>'
        '<div class="gr-ab-plan pro">'
        '<div class="gr-ab-name">Pro</div>'
        '<div class="gr-ab-sub">The edge that helps you reply first</div>'
        '<ul>'
        '<li>Gigs ranked by how well they fit you</li>'
        '<li>Post-aware drafts, written from the actual post</li>'
        '<li>Instant alerts on the channel you choose</li>'
        '<li>Market rates, so you price right</li>'
        '</ul></div>'
        '</div>'
        '<p>The first 50 members get two months of Pro free, our thank-you to '
        'the people who back it first. After that, Pro is free to try for 14 '
        'days whenever you want it, and you choose if and when to start.</p>'
        '</div>', unsafe_allow_html=True)

    _l, _c, _r = st.columns([1, 2, 1])
    with _c:
        signup_card("pricing")

    _b1, _b2, _b3 = st.columns([1, 1.4, 1])
    with _b2:
        if st.button("← Back to the board", width="stretch", key="pricing_back"):
            st.query_params["nav"] = "dashboard"
            st.rerun()


# Imported, not defined here. Two hand-kept copies of this text drifted:
# this one still named every source we read long after that was removed
# from the marketing site, and still said the first reply wins. See
# content.py.
_FAQ = content.FAQ



def view_faq():
    """Common questions, in their own place rather than cluttering the board."""
    with st.container():
        st.markdown('<span class="gr-faq-mark"></span>'
                    '<div class="gr-about"><h2>Questions, answered.</h2></div>',
                    unsafe_allow_html=True)
        for q, a in _FAQ:
            with st.expander(q):
                st.markdown(f'<div class="gr-faq-a">{a}</div>',
                            unsafe_allow_html=True)
        _b1, _b2, _b3 = st.columns([1, 1.4, 1])
        with _b2:
            if st.button("← Back to the board", width="stretch", key="faqback"):
                st.query_params["nav"] = "dashboard"
                st.rerun()


def feedback_card(where="dashboard"):
    """
    Ask what's wrong with it.

    Deliberately never asks for an email first: gating feedback on a signup is
    how you end up hearing only from the people who already liked it.
    """
    if st.session_state.get(f"_fb_sent_{where}"):
        st.markdown('<div class="gr-mini">Got it, thank you ✓ &nbsp; This goes '
                    'straight to the person building it.</div>',
                    unsafe_allow_html=True)
        return

    with st.container(border=True):
        st.markdown(
            '<span class="gr-fb-mark"></span>'
            '<div class="gr-cta-h">What would make this better?</div>'
            '<div class="gr-cta-s">Not seeing the gigs you want? Wrong category? '
            'Something broken? Tell us straight, no email needed.</div>',
            unsafe_allow_html=True)
        with st.form(f"fb_{where}", clear_on_submit=False, border=False):
            msg = st.text_area("Feedback", height=90, label_visibility="collapsed",
                               placeholder="The gigs are all remote, I wanted local ones…")
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            with c1:
                rating = st.radio("How's it working?",
                                  ["Useful", "It's ok", "Not for me"],
                                  horizontal=True, label_visibility="collapsed",
                                  index=None)
            with c2:
                sent = st.form_submit_button("Send", type="primary",
                                             width="stretch")
            # Opt IN, unticked, and asked here rather than assumed later. These
            # notes are written to report that something is broken, and the FAQ
            # promises nothing is shared — so quoting one publicly is a use its
            # author never agreed to unless they say so on the spot.
            quotable = st.checkbox(
                "You can quote this on the site (first name only, no email)",
                value=False, key=f"fb_q_{where}")
        if sent:
            code = {"Useful": "good", "It's ok": "ok", "Not for me": "bad"}.get(rating, "")
            if people.add_feedback(msg, email=ACCESS.get("email", ""),
                                   rating=code, page=where, quotable=quotable):
                st.session_state[f"_fb_sent_{where}"] = True
                note("click", f"feedback:{code or 'none'}")
                st.rerun()
            st.warning("Add a line about what's not working and we'll get it.")


# ---------------------------------------------------------------------------
# Admin: who showed up. Visit ?admin=<ADMIN_KEY>  (see analytics.py)
# ---------------------------------------------------------------------------
def view_admin():
    # Same reasoning as view_market: only place besides Market that touches
    # altair, and only the founder ever opens this page.
    import altair as alt
    s = analytics.stats()
    st.markdown("## Signals")
    st.caption("Who showed up, what they opened, and who raised their hand. "
               "Only reachable with the admin key.")
    stat_cards([
        ("Visitors · all time", f"{s['sessions']:,}", "#E8933A"),
        ("Last 24 hours", f"{s['sessions_24h']:,}", "#5b9dff"),
        ("Last 7 days", f"{s['sessions_7d']:,}", "#35b37e"),
    ])

    # --- Partner links: did the collaboration actually work? ----------------
    _camp = analytics.campaign_funnel(30)
    if _camp:
        st.markdown("#### Partner links")
        st.caption("Last 30 days. Send a partner `nabbly.co/?ref=theirname` and "
                   "they show up here, with what share of them signed up.")
        _cd = pd.DataFrame(_camp)[["tag", "sessions", "signups", "rate"]]
        _cd.columns = ["Link", "Visitors", "Signups", "Signup rate"]
        _cd["Signup rate"] = _cd["Signup rate"].map(lambda v: f"{v:.1f}%")
        st.dataframe(_cd, width="stretch", hide_index=True)
    else:
        st.markdown("#### Partner links")
        st.caption("Nothing tagged yet. Give a partner a link ending "
                   "`?ref=theirname` and their traffic and signups appear here, "
                   "separated from everyone else's.")

    # --- Unmet demand: what people typed and the board barely had -----------
    _misses = analytics.search_misses(30)
    st.markdown("#### Searches that came up empty")
    if _misses:
        st.caption("Last 30 days. Someone typed this and got 2 results or "
                   "fewer — real demand the board doesn't serve well yet.")
        _md = pd.DataFrame(_misses)[["query", "n", "last_seen"]]
        _md.columns = ["Search", "Times", "Last seen"]
        st.dataframe(_md, width="stretch", hide_index=True)
    else:
        st.caption("No near-empty searches logged in the last 30 days.")

    # --- Outcomes: retired, and the history kept ----------------------------
    # The "I got hired" tap that fed these is gone, because nothing could check
    # it: anyone could press it on any gig. It was also the number most likely
    # to be quoted to a partner or a board member, which is the worst place for
    # a figure that cannot be evidenced.
    #
    # What was already recorded is still shown, clearly labelled as what it is,
    # and clearly marked as no longer growing. Deleting somebody's history to
    # tidy up a metric would be worse than the metric was.
    _out = outcomes.site_stats()
    if _out.get("wins"):
        st.markdown("#### Outcomes (retired)")
        st.caption("Self-reported by members while the \"I got hired\" tap "
                   "existed. Never verified, and no longer collected — kept "
                   "here as history, not as a number to quote.")
        _o1, _o2 = st.columns(2)
        _o1.metric("Reported landed", f"{_out['wins']:,}")
        _o2.metric("Reported value", f"${_out['total_amount']:,}")

    # --- Match quality: where the ranking is quietly wrong -------------------
    _worst = match_feedback.worst_categories(30)
    st.markdown("#### Categories with the most 👎")
    if _worst:
        st.caption("Last 30 days, net of 👍 — a category showing up here "
                   "means the fit score is ranking it wrong often enough "
                   "to be worth a look, not just one annoyed person.")
        _wd = pd.DataFrame(_worst)[["job_type", "down_n", "up_n"]]
        _wd.columns = ["Category", "👎", "👍"]
        st.dataframe(_wd, width="stretch", hide_index=True)
    else:
        st.caption("No down-votes logged in the last 30 days.")

    # --- AI spend: the one number that can cost real money ------------------
    # Drafting is the only feature billed per use, and sign-in doesn't verify
    # an address, so this is where abuse would show up first. Visible rather
    # than merely capped: a cap you can't see is a cap you find out about from
    # an invoice.
    _b = budget.today()
    _pct = min(1.0, _b["drafts"] / _b["cap"]) if _b["cap"] else 0
    st.markdown("#### AI drafts today")
    _a1, _a2, _a3 = st.columns(3)
    _a1.metric("Drafts", f"{_b['drafts']:,}", help=f"Daily cap: {_b['cap']:,}")
    _a2.metric("Accounts drafting", f"{_b['accounts']:,}")
    # Sonnet 5 at ~720 in / ~165 out per draft.
    _a3.metric("Rough cost", f"${_b['drafts'] * 0.0047:,.2f}")
    st.progress(_pct, text=f"{_b['drafts']:,} of {_b['cap']:,} daily cap")
    if _b["top"]:
        st.caption("Busiest accounts today: "
                   + " · ".join(f"`{w}` {n}" for w, n in _b["top"]))
    if _pct >= 0.8:
        st.warning("Near the daily cap. Past it, everyone falls back to the "
                   "free template until midnight UTC — check the busiest "
                   "accounts above before raising `AI_DAILY_TOTAL`.")

    # --- Traffic: where it comes from and whether it's growing ---------------
    tr = analytics.traffic_summary(30)
    st.markdown("#### Traffic")
    if tr["daily"]:
        _d = pd.DataFrame(tr["daily"])
        _d["day"] = pd.to_datetime(_d["day"])
        st.altair_chart(
            alt.Chart(_d).mark_bar(size=14, color="#E8933A", opacity=.85).encode(
                x=alt.X("day:T", title=None, axis=alt.Axis(format="%b %d", grid=False)),
                y=alt.Y("sessions:Q", title="Visitors", axis=alt.Axis(grid=True)),
                tooltip=[alt.Tooltip("day:T", title="Day"),
                         alt.Tooltip("sessions:Q", title="Visitors")],
            ).properties(height=170),
            width="stretch")
        st.caption(f"{tr['total_sessions']:,} visitors over {tr['days_kept']} "
                   f"day(s) of history.")
    else:
        st.caption("No traffic recorded yet.")

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**Where they came from**")
        if tr["refs"]:
            st.dataframe(pd.DataFrame(tr["refs"], columns=["Source", "Visits"]),
                         width="stretch", hide_index=True)
        else:
            st.caption("Nothing yet.")
    with t2:
        st.markdown("**What they're on**")
        if tr["devices"]:
            st.dataframe(pd.DataFrame(tr["devices"], columns=["Device", "Visits"]),
                         width="stretch", hide_index=True)
        else:
            st.caption("Nothing yet.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Views opened")
        if s["views"]:
            st.dataframe(pd.DataFrame(s["views"], columns=["View", "Opens"]),
                         width="stretch", hide_index=True)
        else:
            st.caption("Nothing yet.")
    with c2:
        st.markdown("#### Things clicked")
        if s["clicks"]:
            st.dataframe(pd.DataFrame(s["clicks"], columns=["What", "Clicks"]),
                         width="stretch", hide_index=True)
        else:
            st.caption("Nothing yet.")

    ppl = people.stats()
    _pay = ppl.get("pay") or {}
    st.markdown("#### The people")
    stat_cards([
        ("Signed up", f"{ppl['people']:,}", "#E8933A"),
        ("Told us their craft", f"{ppl['with_profile']:,}", "#5b9dff"),
        ("Left feedback", f"{ppl['feedback']:,}", "#35b37e"),
        ("Would pay · yes", f"{_pay.get('yes', 0):,}", "#e5675f"),
    ])
    if _pay:
        # $12 STAYS. These are answers to a question that asked about $12,
        # collected before the price moved to $15. Relabelling them would
        # quietly restate what people actually said.
        st.caption(f"Would pay $12/month (asked pre-$15) — yes: **{_pay.get('yes', 0)}** · "
                   f"maybe: **{_pay.get('maybe', 0)}** · no: **{_pay.get('no', 0)}**")

    acc = accounts.stats()
    st.markdown("#### Accounts & trials")
    stat_cards([
        ("Accounts", f"{acc['accounts']:,}", "#E8933A"),
        ("On a live trial", f"{acc['on_trial']:,}", "#5b9dff"),
        ("Trial ended", f"{acc['expired']:,}", "#e5675f"),
        ("Came back", f"{acc['returning']:,}", "#35b37e"),
    ])
    # Where the free Pro is actually going. These two belong side by side: a
    # partner announcement can quietly spend the founding fifty on people the
    # partner deal already covered, because a member who signs in with Google
    # comes back from the redirect without their ?ref= tag and falls through to
    # the founding branch. Founding climbing while partner sits still is that
    # happening, and it is otherwise invisible.
    stat_cards([
        ("On a partner grant", f"{acc['partner']:,}", "#a78bfa"),
        ("Founding members", f"{acc['founding']:,}", "#E8933A"),
        ("Founding slots left", f"{acc['founding_left']:,}", "#868D98"),
    ])
    # Only RECENT founding signups can mean anything is wrong. An old founding
    # account is the programme doing its job; one created while a partner
    # announcement is out is more likely a member who lost their ?ref= tag to
    # the Google redirect. Counting every founding account ever cried wolf
    # about signups from long before any partner existed.
    if acc["founding_recent"] and not acc["partner"]:
        st.warning(
            f"**{acc['founding_recent']}** founding slot(s) taken in the last "
            f"{accounts.FOUNDING_ALERT_DAYS} days, with no partner grants "
            f"issued. If a partner announcement is live, those are likely "
            f"members who lost their `?ref=` tag to the Google sign-in "
            f"redirect, so they are on {accounts.FOUNDING_DAYS} days instead "
            f"of the partner's. Opening the partner link again fixes an "
            f"account and returns its slot.")
    # Whether profiles will actually survive the next redeploy. This is the one
    # signal that tells you if the Supabase connection string is really wired.
    if store.enabled():
        if store.healthy():
            st.success("Durable backup: **connected**. Profiles and accounts "
                       "survive redeploys.")
            # healthy() is a probe of this instant. It says nothing about
            # whether the writes that matter have been landing, and a mirror
            # that has been refusing writes all afternoon still answers
            # SELECT 1. The counters are the part that would have told you.
            _wh = store.write_health()
            if _wh["streak"]:
                st.error(f"But the last **{_wh['streak']}** durable writes "
                         f"failed — data since then is only on the disk, and "
                         f"the disk does not survive a redeploy.")
                if _wh["last_error"]:
                    st.caption(f"Reason: `{_wh['last_error']}`")
            elif _wh["ok"] or _wh["failed"]:
                _ago = (f"{int(time.time() - _wh['last_ok'])}s ago"
                        if _wh["last_ok"] else "not yet this boot")
                st.caption(f"{_wh['ok']:,} writes saved this boot, "
                           f"{_wh['failed']:,} failed · last saved {_ago}")
        else:
            st.error("Durable backup: **configured but unreachable**. Check the "
                     "DATABASE_URL value in Render.")
            _err = store.last_error()
            if _err:
                st.caption(f"Reason: `{_err}`")
    else:
        st.warning("Durable backup: **off**. Set DATABASE_URL (Supabase) in "
                   "Render, or profiles reset on every deploy.")

    # Which feeds are actually producing. One source of forty going quiet moves
    # the total so little that nothing looks wrong — the board just gets a bit
    # thinner in one field, for weeks, until someone notices that category dried
    # up. This is the page that would have told you on day one.
    _sh = sources.health()
    if _sh:
        _broken = [(n, h) for n, h in _sh.items() if h["err_run"] >= 3]
        _quiet = [(n, h) for n, h in _sh.items()
                  if h["best"] and h["zero_run"] >= 12 and h["err_run"] < 3]
        if _broken:
            st.error("Sources failing: " + ", ".join(
                f"**{n}** ({h['err_run']} cycles)" for n, h in _broken))
            for n, h in _broken[:3]:
                st.caption(f"{n}: `{h['last_error']}`")
        if _quiet:
            st.warning("Sources returning nothing despite having worked before: "
                       + ", ".join(f"**{n}** ({h['zero_run']} cycles, best "
                                   f"{h['best']})" for n, h in _quiet))
        if not _broken and not _quiet:
            _live = sum(1 for h in _sh.values() if h["total"])
            st.success(f"Sources: **{_live} of {len(_sh)}** have produced gigs "
                       f"this boot, none failing.")
        with st.expander("Per-source detail"):
            st.dataframe(pd.DataFrame([
                {"source": n, "last": h["last"], "best": h["best"],
                 "total": h["total"], "zero run": h["zero_run"],
                 "err run": h["err_run"], "last error": h["last_error"][:60]}
                for n, h in sorted(_sh.items(), key=lambda kv: -kv[1]["total"])
            ]), width="stretch", hide_index=True)

    rows = people.people_rows()
    if rows:
        cols = ["created", "email", "pay", "name", "headline", "skills",
                "rate_floor", "rate_unit", "country", "city", "portfolio", "source"]
        table = pd.DataFrame(rows)[[c for c in cols if c in rows[0]]]
        st.dataframe(table, width="stretch", hide_index=True)
        st.download_button("Download people CSV", table.to_csv(index=False),
                           file_name="nabbly-people.csv", mime="text/csv")
    else:
        st.caption("Nobody yet.")

    st.markdown("#### What they said")
    fb = people.feedback_rows()
    if fb:
        for r in fb[:25]:
            who = r["email"] or "anonymous"
            tone = {"good": "#35b37e", "ok": "#E8933A", "bad": "#e5675f"}.get(r["rating"], "#697080")
            st.markdown(
                f'<div style="border-left:3px solid {tone};background:#15181d;'
                f'border-radius:0 10px 10px 0;padding:11px 15px;margin-bottom:9px">'
                f'<div style="font-size:14.5px;color:#e9ecf1">{html.escape(r["message"])}</div>'
                f'<div style="font-size:11.5px;color:#7b828d;margin-top:5px">'
                f'{html.escape(who)} · {html.escape(r["page"] or "—")} · {r["ts"][:16]}</div>'
                f'</div>', unsafe_allow_html=True)
        st.download_button("Download feedback CSV", pd.DataFrame(fb).to_csv(index=False),
                           file_name="nabbly-feedback.csv", mime="text/csv")
    else:
        st.caption("No feedback yet.")

    if not people.WEBHOOK_URL:
        st.warning(
            "**All of this resets on every deploy.** Render's free tier wipes the disk. "
            "Set `SIGNUP_WEBHOOK_URL` in Render → Environment and every signup, profile "
            "and piece of feedback is also POSTed there the moment it arrives, so the "
            "copy that matters lives somewhere you own.")


# ---------------------------------------------------------------------------
# Top nav bar (+ stat-card click navigation via query params)
# ---------------------------------------------------------------------------
# Alerts is no longer a tab. It's a settings screen, and it sat beside the
# three tabs that actually show gigs while its own copy told you to go to
# Profile to switch it on. It's a section of Profile now; ?nav=alerts still
# resolves there so any existing link or bookmark keeps working.
#
# Saved earns its place by the same rule Alerts failed: every tab here shows
# GIGS. Dashboard shows what's fresh, Gigs the whole board, Saved the ones you
# kept, Market what they pay. A settings screen in this row would be the odd
# one out again.
_TABS = ["Dashboard", "Gigs", "Market", "Saved"]
# Pages that live outside the tab strip: reachable by ?nav=, linked from the
# footer and the account menu, and they never light up a tab.
_SIDE_PAGES = {"profile": "Profile", "about": "About", "faq": "FAQ",
               "pricing": "Pricing", "signin": "Sign in", "admin": "Admin",
               "privacy": "Privacy", "terms": "Terms",
               "unsubscribe": "Unsubscribe"}

# Every gig title routes through here instead of linking straight out, so an
# apply click can be logged before the browser leaves — a plain <a href> to
# the external URL has no server round-trip at all to hook into. Checked
# before the ?nav= dispatch below for the same reason IS_ADMIN is: the first
# click on a gig title must not fall through and render the dashboard instead
# of redirecting.
# Save/unsave, then bounce back to where they were. Handled HERE, after the
# account has been resolved and paths.set_scope() has run, so the write lands
# in the signed-in person's own store rather than the anonymous scratch scope.
# Doing this as a link + redirect rather than an st.button keeps the gig card's
# DOM identical to what the card stylesheet was built against.
# Stripe Checkout redirects back here after a card is charged. The session id
# is trusted only as far as "go ask Stripe about it" — billing.confirm_session
# re-verifies payment_status server-side before flipping anyone to Pro, so a
# forged query param can't buy a free upgrade. Same redirect-then-stop shape
# as ?save=/?won=/?rate= below, so the URL doesn't keep the session id around
# on refresh.
# ── ONE FRONT DOOR ────────────────────────────────────────────────────────
# The board is the product now: feed, search, categories, Market, settings all
# moved there. This app kept rendering its OWN dashboard, so anyone holding an
# old bookmark — app.nabbly.co was the main site for months — landed in the
# previous generation and saw a different Nabbly. The founder hit exactly that
# on his Windows desktop and asked why the site looked completely different.
#
# So the browsing surfaces redirect and the money/admin surfaces stay. Pricing,
# checkout, unsubscribe and admin all live here and are untouched; the redirect
# only fires for a signed-in member, because a signed-out visitor lands on the
# marketing site's own paths and Streamlit is where sign-in still happens.
#
# BOARD_URL unset means no redirect at all — the same guard settings and Market
# already use, so clearing one variable cannot strand anybody.
_BOARD_PAGES = {"dashboard": "/", "gigs": "/gigs", "market": "/market",
                "saved": "/saved", "profile": "/profile", "alerts": "/profile"}
# THIS BLOCK RUNS BEFORE EVERY OTHER QUERY-PARAM HANDLER, so it must not
# swallow their URLs. A returning Stripe checkout arrives as ?stripe_session=
# with no nav, and redirecting it would bounce a paying member away before the
# payment is confirmed. The admin key arrives as ?admin=. Same for the one-shot
# save/won/rate actions and the unsubscribe token. Any of these present means
# this URL is a job for a handler below, not a front door.
_PASS_THROUGH = ("stripe_session", "admin", "save", "won", "rate", "t", "gid", "e")
if (ACCESS["signed_in"] and BOARD_URL
        and not any(st.query_params.get(k) for k in _PASS_THROUGH)):
    _want = (st.query_params.get("nav", "") or "").lower()
    # No ?nav= at all is the bare front door: app.nabbly.co typed or bookmarked.
    _dest = _BOARD_PAGES.get(_want) if _want else "/"
    if _dest:
        st.markdown(
            f'<meta http-equiv="refresh" content="0; '
            f'url={html.escape(BOARD_URL + _dest, quote=True)}">',
            unsafe_allow_html=True)
        st.caption("Taking you to the board…")
        st.stop()

if st.query_params.get("stripe_session"):
    _sid = st.query_params.get("stripe_session", "")
    _ok, _ = billing.confirm_session(_sid)
    if _ok:
        st.session_state["_pro_activated"] = True
    _allowed = {t.lower() for t in _TABS} | set(_SIDE_PAGES)
    _raw = (st.query_params.get("from") or "").lower()
    _back = _raw if _raw in _allowed else "profile"
    st.markdown(
        f'<meta http-equiv="refresh" content="0; '
        f'url={html.escape(ilink(f"?nav={_back}"), quote=True)}">',
        unsafe_allow_html=True)
    st.stop()

if st.query_params.get("save"):
    _sgid = st.query_params.get("save", "")
    if ACCESS["signed_in"] and _sgid:
        saved.toggle(_sgid)
        # Drop the cached set so the star and the tab count both show the new
        # state on the very next render rather than a stale one.
        st.session_state.pop("_saved_set", None)
    # Back to the page they were on, carrying the token so an email sign-in
    # isn't dropped by the round trip — same reasoning as ilink() everywhere.
    #
    # WHITELISTED, then escaped. `from` is attacker-controlled and was being
    # dropped straight into a double-quoted attribute rendered with
    # unsafe_allow_html — so `?from=x"><base href="https://evil/` closed the
    # meta tag early and injected a <base>, against which the relative redirect
    # (carrying ?u=<token>, which IS the credential here) would resolve. One
    # emailed link, one click, token gone. The ?nav=out handler just below has
    # always escaped its URL; this one didn't, and that inconsistency was the
    # bug. Matching an allowed page by name means nothing arbitrary can reach
    # the attribute at all — escaping alone would stop the injection but would
    # still let a stranger's link decide where the visitor lands.
    _allowed = {t.lower() for t in _TABS} | set(_SIDE_PAGES)
    _raw = (st.query_params.get("from") or "").lower()
    _back = _raw if _raw in _allowed else "gigs"
    st.markdown(
        f'<meta http-equiv="refresh" content="0; '
        f'url={html.escape(ilink(f"?nav={_back}"), quote=True)}">',
        unsafe_allow_html=True)
    st.stop()

# "I got this one" — same shape as ?save= just above: a link + redirect, not
# an st.button, so the card's DOM stays exactly what the stylesheet expects.
# Same whitelist-then-escape on `from` too — see the comment on ?save= for
# why that's load-bearing and not decorative.
# ?won= is retired with the control that produced it. An old link or a
# bookmark carrying it now just goes back to the board rather than recording
# something nobody can check.
if st.query_params.get("won"):
    _allowed = {t.lower() for t in _TABS} | set(_SIDE_PAGES)
    _raw = (st.query_params.get("from") or "").lower()
    _back = _raw if _raw in _allowed else "gigs"
    st.markdown(
        f'<meta http-equiv="refresh" content="0; '
        f'url={html.escape(ilink(f"?nav={_back}"), quote=True)}">',
        unsafe_allow_html=True)
    st.stop()

# Match-quality thumbs — same shape as ?won= just above, same reasons.
if st.query_params.get("rate"):
    _rgid = st.query_params.get("rate", "")
    _rdir = st.query_params.get("dir", "")
    if ACCESS["signed_in"] and _rgid and _rdir in ("up", "down"):
        import db as _db
        _rrow = _db.post_by_id(_rgid) or {}
        match_feedback.rate(ACCESS.get("email", ""), _rgid, _rdir,
                            job_type=_rrow.get("job_type", ""),
                            source=_rrow.get("source", ""))
        st.session_state.pop("_rated", None)
    _allowed = {t.lower() for t in _TABS} | set(_SIDE_PAGES)
    _raw = (st.query_params.get("from") or "").lower()
    _back = _raw if _raw in _allowed else "gigs"
    st.markdown(
        f'<meta http-equiv="refresh" content="0; '
        f'url={html.escape(ilink(f"?nav={_back}"), quote=True)}">',
        unsafe_allow_html=True)
    st.stop()

if st.query_params.get("nav", "").lower() == "out" and st.query_params.get("gid"):
    import db as _db
    _row = _db.post_by_id(st.query_params.get("gid"))
    if _row and _row.get("url"):
        # Who clicked? Either they're signed in in this browser, or they came
        # from an email carrying ?e=<email token> — which identifies them for
        # the count without being a credential (see accounts.email_token).
        import activity
        _who_scope = ""
        if ACCESS["signed_in"]:
            _who_scope = paths.get_scope()
        elif st.query_params.get("e"):
            _acc = accounts.by_email_token(st.query_params.get("e", ""))
            if _acc:
                _who_scope = paths.scope_for(_acc["email"])
        if _who_scope:
            activity.log_apply(_who_scope, _row["id"])
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={html.escape(_row["url"], quote=True)}">',
            unsafe_allow_html=True)
    else:
        # ilink() so a stale gig id doesn't also sign them out on the way back.
        st.markdown(f'<meta http-equiv="refresh" content="0; url={ilink("?nav=gigs")}">',
                    unsafe_allow_html=True)
    st.stop()

# The admin panel replaces the whole page — nothing else needs to render.
# Two ways in: the secret ?admin= key (works signed out), or simply being signed
# in as an owner account, so the founder doesn't have to keep a URL around.
def _admin_key_ok(supplied) -> bool:
    """
    Constant-time check of the ?admin= key.

    `==` on a secret returns as soon as two bytes differ, so how long it takes
    to say no leaks how much of the key was right — enough, over many tries, to
    recover it a character at a time. compare_digest always looks at every byte.
    Encoded to bytes first because the str form raises TypeError on anything
    non-ASCII, and ?admin= is whatever the visitor decided to type.
    """
    key = analytics.ADMIN_KEY or ""
    if not key:
        return False
    return hmac.compare_digest(str(supplied or "").encode("utf-8"),
                               key.encode("utf-8"))


IS_ADMIN = (_admin_key_ok(st.query_params.get("admin", ""))
            or (ACCESS["signed_in"] and accounts.is_owner(ACCESS.get("email"))))
# This gate runs BEFORE the ?nav= dispatch below, so check the raw query param
# as well as the page already in session — otherwise the first click on the
# Admin link would fall through and render nothing.
if IS_ADMIN and (st.query_params.get("admin") is not None
                 or st.query_params.get("nav", "").lower() == "admin"
                 or st.session_state.get("_page") == "admin"):
    st.session_state["_page"] = "admin"
    view_admin()
    st.stop()

if "nav" in st.query_params:
    _nav = st.query_params.get("nav", "").lower()
    if _nav == "alerts":
        _nav = "profile"          # alerts moved into Profile; keep old links alive
    if _nav in _SIDE_PAGES:
        st.session_state["_page"] = _nav
        if _nav == "unsubscribe":
            # query_params.clear() below would wipe ?t= before view_unsubscribe()
            # runs at dispatch time, same reason qf/cat/group get captured above.
            st.session_state["_unsub_token"] = st.query_params.get("t", "")
    else:
        _idx = {t.lower(): i for i, t in enumerate(_TABS)}.get(_nav)
        if _idx is not None:
            st.session_state["_navidx"] = _idx
            st.session_state["quickfilter"] = st.query_params.get("qf", "")
            st.session_state["catfilter"] = st.query_params.get("cat", "")
            st.session_state["groupfilter"] = st.query_params.get("group", "")
            # What pulled them in? Tracked per click, not per session.
            for _kind, _val in (("category", st.session_state["groupfilter"]),
                                ("skill", st.session_state["catfilter"]),
                                ("stat", st.session_state["quickfilter"])):
                if _val:
                    if not _OWNER_VISIT:
                        analytics.track("click", f"{_kind}:{_val}", SID)
                    break
        st.session_state["_page"] = ""      # a real tab leaves any info page
    # Keep the sign-in token in the address bar. clear() used to strip it,
    # which meant a reload (or a bookmark) of any page after the first click
    # came back anonymous — see ilink() for why the URL is the only thing
    # carrying identity for an email sign-in.
    _keep_u = st.query_params.get("u", "")
    st.query_params.clear()
    if _keep_u:
        st.query_params["u"] = _keep_u

_bcol, _ncol, _rcol = st.columns([2.0, 4.9, 1.3], vertical_alignment="center")
with _bcol:
    # Clicking the mark goes home — the way out when someone has filtered
    # themselves into a corner three pages deep.
    st.markdown(f'<a class="gr-home" href="{ilink("?nav=dashboard")}" target="_self" '
                f'title="Back to the dashboard">{LOGO_SVG}</a>',
                unsafe_allow_html=True)
# Which tab is live is ours to track now, rather than something we read back
# out of a component. ?nav= (set by the links below, and by every stat card and
# category chip) writes _navidx during dispatch above, so a deep link and a tab
# click land in the same place — no more manual_select juggling.
selected = _TABS[st.session_state.get("_navidx", 0)]
with _ncol:
    _side = bool(st.session_state.get("_page"))
    # A count on Saved, and only when there IS one. A "0" badge is a tab
    # telling you it has nothing — worse than no badge at all — and an empty
    # Saved tab already explains itself when you open it. Signed-out visitors
    # can't have saved anything, so they never see it either.
    #
    # Reads the same session-cached set the cards use — see saved_ids() for why
    # touching the store directly here would put a network call on every click.
    _saved_n = len(saved_ids())
    _links = ""
    for t in _TABS:
        _badge = (f'<span class="gr-tabn">{_saved_n}</span>'
                  if t == "Saved" and _saved_n else "")
        # Gigs can point at the fast board instead of this app's own page.
        # OFF unless NABBLY_BOARD_URL is set, so shipping this changes nothing
        # and the switch — and the way back — is one dashboard variable.
        #
        # Same tab, not a new one: it is the same product on a sibling
        # subdomain, and the session cookie is scoped to .nabbly.co so the
        # visitor stays signed in across it. Opening it in a new tab would
        # make an internal navigation look like leaving the site.
        _href = ilink(f"?nav={t.lower()}")
        if t == "Gigs" and BOARD_URL:
            _href = f"{BOARD_URL}/gigs"
        _links += (f'<a class="{"on" if t == selected and not _side else ""}" '
                   f'href="{_href}" target="_self">'
                   f'{t}{_badge}</a>')
    st.markdown(f'<div class="gr-nav">{_links}</div>', unsafe_allow_html=True)

# Leaving an info page is handled where ?nav= is dispatched: a tab link clears
# _page there, so the old "did the component's value change?" bookkeeping the
# iframe menu needed is gone.
_page = st.session_state.get("_page", "")
_on_profile = _page == "profile"
active = _SIDE_PAGES.get(_page) or selected
# Which tab the cards below are being drawn on, so a save link can send them
# back to it. Read by gig_card(), which runs after this.
st.session_state["_active_tab"] = active

with _rcol:
    _name = (prof.get("name") or "").strip()
    _acls = "gr-avatar active" if _on_profile else "gr-avatar"
    # The plan shown here used to read a session key that no longer exists, so
    # it said "Free plan" to everyone — including people mid-trial. Read the
    # real entitlement instead.
    if ACCESS["signed_in"]:
        _email = ACCESS.get("email", "")
        _who = _name or _email.split("@")[0] or "Your account"
        _founding_html = ""
        if ACCESS["plan"] == "pro":
            _plan = "Pro"
        elif ACCESS["pro"]:
            _d = ACCESS["days_left"]
            if ACCESS.get("founding"):
                # The badge carries "founding #N" now, so the text line only
                # needs to say how long is left, not repeat the label.
                _founding_html = founding_badge_html(ACCESS.get("founding_rank"))
                _plan = f"{_d} day{'s' if _d != 1 else ''} left"
            else:
                _plan = f"Pro trial · {_d} day{'s' if _d != 1 else ''} left"
        else:
            _plan = "Free"
        _last = f'<a href="{ilink("?signout=1")}" target="_self">Sign out</a>'
    else:
        _who, _plan, _founding_html = _name or "Your account", "Not signed in", ""
        _last = f'<a href="{ilink("?nav=signin")}" target="_self">Sign in</a>'
    # Signed in (or a local name filled in) → their initial. Anonymous → a small
    # person icon rather than a lone dot that reads as a stray period.
    _user_icon = ('<svg width="18" height="18" viewBox="0 0 24 24" '
                  'style="opacity:.75" xmlns="http://www.w3.org/2000/svg">'
                  '<circle cx="12" cy="8.2" r="3.7" fill="currentColor"/>'
                  '<path d="M4.8 20c0-3.7 3.2-5.7 7.2-5.7s7.2 2 7.2 5.7z" '
                  'fill="currentColor"/></svg>')
    _init = _who[:1].upper() if _who != "Your account" else _user_icon
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;padding-right:2px">'
        f'<div class="gr-acct">'
        f'<input type="checkbox" id="acct-menu-toggle" class="gr-acct-cb">'
        f'<label class="{_acls}" for="acct-menu-toggle" title="Your account">{_init}</label>'
        f'<div class="gr-menu">'
        # gr-menu-hd is flex-column, so the name and the badge share a wrapper
        # div to stay on one row — as separate direct children they'd each
        # become their own row and the badge would stack under the name.
        f'<div class="gr-menu-hd"><div>{html.escape(_who)}{_founding_html}</div>'
        f'<span>{html.escape(_plan)}</span></div>'
        # One entry, not two. "Your profile" and "Location & settings" were
        # different labels on the identical ?nav=profile link, which reads as a
        # menu with a broken item. STRAIGHT TO THE BOARD when signed in: the
        # app's own profile page is a one-button stub pointing there, and the
        # founder hit it and called it — "this page doesn't even do anything".
        # A menu item that opens a page whose only job is another click is a
        # broken menu item with extra steps. The stub stays reachable as the
        # BOARD_URL-unset fallback only.
        f'<a href="{(BOARD_URL + "/profile") if (ACCESS["signed_in"] and BOARD_URL) else ilink("?nav=profile")}" target="_self">Profile &amp; settings</a>'
        # One line, every tab, opt-in (the menu only opens on click) — the
        # actual upgrade card still lives at the bottom of the Dashboard feed
        # for anyone reading gigs, but that's a long scroll away on a busy
        # board. This is the always-there path that doesn't compete with the
        # gigs themselves for attention.
        + (f'<a class="gr-menu-pro" href="{ilink("?nav=pricing")}" target="_self">'
           f'Upgrade to Pro</a>' if ACCESS["signed_in"] and not ACCESS["pro"] else '')
        # Owners only — everyone else never sees this link exists.
        + (f'<a href="{ilink("?nav=admin")}" target="_self">Admin</a>' if IS_ADMIN else '') +
        f'<div class="gr-menu-sep"></div>'
        f'{_last}'
        f'</div></div></div>', unsafe_allow_html=True)

# (No st.divider here any more — the full-width top bar carries its own bottom
# border, so a second centred rule under it would just look like a stray line.)
st.write("")

# A quick-filter / category (from a Dashboard click) only lives while on Gigs.
if active != "Gigs":
    st.session_state["quickfilter"] = ""
    st.session_state["catfilter"] = ""
    st.session_state["groupfilter"] = ""

# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
note("view", active)

if active == "Dashboard":
    view_dashboard(PRO)
elif active == "Gigs":
    view_gigs(PRO)
elif active == "Saved":
    view_saved(PRO)
elif active == "Market":
    view_market(PRO)
elif active == "Profile":
    view_profile(PRO)
elif active == "About":
    view_about()
elif active == "Pricing":
    view_pricing()
elif active == "FAQ":
    view_faq()
elif active == "Sign in":
    view_signin()
elif active == "Privacy":
    view_legal("privacy")
elif active == "Terms":
    view_legal("terms")
elif active == "Unsubscribe":
    view_unsubscribe()

st.markdown(
    '<div class="gr-footer">'
    '<span class="brand">Nabbly</span>'
    '<span class="tag">Every gig. The moment it drops.</span>'
    '<div class="foot-links">'
    f'<a class="foot-link" href="{ilink("?nav=about")}" target="_self">About</a>'
    f'<a class="foot-link" href="{ilink("?nav=pricing")}" target="_self">Pricing</a>'
    f'<a class="foot-link" href="{ilink("?nav=faq")}" target="_self">FAQ</a>'
    f'<a class="foot-link" href="{ilink("?nav=privacy")}" target="_self">Privacy</a>'
    f'<a class="foot-link" href="{ilink("?nav=terms")}" target="_self">Terms</a>'
    '</div>'
    '<span class="meta">Nabbly · © 2026</span>'
    '</div>', unsafe_allow_html=True)

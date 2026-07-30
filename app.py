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
import secrets
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import pandas as pd
import altair as alt
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

import db
import config
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
import refresh
import inbox
import legal
import analytics
import people
import paths
import auth
import accounts
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
  --ink:#ECEEF1; --ink2:#c3c8d0; --mute:#969da7; --faint:#6b7280;
  --amber:#E8933A; --amber-l:#F7B569; --amber-d:#CB6F16;
  /* Vertical rhythm. The whole point is that these are DIFFERENT from each
     other — Streamlit ships one flat 16px between everything, which is why the
     page reads as undesigned no matter how good the individual pieces are. */
  --s-item:.5rem;      /* between parts of one thing (title, pills, body) */
  --s-group:1rem;      /* between sibling things (card to card) */
  --s-section:2.2rem;  /* before a new section heading */
}
/* Section headings speak the wordmark's language: the last word in amber, the
   way "ly" is amber in Nabbly. Replaces the scattered emoji prefixes so every
   heading reads as one family. */
.gr-accent{color:#E8933A}
.gr-stats{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 4px;
  justify-content:center;max-width:none}
.gr-stat{flex:1;min-width:150px;background:#15181d;border:1px solid #262a31;
  border-radius:14px;padding:15px 16px 16px;position:relative;overflow:hidden}
/* Four saturated bars competing for attention read as noise. Keep the colour
   as a quiet cue, not a stripe: thinner, dimmer, shorter. */
.gr-stat .accent{position:absolute;left:0;top:18px;bottom:18px;width:2px;
  border-radius:0 3px 3px 0;opacity:.55}
.gr-stat .l{font-size:12.5px;color:#98a0ab;font-weight:500;margin:0 0 9px}
.gr-stat .n{font-size:31px;font-weight:600;color:#f2f4f7;line-height:1;
  font-variant-numeric:tabular-nums;perspective:240px}
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
a.gr-title{font-size:19px;font-weight:600;color:#eaeef4 !important;
  text-decoration:none !important;line-height:1.35;letter-spacing:-.1px}
a.gr-title:hover{color:#E8933A !important;text-decoration:underline !important;
  text-decoration-color:rgba(232,147,58,.55);text-underline-offset:3px}
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
.gr-pill.low{background:rgba(212,160,60,.14);color:#ddb478}
.gr-pill.loc{background:rgba(76,141,255,.13);color:#89b0f5}
.gr-pill.locnear,.gr-pill.remote{background:rgba(94,196,120,.14);color:#7ecb93}
.gr-pill.locoff{background:#1a1d23;color:#767c86}
.gr-why{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 11px}
.gr-why .lead{font-size:10px;font-weight:600;letter-spacing:.8px;
  text-transform:uppercase;color:#6d747f;margin-right:2px}
.gr-why-chip{font-size:11px;font-weight:500;color:#caa06e;
  background:rgba(232,147,58,.07);border:1px solid rgba(232,147,58,.18);
  border-radius:999px;padding:2px 10px}
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
.gr-qf{display:inline-block;font-size:13px;font-weight:500;color:#eaa662;
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
a.gr-avatar{display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:50%;background:#22262e;border:1px solid #3a4150;
  color:#eaa662!important;font-size:15px;font-weight:600;text-decoration:none!important;
  cursor:pointer;transition:border-color .15s ease,background .15s ease}
a.gr-avatar:hover{border-color:#E8933A;background:#2a2f38}
a.gr-avatar.active{background:#E8933A;color:#141414!important;border-color:#E8933A}
.gr-acct{position:relative;display:inline-block}
.gr-menu{position:absolute;right:0;top:48px;min-width:196px;background:#1b1e25;
  border:1px solid #2f3540;border-radius:12px;padding:6px;z-index:1000;
  box-shadow:0 14px 34px rgba(0,0,0,.5);opacity:0;visibility:hidden;
  transform:translateY(-6px);transition:opacity .14s ease,transform .14s ease,visibility .14s}
.gr-acct:hover .gr-menu{opacity:1;visibility:visible;transform:translateY(0)}
.gr-menu-hd{padding:8px 10px 7px;color:#eaeef4;font-weight:600;font-size:14px;
  display:flex;flex-direction:column;line-height:1.55;text-align:left}
.gr-menu-hd span{color:#eaa662;font-weight:500;font-size:11.5px;letter-spacing:.02em}
.gr-menu a,.gr-menu .gr-mi{display:block;padding:8px 10px;border-radius:8px;text-align:left;
  color:#cdd3dc!important;text-decoration:none!important;font-size:13.5px;transition:background .12s}
.gr-menu a:hover{background:#262b34;color:#fff!important}
.gr-menu .gr-mi.muted{color:#6b7178!important;cursor:default}
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
.gr-nav a,.gr-nav a:link,.gr-nav a:visited{font-size:15.5px;font-weight:600;
  color:#c3cad3!important;text-decoration:none!important;padding:10px 22px;
  border-radius:9px;white-space:nowrap;letter-spacing:-.1px;
  transition:background .15s,color .15s}
.gr-nav a:hover{background:rgba(232,147,58,.12);color:#eaa662!important}
.gr-nav a.on,.gr-nav a.on:link,.gr-nav a.on:visited,.gr-nav a.on:hover{
  background:#E8933A;color:#141414!important}
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
  padding:0 clamp(22px, 4vw, 64px) 12px;
  border-bottom:1px solid #23272f}   /* a full-width bar rule, so the divider below it goes */
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
header[data-testid="stHeader"]{height:0;background:transparent}
/* Hide Streamlit's own chrome so it reads as a real product, not a demo. */
#MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],.stDeployButton,[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],footer{display:none!important;visibility:hidden!important}
.gr-footer{max-width:980px;margin:52px auto 6px;padding:22px 16px 4px;
  border-top:1px solid #23262d;display:flex;flex-direction:column;
  align-items:center;gap:4px;text-align:center}
.gr-footer .brand{color:#eaa662;font-weight:700;font-size:14px;letter-spacing:.02em}
.gr-footer .tag{color:#8a919c;font-size:13px}
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
.gr-search-hint{text-align:center;font-size:13px;color:#7c838d;margin:8px 0 0}
.gr-search-hint a{color:#98a0ab!important;text-decoration:none!important;
  font-weight:600;border-bottom:1px solid rgba(232,147,58,.35)}
.gr-search-hint a:hover{color:#eaa662!important}
.gr-onb-hit{max-width:620px;margin:10px auto 2px;text-align:center;font-size:15px;
  color:#b9c0c9;animation:gr-count .32s ease-out}
.gr-onb-hit b{color:#E8933A;font-size:21px;font-weight:750;font-variant-numeric:tabular-nums}
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
  .gr-onb-hit{animation:none}
}
/* --- The reply we already wrote ------------------------------------------
   This was the best thing in the product and it was hidden behind a collapsed
   row on every card, so nobody ever saw it. Shown, it's the moment people
   screenshot. */
.gr-draft{margin:2px 0 6px;border:1px solid rgba(232,147,58,.34);border-radius:16px;
  overflow:hidden;background:linear-gradient(180deg,rgba(232,147,58,.07),rgba(232,147,58,.02))}
.gr-draft-hd{padding:14px 18px 13px;border-bottom:1px solid rgba(232,147,58,.20);
  display:flex;flex-direction:column;gap:5px}
.gr-draft-k{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  letter-spacing:.16em;text-transform:uppercase;color:#eaa662;font-weight:700}
.gr-draft-t{font-size:17px;font-weight:650;color:#f2f4f7;line-height:1.3;letter-spacing:-.2px}
.gr-draft-m{display:flex;gap:7px;flex-wrap:wrap;margin-top:2px}
/* Real paragraphs, not pre-wrap: the template's blank lines rendered as
   full-height gaps and the text ran the whole window. A message needs a
   readable measure, same as any other prose. */
.gr-draft-body{padding:16px 18px 17px;font-size:14px;line-height:1.62;color:#cbd2db;
  font-family:inherit;max-width:70ch}
.gr-draft-body p{margin:0 0 11px}
.gr-draft-body p:last-child{margin-bottom:0}
.gr-draft-lock{padding:20px 18px;text-align:center;color:#98a0ab;font-size:14px;line-height:1.6}
.gr-draft-lock b{color:#eaa662}
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
.gr-trial{display:block;font-size:13px;line-height:1.5;padding:9px 16px;
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
.gr-cap-s{font-size:14px;color:#98a0ab;line-height:1.55;max-width:52ch;margin:0 auto}
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
.gr-cta-fine{text-align:center;font-size:11.5px;color:#6b7280;margin:9px 0 6px}
.gr-mini{text-align:center;font-size:13px;color:#9aa1ab;margin:4px 0 8px}
.gr-mini b{color:#eaa662;font-weight:700}

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
.gr-page-n{text-align:center;font-size:13px;color:#969da7;line-height:1.3;
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
.gr-about ol li{position:relative;padding:2px 0 12px 40px;font-size:15px;color:#b8bfc9}
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
  .gr-doc p,.gr-doc li{font-size:15px}}
.gr-footer .foot-links{display:flex;gap:16px;align-items:center}
/* Keep the FAQ's heading and its rows in one column — the heading sat in a
   centred 680px block while the expanders ran the full width. */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .gr-faq-mark){
  max-width:680px!important;margin-left:auto!important;margin-right:auto!important}
.gr-about h2{text-align:center}
.gr-about ol li::before{counter-increment:step;content:counter(step);
  position:absolute;left:0;top:0;width:27px;height:27px;border-radius:8px;
  background:rgba(232,147,58,.14);border:1px solid rgba(232,147,58,.3);
  color:#eaa662;font-weight:700;font-size:13px;display:flex;align-items:center;
  justify-content:center;font-family:ui-monospace,Menlo,monospace}
/* Free vs Pro as two cards. The same information was a single paragraph of
   bolded fragments — you had to read it to compare two things that a reader
   wants to scan side by side. Pro carries the one amber edge on the page
   (FEEL.md §2: one focal point), Free stays neutral. */
.gr-ab-plans{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:6px 0 20px}
.gr-ab-plan{background:var(--bg2);border:1px solid var(--line);
  border-radius:14px;padding:18px 18px 6px;text-align:left}
.gr-ab-plan.pro{border-color:rgba(232,147,58,.32);
  background:linear-gradient(180deg,rgba(232,147,58,.06),rgba(232,147,58,.015))}
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
  .gr-pill{font-size:11px}

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
.st-key-arrivals button p{font-size:13px!important;font-weight:500!important;margin:0!important}

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

/* Dashboard header for the no-hero variant: a working title, not a billboard.
   The pitch already did its job on nabbly.co; once you're inside, the page
   should get out of the way. */
.gr-dash-head{margin:2px 0 16px}
.gr-dash-head h2{font-size:25px;font-weight:600;letter-spacing:-.4px;color:#ECEEF1;
  margin:0 0 5px}
.gr-dash-head p{font-size:14.5px;color:#8a919c;margin:0}
@media (max-width:640px){.gr-dash-head h2{font-size:21px}}

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
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] a.gr-title):hover{
  border-color:#30353f!important}

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
  font-size:12px!important;color:var(--faint)!important}

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
.gr-posted{font-size:12px;color:var(--faint);margin-top:9px;margin-bottom:16px}

/* "Send to hr@company.com" — the one place a draft turns into a sent message.
   Amber gradient because on a card where it appears, it IS the primary action
   (FEEL.md §4: one primary per screen; a gig card is that screen). */
a.gr-sendmail{display:block;margin:10px 0 2px;padding:11px 16px;border-radius:11px;
  text-align:center;font-size:14px;font-weight:650;letter-spacing:-.1px;
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
.gr-soon{display:inline-block;margin-left:10px;font-size:10.5px;font-weight:650;
  letter-spacing:.08em;text-transform:uppercase;color:var(--amber);
  background:rgba(232,147,58,.10);border:1px solid rgba(232,147,58,.26);
  border-radius:100px;padding:3px 9px;vertical-align:4px}
.gr-plan{background:var(--bg2);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px}

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
.gr-plan-note{font-size:13px;color:var(--mute);margin-top:3px;line-height:1.5}
.gr-plan-price{text-align:right;font-size:15px;font-weight:600;color:var(--amber);
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
    > [data-testid="stElementContainer"] > [data-testid="stMarkdown"] p{font-size:14px}
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
def _resolve_account():
    # Google first: it hands us an address it has already verified, so it beats
    # a link that anyone could forward and an email box that nobody checked.
    gmail = auth.google_email(st)
    if gmail:
        acc, _ = accounts.sign_in(gmail, source="google")
        if acc:
            return acc

    tok = st.query_params.get("u") or st.session_state.get("_tok") or ""
    if tok:
        acc = accounts.by_token(tok)
        if acc:
            st.session_state["_tok"] = tok
            return acc
        st.session_state.pop("_tok", None)   # stale or forged token
    return None


# The account menu is raw HTML, so its "Sign out" can't call Python directly.
# It links back as ?signout=1 and we handle it here, before the account is
# resolved, so the cleared token actually takes effect on this run.
if st.query_params.get("signout"):
    _was_google = bool(auth.google_email(st))
    st.session_state.pop("_tok", None)
    st.query_params.clear()
    if _was_google:
        st.logout()          # reruns on its own
    st.rerun()

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

prof = profile_mod.load()
ALL_SKILLS = list(config.JOB_TYPES.keys()) + ["Other / general"]
FEED_CAP = 60
PAGE_SIZE = 25   # a couple of screens of scroll, not sixty cards in one column
# The dashboard showed five gigs and then stopped, which made a board of
# thousands feel thin — the point of the page is that there's always more.
DASH_FEED = 12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_dt(raw):
    """Parse the varied timestamp formats the boards send us."""
    raw = str(raw).strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass
    try:
        return parsedate_to_datetime(raw)  # RFC-822 (reddit / WWR RSS)
    except Exception:
        pass
    try:
        from dateutil import parser as _dp
        return _dp.parse(raw)
    except Exception:
        return None


def human_time(raw):
    """Friendly, low-precision time in the viewer's local timezone."""
    if not raw:
        return "recently"
    dt = _parse_dt(raw)
    if dt is None:
        return "recently"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()  # -> the machine's local timezone
    secs = max(0, (datetime.now(local.tzinfo) - local).total_seconds())
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    if secs < 7 * 86400:
        return f"{int(secs // 86400)}d ago"
    return local.strftime("%b ") + str(local.day)  # e.g. "Jul 16"


def is_recent(raw, hours=24):
    dt = _parse_dt(raw)
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) >= datetime.now(timezone.utc) - timedelta(hours=hours)


def recent_count(data, hours=24):
    """How many gigs were actually posted within the last `hours` (real freshness)."""
    if data.empty:
        return 0
    return int(sum(is_recent(r, hours) for r in data["posted_at"]))


def smart_trim(text, target=230, hard=520):
    """Trim to a full sentence so a preview never trails off mid-thought."""
    text = (text or "").strip()
    if len(text) <= target:
        return text
    for i in range(target, min(len(text), hard)):
        if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1] in " \n"):
            return text[:i + 1]
    cut = text[:hard]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 0 else cut) + "…"


_HINT_SEP = "\x1f"
# Rows written before sources._body existed (including the bundled seed) have
# the machine hints glued straight onto the description. Trim the tell-tale
# tail: a run of capitalised skill tags, and a trailing budget/salary string.
_BUDGET_TAIL = re.compile(
    r"\s*\$?[\d,.]+\s*[-–—]\s*\$?[\d,.]*\s*(?:[A-Z]{3})?\s*"
    r"(?:budget|/\s*year|/\s*yr|per\s+year)?\s*$", re.I)
_TAGLIKE = re.compile(r"^[A-Z][A-Za-z0-9+#./-]*$")       # "WordPress", "Make.com"
_TECHY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+#./-]*$")   # "n8n", "3D", "24/7"


def _strip_tag_tail(text):
    """Peel a trailing run of skill tags: 'PHP Website Design WordPress n8n'."""
    words = text.split()
    i = len(words)
    while i:
        w = words[i - 1]
        if w.endswith((".", "!", "?", ",", ":", ";")):
            break  # real punctuation means we're back in prose
        taggy = _TAGLIKE.match(w) or (
            _TECHY.match(w)
            and any(c.isdigit() or c == "." for c in w)   # "n8n", "3D", "v2.0"
            and any(c.isalpha() for c in w))              # but never a bare number
        if not taggy:
            break
        i -= 1
    # Only a long run is a tag dump; a couple of proper nouns is just a sentence.
    return " ".join(words[:i]) if len(words) - i >= 5 else text


# Job-board feeds open the description with the company's own metadata before a
# word of the actual role, which is pure noise in the card's most valuable spot
# (365 posts on the current board start this way). Two shapes:
#   "Headquarters: Brazil URL: http://x.com  <description>"   — clean to cut
#   "Headquarters: State College, PA  <description>"          — no delimiter
_HQ_LABEL = re.compile(r"^\s*headquarters\s*:\s*", re.I)
_HQ_URL = re.compile(r".*?\burl\s*:\s*\S+\s*", re.I)
_FEED_LOC = re.compile(r"^\s*(?:location|company)\s*:\s*[^\n]{0,60}?\s{2,}", re.I)


def _strip_feed_head(text: str) -> str:
    """
    Drop a leading 'Headquarters: …' metadata block.

    The "URL:" form is cut entirely — it ends at a known marker, so there's no
    guesswork. The bare form ("Headquarters: State College, PA <description>")
    has nothing separating the place list from the prose; a heuristic that
    guessed where the sentence began ate a real word ("At Nextcloud…" became
    "Nextcloud…") and missed several others, so we only remove the label and
    leave the location text alone. Losing copy is worse than a little noise.
    """
    m = _HQ_LABEL.match(text)
    if not m:
        return text
    rest = text[m.end():]
    u = _HQ_URL.match(rest)
    return rest[u.end():] if u else rest


def display_body(raw):
    """The half of a post a human should actually read (see sources._body)."""
    text = (raw or "").split(_HINT_SEP)[0].strip()
    # Rows fetched before sources._strip learned to drop it still carry
    # RemoteOK's "please mention the word …" scraper bait.
    text = sources.BOILERPLATE.sub("", text).strip()
    text = _strip_feed_head(text)
    text = _FEED_LOC.sub("", text, count=1).strip()
    for _ in range(3):  # a budget can sit behind the tags, so peel a few times
        before = text
        text = _strip_tag_tail(_BUDGET_TAIL.sub("", text))
        if text == before:
            break
    text = text.strip(" ·,-–—")
    # Several feeds hand us a preview that stops mid-word. Say so, rather than
    # pretending the sentence ended there.
    if text and text[-1] not in ".!?…\"')":
        text += "…"
    return text


def fmt_ceiling(n: int, ceiling: int) -> str:
    """
    An honest number that still reads as "there's always more."

    Below the ceiling, the exact count — it changes every fetch, so a precise
    number is true and worth showing. At or above it, "10,000+" instead of
    whatever the live figure happens to be: FEEL.md §7 killed one stale claim
    already ("6,000+ gigs" shipped as a fixed line and drifted the moment a
    redeploy reset the seed). A live ceiling can't go stale — it's either still
    true, or the real count has grown past it and it's MORE true.
    """
    return f"{ceiling:,}+" if n >= ceiling else f"{n:,}"


def _flip_spans(value: str) -> str:
    """
    Wrap each character so CSS can stagger a per-digit flip when it lands —
    the departure-board effect. Streamlit remounts this markup fresh on every
    rerun (it's not a persistent DOM node Python mutates in place), so a plain
    CSS `animation` replays on its own each time with no JS and nothing to
    orchestrate — see .gr-flip in the stylesheet.
    """
    return "".join(f'<span class="gr-flip" style="animation-delay:{i*35}ms">'
                   f'{ch}</span>' for i, ch in enumerate(value))


def stat_cards(items):
    html = ('<div class="gr-stats" style="max-width:980px;margin-left:auto;'
            'margin-right:auto;justify-content:center">')
    for label, value, accent, *rest in items:
        cls = "n small" if "small" in rest else "n"
        href = next((x for x in rest if x and x != "small"), "")
        inner = (f'<div class="accent" style="background:{accent}"></div>'
                 f'<div class="l">{label}</div>'
                 f'<div class="{cls}">{_flip_spans(value)}</div>')
        if href:
            html += (f'<a class="gr-stat" href="{href}" target="_self">{inner}'
                     f'<div class="go">→</div></a>')
        else:
            html += f'<div class="gr-stat">{inner}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def pills(items):
    spans = "".join(f'<span class="gr-pill {v}">{t}</span>' for t, v in items)
    st.markdown(f'<div class="gr-pills">{spans}</div>', unsafe_allow_html=True)


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
    df = df[df["_key"] != ""].drop_duplicates(subset="_key", keep="first")
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
refresh.start()     # background fetcher: grows the feed while the app is in use
analytics.init()    # visit counting, in its own database file
people.init()       # who signed up, their profile, and their feedback

# One id per browser tab. Streamlit reruns this script constantly, so without
# this every scroll and click would look like a brand-new visitor.
if "_sid" not in st.session_state:
    st.session_state["_sid"] = uuid.uuid4().hex[:12]
    _sid = st.session_state["_sid"]
    analytics.track("session", "", _sid)
    # Where did they come from, and on what? Read once, from the request that
    # opened the session. We keep only the referring host and a coarse device
    # bucket — never the full URL, never anything identifying.
    try:
        _h = st.context.headers or {}
        analytics.track("ref", analytics.referrer_label(_h.get("Referer", "")), _sid)
        analytics.track("device", analytics.device_label(_h.get("User-Agent", "")), _sid)
    except Exception:
        pass          # header access must never break a page load
    # A partner's own tag: ?ref=name (or utm_source=, which is what most
    # newsletter tools emit by default). Captured HERE, at session start,
    # because the nav dispatch calls st.query_params.clear() further down —
    # read it any later and it's already gone. Held in session state so it
    # survives to whenever they actually sign up, which is the only moment
    # that answers whether the collaboration worked.
    try:
        _tag = analytics.campaign_label(
            st.query_params.get("ref", "") or st.query_params.get("utm_source", ""))
        if _tag:
            st.session_state["_campaign"] = _tag
            analytics.track("campaign", _tag, _sid)
    except Exception:
        pass
SID = st.session_state["_sid"]
CAMPAIGN = st.session_state.get("_campaign", "")


def note(event: str, detail: str = ""):
    """Record something the visitor did (once per session per thing)."""
    seen = st.session_state.setdefault("_seen_events", set())
    key = f"{event}:{detail}"
    if key in seen:
        return
    seen.add(key)
    analytics.track(event, detail, SID)


df, merged = load_feed()
stats = market.skill_stats(df.to_dict("records")) if not df.empty else {}


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
    remote = local = 0
    for r in data.to_dict("records"):
        t = location.tag(r)
        if t["remote"] and location.eligible(t, region):
            remote += 1
        if t["onsite"] or location.is_local(r, city):
            local += 1
    return len(data), remote, local


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
    recs = view.to_dict("records")
    if mode.startswith("On-site"):
        keep = [r["id"] for r in recs
                if location.tag(r)["onsite"] or location.is_local(r, city)]
    else:  # "Remote I can take" — drop gigs geo-locked to other regions
        keep = [r["id"] for r in recs
                if location.tag(r)["remote"] and location.eligible(location.tag(r), region)]
    return view[view["id"].isin(keep)]


def scored(view):
    if view.empty:
        return view
    sc = [score.fit_score(r, prof) for r in view.to_dict("records")]
    view = view.copy()
    view["_score"] = [s for s, _ in sc]
    view["_reasons"] = [r for _, r in sc]
    return view.sort_values("_score", ascending=False)


def _save_draft(gig_id, key):
    drafts.save(gig_id, st.session_state.get(key, ""))
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
        url = html.escape(r.get("url") or "", quote=True)
        st.markdown(f'{new}<a class="gr-title" href="{url}" target="_blank">{title}</a>',
                    unsafe_allow_html=True)

        # Pills carry their meaning in colour (FEEL.md §2: match is amber,
        # urgent is red, low is amber-dim, location is blue/green) — an emoji
        # prefix on top of a tinted pill was saying the same thing twice.
        badge_items = []
        if pro and r.get("_score") is not None:
            badge_items.append((f"{int(r['_score'])}% match", "match"))
        _src = (r["source"] or "").lower()
        badge_items += [(r["job_type"], ""), (f"{r['size_tier']} budget", ""),
                        source_pill(_src)]
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
        # Only ever shown when a non-English gig is ON the board — either the
        # reader opened it up in Profile, or it's their country's language. It
        # answers "why is this one in German?" before they have to wonder.
        if (r.get("apply_email") or "").strip():
            badge_items.append(("Apply by email", "match"))
        _lc = r.get("_lang") or "en"
        if _lc != "en":
            badge_items.append((lang.label(_lc), "locoff"))
        if r.get("urgency") == "Urgent":
            badge_items.append(("Urgent", "urgent"))
        if pro:
            lb, reason = market.lowball(r, stats, prof)
            if lb:
                badge_items.append((reason, "low"))
        pills(badge_items)

        if pro and r.get("_reasons"):
            chips = "".join(f'<span class="gr-why-chip">{html.escape(x)}</span>'
                            for x in r["_reasons"])
            if chips:
                st.markdown('<div class="gr-why"><span class="lead">why</span>'
                            + chips + "</div>", unsafe_allow_html=True)

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
        posted = html.escape(
            f"Posted {human_time(r.get('posted_at') or r.get('fetched_at'))}")
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
        # "Pro" carries the gating on its own in bold amber text — a padlock
        # glyph next to it was decoration on top of a word already doing the job.
        label = "Draft my reply" if pro else "Draft my reply  ·  Pro"
        if pro and saved_exists:
            label += "  ·  draft saved"
        with st.expander(label):
            if pro:
                key = f"pitch_{gid}"
                # Seed once: your saved edit if you have one, else a fresh draft.
                if key not in st.session_state:
                    st.session_state[key] = drafts.load(gid) or pitch.draft_pitch(
                        r, prof, resume_text=st.session_state.get("_resume_text", ""),
                        who=paths.get_scope())
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
                st.caption("On **Pro**, we write a ready-to-send reply for this exact "
                           "gig — so you can fire back first, without staring at a blank "
                           "message. Upgrade any time from your **Profile**.")
                st.button("Upgrade to Pro", key=f"up_{r['id']}",
                          disabled=True, width="stretch")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
@st.fragment(run_every=60)
def live_stats():
    """Re-reads the feed every ~60s so the headline numbers climb on their own
    as the background fetcher pulls in new gigs — no click needed. (Kept a touch
    slower than the ~5-min fetch to avoid needless reruns.)"""
    cur, _ = load_feed()
    if cur.empty:
        return
    skills = prof.get("skills") or []
    # Signed in with skills → the numbers are about YOU: your matches, your
    # fresh ones, your urgent ones, with one card for whole-board context.
    # Signed out → the board at large, exactly as before.
    # ONE ceiling, on the board total only. Every other number stays live and
    # exact, so it visibly climbs as the board grows — that movement is the
    # point. The board total is the exception because it's the number that runs
    # away from the others, and "10,000+" reads as scale in a way that a precise
    # five-digit figure doesn't. A live ceiling also can't go stale the way the
    # old hard-coded "6,000+ gigs" line did (FEEL.md §7).
    if ACCESS["signed_in"] and skills:
        mine = cur[cur["job_type"].isin(skills)]
        stat_cards([
            ("Matching you", f"{len(mine):,}", "#E8933A", "?nav=gigs&qf=mine"),
            ("Fresh for you · 24h", f"{recent_count(mine, 24):,}", "#4C8DFF",
             "?nav=gigs&qf=mine"),
            ("Urgent for you", f"{int((mine['urgency'] == 'Urgent').sum()):,}",
             "#E96250", "?nav=gigs&qf=urgent"),
            ("On the whole board", fmt_ceiling(len(cur), 10_000), "#35B37E",
             "?nav=gigs"),
        ])
    else:
        stat_cards([
            ("On the board now", fmt_ceiling(len(cur), 10_000), "#E8933A",
             "?nav=gigs"),
            ("Fresh · last 24h", f"{recent_count(cur, 24):,}", "#4C8DFF",
             "?nav=gigs&qf=recent"),
            ("Urgent", f"{int((cur['urgency'] == 'Urgent').sum()):,}", "#E96250",
             "?nav=gigs&qf=urgent"),
            # Not "sources" — no need to advertise where the gigs come from. Breadth
            # of fields is the more useful, and more discreet, fourth number.
            ("Fields hiring", f"{cur['job_type'].nunique()}", "#35B37E", "?nav=gigs"),
        ])


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
    labels = ["All fields"] + [f"{g} · {n:,}" for g, n in groups]
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

    A ready-to-send reply, already written for the single best-matching gig,
    sitting in the open. It was the strongest thing in the product and it lived
    behind a collapsed row on every card, which is where features go to die.
    """
    if df.empty or not prof.get("skills"):
        return
    srcs = sorted(df["source"].unique())
    top = scored(apply_filters(df, prof["skills"], ["Small", "Medium", "Large"],
                               srcs, False, ""))
    if top.empty:
        return
    g = top.iloc[0].to_dict()
    gid = str(g["id"])
    pills_html = "".join(
        f'<span class="gr-pill {c}">{html.escape(str(t))}</span>' for t, c in [
            (f"{int(g['_score'])}% match", "match") if g.get("_score") is not None else ("", ""),
            (g.get("job_type", ""), ""), (f"{g.get('size_tier','')} budget", ""),
            source_pill(g.get("source")),
        ] if t)

    if not pro:
        st.markdown(
            '<div class="gr-draft"><div class="gr-draft-hd">'
            '<div class="gr-draft-k">Pro · we write the reply for you</div>'
            f'<div class="gr-draft-t">{html.escape(g.get("title") or "")}</div></div>'
            '<div class="gr-draft-lock">On <b>Pro</b> this box already contains a '
            'ready-to-send reply for this exact gig, written from your profile, '
            'so you answer in seconds instead of staring at a blank message.</div>'
            '</div>', unsafe_allow_html=True)
        return

    text = drafts.load(gid) or pitch.draft_pitch(
        g, prof, resume_text=st.session_state.get("_resume_text", ""),
        who=paths.get_scope())
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
        st.link_button("Open the gig  ↗", g.get("url") or "#", width="stretch")
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
            f'<div class="gr-dash-head">'
            f'<h2>{"Welcome back, " + html.escape(_who) if _who else "Your board"}</h2>'
            f'<p>Search everything, or pick up where the board left off.</p>'
            f'</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Nothing loaded yet. Pop over to **Gigs** and hit *Check for new gigs* — "
                "we'll pull the latest for you.")
        return

    # The search sits right under the headline: pick what you do, and the
    # numbers below rearrange around you.
    hero_search()

    st.write("")
    live_stats()

    # Category browsing moved to the Gigs page (where people are actually
    # looking), so the dashboard top stays a clean headline + search + stats.
    st.divider()
    arrivals_pill()
    draft_showcase(pro)
    if prof.get("skills"):
        # .gr-sect marks a heading that STARTS A NEW SECTION mid-page, so it
        # earns the big gap above it. Page titles deliberately don't carry it —
        # they'd push the first line of every view down the screen. (Marker goes
        # after the text: "###" only parses at the start of a line.)
        st.markdown('### Picked for <span class="gr-accent">you</span>'
                    '<span class="gr-sect"></span>', unsafe_allow_html=True)
        srcs = sorted(df["source"].unique())
        top = scored(apply_language(apply_city_lock(
            apply_filters(df, prof["skills"], ["Small", "Medium", "Large"],
                          srcs, False, "")))).head(DASH_FEED)
    else:
        st.markdown('### Fresh off the <span class="gr-accent">boards</span>'
                    '<span class="gr-sect"></span>', unsafe_allow_html=True)
        top = apply_language(apply_city_lock(df)).head(DASH_FEED)

    if top.empty:
        st.caption("Nothing's clicking yet — try adding a few more skills on the Profile "
                   "tab. The board moves fast; there'll be more any minute.")
    for r in top.to_dict("records"):
        gig_card(r, pro)

    # The feedback box used to sit here, directly under the gigs. A form asking
    # "what would make this better?" at the end of the reading path interrupts
    # the one thing someone came to do — read gigs. It lives on the Profile page
    # now, where settings and account things belong, and a quiet line points at
    # it from here instead.
    if not (ACCESS["signed_in"] and ACCESS["plan"] == "pro"):
        st.divider()
        signup_card("dashboard")


def view_gigs(pro):
    # The page used to open with SEVEN stacked control rows of different shapes
    # before a single gig appeared: heading, a boxy refresh button, search,
    # browse chips, location pills, a full-width expander, then the result count.
    # Refresh belongs with the title, not in the reading path — it's a
    # maintenance action, not something you do before every search.
    _h, _r = st.columns([3.4, 1], vertical_alignment="center")
    # The marker span goes AFTER the heading: a markdown "###" only parses at the
    # very start of the line, so leading HTML turns it into literal text.
    _h.markdown('### The whole <span class="gr-accent">board</span>'
                '<span class="gr-tools"></span>', unsafe_allow_html=True)
    with _r:
        if st.button("Refresh", key="checknew", width="stretch"):
            with st.spinner("Scanning the web for fresh gigs…"):
                ingest.run()
            _public_feed.clear()         # new gigs should show at once, not in 45s
            st.rerun()

    if df.empty:
        st.info("Nothing here yet — hit **Refresh** and we'll grab the latest.")
        return

    # Search and field sit on ONE row: they are the same decision ("what work?"),
    # so they belong together rather than as two stacked full-width bars.
    _sc, _fc = st.columns([3, 2], vertical_alignment="center")
    _sq = _sc.text_input("Search gigs", value=st.session_state.get("searchq", ""),
                         placeholder="Search gigs — figma, shopify, medical…",
                         label_visibility="collapsed", key="gigsearch")
    kw = (_sq or "").strip().lower()
    if kw != st.session_state.get("searchq", ""):
        st.session_state["searchq"] = kw

    category_strip(_fc)

    # Prominent location lens — the first cut most people want to make.
    _all, _rem, _loc = location_counts(df)
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
        urgent = st.checkbox("Urgent only")
        if skills and set(skills) != set(ALL_SKILLS) and set(skills) != set(prof.get("skills") or []):
            if st.button("Save these as my skills", key="savefilterskills"):
                prof["skills"] = skills
                profile_mod.save(prof)
                note("click", "filter:saveskills")
                st.rerun()

    with st.spinner(f"Searching for “{kw}”…" if kw else "Loading the board…"):
        view = apply_filters(df, skills, sizes, sources, urgent, kw)
        view = apply_language(apply_city_lock(view))
        view = apply_location(view, loc_mode)
        if pro:
            view = scored(view)
        if kw:
            # Best matches first — after scoring, so relevance to what they
            # actually typed wins over a generic fit score.
            view = rank_by_relevance(view, kw)

    # Answer the search plainly, including when it finds nothing — an empty
    # board with no explanation reads as broken rather than as "no matches".
    if kw:
        sc1, sc2, _ = st.columns([3.1, 1, 5.9], vertical_alignment="center")
        sc1.markdown(f'<span class="gr-qf">▸ {len(view):,} result'
                     f'{"" if len(view) == 1 else "s"} for '
                     f'<b>{html.escape(kw)}</b></span>', unsafe_allow_html=True)
        if sc2.button("Clear", key="clearsearch", width="stretch"):
            st.session_state["searchq"] = ""
            st.session_state.pop("gigsearch", None)
            st.rerun()
        if view.empty:
            st.info(f"Nothing matches **{kw}** right now. Try a broader word, or "
                    "browse by category from the dashboard.")

    # Quick-filter arriving from a Dashboard stat click
    qf = st.session_state.get("quickfilter", "")
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
            f'<a class="gr-cat" href="?nav=gigs&cat={quote(s)}" target="_self">'
            f'{html.escape(s)}<span class="n">{vc.get(s, 0):,}</span></a>'
            for s in subs if vc.get(s, 0)
        )
        if subchips:
            st.markdown('<div style="font-size:12px;color:#7c828d;margin:2px 0 5px">'
                        'Narrow to a sub-category:</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="gr-cats" style="justify-content:flex-start">'
                        f'{subchips}</div>', unsafe_allow_html=True)

    note = f"**{len(view):,}** gigs for you"
    if merged:
        note += f"  ·  {merged} duplicates tidied up"
    if len(view) > FEED_CAP:
        note += f"  ·  showing the freshest {FEED_CAP}"
    st.caption(note)

    if view.empty:
        st.info("Nothing matches those filters right now — try widening them, or hit "
                "**Check for new gigs** up top.")
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


def view_market(pro):
    st.markdown('### What gigs like yours are <span class="gr-accent">paying</span>',
                unsafe_allow_html=True)
    if not pro:
        st.info("This one's a **Pro** perk. See what work like yours actually pays, "
                "what's hot this week, and which posts are lowballing — pulled from "
                "everywhere at once. You can switch to Pro any time from your **Profile**.")
        return
    if not stats:
        st.info("Nothing to crunch yet — grab some gigs first.")
        return

    st.caption("Straight from the whole board — no guessing.")
    total = sum(d["count"] for d in stats.values())
    hottest = market.hot_skills(stats)[0]
    priced = [(s, d["typical"]) for s, d in stats.items() if d["typical"]]
    toprate = max(priced, key=lambda x: x[1]) if priced else ("—", 0)
    stat_cards([
        ("Gigs on the board", f"{total:,}", "#E8933A"),
        ("Skills tracked", f"{len(stats)}", "#4C8DFF"),
        ("Hottest skill", hottest[0], "#35B37E", "small"),
        ("Top typical rate", f"${toprate[1]:,}", "#B889F0"),
    ])
    # sequential amber ramp for budget size (light = small, deep = large)
    BUDGET_SCALE = alt.Scale(domain=["Small", "Medium", "Large"],
                             range=["#F3C07A", "#E8933A", "#A85D1B"])
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**What's hot right now**")
        dd = (pd.DataFrame([{"Skill": s, "Gigs": d["count"]} for s, d in stats.items()])
              .sort_values("Gigs", ascending=False).head(8))
        chart = alt.Chart(dd).mark_bar(color="#E8933A", cornerRadiusEnd=4).encode(
            x=alt.X("Gigs:Q", title=None),
            y=alt.Y("Skill:N", sort="-x", title=None),
            tooltip=["Skill", "Gigs"]).properties(height=300)
        st.altair_chart(chart, width="stretch")
        # A chart that tells you Development is busiest and then leaves you to
        # go find it is half an answer. These are the same rows, as links.
        # Deliberately NOT Altair's own click-selection: that routes through a
        # rerun-on-select round trip, and these are plain anchors using the
        # ?nav=gigs&cat= routing the category chips already use — no new
        # mechanism, and they work on a phone where a bar is a poor tap target.
        _hot = "".join(
            f'<a class="gr-cat" href="?nav=gigs&cat={quote(row.Skill)}" target="_self">'
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
        chart2 = alt.Chart(rr).mark_bar(color="#4C8DFF", cornerRadiusEnd=4).encode(
            x=alt.X("Budget:Q", title=None, axis=alt.Axis(format="$,d")),
            y=alt.Y("Skill:N", sort="-x", title=None),
            tooltip=["Skill", alt.Tooltip("Budget", format="$,d")]).properties(height=300)
        st.altair_chart(chart2, width="stretch")

    st.write("")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Budget mix** — how the board splits")
        bm = df["size_tier"].value_counts().rename_axis("Budget").reset_index(name="Gigs")
        donut = alt.Chart(bm).mark_arc(innerRadius=58, stroke="#0e1117",
                                       strokeWidth=2).encode(
            theta=alt.Theta("Gigs:Q"),
            color=alt.Color("Budget:N", scale=BUDGET_SCALE,
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Budget", "Gigs"]).properties(height=300)
        st.altair_chart(donut, width="stretch")
    with c4:
        # This was a "Where the gigs come from" donut, which put every board we
        # read on screen with its share of the pie — a labelled map of exactly
        # where to go instead of us. Same rule that took the sources out of the
        # FAQ and the landing page (FEEL.md §7): the feed is the product,
        # provenance is plumbing. Urgency is the thing a freelancer can act on.
        st.markdown("**How fast you need to move**")
        urg = (df["urgency"].fillna("").replace("", "Standard")
               .value_counts().rename_axis("Pace").reset_index(name="Gigs"))
        urg_donut = alt.Chart(urg).mark_arc(innerRadius=58, stroke="#0e1117",
                                            strokeWidth=2).encode(
            theta=alt.Theta("Gigs:Q"),
            color=alt.Color("Pace:N",
                            scale=alt.Scale(domain=["Standard", "Urgent"],
                                            range=["#4C8DFF", "#E96250"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Pace", "Gigs"]).properties(height=300)
        st.altair_chart(urg_donut, width="stretch")

    st.write("")
    st.markdown("**Where the big budgets sit** — gigs by skill, split by budget")
    top_skills = df["job_type"].value_counts().head(8).index.tolist()
    sk = (df[df["job_type"].isin(top_skills)]
          .groupby(["job_type", "size_tier"]).size().reset_index(name="Gigs"))
    stacked = alt.Chart(sk).mark_bar().encode(
        x=alt.X("Gigs:Q", title=None),
        y=alt.Y("job_type:N", sort=top_skills, title=None),
        color=alt.Color("size_tier:N", scale=BUDGET_SCALE,
                        legend=alt.Legend(orient="bottom", title="Budget")),
        order=alt.Order("size_tier:N"),
        tooltip=["job_type", "size_tier", "Gigs"]).properties(height=330)
    st.altair_chart(stacked, width="stretch")
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
    st.markdown('#### Forward your <span class="gr-accent">newsletters</span>'
                '<span class="gr-soon">Coming soon</span>',
                unsafe_allow_html=True)
    if not inbox.enabled():
        st.caption("Your own address for forwarding the mailing lists and "
                   "newsletters the job boards never see. We're finishing it off.")
        return
    if not ACCESS["signed_in"]:
        st.caption("Sign in and you get your own address to forward mailing "
                   "lists and newsletters to. Whatever you send lands on your "
                   "board, and only yours.")
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


def view_profile(pro):
    st.markdown('### Tell us about <span class="gr-accent">you</span>',
                unsafe_allow_html=True)
    st.caption("The more we know, the better the gigs we surface for you.")

    # No "Signed in as …" line and no Sign out button up here: the account menu
    # in the top bar already shows both, and repeating them at the top of the
    # page pushed the actual form down for no new information. Sign out now
    # sits at the very bottom, where a destructive action belongs. The setup
    # progress bar went with them — a percentage on an optional form reads as
    # homework, and every field on it is already optional by design.
    if not ACCESS["signed_in"]:
        st.caption("We'll use this right away. Sign in from the **Dashboard** to "
                   "keep it for next time.")

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
            st.caption("Rates, filters, and a couple of details for your replies. "
                       "Skip anything — you can come back to it whenever.")
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
            st.success("Got it — we've tuned things to you.")
            st.rerun()

    if pro:
        st.divider()
        resume_card()

    st.divider()
    alerts_section(pro)

    st.divider()
    inbox_card()

    st.divider()
    plan_card()

    st.divider()
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
                st.query_params.clear()
                if auth.google_email(st):
                    st.logout()
                st.rerun()


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
        _when = (datetime.now(timezone.utc) + timedelta(days=days))
        # "Ends", never "renews": nothing is charged today, and implying a
        # billing date we don't have would be the kind of claim FEEL.md §7
        # exists to prevent.
        renews = f"Ends {_when.strftime('%-d %B %Y')}"

    if ACCESS["plan"] == "pro" and not days:
        name, price, note = "Pro", "On the house", "Thanks for backing us."
    elif ACCESS["pro"] and ACCESS.get("founding"):
        name, price, note = ("Pro · founding member", "Free for 60 days",
                             "Our thank-you to the people who backed it first.")
    elif ACCESS["pro"]:
        name, price, note = ("Pro · trial", "Free for 14 days",
                             "You drop back to Free when it ends, not charged.")
    else:
        name, price, note = ("Free", "$0 — the whole board",
                             "Every gig, every field, search and browse.")

    st.markdown(
        f'<div class="gr-plan">'
        f'<div class="gr-plan-top">'
        f'<div><div class="gr-plan-name">{html.escape(name)}</div>'
        f'<div class="gr-plan-note">{html.escape(note)}</div></div>'
        f'<div class="gr-plan-price">{html.escape(price)}'
        + (f'<span>{html.escape(renews)}</span>' if renews else "")
        + '</div></div></div>', unsafe_allow_html=True)

    if not ACCESS["pro"]:
        st.caption("**Pro** adds instant pings, drafted replies, picks ranked for "
                   "you, and what-it-pays market rates.")
        if ACCESS.get("can_trial"):
            if st.button("Try Pro free for 14 days", type="primary", key="trial_profile"):
                ok, msg = accounts.start_trial(ACCESS["email"])
                if ok:
                    st.rerun()
                st.warning(msg)
        elif ACCESS.get("trialed"):
            st.caption("Your 14-day Pro trial has been used. We'll email you the "
                       "moment paid Pro opens.")
        return

    # The way out. Owner accounts are permanently Pro (accounts.status), so
    # there's nothing to downgrade and the control would do nothing.
    if not accounts.is_owner(ACCESS.get("email")):
        _d1, _ = st.columns([1, 2])
        with _d1:
            if st.button("Switch to Free", width="stretch", key="downgrade"):
                st.session_state["_confirm_downgrade"] = True
        if st.session_state.get("_confirm_downgrade"):
            st.caption("You'll keep the whole board, search and your profile. "
                       "You'd lose ranked picks, drafted replies, market rates "
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
    acc, is_new = accounts.sign_in(email, source=where, campaign=CAMPAIGN)
    if not acc:
        return False, "That doesn't look like an email address."
    st.session_state["_tok"] = acc["token"]
    st.query_params["u"] = acc["token"]
    note("signup" if is_new else "signin", where)
    return True, ""


_FEAT = ('<div class="gr-feat"><span>Ranked picks</span><span>Drafted replies</span>'
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
    if a["signed_in"] and a["plan"] == "pro":
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
                    '<b>$12/mo</b> to keep ranked picks, drafted replies and '
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
                        f'{_FEAT}'
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
        return

    # Signed in with a lapsed trial → keep-Pro interest. Not signed in → sign in
    # (which lands on Free; the trial above is where Pro gets chosen).
    signed = a["signed_in"]
    with st.container(border=True):
        if signed:
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Keep Pro after your trial</div>'
                        f'{_FEAT}', unsafe_allow_html=True)
            # No billing is wired yet, so "I want Pro" honestly records interest.
            if st.session_state.get("_upgrade_noted"):
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
                st.markdown('<div class="gr-cta-fine">$12/mo when it launches · '
                            'nothing charged now</div>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Sign in to save your board</div>'
                        '<div class="gr-cta-s">Keeps your profile and picks for next '
                        'time. Free, and Pro is there to try whenever you want it.'
                        '</div>', unsafe_allow_html=True)
            # Email first — any provider, their choice — with Google as a
            # one-tap option beneath when it's configured.
            with st.form(f"signup_{where}", clear_on_submit=False, border=False):
                c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
                with c1:
                    email = st.text_input("Email", placeholder="you@example.com",
                                          label_visibility="collapsed")
                with c2:
                    sent = st.form_submit_button("Sign in", type="primary",
                                                 width="stretch")
            if sent:
                ok, msg = sign_in_here(email, where)
                if ok:
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


def view_signin():
    """
    A focused sign-in page. The account menu's "Sign in" used to point at the
    dashboard, where the actual sign-in card sits far down the page — so it read
    as "nothing happened, back to home". This gives the click a real destination.
    """
    if ACCESS["signed_in"]:
        st.markdown('### You\'re <span class="gr-accent">signed in</span>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<div class="gr-confirm"><span class="gr-confirm-dot"></span>'
            f'<span class="gr-confirm-txt">Signed in as '
            f'<b>{html.escape(ACCESS["email"] or "")}</b></span></div>',
            unsafe_allow_html=True)
        st.write("")
        _l, _c, _r = st.columns([1, 1.6, 1])
        with _c:
            # The board, not the profile: someone who just signed in came to
            # look at gigs, and the profile is a detour they can take from the
            # account menu whenever they actually want it.
            if st.button("Go to your board", type="primary", width="stretch"):
                st.query_params["nav"] = "dashboard"
                st.rerun()
        return

    st.markdown('### Sign in to <span class="gr-accent">Nabbly</span>',
                unsafe_allow_html=True)
    st.caption("Save your profile and picks, get alerts, and keep your board "
               "across visits. No password.")
    _l, _c, _r = st.columns([1, 2, 1])
    with _c:
        with st.container(border=True):
            st.markdown('<span class="gr-cta-mark"></span>'
                        '<div class="gr-cta-h">Welcome</div>'
                        '<div class="gr-cta-s">Your board, saved and sorted to you.'
                        '</div>', unsafe_allow_html=True)
            # Any email, any provider — people keep full say over how they sign
            # up. Google sits below as a one-tap option, not the only door.
            with st.form("signin_page_form", clear_on_submit=False, border=False):
                email = st.text_input("Email", placeholder="you@example.com",
                                      label_visibility="collapsed")
                sent = st.form_submit_button("Continue with email", type="primary",
                                             width="stretch")
            if sent:
                ok, msg = sign_in_here(email, "signin")
                if ok:
                    # Just rerun — do NOT set ?nav here. sign_in_here put the
                    # token in the URL (?u=), and the nav dispatch clears the
                    # query string; setting nav would wipe the token that
                    # keeps them signed in on a later reload. On this rerun
                    # they're signed in and see the signed-in state below.
                    st.rerun()
                st.warning(msg)
            st.markdown('<div class="gr-cta-fine">Works with any email · keep the '
                        'link we put in your address bar to sign back in</div>',
                        unsafe_allow_html=True)
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
    told properly: the problem, how Nabbly works, and what's free versus Pro.
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
        '<li>We even <b>draft the first reply</b> from the actual post, so you '
        'answer in seconds instead of staring at a blank message.</li>'
        '</ol>'

        # Two cards, not one paragraph: someone deciding between plans should be
        # able to compare them at a glance rather than parse a wall of prose.
        '<h2>Free, and Pro</h2>'
        '<div class="gr-ab-plans">'
        '<div class="gr-ab-plan">'
        '<div class="gr-ab-name">Free</div>'
        '<div class="gr-ab-sub">The whole board, no catch</div>'
        '<ul>'
        '<li>Every gig, every field</li>'
        '<li>Search and browse it all</li>'
        '<li>Your profile, so the board sorts around you</li>'
        '<li>Fresh gigs, minutes after they\'re posted</li>'
        '</ul></div>'
        '<div class="gr-ab-plan pro">'
        '<div class="gr-ab-name">Pro</div>'
        '<div class="gr-ab-sub">The edge that helps you reply first</div>'
        '<ul>'
        '<li>Gigs ranked by how well they fit you</li>'
        '<li>Drafted replies written from the actual post</li>'
        '<li>Instant alerts on the channel you choose</li>'
        '<li>Market rates, so you price right</li>'
        '</ul></div>'
        '</div>'
        '<p>The first 50 members get two months of Pro free, our thank-you to '
        'the people who back it first. After that, Pro is free to try for 14 '
        'days whenever you want it, and you choose if and when to start.</p>'

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


_FAQ = [
    ("Where do the gigs come from?",
     "Public job boards and hiring communities: We Work Remotely, RemoteOK, "
     "Remotive, Jobicy, Arbeitnow, Freelancer.com and the hiring subreddits. "
     "We read them continuously and put everything in one place, so you're not "
     "keeping ten tabs open."),
    ("How fresh are they?",
     "The board refreshes itself every couple of minutes, around the clock. "
     "Most gigs show up here within minutes of being posted, which is the "
     "whole point — the person who answers first usually gets the work."),
    ("Do I have to sign up?",
     "No. The entire board is free to search and browse without an account. "
     "Signing in saves your profile so the board can sort itself around you. "
     "Pro is free to try for 14 days whenever you want it; you choose if and "
     "when to start, so you're never dropped into a trial you didn't ask for."),
    ("What's the difference between Free and Pro?",
     "Free gives you every gig from every source, search and browse. Pro adds "
     "the parts that help you reply first: gigs ranked by how well they fit "
     "you, drafted replies, market rate data, and instant alerts."),
    ("How do the alerts work?",
     "You pick the channel — phone push, Slack or Discord, Telegram, SMS or "
     "email — plus how often you'll tolerate being pinged, which sources "
     "count, and how many gigs per message. Then new matches come to you "
     "instead of you refreshing a page."),
    ("Do you really write the reply for me?",
     "Yes, on Pro. It reads the actual post and your profile and drafts a "
     "reply you can send or edit. It's a starting point that beats staring at "
     "a blank message, not a promise you'll never touch it."),
    ("Are the gigs verified?",
     "No, and be careful. These are public postings gathered as they were "
     "written; we classify and rank them, we don't vet the people behind "
     "them. Treat anything asking for money up front or unpaid \"test work\" "
     "the way you would anywhere else."),
    ("What do you do with my data?",
     "We keep your email so you can sign back in, plus the profile you fill "
     "in so we can match gigs to you. Analytics are counted on our own server "
     "with no third-party trackers and no advertising cookies. Nothing is "
     "sold, and nothing is shared."),
    ("Why is a gig in the wrong category?",
     "Categories are worked out from the words in each post, so it gets most "
     "of them right and occasionally gets one wrong. If you spot a bad one, "
     "the feedback box on the dashboard goes straight to the person building "
     "this."),
]


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
        if sent:
            code = {"Useful": "good", "It's ok": "ok", "Not for me": "bad"}.get(rating, "")
            if people.add_feedback(msg, email=ACCESS.get("email", ""),
                                   rating=code, page=where):
                st.session_state[f"_fb_sent_{where}"] = True
                note("click", f"feedback:{code or 'none'}")
                st.rerun()
            st.warning("Add a line about what's not working and we'll get it.")


# ---------------------------------------------------------------------------
# Admin: who showed up. Visit ?admin=<ADMIN_KEY>  (see analytics.py)
# ---------------------------------------------------------------------------
def view_admin():
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
        st.caption(f"Would pay $12/month — yes: **{_pay.get('yes', 0)}** · "
                   f"maybe: **{_pay.get('maybe', 0)}** · no: **{_pay.get('no', 0)}**")

    acc = accounts.stats()
    st.markdown("#### Accounts & trials")
    stat_cards([
        ("Accounts", f"{acc['accounts']:,}", "#E8933A"),
        ("On a live trial", f"{acc['on_trial']:,}", "#5b9dff"),
        ("Trial ended", f"{acc['expired']:,}", "#e5675f"),
        ("Came back", f"{acc['returning']:,}", "#35b37e"),
    ])
    # Whether profiles will actually survive the next redeploy. This is the one
    # signal that tells you if the Supabase connection string is really wired.
    if store.enabled():
        if store.healthy():
            st.success("Durable backup: **connected**. Profiles and accounts "
                       "survive redeploys.")
        else:
            st.error("Durable backup: **configured but unreachable**. Check the "
                     "DATABASE_URL value in Render.")
            _err = store.last_error()
            if _err:
                st.caption(f"Reason: `{_err}`")
    else:
        st.warning("Durable backup: **off**. Set DATABASE_URL (Supabase) in "
                   "Render, or profiles reset on every deploy.")

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
_TABS = ["Dashboard", "Gigs", "Market"]
# Pages that live outside the tab strip: reachable by ?nav=, linked from the
# footer and the account menu, and they never light up a tab.
_SIDE_PAGES = {"profile": "Profile", "about": "About", "faq": "FAQ",
               "signin": "Sign in", "admin": "Admin",
               "privacy": "Privacy", "terms": "Terms"}

# The admin panel replaces the whole page — nothing else needs to render.
# Two ways in: the secret ?admin= key (works signed out), or simply being signed
# in as an owner account, so the founder doesn't have to keep a URL around.
IS_ADMIN = ((analytics.ADMIN_KEY
             and st.query_params.get("admin", "") == analytics.ADMIN_KEY)
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
                    analytics.track("click", f"{_kind}:{_val}", SID)
                    break
        st.session_state["_page"] = ""      # a real tab leaves any info page
    st.query_params.clear()

_bcol, _ncol, _rcol = st.columns([2.0, 4.9, 1.3], vertical_alignment="center")
with _bcol:
    # Clicking the mark goes home — the way out when someone has filtered
    # themselves into a corner three pages deep.
    st.markdown(f'<a class="gr-home" href="?nav=dashboard" target="_self" '
                f'title="Back to the dashboard">{LOGO_SVG}</a>',
                unsafe_allow_html=True)
# Which tab is live is ours to track now, rather than something we read back
# out of a component. ?nav= (set by the links below, and by every stat card and
# category chip) writes _navidx during dispatch above, so a deep link and a tab
# click land in the same place — no more manual_select juggling.
selected = _TABS[st.session_state.get("_navidx", 0)]
with _ncol:
    _side = bool(st.session_state.get("_page"))
    _links = "".join(
        f'<a class="{"on" if t == selected and not _side else ""}" '
        f'href="?nav={t.lower()}" target="_self">{t}</a>'
        for t in _TABS)
    st.markdown(f'<div class="gr-nav">{_links}</div>', unsafe_allow_html=True)

# Leaving an info page is handled where ?nav= is dispatched: a tab link clears
# _page there, so the old "did the component's value change?" bookkeeping the
# iframe menu needed is gone.
_page = st.session_state.get("_page", "")
_on_profile = _page == "profile"
active = _SIDE_PAGES.get(_page) or selected

with _rcol:
    _name = (prof.get("name") or "").strip()
    _acls = "gr-avatar active" if _on_profile else "gr-avatar"
    _href = f"?nav={selected.lower()}" if _on_profile else "?nav=profile"
    # The plan shown here used to read a session key that no longer exists, so
    # it said "Free plan" to everyone — including people mid-trial. Read the
    # real entitlement instead.
    if ACCESS["signed_in"]:
        _email = ACCESS.get("email", "")
        _who = _name or _email.split("@")[0] or "Your account"
        if ACCESS["plan"] == "pro":
            _plan = "Pro"
        elif ACCESS["pro"]:
            _d = ACCESS["days_left"]
            _tag = "Founding Pro" if ACCESS.get("founding") else "Pro trial"
            _plan = f"{_tag} · {_d} day{'s' if _d != 1 else ''} left"
        else:
            _plan = "Free"
        _last = '<a href="?signout=1" target="_self">Sign out</a>'
    else:
        _who, _plan = _name or "Your account", "Not signed in"
        _last = '<a href="?nav=signin" target="_self">Sign in</a>'
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
        f'<a class="{_acls}" href="{_href}" target="_self" title="Your account">{_init}</a>'
        f'<div class="gr-menu">'
        f'<div class="gr-menu-hd">{html.escape(_who)}'
        f'<span>{html.escape(_plan)}</span></div>'
        # One entry, not two. "Your profile" and "Location & settings" were
        # different labels on the identical ?nav=profile link, which reads as a
        # menu with a broken item. Profile genuinely IS the settings page now —
        # it holds your details, location, alerts, resume and plan.
        f'<a href="?nav=profile" target="_self">Profile &amp; settings</a>'
        # Owners only — everyone else never sees this link exists.
        + (f'<a href="?nav=admin" target="_self">Admin</a>' if IS_ADMIN else '') +
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
elif active == "Market":
    view_market(PRO)
elif active == "Profile":
    view_profile(PRO)
elif active == "About":
    view_about()
elif active == "FAQ":
    view_faq()
elif active == "Sign in":
    view_signin()
elif active == "Privacy":
    view_legal("privacy")
elif active == "Terms":
    view_legal("terms")

st.markdown(
    '<div class="gr-footer">'
    '<span class="brand">Nabbly</span>'
    '<span class="tag">Every gig. The moment it drops.</span>'
    '<div class="foot-links">'
    '<a class="foot-link" href="?nav=about" target="_self">About</a>'
    '<a class="foot-link" href="?nav=faq" target="_self">FAQ</a>'
    '<a class="foot-link" href="?nav=privacy" target="_self">Privacy</a>'
    '<a class="foot-link" href="?nav=terms" target="_self">Terms</a>'
    '</div>'
    '<span class="meta">OneLonelyCow · © 2026</span>'
    '</div>', unsafe_allow_html=True)

"""
app.py — Dartly.

Made for freelancers, by freelancers. An icon-navigated app: Dashboard (welcome +
your picks), Gigs (the whole board), Market (what work pays), Alerts, and Profile
(you + your plan).

Run:   streamlit run app.py
"""
import os
import re
import html
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import pandas as pd
import altair as alt
import streamlit as st
from streamlit_option_menu import option_menu

from dotenv import load_dotenv
load_dotenv()

import db
import config
import ingest
import alerts
import pitch
import market
import score
import location
import drafts
import refresh
import profile as profile_mod

BASE = Path(__file__).parent

st.set_page_config(page_title="Dartly",
                   page_icon=str(BASE / "assets" / "favicon.png"), layout="wide",
                   initial_sidebar_state="collapsed")

# --- a little house style so cards/pills read as one cohesive, non-"code" look ---
st.markdown("""
<style>
.gr-stats{display:flex;gap:14px;flex-wrap:wrap;margin:2px 0 4px}
.gr-stat{flex:1;min-width:150px;background:#15181d;border:1px solid #262a31;
  border-radius:14px;padding:15px 16px 16px;position:relative;overflow:hidden}
.gr-stat .accent{position:absolute;left:0;top:14px;bottom:14px;width:3px;border-radius:0 4px 4px 0}
.gr-stat .l{font-size:12.5px;color:#98a0ab;font-weight:500;margin:0 0 9px}
.gr-stat .n{font-size:31px;font-weight:600;color:#f2f4f7;line-height:1;
  font-variant-numeric:tabular-nums}
.gr-stat .n.small{font-size:20px}
a.gr-title{font-size:19px;font-weight:600;color:#eaeef4 !important;
  text-decoration:none !important;line-height:1.35;letter-spacing:-.1px}
a.gr-title:hover{color:#E8933A !important;text-decoration:underline !important;
  text-decoration-color:rgba(232,147,58,.55);text-underline-offset:3px}
.gr-new{display:inline-block;font-size:10px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;color:#69d7a1;background:rgba(53,179,126,.13);
  border:1px solid rgba(53,179,126,.32);border-radius:6px;padding:1px 7px;
  vertical-align:2px;margin-right:9px}
.gr-pills{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 8px}
.gr-pill{font-size:12px;font-weight:500;padding:3px 11px;border-radius:999px;
  background:#22262e;color:#cdd3dc;border:1px solid #333845;line-height:1.6}
.gr-pill.match{background:rgba(232,147,58,.18);color:#f4b374;border-color:rgba(232,147,58,.5)}
.gr-pill.urgent{background:rgba(233,98,80,.18);color:#f2a08f;border-color:rgba(233,98,80,.5)}
.gr-pill.low{background:rgba(212,160,60,.16);color:#e2bd7c;border-color:rgba(212,160,60,.4)}
.gr-pill.loc{background:rgba(76,141,255,.15);color:#8fb6ff;border-color:rgba(76,141,255,.42)}
.gr-pill.locnear{background:rgba(94,196,120,.16);color:#84d99b;border-color:rgba(94,196,120,.45)}
.gr-pill.locoff{background:#1c1f26;color:#7c828d;border-color:#2e333d}
.gr-why{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 11px}
.gr-why .lead{font-size:10px;font-weight:600;letter-spacing:.8px;
  text-transform:uppercase;color:#6d747f;margin-right:2px}
.gr-why-chip{font-size:11px;font-weight:500;color:#caa06e;
  background:rgba(232,147,58,.07);border:1px solid rgba(232,147,58,.18);
  border-radius:999px;padding:2px 10px}
.gr-hero{text-align:center;max-width:860px;margin:2px auto 6px;padding:14px 16px 6px;
  background:radial-gradient(ellipse 640px 260px at 50% -8%,rgba(232,147,58,.11),transparent 72%)}
.gr-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:11.5px;font-weight:600;
  letter-spacing:.6px;text-transform:uppercase;color:#eaa662;
  background:rgba(232,147,58,.09);border:1px solid rgba(232,147,58,.18);
  border-radius:999px;padding:5px 14px;margin-bottom:22px}
.gr-eyebrow .dot{width:7px;height:7px;border-radius:50%;background:#37c689;
  animation:gr-ping 2s ease-in-out infinite}
@keyframes gr-ping{
  0%{box-shadow:0 0 0 0 rgba(55,198,137,.5)}
  70%{box-shadow:0 0 0 6px rgba(55,198,137,0)}
  100%{box-shadow:0 0 0 0 rgba(55,198,137,0)}}
.gr-h1{font-size:46px;line-height:1.06;font-weight:700;letter-spacing:-1.4px;
  color:#f5f7fa;margin:0 0 18px;text-wrap:balance}
.gr-h1 .accent{color:#E8933A}
.gr-sub{display:inline-block;font-size:17px;line-height:1.6;color:#99a1ac;
  max-width:600px;margin:0;text-align:center;text-wrap:pretty}
.gr-sub b{color:#ced4dc;font-weight:600}
.gr-stats{justify-content:center;max-width:940px;margin:6px auto 4px}
.gr-stat{transition:transform .15s ease,border-color .15s ease,background .15s ease}
.gr-stat:hover{transform:translateY(-3px);border-color:#3b4250;background:#181c22}
a.gr-stat{text-decoration:none;color:inherit;cursor:pointer;display:block}
.gr-stat .go{position:absolute;top:12px;right:14px;color:#5a616c;font-size:16px;
  opacity:0;transition:opacity .15s ease}
.gr-stat:hover .go{opacity:1;color:#E8933A}
.gr-qf{display:inline-block;font-size:13px;font-weight:500;color:#eaa662;
  background:rgba(232,147,58,.1);border:1px solid rgba(232,147,58,.28);
  border-radius:999px;padding:4px 13px}
.gr-cats{display:flex;flex-wrap:wrap;gap:9px;margin:2px 0 2px;
  max-width:980px;margin-left:auto;margin-right:auto;justify-content:center}
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
section[data-testid="stSidebar"],div[data-testid="stSidebarCollapsedControl"]{display:none!important}
.block-container,div[data-testid="stMainBlockContainer"]{padding-top:1.3rem!important}
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
.gr-footer .meta{color:#5a616c;font-size:11.5px}
/* In-copy links (e.g. URLs inside gig descriptions): on-brand amber + soft
   underline instead of Streamlit's default blue. Skips our own gr-* links. */
[data-testid="stMarkdownContainer"] a:not([class*="gr-"]){
  color:#e0a56a;text-decoration:underline;text-decoration-thickness:1px;
  text-decoration-color:rgba(232,147,58,.4);text-underline-offset:2.5px;
  transition:color .13s ease,text-decoration-color .13s ease}
[data-testid="stMarkdownContainer"] a:not([class*="gr-"]):hover{
  color:#E8933A;text-decoration-color:#E8933A}
/* --- Mobile (phones): scale the hero down, tidy the stacked top bar --- */
@media (max-width:640px){
  .gr-h1{font-size:30px!important;letter-spacing:-.7px!important;line-height:1.12!important;margin-bottom:13px!important}
  .gr-sub{font-size:15px!important;line-height:1.55!important}
  .gr-hero{padding:6px 4px 4px;margin-top:0}
  .gr-eyebrow{margin-bottom:15px;font-size:10px;letter-spacing:.4px;padding:4px 11px}
  .gr-stats{gap:9px}
  .gr-stat{min-width:calc(50% - 5px)}          /* two stat cards per row */
  .gr-stat .n{font-size:26px}
  /* pull the stacked logo / nav / avatar rows together and right-align account */
  div[data-testid="stHorizontalBlock"]:first-of-type{gap:.15rem!important}
  div[data-testid="stHorizontalBlock"]:first-of-type div[data-testid="stImage"]{margin:0 auto}
  .gr-acct{display:block;text-align:right}
  .gr-menu{top:44px}
}
</style>
""", unsafe_allow_html=True)

db.init_db()
prof = profile_mod.load()
ALL_SKILLS = list(config.JOB_TYPES.keys()) + ["Other / general"]
FEED_CAP = 60

# Demo default: always Pro. (Swap to an admin login on a real deployment.)
if "plan" not in st.session_state:
    st.session_state.plan = "Pro"
PRO = st.session_state.plan == "Pro"


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


def stat_cards(items):
    html = ('<div class="gr-stats" style="max-width:980px;margin-left:auto;'
            'margin-right:auto;justify-content:center">')
    for label, value, accent, *rest in items:
        cls = "n small" if "small" in rest else "n"
        href = next((x for x in rest if x and x != "small"), "")
        inner = (f'<div class="accent" style="background:{accent}"></div>'
                 f'<div class="l">{label}</div><div class="{cls}">{value}</div>')
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


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------
def load_feed():
    posts = db.all_posts(demand_only=True)
    if not posts:
        return pd.DataFrame(), 0
    df = pd.DataFrame(posts)

    def _key(title):
        toks = [w for w in re.findall(r"[a-z0-9]+", str(title).lower()) if len(w) > 2]
        return " ".join(sorted(set(toks)))

    df["_key"] = df["title"].map(_key)
    before = len(df)
    df = df[df["_key"] != ""].drop_duplicates(subset="_key", keep="first")
    return df, before - len(df)


db.ensure_seeded()  # first run on a fresh deploy loads the bundled seed.db
refresh.start()     # background fetcher: grows the feed while the app is in use
df, merged = load_feed()
stats = market.skill_stats(df.to_dict("records")) if not df.empty else {}


def apply_filters(data, skills, sizes, sources, urgent_only, keyword):
    if data.empty:
        return data
    mask = (data["job_type"].isin(skills) & data["size_tier"].isin(sizes)
            & data["source"].isin(sources))
    if urgent_only:
        mask &= data["urgency"] == "Urgent"
    if keyword:
        mask &= (data["title"].str.lower().str.contains(keyword, na=False)
                 | data["body"].str.lower().str.contains(keyword, na=False))
    mutes = [m.strip().lower() for m in (prof.get("mute", "") or "").split(",") if m.strip()]
    if mutes:
        text_l = (data["title"].fillna("") + " " + data["body"].fillna("")).str.lower()
        for m in mutes:
            mask &= ~text_l.str.contains(re.escape(m), na=False)
    return data[mask]


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
    st.session_state[key] = pitch.draft_pitch(gig, prof)
    st.session_state[f"_saved_{gig['id']}"] = False


def gig_card(r, pro):
    with st.container(border=True):
        new = '<span class="gr-new">New</span>' if r.get("is_new") == 1 else ""
        title = html.escape(r.get("title") or "(no title)")
        url = html.escape(r.get("url") or "", quote=True)
        st.markdown(f'{new}<a class="gr-title" href="{url}" target="_blank">{title}</a>',
                    unsafe_allow_html=True)

        badge_items = []
        if pro and r.get("_score") is not None:
            badge_items.append((f"🎯 {int(r['_score'])}% match", "match"))
        badge_items += [(r["job_type"], ""), (f"{r['size_tier']} budget", ""),
                        (r["source"], "")]
        # where can this be done — and can *you* take it?
        loc = location.tag(r)
        if location.is_local(r, prof.get("city")):
            badge_items.append((f"📍 Near {prof.get('city')}", "locnear"))
        else:
            loc_lbl = location.label(loc)
            if loc_lbl:
                ok = location.eligible(loc, location.country_region(prof.get("country")))
                if ok:
                    badge_items.append((loc_lbl, "loc"))
                else:
                    # geo-locked to a region you're not in — make that obvious
                    badge_items.append((f"🔒 {loc['restrict']}-only · can't apply", "locoff"))
        if r.get("urgency") == "Urgent":
            badge_items.append(("🔥 Urgent", "urgent"))
        if pro:
            lb, reason = market.lowball(r, stats, prof)
            if lb:
                badge_items.append((f"💸 {reason}", "low"))
        pills(badge_items)

        if pro and r.get("_reasons"):
            chips = "".join(f'<span class="gr-why-chip">{html.escape(x)}</span>'
                            for x in r["_reasons"])
            if chips:
                st.markdown('<div class="gr-why"><span class="lead">why</span>'
                            + chips + "</div>", unsafe_allow_html=True)

        body = smart_trim(r.get("body") or "")
        if body:
            # escape $ so "$30 - $250" isn't rendered as a LaTeX formula
            st.write(body.replace("$", "\\$"))
        st.caption(f"Posted {human_time(r.get('posted_at'))}")

        gid = r["id"]
        saved_exists = drafts.has(gid)
        label = "✍️ Draft my reply" if pro else "✍️ Draft my reply  🔒 Pro"
        if pro and saved_exists:
            label += "  ·  📝 saved"
        with st.expander(label):
            if pro:
                key = f"pitch_{gid}"
                # Seed once: your saved edit if you have one, else a fresh draft.
                if key not in st.session_state:
                    st.session_state[key] = drafts.load(gid) or pitch.draft_pitch(r, prof)
                st.text_area("Your draft", height=240, key=key,
                             label_visibility="collapsed")
                bc1, bc2 = st.columns(2)
                bc1.button("💾 Save draft", key=f"save_{gid}", use_container_width=True,
                           on_click=_save_draft, args=(gid, key))
                bc2.button("🔄 Start fresh", key=f"regen_{gid}", use_container_width=True,
                           on_click=_regen_draft, args=(r, key),
                           help="Replace your edits with a new auto-draft")
                if st.session_state.pop(f"_saved_{gid}", False):
                    st.caption("Saved ✓ — your edits will be here when you come back. 🧡")
                elif saved_exists:
                    st.caption("Editing your saved draft. Tweak it, hit **Save**, and you're set.")
                else:
                    st.caption("Tweak it, save it, copy — and you're first in line. 🧡")
            else:
                st.caption("🔒 On **Pro**, we write a ready-to-send reply for this exact "
                           "gig — so you can fire back first, without staring at a blank "
                           "message. Upgrade any time from your **Profile**.")
                st.button("⭐ Upgrade to Pro", key=f"up_{r['id']}",
                          disabled=True, use_container_width=True)


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
    my = cur[cur["job_type"].isin(prof.get("skills"))] if prof.get("skills") else cur
    stat_cards([
        ("On the board now", f"{len(cur):,}", "#E8933A", "?nav=gigs"),
        ("Fresh · last 24h", f"{recent_count(cur, 24):,}", "#4C8DFF", "?nav=gigs&qf=recent"),
        ("In your wheelhouse", f"{len(my):,}", "#35B37E", "?nav=gigs&qf=mine"),
        ("Urgent", f"{int((cur['urgency'] == 'Urgent').sum()):,}", "#E96250",
         "?nav=gigs&qf=urgent"),
    ])


def category_strip():
    """A few BROAD category buckets (with live counts) so people can browse the
    board at a glance. Each links to a filtered Gigs view where they can drill
    into the specific sub-categories."""
    if df.empty:
        return
    counts = df["job_type"].value_counts().to_dict()
    groups = [(g, sum(counts.get(s, 0) for s in subs))
              for g, subs in config.CATEGORY_GROUPS.items()]
    groups = sorted([(g, n) for g, n in groups if n], key=lambda x: -x[1])
    if not groups:
        return
    st.markdown('<div style="text-align:center;color:#8a919c;font-size:13px;'
                'font-weight:600;letter-spacing:.02em;margin:2px 0 10px">'
                'Or browse by category</div>', unsafe_allow_html=True)
    chips = "".join(
        f'<a class="gr-cat" href="?nav=gigs&group={quote(g)}" target="_self">'
        f'{html.escape(g)}<span class="n">{n:,}</span></a>'
        for g, n in groups
    )
    st.markdown(f'<div class="gr-cats">{chips}</div>', unsafe_allow_html=True)


def view_dashboard(pro):
    n = len(df)
    eyebrow = "Live · new gigs land here in real time" if n else "Live · scanning the boards"
    st.markdown(
        '<div class="gr-hero">'
        f'<span class="gr-eyebrow"><span class="dot"></span>{eyebrow}</span>'
        '<h1 class="gr-h1">Every gig, the moment it drops.<br>'
        'You just <span class="accent">reply first.</span></h1>'
        "<p class=\"gr-sub\">Freelancing's enough of a hustle. We watch "
        "<b>every board and community</b> around the clock, then surface the gigs "
        "that fit you, from a quick $20 task to a full project.</p>"
        "</div>", unsafe_allow_html=True)

    if df.empty:
        st.info("Nothing loaded yet. Pop over to **Gigs** and hit *Check for new gigs* — "
                "we'll pull the latest for you.")
        return

    if not prof.get("skills"):
        st.warning("👋 **First time here?** Take 30 seconds on the **Profile** tab to tell "
                   "us what you do — then the gigs that actually fit you show up right here.")

    st.write("")
    live_stats()

    st.write("")
    category_strip()

    st.divider()
    if prof.get("skills"):
        st.markdown("### 🎯 Picked for you")
        srcs = sorted(df["source"].unique())
        top = scored(apply_filters(df, prof["skills"], ["Small", "Medium", "Large"],
                                   srcs, False, "")).head(5)
    else:
        st.markdown("### 🔥 Fresh off the boards")
        top = df.head(5)

    if top.empty:
        st.caption("Nothing's clicking yet — try adding a few more skills on the Profile "
                   "tab. The board moves fast; there'll be more any minute.")
    for r in top.to_dict("records"):
        gig_card(r, pro)


def view_gigs(pro):
    st.markdown("### 📡 The whole board")
    head = st.columns([1, 2])
    with head[0]:
        if st.button("🔄 Check for new gigs", use_container_width=True):
            with st.spinner("Scanning the web for fresh gigs…"):
                ingest.run()
            st.rerun()
    if df.empty:
        st.info("Nothing here yet — hit **Check for new gigs** and we'll grab the latest.")
        return

    # Prominent location lens — the first cut most people want to make.
    _all, _rem, _loc = location_counts(df)
    _CITY = (prof.get("city") or "").strip()
    _opts = [f"🌐 Everywhere · {_all}", f"🌍 Remote I can take · {_rem}",
             f"📍 {'Near ' + _CITY if _CITY else 'On-site / local'} · {_loc}"]
    _pick = st.segmented_control("Where you can work", _opts, default=_opts[0],
                                 key="locseg", label_visibility="collapsed")
    loc_mode = ("Remote I can take" if _pick and "Remote" in _pick
                else "On-site / local" if _pick and _pick.startswith("📍")
                else "Everywhere")
    if loc_mode == "On-site / local" and not _CITY:
        st.caption("Showing hands-on gigs everywhere — add your **city** in Profile to pin "
                   "these to your area.")

    with st.expander("Narrow it down"):
        skills = st.multiselect("Skill", ALL_SKILLS, default=ALL_SKILLS)
        sizes = st.multiselect("Budget", ["Small", "Medium", "Large"],
                               default=["Small", "Medium", "Large"])
        srcs = sorted(df["source"].unique())
        sources = st.multiselect("Source", srcs, default=srcs)
        urgent = st.checkbox("🔥 Urgent only")
        kw = st.text_input("Contains keyword").strip().lower()

    view = apply_filters(df, skills, sizes, sources, urgent, kw)
    view = apply_location(view, loc_mode)
    if pro:
        view = scored(view)

    # Quick-filter arriving from a Dashboard stat click
    qf = st.session_state.get("quickfilter", "")
    if qf:
        qlabel = {"recent": "posted in the last 24h", "mine": "in your skills",
                  "urgent": "urgent only"}.get(qf, qf)
        fc1, fc2 = st.columns([5, 1], vertical_alignment="center")
        fc1.markdown(f'<span class="gr-qf">▸ {qlabel}</span>', unsafe_allow_html=True)
        if fc2.button("✕ clear", key="clearqf", use_container_width=True):
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
        cc1, cc2 = st.columns([5, 1], vertical_alignment="center")
        cc1.markdown(f'<span class="gr-qf">▸ {html.escape(cat)}</span>',
                     unsafe_allow_html=True)
        if cc2.button("✕ clear", key="clearcat", use_container_width=True):
            st.session_state["catfilter"] = ""
            st.rerun()
        view = view[view["job_type"] == cat]
    elif group and group in config.CATEGORY_GROUPS:
        subs = config.CATEGORY_GROUPS[group]
        cc1, cc2 = st.columns([5, 1], vertical_alignment="center")
        cc1.markdown(f'<span class="gr-qf">▸ {html.escape(group)}</span>',
                     unsafe_allow_html=True)
        if cc2.button("✕ clear", key="cleargrp", use_container_width=True):
            st.session_state["groupfilter"] = ""
            st.rerun()
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
        note += f"  ·  🔗 {merged} duplicates tidied up"
    if len(view) > FEED_CAP:
        note += f"  ·  showing the freshest {FEED_CAP}"
    st.caption(note)

    if view.empty:
        st.info("Nothing matches those filters right now — try widening them, or hit "
                "**Check for new gigs** up top.")
        return

    for r in view.head(FEED_CAP).to_dict("records"):
        gig_card(r, pro)


def view_market(pro):
    st.markdown("### 📊 What gigs like yours are paying")
    if not pro:
        st.info("🔒 This one's a **Pro** perk. See what work like yours actually pays, "
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
    PALETTE = ["#E8933A", "#4C8DFF", "#35B37E", "#B889F0", "#E96250", "#38BDF8", "#9AA1AB"]
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
        st.altair_chart(chart, use_container_width=True)
    with c2:
        st.markdown("**Typical budget by skill**")
        rr = (pd.DataFrame([{"Skill": s, "Budget": b} for s, b in priced])
              .sort_values("Budget", ascending=False).head(8))
        chart2 = alt.Chart(rr).mark_bar(color="#4C8DFF", cornerRadiusEnd=4).encode(
            x=alt.X("Budget:Q", title=None, axis=alt.Axis(format="$,d")),
            y=alt.Y("Skill:N", sort="-x", title=None),
            tooltip=["Skill", alt.Tooltip("Budget", format="$,d")]).properties(height=300)
        st.altair_chart(chart2, use_container_width=True)

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
        st.altair_chart(donut, use_container_width=True)
    with c4:
        st.markdown("**Where the gigs come from**")
        src = df["source"].value_counts().rename_axis("Source").reset_index(name="Gigs")
        src_donut = alt.Chart(src).mark_arc(innerRadius=58, stroke="#0e1117",
                                            strokeWidth=2).encode(
            theta=alt.Theta("Gigs:Q"),
            color=alt.Color("Source:N", scale=alt.Scale(range=PALETTE),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Source", "Gigs"]).properties(height=300)
        st.altair_chart(src_donut, use_container_width=True)

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
    st.altair_chart(stacked, use_container_width=True)
    st.caption("Ballpark — budgets blend project & hourly figures across sources.")


def view_alerts(pro):
    st.markdown("### 🔔 We'll tap you on the shoulder")
    if not pro:
        st.info("🔒 A **Pro** perk. The moment a gig that fits you lands, we'll ping you — "
                "so you're first to reply. Turn it on by upgrading in your **Profile**.")
        return
    st.caption("The faster you hear, the more you win. Switch on as many as you like — "
               "we hit every one the second a gig fits you.")
    p = alerts.load_prefs()

    st.markdown("**📱 Phone push** — instant, even with the site closed")
    ntfy = st.text_input("ntfy topic", value=p.get("ntfy_topic", ""),
                         placeholder="pick a private topic, e.g. dartly-alex-9f2",
                         help="Install the free **ntfy** app, subscribe to this exact "
                              "topic name, and pushes land on your phone in seconds.")

    st.markdown("**💬 Discord / Slack**")
    webhook = st.text_input("Webhook URL", value=p.get("discord_webhook", ""),
                            label_visibility="collapsed",
                            placeholder="paste your Discord or Slack webhook URL")

    with st.expander("More ways to hear about it"):
        st.markdown("**✈️ Telegram**")
        tg_token = st.text_input("Bot token", value=p.get("telegram_token", ""))
        tg_chat = st.text_input("Chat ID", value=p.get("telegram_chat", ""))
        st.markdown("**✉️ Email** — add SMTP details to your `.env` and it sends itself.")
        st.markdown("**🖥️ Desktop pop-up** — on automatically while the watcher runs on "
                    "your Mac.")
        st.caption("📲 Text/SMS is next — it needs a paid provider, so we started with the "
                   "free, instant options above.")

    crit = {"skills": prof.get("skills", []), "budgets": ["Small", "Medium", "Large"],
            "keyword": prof.get("keywords", ""), "discord_webhook": webhook.strip(),
            "ntfy_topic": ntfy.strip(), "telegram_token": tg_token.strip(),
            "telegram_chat": tg_chat.strip()}

    cols = st.columns(2)
    with cols[0]:
        if st.button("💾 Save my alerts", use_container_width=True):
            alerts.save_prefs(crit)
            st.success("Saved — your alert preferences are set. 🔔")
    with cols[1]:
        if st.button("🔔 Send a test ping", use_container_width=True):
            n = alerts.notify_new(crit)
            live = ["desktop"]
            if ntfy.strip():
                live.append("phone push")
            if webhook.strip():
                live.append("Discord/Slack")
            if tg_token.strip() and tg_chat.strip():
                live.append("Telegram")
            if os.environ.get("SMTP_HOST"):
                live.append("email")
            st.info(f"Pinged you about {n} new gig(s) via {', '.join(live)}.")

    st.caption("Alerts follow the skills & keywords in your **Profile**. Hit "
               "**Send a test ping** to confirm your channels are wired up.")


def view_profile(pro):
    st.markdown("### 👋 Tell us about you")
    st.caption("The more we know, the better the gigs we surface for you.")
    pct = profile_mod.completeness(prof)
    st.progress(pct / 100, text=f"You're {pct}% set up")

    # Location pre-fill: detect once, the form below uses it as the default.
    geo = st.session_state.get("_geo", {})
    dcol, mcol = st.columns([1, 3], vertical_alignment="center")
    if dcol.button("📍 Detect my location", use_container_width=True):
        st.session_state["_geo"] = location.geo_from_ip()
        st.rerun()
    if geo:
        found = ", ".join(x for x in [geo.get("city"), geo.get("country")] if x)
        if found:
            mcol.markdown(f"📍 Looks like you're in **{found}** — check the fields below "
                          "and hit **Save**.")
        else:
            mcol.caption("Couldn't place you automatically — just pick your country below.")

    with st.form("profile_form"):
        fc1, fc2 = st.columns(2)
        with fc1:
            f_name = st.text_input("Your name", value=prof.get("name", ""))
            f_headline = st.text_input("What you do", value=prof.get("headline", ""),
                                       placeholder="e.g. Brand & logo designer")
            f_skills = st.multiselect("Your skills", ALL_SKILLS,
                                      default=prof.get("skills", []))
            f_portfolio = st.text_input("Where's your work?",
                                        value=prof.get("portfolio", ""),
                                        placeholder="your portfolio link")
        with fc2:
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
        f_bio = st.text_area("A line about you (we'll use it in your replies)",
                             value=prof.get("bio", ""),
                             placeholder="10+ yrs designing brand identities for small businesses.")
        if st.form_submit_button("💾 Save", use_container_width=True):
            profile_mod.save({
                "name": f_name.strip(), "headline": f_headline.strip(),
                "skills": f_skills, "rate_floor": f_floor, "rate_unit": f_unit,
                "keywords": f_keywords.strip(), "mute": f_mute.strip(),
                "portfolio": f_portfolio.strip(), "bio": f_bio.strip(),
                "country": f_country if f_country != "Other / elsewhere" else "",
                "city": f_city.strip(),
            })
            st.session_state.pop("_geo", None)
            st.success("Got it — we've tuned things to you. 🧡")
            st.rerun()

    st.divider()
    st.markdown("#### Your plan")
    if pro:
        st.success("You're on **Pro** — instant pings, drafted replies, ranked picks & "
                   "market rates. Thanks for backing us. 🧡")
        if st.button("Switch back to Free"):
            st.session_state.plan = "Free"
            st.rerun()
    else:
        st.info("You're on **Free** — the whole board, filters, your profile, and a "
                "daily digest. All yours, no catch.")
        st.caption("Want the edge? **Pro** adds instant pings, drafted replies, picks "
                   "ranked for you, and what-it-pays market rates.")
        if st.button("⭐ Upgrade to Pro", type="primary"):
            st.session_state.plan = "Pro"
            st.rerun()


# ---------------------------------------------------------------------------
# Top nav bar (+ stat-card click navigation via query params)
# ---------------------------------------------------------------------------
_TABS = ["Dashboard", "Gigs", "Market", "Alerts"]
if "nav" in st.query_params:
    _nav = st.query_params.get("nav", "").lower()
    if _nav == "profile":
        st.session_state["_profile"] = True
    else:
        _idx = {t.lower(): i for i, t in enumerate(_TABS)}.get(_nav)
        if _idx is not None:
            st.session_state["_manualnav"] = _idx
            st.session_state["quickfilter"] = st.query_params.get("qf", "")
            st.session_state["catfilter"] = st.query_params.get("cat", "")
            st.session_state["groupfilter"] = st.query_params.get("group", "")
        st.session_state["_profile"] = False
    st.query_params.clear()

_bcol, _ncol, _rcol = st.columns([1.5, 5.2, 1.4], vertical_alignment="center")
with _bcol:
    st.image(str(BASE / "assets" / "logo.svg"), width=100)
with _ncol:
    selected = option_menu(
        None, _TABS,
        icons=["speedometer2", "broadcast", "graph-up-arrow", "bell"],
        orientation="horizontal", default_index=0, key="topnav",
        manual_select=st.session_state.pop("_manualnav", None),
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"font-size": "15px"},
            "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0 2px",
                         "padding": "9px 15px", "border-radius": "8px",
                         "--hover-color": "rgba(232,147,58,0.12)"},
            "nav-link-selected": {"background-color": "#E8933A", "color": "#141414",
                                  "font-weight": "600"},
        },
    )

# Clicking a main tab (a real change) leaves the Profile view.
if "_omprev" in st.session_state and selected != st.session_state["_omprev"]:
    st.session_state["_profile"] = False
st.session_state["_omprev"] = selected
_on_profile = bool(st.session_state.get("_profile"))
active = "Profile" if _on_profile else selected

with _rcol:
    _name = (prof.get("name") or "").strip()
    _init = _name[:1].upper() or "•"
    _acls = "gr-avatar active" if _on_profile else "gr-avatar"
    _href = f"?nav={selected.lower()}" if _on_profile else "?nav=profile"
    _plan = st.session_state.get("plan", "Free")
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;padding-right:2px">'
        f'<div class="gr-acct">'
        f'<a class="{_acls}" href="{_href}" target="_self" title="Your account">{_init}</a>'
        f'<div class="gr-menu">'
        f'<div class="gr-menu-hd">{html.escape(_name or "Your account")}'
        f'<span>{_plan} plan</span></div>'
        f'<a href="?nav=profile" target="_self">Your profile</a>'
        f'<a href="?nav=profile" target="_self">Location &amp; settings</a>'
        f'<div class="gr-menu-sep"></div>'
        f'<span class="gr-mi muted">Sign out</span>'
        f'</div></div></div>', unsafe_allow_html=True)

st.divider()

# A quick-filter / category (from a Dashboard click) only lives while on Gigs.
if active != "Gigs":
    st.session_state["quickfilter"] = ""
    st.session_state["catfilter"] = ""
    st.session_state["groupfilter"] = ""

# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
if active == "Dashboard":
    view_dashboard(PRO)
elif active == "Gigs":
    view_gigs(PRO)
elif active == "Market":
    view_market(PRO)
elif active == "Alerts":
    view_alerts(PRO)
elif active == "Profile":
    view_profile(PRO)

st.markdown(
    '<div class="gr-footer">'
    '<span class="brand">Dartly</span>'
    '<span class="tag">Freelance gigs, the moment they drop — so you reply first.</span>'
    '<span class="meta">An early preview, built in the open · © 2026</span>'
    '</div>', unsafe_allow_html=True)

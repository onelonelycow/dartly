# FEEL.md — how Nabbly looks, sounds, and behaves

The single reference for every UI/UX edit, redesign, or new surface (app pages,
landing site, 404, legal pages, emails, social posts, preview images). If a
change contradicts this file, either the change is wrong or this file gets
updated in the same commit — never let them drift.

Everything in here was decided on a real screen with the founder, usually after
seeing the wrong version first. The "why" lines are the point: they stop the
same mistake being re-introduced with fresh confidence.

---

## 1. The one-line identity

**Calm, dark, warm. One amber thing at a time.**

Nabbly is a radar: it watches quietly and points at what matters. The UI should
feel like that — not like an alarm going off. Whenever a choice is between loud
and quiet, pick quiet. ("I do like that loading screen" came from a thin 2.5px
sweep; the full-width amber banner it replaced was "off-putting.")

---

## 2. Color

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#121418` | page ground (app + site). `#0B0D10` for artwork/posters only |
| `--bg2` | `#15181d` | cards, stat tiles, inputs |
| `--panel` | `#171a20` | quiet buttons, hover surfaces |
| `--line` | `#262a31` | default hairline border |
| `--line2` | `#2f343d` | stronger border / hover border |
| `--ink` | `#ECEEF1` | primary text |
| `--ink2` | `#c3c8d0` | body text on the site / lead copy |
| `--mute` | `#969da7` | secondary text, labels |
| `--faint` | `#6b7280` | fine print, footers |
| `--amber` | `#E8933A` | THE accent. Headings' last word, active nav, links |
| `--amber-l` | `#F7B569` | gradient top, highlights |
| `--amber-d` | `#CB6F16` | gradient bottom |
| soft amber | `#D69858` | amber pulled back — for artwork text, never full-strength there |
| warm white | `#FCE4C6` | points of emphasis in artwork (blips). NEVER pure white glows |

Semantic colors (stat accents, pills): blue `#4C8DFF` (fresh), red `#E96250`
(urgent), green `#35B37E` (fields/positive). These are data colors, not brand
accents — don't decorate with them.

**Rules**
- One amber focal point per view. If two things shout, demote one.
  (Two identical primary buttons on screen = a bug. Nav CTA became a ghost.)
- Amber gradients run light→dark, top-left→bottom-right:
  `linear-gradient(180deg, #F7B569, #CB6F16)` for buttons,
  `(135deg)` equivalents for tiles/artwork.
- Backgrounds are near-black, never pure `#000`; text never pure `#fff`.

---

## 3. Typography

- **Face:** system stack everywhere:
  `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
  No webfonts — nothing loads from third parties.
- **Weights:** 650 for headings (site), 600–700 in-app. Body 400.
  Letter-spacing tightens slightly as size grows (`-.02em` on big headings).
- **The wordmark:** `Nabb` in ink + `ly` in amber. Always one flex item —
  `<span>Nabb<span class="amber">ly</span></span>` — because a bare text node in
  a `gap` flex container splits into "Nabb ly". (Shipped that bug once.)
- **Headings speak the wordmark's language:** last word amber, like the "ly".
  `### The whole <span class="gr-accent">board</span>`. This REPLACED emoji
  prefixes (📡🔥👋) — never reintroduce emoji in headings.
- **No emoji anywhere in the product, full stop** (July 2026) — not just
  headings. It had spread everywhere: pills (🎯🔒🔥📍), buttons (💾🔄⭐📍),
  captions (🧡✨), the marketing site's mail-preview icons (📬✉️🎬🎨). A
  cartoon pictograph next to hand-tuned type is the fastest way to look like a
  demo instead of a product — colour and weight are supposed to be doing that
  work already. **Not on buttons at all** — `↻ Refresh` was cut on sight even
  though `↻` is technically a glyph, not an emoji: if it reads as an icon
  bolted to a label, it goes, and a button label is the last place that needs
  decorating. Arrows survive ONLY where they carry information the words
  don't: `↗` (opens in a new tab), `→` (a hover affordance on a card), `↑`
  (jump to top), `▸` (an active-filter marker). The plain `✓` is fine.
  If a control needs a state marker, reach for what's already
  established instead: a coloured dot (`.gr-ch-st::before`), the pill's own
  tint (match/urgent/low already carry their meaning in colour — see §2 — so a
  🎯 or 🔥 in front of one said the same thing twice), or the small radar-glow
  mark below.
  - **The radar-glow mark** — the replacement when a row genuinely needs a
    visual anchor and plain text isn't enough (e.g. a list of forwarded-mail
    previews on the marketing site). A miniature version of the artwork motif
    in §6: a soft radial amber glow fading to the card's own background, one
    small warm-white point lit inside it. Same restraint rule as a poster —
    ONE point of emphasis, never a second colour. See `.mailrow .ic` in
    `site/index.html` for the reference implementation.
- **No eyebrow/kicker labels** above headlines ("LIVE FREELANCE DEMAND" was
  removed). Let negative space do that job.
- Markdown gotcha: `###` only parses at line start — any HTML before it turns
  the heading into literal text.

---

## 4. Space & layout

- Content column: `max-width: 1080px` (site `--maxw`), long-form text `680px`
  (About, FAQ, Privacy, Terms — `.gr-about` / `.gr-doc`).
- **The top bar spans full width** (logo far left, avatar far right, breakout
  via `margin-left: calc(50% - 50vw)`); content stays in the centered column.
  The bar carries its own bottom border — no second divider under it.
- Radius: 999px pills, ~10–14px cards/buttons/inputs, 16px large cards.
- Controls that belong together sit together, tightly. Streamlit's default 16px
  block gap makes stacked controls read as separate floating bars — group them
  (`gap: .55rem` inside a marked toolbar region). Seven stacked full-width
  control rows before content = the anti-pattern that triggered this rule.
- A "clear/dismiss" control sits NEXT TO the thing it clears, styled as a small
  pill — never stranded at the far edge of the page.
- Maintenance actions (Refresh) go on the title row, right-aligned, quiet.
  They are not part of the reading path.
- Search boxes are a readable width (~60%, `st.columns([3, 2])`), never
  full-bleed.
- Buttons: ONE `btn-primary` (amber gradient) per screen; everything else is
  `btn-ghost` (dark, hairline border) or a text link. Hover: brighten + 1px
  lift on primary; border-to-amber on ghost. Mobile tap targets ≥44px.

---

## 5. Motion & feedback

- **Loading = the amber sweep.** A 2.5px fixed bar at the very top, gradient
  band sweeping left→right (1.15s, `cubic-bezier(.45,.05,.35,1)`), driven by
  Streamlit's `data-test-script-state`. Content stays at FULL brightness —
  the stale-dim (`[data-stale] { opacity: 1 !important }`) stays killed.
  Respect `prefers-reduced-motion` (bar shows static at center).
- The sweep element exists ONLY while running — no base rule that could leave a
  stray strip when idle.
- Transitions ~.15s ease. Hover states are subtle shifts, not transforms
  (exception: primary button's 1px lift).
- "New items" notices are quiet centered chips ("↻ Show 3 new gigs"), outline +
  amber text — never a full-width colored banner.
- Spinners get a specific label ("Searching for "figma"…"), not generic.

---

## 6. Artwork (posts, og-image, illustrations)

Same motif, smaller: this is also the icon-mark used in-product wherever a row
needs a visual anchor and text alone isn't enough — see §3's "radar-glow mark."
Scale down, don't reinvent.

The radar motif, treated with restraint:
- Soft gradients, never hard-edged beams — blur the sweep's leading edge.
- **ONE point of emphasis** (one bright blip); everything else recedes.
- Warm tones: blips `#FCE4C6`, never white flashbulbs. Rings at 11–30 alpha.
- Amber pulled back (`#D69858`) for display type on artwork.
- Sign off with the mark beside `nabbly.co`, small (~36px at 1080), bottom
  center or left. Never park the logo mid-artwork (needs a pad → reads as a
  smudge).
- ~5% breathing room from every edge. Type set at final scale; supersample
  2–3x and LANCZOS-downscale the vector work.
- No eyebrow labels on posters either.

---

## 7. Voice & copy

- **Tone:** calm, direct, a careful colleague. No hype, no exclamation marks.
  Warm is fine ("Tell us straight", "on us"); salesy is not.
- **Dashes only when truly necessary** (founder preference). Prefer commas,
  periods, "·" separators in metadata rows.
- Sentence case everywhere. No ALL-CAPS except tiny letterspaced tags.
- **Numbers must be true at all times** — "6,000+ gigs" died because a fresh
  deploy resets to ~1,558; it shipped as "1,500+". If a number can go stale,
  state its floor or make it live.
- **Never advertise sources.** No "Live sources" stats, no "Missing a source?"
  prompts, no board names in marketing copy. The feed is the product;
  provenance is plumbing. (Chart raw-data toggles that expose `job_type` /
  `size_tier` get hidden; exports get human headings: Field, Budget, Gigs.)
- Marketing pitch lives on nabbly.co and signed-out views ONLY. Signed-in
  surfaces use working headers ("Welcome back, Ben" / "Your board") — never
  re-sell to someone already inside.
- Time-limited offers (founding 50) go in posts/pinned content, not permanent
  bios or headers.
- Explain-the-obvious hints get cut ("Press Enter to submit form" is hidden
  globally).
- Privacy/limits stated plainly and honestly ("It's a starting point, not
  finished work"; "we don't store it — it is sent to Anthropic to draft").
  Never stretch a true statement into a bigger claim.

**Vocabulary:** gigs (not jobs/postings) · board (not feed/list) · fields (not
categories/sources) · "the moment it drops" · "reply first" · Free / Pro /
founding member.

---

## 8. Streamlit implementation notes (the app)

- Scope CSS by what a container CONTAINS (`:has(.gr-marker)`), never
  `:first-of-type` (it leaked into the profile form once).
- Buttons are styled per-key: `.st-key-<key> button { … }` — keys are the
  design system's hooks. Name keys deliberately.
- Streamlit 1.59 puts container borders on `stVerticalBlock`, not
  `stVerticalBlockBorderWrapper`.
- Hide Streamlit chrome we've replaced: `InputInstructions`, chart
  `[aria-label="Show data"]` (keep Fullscreen), stale-dim.
- `width="stretch"`, never the deprecated `use_container_width`.
- Confirm selectors against Streamlit's own bundle
  (`.venv/.../streamlit/static/`) before styling — don't guess test-ids.

## 9. Benchmarks — the three sites to measure against

Not for copying. They are the calibration reference when a change is "fine but
not sharp": open one, look at the same element there, and ask what it does that
we don't. All three are dark-native, single-accent, restrained products — the
same territory Nabbly is in — and all three read as expensive.

### Linear — linear.app · the standard for restraint
Near-black grounds, accents used strategically rather than decoratively, and a
type scale with real range: generous display sizes against compact UI labels.
Cards are defined by understated borders and crisp edges, no ornament. It is
**premium through omission** — deliberately anti-trend.

*Steal:* the type-scale range. Nabbly's headings and body sit too close
together; Linear's confidence comes from a bigger jump between display and
label. Also its refusal to decorate — every element earns its place.

### Vercel — vercel.com · the standard for spacing and neutrals
Near-black, never pure black. Extreme colour restraint. What carries it is
**spacing discipline**: generous, consistent whitespace that compartmentalises
sections so the page breathes. Cards use subtle borders and layered depth
rather than heavy frames. Buttons are high-contrast with restrained ornament.

*Steal:* section rhythm. Our density problem was never the components, it was
that everything sat at the same vertical distance. Vercel varies the gap
between *sections* far more than the gap between *items*, and that alone reads
as designed.

### Raycast — raycast.com · the standard for presenting lists
Closest to Nabbly's actual job: rows and rows of items that must stay scannable.
Dark neutral base, accents strategic, cards on a consistent grid with icon →
title → description left, preview right. Gentle differentiation between rows,
never stark separators.

*Steal:* row structure. A gig card is Raycast's extension card. Consistent
internal alignment across every row is what makes a long list feel calm rather
than endless.

**Where we fell short of all three, and what we did (July 2026).** All four are
closed. Kept here because the RULES are the useful part — the diagnosis is what
stops each one being reintroduced.

1. **Vertical rhythm was flat.** Streamlit ships one 16px gap between
   everything, and we had never overridden it on desktop. The gap *inside* a gig
   card was 16px and the gap *between* two cards was also 16px, so a card read as
   four loose rows instead of one object.
   **Rule:** three distances, always different — `--s-item` (parts of one thing)
   < `--s-group` (thing to thing) < `--s-section` (before a new heading). Never
   let the inner gap equal the outer gap.
2. **Type scale was compressed.** Desktop `h3`/`h4` were never styled at all.
   Worse, inside a card the title (19px), body (16px) and "Posted…" (14px) were
   all essentially the same brightness — body and caption were both pure
   `#fafafa`. Nothing receded, so nothing stood out.
   **Rule:** most of the fix is at the BOTTOM of the ramp. Pull meta down and
   back (12px `--faint`) before you push headings up. Colour separates as much
   as size does.
3. **Gig cards repeated.** Now: title dominant (18px/650), pills recessive,
   body 14.5px `--mute`, caption 12px `--faint`, one shared left edge.
   **Rule:** one dominant thing per row; everything else is context for it.
4. **Borders did too much work.** The card was the most repeated element on the
   site and the ONLY box still on Streamlit's stock `rgba(250,250,250,.2)`; pills
   drew 4-6 more outlines inside every card; the reply expander was a frame
   inside a frame; a full-width `<hr>` sat immediately above a section gap.
   **Rule:** an edge must earn its place. Prefer a background shift. Never put a
   bordered box inside a bordered box, and never state a separation twice (a
   rule AND a gap).

**Tokens live in `app.py`'s `:root`** (mirroring `site/index.html`). New rules use
them; old literals were deliberately left alone rather than sweeping 40 values in
a design commit.

**Two traps this pass hit, both worth remembering:**
- The new block sits AFTER the mobile media query, so an unscoped `!important`
  wins on phones too — it silently undid the mobile type ramp. Desktop-only type
  rules go in `@media (min-width:641px)`.
- `[data-testid="stVerticalBlockBorderWrapper"]` **does not exist** in Streamlit
  1.59. Two rules targeting it had never fired. Confirm selectors against the
  live DOM, not memory.

**Controls collapse before they wrap.** "Browse by field" was five chips that fit
one desktop line and stacked into four ragged rows on a phone, pushing the first
gig off-screen. It became a select beside the search. If a control set wraps on a
phone, that is the signal to collapse it into one, not to restyle the chips.

## 10. The checklist before shipping any UI change

1. One primary action on screen? One amber focal point?
2. Does it read as ONE surface (grouped, consistent radii/borders), not
   stacked bars?
3. True at all times — numbers, claims, states?
4. Mobile: ≥44px targets, no horizontal scroll, two-row header intact?
5. Screenshot it and LOOK — desktop and 375px — before pushing. The literal
   `###` heading and the "Nabb ly" gap both shipped because nobody looked.
6. Does it expose plumbing (sources, column names, internals)? Hide it.
7. Loud or quiet? When unsure: quiet.
8. Any emoji snuck in? (§3) Colour/weight/the radar-glow mark instead.

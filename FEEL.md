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

## 9. The checklist before shipping any UI change

1. One primary action on screen? One amber focal point?
2. Does it read as ONE surface (grouped, consistent radii/borders), not
   stacked bars?
3. True at all times — numbers, claims, states?
4. Mobile: ≥44px targets, no horizontal scroll, two-row header intact?
5. Screenshot it and LOOK — desktop and 375px — before pushing. The literal
   `###` heading and the "Nabb ly" gap both shipped because nobody looked.
6. Does it expose plumbing (sources, column names, internals)? Hide it.
7. Loud or quiet? When unsure: quiet.

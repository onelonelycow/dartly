# Brand kit setup — Canva, and anything else that asks

Canva's API is read-only for brand kits (`brandkit:read`), so this cannot be
created from here. Enter it once in the Canva UI and every generated design
stops inventing its own logo and palette, which is exactly what went wrong the
first time: four generated candidates, four different made-up Nabbly marks, one
misspelling the partner as "NEXTW" and one inventing an event date that does
not exist.

Values below are lifted from [FEEL.md](../FEEL.md), which is the source of
truth. If the two ever disagree, FEEL.md wins and this file is stale.

Folder already created: https://www.canva.com/folder/FAHTow5NJKA

---

## Colours

Add these in Brand Kit → Colours. The names matter — a palette of unnamed
swatches gets used at random.

| Name in Canva | Hex | What it is for |
|---|---|---|
| Ground | `#121418` | every background |
| Surface | `#15181D` | cards, tiles, inputs |
| Hairline | `#262A31` | borders |
| Ink | `#ECEEF1` | primary text |
| Body | `#C3C8D0` | body copy |
| Mute | `#969DA7` | labels, secondary text |
| **Amber** | `#E8933A` | **THE accent** |
| Amber light | `#F7B569` | gradient top |
| Amber deep | `#CB6F16` | gradient bottom |
| Soft amber | `#D69858` | amber pulled back, for artwork text only |

Not brand colours — data only, never decoration: blue `#4C8DFF` (fresh),
red `#E96250` (urgent), green `#35B37E` (positive).

Partner green, for co-branded work only: `#54B95A`, sampled from nextnw.org.
On co-branded artwork the ground shifts to `#0E1613` so their green does not
look pasted onto our near-black.

## Type

**Archivo.** Weights 400 body, 600 headings. Canva has it.

One caveat worth knowing: FEEL.md still says "system stack everywhere, no
webfonts". That line is being overtaken — there is an in-flight change on this
machine self-hosting Archivo across the board templates. Archivo is the
direction; if that work is abandoned, this section needs revisiting.

Letter-spacing tightens as size grows, about `-0.02em` on large headings.

## Logos

Already uploaded to the Canva folder, pulled from nabbly.co:

- **Nabbly mark** — `icon-512.png`, and `icon.svg` as vector
- **NextNW mark** — `nextnw-icon.png`, transparent, partner work only
- **Share card** — `og-image.png`, 1200x630
- **Board screenshot** — `board-live.png`

Still local-only, so Canva cannot fetch them — drag these in by hand from
`~/Desktop/Nabbly Brand/` and `brand/posts/`:

`avatar-1000.png`, `avatar-pfp-1080.png`, `avatar-tight-1000.png`,
`logo-dark.png`, `linkedin-banner.png`, `social-banner.png`, and the nine
weekly post squares plus the three NextNW collab squares.

They are deliberately not deployed to nabbly.co. Publishing them just to let a
tool ingest them would put unposted material on the open internet permanently.

## The rules a generator keeps breaking

- **One amber focal point per view.** Two things shouting is a bug.
- **Never pure black or pure white.** Grounds are near-black, text is never `#fff`.
- **The wordmark is `Nabb` in ink + `ly` in amber.** One unit, never split.
- **Headings echo it** — last word amber. This replaced emoji prefixes; do not
  reintroduce emoji in headings.
- **Amber gradients run light to dark**, top-left to bottom-right.
- **No stock photography, no illustrated people, no gradient blobs.** The look
  comes from real product UI and restrained type. A drawing dropped next to
  real interface reads as clip art — proven twice.

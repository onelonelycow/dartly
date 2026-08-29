# Deck alternates — considered, not used

Three layouts built for the NextNW deck on 2026-08-28 and deliberately left
out of it. Kept because the material is good, not because the slides were.

| file | what it is | why it is not in the deck |
|---|---|---|
| `field-mix-slide.png` | A whole slide: 51,122 gigs ranked across 24 fields | Answers "what is on Nabbly", not "what is here for me" |
| `covers-with-chart.png` | "What it covers" with the chart in place of the six pills | Leaves no room for the newsletter block, which is the stronger claim |
| `forwarding-own-slide.png` | The newsletter story promoted to its own slide | Lands better as the payoff at the bottom of the covers slide |
| `field-mix.svg` | The chart itself, editable vectors | — |

The chart is live data from 2026-08-28: 24 named fields, plus 615 gigs the
classifier had not placed. It ages in weeks, not months — regenerate before
reusing it anywhere. The numbers came from `nabbly_posts` grouped by
`job_type` where `is_demand = 1` and `archived_at` is null.

The SVG is the useful artifact. It uploads into Figma as editable vectors and
text (not a flat image), and it suits a partner page or a follow-up email
better than it suited a slide.

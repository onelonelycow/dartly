# Classifier measurement — 2026-09-13

300 English rows sampled at random from the 24,993 on the board in the last 8
days, labelled independently (Claude Opus 5, effort low, given the category
list and the rule "name the work being hired for"), then every disagreement
read by hand. `tools/classifier_measure.py` reproduces it; the sample and
both labels are in `tools/classifier_sample_2026-09-13.csv`.

| | |
|---|---|
| exact agreement with the judge | **63%** |
| same category group (the rail's six) | **78%** |
| judge confidence high / medium / low | 176 / 110 / 14 |

Per label, where it is worst (n = rows the classifier put there, % = judge agreed):

| classifier label | n | precision | where the rest belonged |
|---|---|---|---|
| Design / creative | 34 | 41% | Development 8, Marketing 5, Architecture 2 |
| Admin / VA | 18 | 28% | Management 5, Healthcare 5 |
| Management / operations | 8 | 38% | Marketing, Finance, Sales |
| Architecture / 3D | 4 | 25% | Development 2 ("Senior Architect", "Database Architect") |
| Development / tech | 50 | 72% | QA 4, Engineering 3, IT 3 |

And from the other side — of what the judge says is Management / operations,
the classifier finds 21%; IT / support 14%; Architecture 20%; Writing 40%;
Healthcare 50% (five Care/Patient Coordinators filed under Admin / VA).

## Why, by count (111 disagreements)

| mechanism | n |
|---|---|
| a generic title word matched one wrong category and nothing else (`coordinator` 7, `engineer` 6, `brand`, `strategy`, `architect`, `director`, `sales`, `marketing` …) | 40 |
| the right category ALSO matched the body, but lost because `classify()` takes the first category in dict order | 32 |
| only wrong categories matched, and only in the body ("graphic design" in a ranch guest-house listing, `python` in a propeller test report) | 17 |
| nothing matched (Other / general), or the judge said Other | 13 |
| the right category ALSO matched the title and lost on dict order ("Makhana E-commerce Website Development": web design 2nd in the dict, website development 7th) | 9 |

So two structural causes carry 81 of the 111:

1. **First match in dict order decides ties.** Design / creative is second in
   `config.JOB_TYPES`, Development / tech seventh, Management twenty-third.
   Any posting that mentions both is Design. A tie-break that prefers the
   category with the most (or most specific) matches would recover 41 of the
   111 on this sample alone — **77% exact from 63%**, no keyword edits.
2. **Single generic words as keywords.** `coordinator` → Admin / VA is wrong
   on 7 of 7 here (they were healthcare, ops, events, media). `engineer` →
   Development is wrong whenever the engineer is a network, controls, sales
   or QA engineer. `va` → Admin / VA matches the US state. These want either
   removal or a specific form ("project coordinator" is still Admin-ish;
   "care coordinator" is not).

Not a cause: the source. Himalayas 64%, Freelancer 61%, Arbeitnow 64% — the
classifier is equally wrong everywhere, which is what a keyword-order problem
looks like and what a source-quality problem does not.

## What this means for readers

A member who sets "Design / creative" and nothing else gets a board where
59% of the cards are not design work. The rail's group view is better
(78%) because Design and Video are in the same group, but Development is
not, and that is where most of the leakage goes.

## Next (not started)

1. Tie-break by match count, title matches weighted over body — measured
   against this same sample before and after, with the CSV as the fixture.
2. Retire or specialise the generic single words listed above.
3. Re-run the 300 and read the disagreements again. The target is not 100%;
   the judge itself is "medium" or "low" on 124 of 300. 85% exact is a
   reasonable bar for a keyword classifier.

# The product demo — beat sheet

16:9, for a site, a partner send, or a link in the deck. Not the Instagram cut;
that lineage is 9:16 and lives in the same folder under other names.

Built around what each beat has to PROVE. A demo that tours the nav shows
features; this one answers, in order, the questions a sceptic actually asks.

Durations below are measured from the pieces that already exist, not guessed.

---

## The cut

| # | Beat | Proves | Source | Length |
|---|---|---|---|---|
| 1 | The alert lands | You are told. You do not check. | `make_alert_open.py` | 3.4s |
| 2 | The board | It watches so you do not have to. Real titles, real "posted 4 min ago" | `capture_demo.py` | 7.6s |
| 3 | Search, and the gig | It is findable, and this one matched the search | same capture | in the 7.6s |
| 4 | The reply writes itself | Not a template — from the client's own words | `draft-my-reply-wide.mp4` | 21.9s |
| 5 | Why it wrote that | You set this once. Fields, boost words, alert channels | `capture_demo.py --settings` | 2.7s captured, wants ~8s |
| 6 | The gigs nobody else has | Forwarding. The one claim a competitor cannot answer | `make_forward_beat.py` | still only |
| 7 | Lockup | — | inside beat 4 today | 2s |

Beats 1–4 exist and run **33.3s** as `demo-full-wide.mp4`. Adding 5 and 6 at
the lengths above lands near **50s**, which is the right size for a site hero
and short enough to survive an email.

## Order, and why 5 comes after 4

The obvious order puts the settings early — here is how you configure it, now
watch it work. That is a feature tour, and it asks someone to care about
controls before they have seen anything worth controlling.

Reversed, beat 5 is the answer to a question beat 4 just raised. The reply
lands, it is unnervingly specific, and the viewer thinks *how did it know
that*. Then the settings appear. Same frames, completely different job.

## What is not built

**Beat 5 needs an assembler.** The frames exist (14 shots, real settings, the
private fields redacted before the shutter). `make_walkthrough.py` only knows
how to join a board capture to a reply cut; it has no notion of a third
section. Either it grows one, or a small tool concatenates the settings frames
with their own paces.

**Beat 5 is too short as captured.** 2.7s for three ideas — what you do, the
words that matter, where alerts reach you — is a blur. It wants a hold on each,
roughly 2.5s apiece, which means longer holds rather than more shots.

**Beat 6 is a still.** `forward-beat.png` is composed and approved in layout.
The animation it wants: the newsletter card lands, the address line lights, the
three gigs peel off it one at a time, hold. About 7s.

**Beat 7 is currently trapped inside beat 4.** The wide reply cut ends on the
wordmark. If 5 and 6 come after it, that ending fires in the middle of the
video. Either the lockup is stripped from the reply cut for this assembly, or
the reply cut gains a flag to end without it.

## Open decisions

**Does beat 5 duplicate the reply cut's own punch-ins?** Beat 4 already zooms
three times, chipping "Include", "Avoid" and "Signature" onto the clauses they
shaped. Showing the settings page afterwards may be the proof that lands, or
may be saying it twice. The stronger version cuts from the Include punch-in
STRAIGHT to the Include field on the settings page — but that means editing
inside the reply cut rather than appending after it.

**Is the marketing site in scope?** Everything here is the board. A stranger's
actual path starts at nabbly.co, and showing it doubles the capture.

**Narration or silent?** Silent and captioned survives autoplay on a site.
Narrated is better for a partner send. The cut does not change; the pacing does.

## Rebuilding any of it

```
.venv/bin/python tools/capture_login.py                                  # once, by hand
.venv/bin/python tools/capture_demo.py /tmp/f-board 1920x1080            # beats 2-3
.venv/bin/python tools/capture_demo.py /tmp/f-set 1920x1080 --settings   # beat 5
.venv/bin/python tools/make_demo_video.py wide                           # beat 4
.venv/bin/python tools/make_walkthrough.py /tmp/f-board 1920x1080        # 2-4 joined
.venv/bin/python tools/make_alert_open.py 1920x1080                      # + beat 1
```

`auth.json` is a live session cookie. Gitignored; delete it when done.

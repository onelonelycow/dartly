# Putting Nabbly online (Render) — a preview, before the "real" site

> **✅ SUPERSEDED.** This walks through the very first bare-preview deploy —
> before accounts existed, before the paid always-on plan, before nabbly.co and
> app.nabbly.co were real domains. All of that has since shipped; see
> `DEPLOY_SEO.md` for how the domain split actually happened. Kept here as a
> historical record of the first "get something on a URL" step, not as a
> current how-to — the "Good to know" caveats below no longer hold.

This gets Nabbly onto a public URL you can send to people to test. It's a
**preview**, not the finished product — see "Good to know" at the bottom for what
changes before it's a real website.

Everything is already set up in the code (`render.yaml`, `requirements.txt`, etc.).
You just need to do the account/click steps below — those need your own logins, so
they can't be automated for you.

---

## Step 1 — Put the code on GitHub

Render deploys from a GitHub repo.

1. Make a free account at **https://github.com** if you don't have one.
2. Create a new **empty** repository (green "New" button). Name it `nabbly`.
   Leave "Add a README" unchecked. Keep it **Private** if you like.
3. GitHub then shows a "…or push an existing repository" box with two lines that
   start with `git remote add origin …` and `git push …`. Copy those two lines.
4. Paste them to me here, or run them yourself in the `~/demand-radar` folder.
   (I've already committed the code locally — it just needs pushing up.)

## Step 2 — Deploy on Render

1. Make a free account at **https://render.com** (you can sign in with GitHub —
   easiest, because it connects the two).
2. Click **New +**  ->  **Blueprint**.
3. Pick your `dartly` repository (the code is Nabbly; the GitHub repo name
   never got renamed, it's cosmetic and doesn't matter). Render reads
   `render.yaml` and fills in everything automatically. Click **Apply** /
   **Create**.
4. Wait ~3–6 minutes for the first build. It installs the app and pulls in a fresh
   batch of live gigs so the site isn't empty. When it's done you get a public URL
   like `https://nabbly.onrender.com`.

That's it — open the URL and you'll see the dashboard.

## Step 3 (optional) — Turn on extras

These are **not required** for the preview. Set them under the service's
**Environment** tab in Render (key = value), then it redeploys:

| What | Keys to add |
|------|-------------|
| Email alerts | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_EMAIL_TO` |
| Keep data + profile across redeploys | Uncomment the `disk:` block and `DATA_DIR` in `render.yaml` (small monthly cost) |

Reddit gigs (r/forhire etc.) need no setup at all — they're pulled from
Reddit's public RSS feed, no account or key required.

Even with none of these, the site works and fills with gigs from the free sources.

---

## Good to know (true of that first bare preview — not true anymore)

- ~~It sleeps when idle.~~ The live service now runs on Render's Standard plan
  (upgraded 2026-08-01, after the free tier's 512MB ceiling actually crashed it) —
  always-on, no sleep.
- ~~Everyone shares one profile + feed.~~ Real accounts shipped: Google OAuth and
  email-code sign-in, each with its own profile, saved gigs, and drafts.
- **Data refreshes on each deploy** is still true, plus a background fetcher now
  pulls fresh gigs on its own on a live schedule — not just at deploy time.
- **Secrets stay out of the code.** Still true, unchanged: passwords/keys go in
  Render's Environment tab, never in the repo (`.env` is ignored by git on
  purpose).

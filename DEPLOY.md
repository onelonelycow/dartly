# Putting Gig Radar online (Render) — a preview, before the "real" site

This gets Gig Radar onto a public URL you can send to people to test. It's a
**preview**, not the finished product — see "Good to know" at the bottom for what
changes before it's a real website.

Everything is already set up in the code (`render.yaml`, `requirements.txt`, etc.).
You just need to do the account/click steps below — those need your own logins, so
they can't be automated for you.

---

## Step 1 — Put the code on GitHub

Render deploys from a GitHub repo.

1. Make a free account at **https://github.com** if you don't have one.
2. Create a new **empty** repository (green "New" button). Name it `gig-radar`.
   Leave "Add a README" unchecked. Keep it **Private** if you like.
3. GitHub then shows a "…or push an existing repository" box with two lines that
   start with `git remote add origin …` and `git push …`. Copy those two lines.
4. Paste them to me here, or run them yourself in the `~/demand-radar` folder.
   (I've already committed the code locally — it just needs pushing up.)

## Step 2 — Deploy on Render

1. Make a free account at **https://render.com** (you can sign in with GitHub —
   easiest, because it connects the two).
2. Click **New +**  ->  **Blueprint**.
3. Pick your `gig-radar` repository. Render reads `render.yaml` and fills in
   everything automatically. Click **Apply** / **Create**.
4. Wait ~3–6 minutes for the first build. It installs the app and pulls in a fresh
   batch of live gigs so the site isn't empty. When it's done you get a public URL
   like `https://gig-radar.onrender.com`.

That's it — open the URL and you'll see the dashboard.

## Step 3 (optional) — Turn on extras

These are **not required** for the preview. Set them under the service's
**Environment** tab in Render (key = value), then it redeploys:

| What | Keys to add |
|------|-------------|
| Reddit gigs (r/forhire etc.) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` — see `REDDIT_SETUP.md` |
| Email alerts | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_EMAIL` |
| Keep data + profile across redeploys | Uncomment the `disk:` block and `DATA_DIR` in `render.yaml` (small monthly cost) |

Even with none of these, the site works and fills with gigs from the free sources.

---

## Good to know (preview vs. real website)

- **It sleeps when idle.** On the free plan the site nods off after ~15 min and
  takes ~30–60s to wake on the next visit. Upgrading the Render plan makes it
  always-on.
- **Everyone shares one profile + feed.** Right now there are no user accounts, so
  every visitor sees the same profile and the same "Pro" view. Great for showing a
  tester; the real website needs **logins** so each person has their own profile.
  (That's the planned "admin login" step.)
- **Data refreshes on each deploy.** New gigs are pulled when the site builds, and
  anyone can hit **"Check for new gigs"** in the app to pull the latest live. For a
  feed that updates on its own around the clock, we'd add a scheduled job later.
- **Secrets stay out of the code.** Passwords/keys go in Render's Environment tab,
  never in the repo (`.env` is ignored by git on purpose).

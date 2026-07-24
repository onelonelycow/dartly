# Going live: the landing page + the app

Today `nabbly.co` points straight at the Streamlit app. We're changing that to:

```
nabbly.co        → the new fast landing page   (great for Google + link previews)
app.nabbly.co    → the Streamlit app           (exactly what you have now)
```

The landing page's buttons all link to `app.nabbly.co`, so the two work together.

**Do the steps in this order** — it means the live site is never broken for even
a minute. Nothing here needs code from me; it's all clicks in Render + your
domain registrar. Render shows you the exact DNS record to add at each step, so
you're never guessing.

---

## Step 0 — push the code

Everything I built (the `site/` folder, `render.yaml` update, brand assets) needs
to be on GitHub first. Tell me when you're ready and I'll commit and push it, or
push it yourself. Once it's on `main`, Render can see it.

---

## Step 1 — make `app.nabbly.co` work first

So the landing page's buttons have somewhere to go *before* we move `nabbly.co`.

1. Render dashboard → your existing app service (**gig-radar**) → **Settings → Custom Domains**.
2. Click **Add Custom Domain**, enter `app.nabbly.co`.
3. Render shows a **CNAME** record to add. Go to your domain registrar (wherever
   you bought nabbly.co) and add it: a CNAME for `app` pointing to the value
   Render gives you.
4. Wait for Render to show **Verified** + a green certificate (usually minutes,
   sometimes up to an hour).
5. Test: open `https://app.nabbly.co` — you should see the app. ✅

At this point both `nabbly.co` and `app.nabbly.co` show the app. Nothing's broken.

---

## Step 2 — create the landing-page service

1. Render dashboard → **New +** → **Static Site**.
2. Connect the same GitHub repo (`onelonelycow/dartly`).
3. Settings:
   - **Publish directory:** `site`
   - **Build command:** leave blank (it's plain HTML, nothing to build)
4. Create it. Render gives it a free URL like `nabbly-site.onrender.com`.
5. Test that URL — you should see the new landing page. ✅

> If you deploy from the `render.yaml` blueprint instead, the static site
> (`nabbly-site`) is already defined in there — Render will offer to create it.

---

## Step 3 — hand `nabbly.co` to the landing page

Now the swap. This is the only step that changes what visitors to `nabbly.co` see.

1. **Remove** `nabbly.co` (and `www.nabbly.co` if present) from the **gig-radar**
   app service → Settings → Custom Domains.
2. **Add** `nabbly.co` (and `www.nabbly.co`) to the new **nabbly-site** static
   service → Settings → Custom Domains.
3. Render tells you the DNS records. The apex (`nabbly.co`) record most likely
   **doesn't change** (it already points at Render) — but confirm it matches what
   Render now shows. Add the `www` record if you want `www` to work too.
4. Wait for **Verified** + green certificate on the static service.
5. Test `https://nabbly.co` → landing page. Click **Open the board** → app. ✅

Done. `nabbly.co` is now the fast, crawlable front door; the app lives one click in.

---

## Step 4 — tell Google (10 minutes, big payoff)

1. Go to **Google Search Console** (search.google.com/search-console), add
   `nabbly.co` as a property, verify (usually a DNS TXT record it gives you).
2. In Search Console → **Sitemaps**, submit `https://nabbly.co/sitemap.xml`.
3. Use **URL Inspection** on `https://nabbly.co/` → **Request indexing**.

That's what gets you into Google fast instead of waiting weeks to be crawled.

---

## Checking the link preview

After Step 3, paste `https://nabbly.co` into:
- **Slack / iMessage / WhatsApp** — should show the amber preview card.
- **LinkedIn Post Inspector** (linkedin.com/post-inspector) — paste the URL, hit
  Inspect. If it looks stale, click to re-scrape.
- **Facebook Sharing Debugger** (developers.facebook.com/tools/debug) — same idea,
  and it forces a refresh of the cached preview.

---

## When you change the landing copy later

Just edit `site/index.html` and push — Render redeploys the static site in
seconds. If you change the preview image, re-run
`.venv/bin/python tools/make_og.py`, and re-scrape with the LinkedIn/Facebook
tools above so they pick up the new image.

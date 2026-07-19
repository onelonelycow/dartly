# Connecting Reddit (3 minutes, no coding)

Reddit blocks anonymous access, so we use their **official, free** developer access.
You just create a free "app" (really just a key) and paste two values into the tool.
This is legitimate and within Reddit's rules for low-volume, non-commercial use.

## Steps

1. Log in to Reddit (any account works — make a throwaway one if you like).

2. Go to: **https://www.reddit.com/prefs/apps**

3. Scroll to the bottom and click **"are you a developer? create an app…"**

4. Fill in the little form:
   - **name:** `demand-radar` (anything is fine)
   - Choose the **"script"** option (the radio button)
   - **description:** leave blank
   - **about url:** leave blank
   - **redirect uri:** type `http://localhost:8080`  (required, but we don't use it)

5. Click **"create app"**.

6. You'll now see your app box. Two values matter:
   - The **client ID** — a random string *under the app name / under the words "personal use script"* (looks like `Xy9_abc123DEF`).
   - The **secret** — labeled **secret** (a longer random string).

7. In the `demand-radar` folder, make a copy of the file `.env.example` and name the
   copy `.env` — then open it in TextEdit and paste your two values in:

   ```
   REDDIT_CLIENT_ID=Xy9_abc123DEF
   REDDIT_CLIENT_SECRET=the_longer_secret_string
   ```

   Save the file.

8. Tell me it's done (or just click **"🔄 Fetch new demand now"** in the dashboard).
   Real Portland Reddit posts will start flowing in.

## Notes
- Keep the `.env` file private — it's your key. It's already set to never be shared
  or committed to git.
- This free tier is fine for testing and personal validation. If Demand Radar
  becomes a paid product, Reddit requires a commercial data agreement — we handle
  that later, before charging anyone.

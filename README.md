# 📻 IsraeliCharts — Daily Instagram Bot

Auto-generates and posts a daily **"On This Day in Israeli Chart History"** image to Instagram.

## How it works
1. `generate_post.py` reads `today_facts.json` (extracted from the israelicharts.com database — 1,548 facts across 365 days), picks today's facts, renders a branded 1080×1350 card, and writes a caption with hashtags.
2. `post_to_instagram.py` publishes it via the official **Instagram Graph API**.
3. GitHub Actions runs the whole thing **daily at ~07:00 Israel time**. Zero servers, zero cost.

## One-time setup (~20 minutes)

### A. Instagram side
1. Convert your Instagram account to a **Business** (or Creator) account: IG app → Settings → Account type.
2. Create a **Facebook Page** (any name) and link it to the IG account: IG → Settings → Business tools → Connect a Facebook Page.

### B. Meta developer side
1. Go to https://developers.facebook.com → **Create App** → type: *Business*.
2. In the app dashboard, add the **Instagram Graph API** product.
3. Open **Graph API Explorer** (Tools menu):
   - Select your app.
   - Add permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`.
   - Click **Generate Access Token** and log in.
4. Get your **IG User ID**:
   - In Explorer, query: `me/accounts` → copy your Page ID.
   - Then query: `{page-id}?fields=instagram_business_account` → copy the `instagram_business_account.id`. That's `IG_USER_ID`.
5. Make the token **long-lived** (60 days):
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-token}
   ```
   Copy the returned token. That's `IG_ACCESS_TOKEN`.
   > Tokens expire after 60 days. Refresh with the same URL, or add the refresh call as another Action.

### C. GitHub side
1. Create a **new GitHub repo** (private is fine) and push these files.
2. Repo → Settings → Secrets and variables → Actions → add:
   - `IG_USER_ID`
   - `IG_ACCESS_TOKEN`
3. Repo → Actions → enable workflows. Test with the **Run workflow** button on "Daily Instagram Post".

## Local testing
```bash
pip install pillow
python generate_post.py 05-26     # any MM-DD, or blank for today
open output/post.jpg
```

## Customizing
- **Handle/branding**: edit `HANDLE` and colors at the top of `generate_post.py`.
- **Posting time**: edit the cron in `.github/workflows/daily_post.yml` (UTC).
- **Hashtags/caption**: edit the caption block at the bottom of `generate_post.py`.

## Maintenance
~2 minutes every 60 days to refresh the access token. Everything else is automatic.

---

## 🎠 Carousel Mode (v2)

`generate_carousel.py` + `post_carousel.py` create a **multi-slide carousel**:
- **Slide 1:** "Guess what was #1 in Israel on [date]?" teaser with vinyl graphic
- **Slides 2–6:** up to 5 facts, each with **real album artwork** fetched automatically from the iTunes Search API (free, no key, high-res 600×600), shown on a blurred art background

Test locally:
```bash
python generate_carousel.py 12-25
```

### ⚠️ About adding music to posts
The Instagram **Graph API does not support adding music** to feed posts or carousels — music stickers are only available when posting manually through the IG app. This is a Meta platform limitation, not a missing feature in this tool. Options:

1. **Fully automatic, no music** (current setup) — zero effort
2. **Semi-auto**: let the bot generate the slides + caption, get them from the repo, and post manually via the IG app in ~2 min — then you can add trending audio, which also boosts reach
3. **Reels with baked-in audio** is technically possible via API but embedding commercial music in the video file itself risks copyright strikes (IG's music licensing only covers audio added through the app)

**Recommendation:** run auto-posting daily, and once a week do one manual post with trending audio for the algorithm boost.

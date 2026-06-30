# SpotifyPM
Spotify Reviews Scraper
Pulls Spotify reviews/mentions from three sources and saves them as both
CSV and JSON, per-platform (raw) and combined (normalized into one schema).
Source	Approach	API key needed?
Google Play Store	`google-play-scraper` library	No
Apple App Store	Direct request to Apple's public customer-reviews RSS/JSON feed (no third-party scraping package)	No
Reddit	Apify actor `spry_wholemeal/reddit-scraper`, called via `apify-client`	Yes — `APIFY_TOKEN`
1. Setup
```bash
cd spotify-reviews-scraper
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
```
Open `.env` and set your Apify token:
```
APIFY_TOKEN=your_apify_token_here
```
> ⚠️ If you've ever pasted an Apify token into a chat, terminal recording,
> or shared doc, treat it as compromised and rotate it at
> https://console.apify.com/account/integrations before using it here.
2. Run
```bash
python main.py
```
This runs all three scrapers across multiple country storefronts (Play Store / App Store) and writes everything to `./output/`:
```
output/
  play_store_raw.json      play_store_raw.csv      # full raw Play Store fields (multi-country)
  app_store_raw.json       app_store_raw.csv       # full raw App Store fields (multi-country)
  reddit_raw.json          reddit_raw.csv          # full raw Reddit fields
  combined_reviews.json    combined_reviews.csv    # all 3, same columns, not deduped/cleaned
```
Combined schema: `platform, id, author, rating, title, text, date, thumbs_up, app_version, reply_text, url`.
Ratings are only meaningful for Play Store / App Store (Reddit posts don't have a star rating — `thumbs_up` carries the post/comment score instead).
Run just one source:
```bash
python main.py --skip-apple --skip-reddit   # Play Store only
```
3. Clean, dedupe, and normalize
```bash
python clean_pipeline.py
```
Reads the `*_raw.json` files in `output/` and writes `output/cleaned_reviews.csv` / `.json` — one
homogeneous schema across all three sources, with text cleaned, dates parsed to ISO-8601, ratings
normalized to 1-5 ints, contentless rows dropped, and duplicates removed (exact-match on
platform+author+text+date, plus Reddit posts deduped by permalink since the same post can surface
under more than one search query). This is the file to feed into the dashboard.
Cleaned schema: `record_id, platform, author, rating, title, text, word_count, date, year_month, country, subreddit, app_version, thumbs_up, reply_text, url`.
Re-run this any time after a fresh scrape — it doesn't touch the network.
4. Explore the data: dashboard.html
Open `dashboard.html` directly in a browser (no server, no build step — it's one self-contained
file). Load `output/cleaned_reviews.csv` or `.json` via the Load CSV / JSON button, or click
Load sample data to preview it with synthetic data first.
Filters available: source platform, country (store geography), app version, subreddit, rating,
date range, and free-text search across title/author/review text. There's also an Export
filtered (CSV) button so you can pull out just the slice you're looking at (e.g. all 1-star
Android reviews from Germany in March) for a slide or report.
Not included as filters: gender and device. Neither Google Play, Apple's App Store, nor
Reddit's public data exposes reviewer demographics or device info. Guessing at gender from
usernames, or device from anything in these feeds, would be fabricating data, not analyzing it —
so those columns simply don't exist rather than being filled with unreliable guesses.
5. Tuning
Everything app-specific lives in `config.py`:
`PLAY_STORE_APP_ID` — defaults to `com.spotify.music`
`PLAY_STORE_COUNTRIES` / `APP_STORE_COUNTRIES` — lists of storefronts to scrape (default: `us, gb, de, in, br, au`). This is what gives the dashboard's "geography" filter real data — add or remove country codes here. Note `PLAY_STORE_LANG` stays `"en"` across all of them, so non-English-market countries only return their English-language reviews, not the dominant local-language ones.
`REDDIT_QUERIES` — search terms sent to the Reddit actor (defaults to a few Spotify-related phrases so you catch more than just exact-match "Spotify")
`REDDIT_COMMENTS_MODE` — `"none"` (fast/cheap, posts only), `"all"` (every post's comments — much slower and uses more Apify usage), or `"high_engagement"` (comments only on popular posts)
6. Things worth knowing
Apple App Store cap: Apple's public reviews feed only exposes a limited, recent window of reviews per country (capped at `MAX_PAGES x 50` in `apple_appstore.py`, roughly the same few-hundred-per-country ceiling as before), no matter how high `APP_STORE_HOW_MANY` is set in `config.py`. This isn't a script limitation — it's what Apple's feed itself returns. To get broader historical coverage you'd need Apple's official App Store Connect API (requires being the app's own developer, which doesn't apply to Spotify) or a paid third-party dataset.
Multi-country scraping takes longer: scraping 6 countries instead of 1 roughly multiplies Play/App Store runtime by 6. Trim `PLAY_STORE_COUNTRIES` / `APP_STORE_COUNTRIES` in `config.py` if you want a faster run.
Apify cost/runtime: `REDDIT_MAX_POSTS_PER_QUERY` is set very high (effectively "no cap" — the actor just stops once a query runs dry). For a popular topic like "Spotify" this can mean a long run and noticeable Apify usage, especially if you switch `REDDIT_COMMENTS_MODE` to `"all"`. Keep an eye on usage in the Apify console; start with a smaller `REDDIT_MAX_POSTS_PER_QUERY` (e.g. 200) to sanity-check output before doing a full run.
Google Play volume: Spotify has an enormous number of Play Store reviews per country. `reviews_all()` will make many sequential requests (200 reviews/page) — this can take a while and is the main reason `sleep_milliseconds` is set rather than 0.
Terms of service: these platforms' reviews/posts are publicly visible, but each has its own ToS around automated access. Use this responsibly (don't hammer their servers, don't republish data in ways that violate Reddit's or Apple's/Google's terms) and add your own rate-limiting/backoff if you plan to run this regularly or at larger scale.
Reddit data shape: posts have a `title` field; comments generally don't. `normalize.py` uses that as a simple way to tell them apart in the combined file — it's a heuristic, not a guarantee, if the actor's schema changes.
Dedup is exact-match, not fuzzy: `clean_pipeline.py` removes exact duplicate rows (same platform+author+text+date) and removes Reddit posts that resurface under more than one search query. It won't catch two genuinely different reviews that happen to say almost the same thing in slightly different words — that would need a fuzzy-matching library (e.g. `rapidfuzz`) on top, which isn't included here.
dashboard.html has no backend: it's a single static file that reads whatever CSV/JSON you load into it, entirely in your browser. Nothing is uploaded anywhere, and nothing persists between page loads — reload the page and you'll need to load the file again.

# SpotifyPM — Spotify Reviews Scraper

This tool collects Spotify reviews and mentions from three places — the Google Play Store, the Apple App Store, and Reddit — and saves them as both CSV and JSON files. You get the raw data from each source separately, plus one combined file that puts everything into the same format so it's easy to work with.

## What you need before starting

| Source | How it gets the data | Do you need an API key? |
|---|---|---|
| Google Play Store | A free library called `google-play-scraper` | No |
| Apple App Store | A direct request to Apple's own public reviews feed (no extra scraping tool needed) | No |
| Reddit | A third-party tool called Apify, accessed through `apify-client` | Yes — you'll need an `APIFY_TOKEN` |

## Step 1: Set up the project

Open a terminal and run:

```bash
cd spotify-reviews-scraper
python3 -m venv .venv && source .venv/bin/activate   # optional, but recommended
pip install -r requirements.txt
cp .env.example .env
```

Then open the `.env` file and add your Apify token, like this:

```
APIFY_TOKEN=your_apify_token_here
```

> ⚠️ **Important:** If you've ever pasted an Apify token into a chat, a recorded terminal session, or a shared document, consider it compromised. Generate a new one at https://console.apify.com/account/integrations before using it here.

## Step 2: Run the scraper

```bash
python main.py
```

This collects reviews from all three sources, across several countries' app stores, and saves everything into a folder called `output/`:

```
output/
  play_store_raw.json      play_store_raw.csv      # everything from the Play Store, multiple countries
  app_store_raw.json       app_store_raw.csv       # everything from the App Store, multiple countries
  reddit_raw.json          reddit_raw.csv          # everything from Reddit
  combined_reviews.json    combined_reviews.csv    # all three sources merged into one format (not yet cleaned)
```

The combined file includes these columns for every entry: `platform, id, author, rating, title, text, date, thumbs_up, app_version, reply_text, url`.

Note: only Play Store and App Store entries have a real star rating. Reddit posts don't have ratings — instead, the `thumbs_up` column shows the post or comment's upvote score.

If you only want one source instead of all three, you can skip the others:

```bash
python main.py --skip-apple --skip-reddit   # Play Store only
```

## Step 3: Clean and organize the data

```bash
python clean_pipeline.py
```

This takes the raw files from `output/` and produces one clean, consistent file: `output/cleaned_reviews.csv` and `.json`. During this step it: tidies up the review text, converts all dates into a standard format, makes sure every rating is a whole number from 1 to 5, removes empty/blank entries, and removes duplicates (exact matches by platform, author, text, and date — Reddit posts are also checked separately since the same post can show up under more than one search term).

This cleaned file has these columns: `record_id, platform, author, rating, title, text, word_count, date, year_month, country, subreddit, app_version, thumbs_up, reply_text, url`.

This is the file you should use for any analysis or for loading into the dashboard. You can re-run this step any time after a new scrape — it just processes files you already have, it doesn't go fetch anything new from the internet.

## Step 4: Explore the data visually

Open the file `dashboard.html` directly in your web browser — no setup, no installation, no server needed, it's just one file. Once it's open, click the "Load CSV" or "Load JSON" button and select your `cleaned_reviews` file. If you want to try it out first without your own data, click "Load sample data" to preview it with placeholder data.

You can filter the data by: which platform it came from, which country's app store, app version, which subreddit, star rating, date range, or by searching for specific words in the title, author, or review text. There's also an "Export filtered (CSV)" button, so you can pull out just the slice you need — for example, "all 1-star Android reviews from Germany in March" — to drop into a slide or report.

**What you won't find as filters:** gender and device type. None of the three sources (Google Play, Apple's App Store, or Reddit) actually provide that information about reviewers. Guessing someone's gender from their username, or their device from anything else in the data, would mean making up information rather than reporting it — so those filters simply don't exist here.

## Step 5: Adjust the settings

All the app-specific settings live in one file: `config.py`. (It currently pulls just 10 reviews per source, for testing purposes — increase this once you're ready for a full run.)

- `PLAY_STORE_APP_ID` — which app to scrape (defaults to Spotify: `com.spotify.music`)
- `PLAY_STORE_COUNTRIES` / `APP_STORE_COUNTRIES` — which countries' app stores to pull from (defaults to: US, UK, Germany, India, Brazil, Australia). This is what powers the "country" filter in the dashboard — add or remove country codes here to change it. Note: the language setting `PLAY_STORE_LANG` is fixed to English across all countries, so for non-English-speaking markets, you'll only get their English-language reviews, not reviews written in the local language.
- `REDDIT_QUERIES` — the search terms used to find Reddit posts (defaults to a few Spotify-related phrases, to catch more than just posts containing the exact word "Spotify")
- `REDDIT_COMMENTS_MODE` — controls how much Reddit data gets pulled: `"none"` (fastest and cheapest — just posts, no comments), `"all"` (every comment on every post — much slower and uses more of your Apify usage), or `"high_engagement"` (comments only on the most popular posts)

## Things worth knowing before you rely on this data

**Apple only gives you recent reviews.** Apple's public reviews feed only exposes a limited, recent window of reviews per country — capped at roughly the same few-hundred-per-country ceiling regardless of how high you set `APP_STORE_HOW_MANY` in `config.py`. This isn't a limitation of this tool — it's simply what Apple's feed makes available. Getting older, broader historical data would require Apple's official App Store Connect API (which is only available to a developer who owns the app — meaning it doesn't apply here, since this isn't Spotify's own team) or a paid third-party dataset.

**More countries means more time.** Scraping 6 countries instead of 1 roughly multiplies how long the Play Store and App Store scraping takes by 6. If you want a faster run, reduce the list of countries in `config.py`.

**Reddit scraping can use significant Apify usage.** The setting controlling how many Reddit posts get pulled per search term is currently set very high (essentially "no limit" — it just stops once a search term runs out of results). For a popular topic like "Spotify," this can mean a long run and noticeable usage on your Apify account, especially if you turn on full comment scraping. Keep an eye on your usage in the Apify console, and consider starting with a smaller limit (e.g., 200 per search term) to check everything looks right before doing a full run.

**Google Play has a lot of reviews.** Spotify has an enormous number of Play Store reviews in every country, and the tool fetches them in batches of 200 with a short pause between each batch — that pause is intentional, to avoid overwhelming Google's servers, and is the main reason a full run takes a while.

**Please use this responsibly.** These reviews and posts are publicly visible, but each platform (Reddit, Apple, Google) has its own terms of service around automated data collection. Don't overload their servers, and don't republish this data in ways that violate their terms. If you plan to run this regularly or at a larger scale, consider adding your own rate-limiting.

**Telling Reddit posts and comments apart isn't perfect.** Reddit posts have a `title`, while comments generally don't — that difference is what the tool uses to tell them apart in the combined file. It's a reasonable shortcut, not a guarantee, and could break if Reddit's data format changes in the future.

**Duplicate removal is exact-match, not "fuzzy."** The cleaning step removes rows that are exact duplicates (same platform, author, text, and date), and removes Reddit posts that show up under more than one search term. It will not catch two different reviews that just happen to say almost the same thing in slightly different words — catching that would require an additional fuzzy-matching tool (such as `rapidfuzz`), which isn't included here.

**The dashboard works entirely offline, in your browser.** `dashboard.html` has no backend — it's a single file that simply reads whatever CSV or JSON file you load into it, directly in your browser. Nothing is uploaded anywhere, and nothing is saved between visits — if you reload the page, you'll need to load your file again.

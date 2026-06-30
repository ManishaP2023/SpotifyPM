import os

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

# ---------------------------------------------------------------------------
# Google Play Store
# ---------------------------------------------------------------------------
PLAY_STORE_APP_ID = "com.spotify.music"
PLAY_STORE_LANG = "en"
# Scraped once per country so "geography" in the dashboard is real signal,
# not a single flat locale. Note: lang stays "en" for all of them, so this
# captures English-language reviews from each storefront, not necessarily
# the dominant local language reviews in that country.
PLAY_STORE_COUNTRIES = ["us", "gb", "de", "in", "br", "au"]
# None = "no cap" (pulls every review -- this is what the full real run uses).
# Set to an int (e.g. 20) for a fast smoke test -- reviews_all() ignores any
# such limit on its own, so this is what actually makes a small test fast.
PLAY_STORE_MAX_REVIEWS_PER_COUNTRY = 10

# ---------------------------------------------------------------------------
# Apple App Store
# ---------------------------------------------------------------------------
APP_STORE_APP_NAME = "spotify-music"
APP_STORE_APP_ID = "324684580"
APP_STORE_COUNTRIES = ["us"]
# Apple's own review endpoint only ever exposes a limited recent window
# (in practice well under ~1000 reviews) per country, no matter how high
# this is set. The scraper stops automatically once it runs out of pages.
APP_STORE_HOW_MANY = 10

# ---------------------------------------------------------------------------
# Reddit (via Apify actor: spry_wholemeal/reddit-scraper)
# ---------------------------------------------------------------------------
REDDIT_ACTOR_ID = "spry_wholemeal/reddit-scraper"
REDDIT_QUERIES = [
    "Spotify",
    "Spotify app",
    "Spotify premium",
    "Spotify review",
]
# High ceiling = "no cap" in practice; the actor stops early once a query
# runs out of results. Lower this if you want to control Apify usage/cost.
REDDIT_MAX_POSTS_PER_QUERY = 10
# "none" (fastest/cheapest), "all" (every post's comments -- slow & costly),
# or "high_engagement" (only popular posts' comments).
REDDIT_COMMENTS_MODE = "none"

# ---------------------------------------------------------------------------
# YouTube (via official YouTube Data API v3)
# ---------------------------------------------------------------------------
YOUTUBE_QUERIES = ["Spotify review", "Spotify app", "Spotify premium"]
# search.list costs 100 quota units PER CALL regardless of how many results
# you ask for (up to 50) -- the expensive part is the number of searches,
# not the number of videos returned. Default free daily quota is 10,000
# units (100 searches/day) unless you've requested more from Google.
YOUTUBE_MAX_VIDEOS_PER_QUERY = 10
# commentThreads.list costs only 1 unit per call (up to 100 comments per
# page) -- comments are cheap once you have video IDs; searches are what
# to ration.
YOUTUBE_MAX_COMMENTS_PER_VIDEO = 50

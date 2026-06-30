#!/usr/bin/env python3
"""
Spotify Reviews Scraper
========================
Pulls everything it can find about Spotify from:
  - Google Play Store  (google-play-scraper      -- no key needed)
  - Apple App Store    (app_store_scraper        -- no key needed)
  - Reddit             (Apify: spry_wholemeal/reddit-scraper -- needs APIFY_TOKEN)

Usage:
    python main.py                          # run all three
    python main.py --skip-reddit            # skip the Apify/Reddit step
    python main.py --skip-play --skip-apple # Reddit only
"""
import argparse
import os
import traceback

from dotenv import load_dotenv

import config
from apple_appstore import scrape_app_store_reviews
from normalize import normalize_app_store, normalize_play_store, normalize_reddit, normalize_youtube
from play_store_scraper import scrape_play_store_reviews
from reddit_scraper import scrape_reddit_mentions
from youtube_scraper import scrape_youtube_comments
from utils import save_csv, save_json

COMBINED_FIELDS = [
    "platform", "id", "author", "rating", "title", "text",
    "date", "thumbs_up", "app_version", "reply_text", "url",
]


def run(skip_play=False, skip_apple=False, skip_reddit=False, skip_youtube=False):
    load_dotenv()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    combined = []

    if not skip_play:
        print("\n=== Google Play Store ===")
        try:
            play_reviews = scrape_play_store_reviews(
                app_id=config.PLAY_STORE_APP_ID,
                lang=config.PLAY_STORE_LANG,
                countries=config.PLAY_STORE_COUNTRIES,
                max_reviews_per_country=config.PLAY_STORE_MAX_REVIEWS_PER_COUNTRY,
            )
            save_json(play_reviews, f"{config.OUTPUT_DIR}/play_store_raw.json")
            save_csv(play_reviews, f"{config.OUTPUT_DIR}/play_store_raw.csv")
            combined.extend(normalize_play_store(r) for r in play_reviews)
        except Exception:
            print("[Play Store] FAILED:")
            traceback.print_exc()

    if not skip_apple:
        print("\n=== Apple App Store ===")
        try:
            apple_reviews = scrape_app_store_reviews(
                app_name=config.APP_STORE_APP_NAME,
                app_id=config.APP_STORE_APP_ID,
                countries=config.APP_STORE_COUNTRIES,
                how_many=config.APP_STORE_HOW_MANY,
            )
            save_json(apple_reviews, f"{config.OUTPUT_DIR}/app_store_raw.json")
            save_csv(apple_reviews, f"{config.OUTPUT_DIR}/app_store_raw.csv")
            combined.extend(normalize_app_store(r) for r in apple_reviews)
        except Exception:
            print("[App Store] FAILED:")
            traceback.print_exc()

    if not skip_reddit:
        print("\n=== Reddit (via Apify) ===")
        try:
            reddit_items = scrape_reddit_mentions(
                queries=config.REDDIT_QUERIES,
                max_posts_per_query=config.REDDIT_MAX_POSTS_PER_QUERY,
                comments_mode=config.REDDIT_COMMENTS_MODE,
            )
            save_json(reddit_items, f"{config.OUTPUT_DIR}/reddit_raw.json")
            save_csv(reddit_items, f"{config.OUTPUT_DIR}/reddit_raw.csv")
            combined.extend(normalize_reddit(r) for r in reddit_items)
        except Exception:
            print("[Reddit] FAILED:")
            traceback.print_exc()

    if not skip_youtube:
        print("\n=== YouTube (official Data API v3) ===")
        try:
            youtube_comments = scrape_youtube_comments(
                queries=config.YOUTUBE_QUERIES,
                max_videos_per_query=config.YOUTUBE_MAX_VIDEOS_PER_QUERY,
                max_comments_per_video=config.YOUTUBE_MAX_COMMENTS_PER_VIDEO,
            )
            save_json(youtube_comments, f"{config.OUTPUT_DIR}/youtube_raw.json")
            save_csv(youtube_comments, f"{config.OUTPUT_DIR}/youtube_raw.csv")
            combined.extend(normalize_youtube(c) for c in youtube_comments)
        except Exception:
            print("[YouTube] FAILED:")
            traceback.print_exc()

    print(f"\n=== Combined: {len(combined)} total records ===")
    save_json(combined, f"{config.OUTPUT_DIR}/combined_reviews.json")
    save_csv(combined, f"{config.OUTPUT_DIR}/combined_reviews.csv", fieldnames=COMBINED_FIELDS)
    print(f"\nDone. Files are in ./{config.OUTPUT_DIR}/")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Spotify reviews/mentions from Play Store, App Store, and Reddit."
    )
    parser.add_argument("--skip-play", action="store_true", help="Skip Google Play Store")
    parser.add_argument("--skip-apple", action="store_true", help="Skip Apple App Store")
    parser.add_argument("--skip-reddit", action="store_true", help="Skip Reddit/Apify")
    parser.add_argument("--skip-youtube", action="store_true", help="Skip YouTube comments")
    args = parser.parse_args()
    run(skip_play=args.skip_play, skip_apple=args.skip_apple, skip_reddit=args.skip_reddit, skip_youtube=args.skip_youtube)


if __name__ == "__main__":
    main()

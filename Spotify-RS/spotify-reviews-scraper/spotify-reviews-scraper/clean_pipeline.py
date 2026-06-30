#!/usr/bin/env python3
"""
clean_pipeline.py
==================
Takes the raw per-platform files produced by main.py
(play_store_raw.json, app_store_raw.json, reddit_raw.json) and produces
one clean, deduplicated, homogeneous dataset:

    output/cleaned_reviews.csv
    output/cleaned_reviews.json

What it does:
  1. Re-normalizes every platform's raw fields onto one schema (reusing
     normalize.py, the same mapping main.py uses for combined_reviews).
  2. Cleans text: unicode-normalizes, decodes HTML entities, collapses
     whitespace, strips control characters.
  3. Parses every date into ISO-8601 UTC, and derives a `year_month`
     column for easy time-based grouping.
  4. Normalizes ratings to int 1-5 (or None where not applicable, e.g.
     Reddit).
  5. Drops empty/contentless rows (no title AND no text).
  6. Deduplicates:
       - Reddit posts can show up under more than one of our search
         queries -- deduped on permalink/id first.
       - Everything else is deduped on (platform, author, cleaned text,
         date) as an exact-match composite key.
     This is exact-match dedup, not fuzzy matching -- near-duplicate
     reviews with slightly different wording will both be kept.
  7. Adds a stable `record_id` (short hash) per row for the dashboard.

Run this any time after main.py finishes (or re-run it after a fresh
scrape) -- it doesn't touch the network at all.

Usage:
    python clean_pipeline.py
    python clean_pipeline.py --output-dir output
"""
import argparse
import hashlib
import html
import json
import os
import re
import unicodedata

from dateutil import parser as date_parser

import config
from normalize import normalize_app_store, normalize_play_store, normalize_reddit, normalize_youtube
from utils import save_csv, save_json

CLEANED_FIELDS = [
    "record_id", "platform", "author", "rating", "title", "text",
    "word_count", "date", "year_month", "country", "subreddit",
    "app_version", "thumbs_up", "reply_text", "url",
]


def clean_text(value):
    """Collapse whitespace, decode entities, normalize unicode. None-safe."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # control chars
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_rating(value):
    if value is None or value == "":
        return None
    try:
        rating = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if 1 <= rating <= 5:
        return rating
    return None


def normalize_date(value):
    """Returns (iso_string, year_month) or ('', '') if unparseable."""
    if value is None or value == "":
        return "", ""
    try:
        dt = date_parser.parse(str(value))
    except (ValueError, OverflowError, TypeError):
        return "", ""
    iso = dt.isoformat()
    return iso, iso[:7]


def make_record_id(platform, author, date_iso, clean_txt):
    basis = f"{platform}|{author}|{date_iso}|{clean_txt[:200]}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def load_raw(output_dir, filename):
    path = os.path.join(output_dir, filename)
    if not os.path.exists(path):
        print(f"  (skipping {filename} -- not found in {output_dir}/)")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_clean_record(normalized):
    """normalized is one of normalize_play_store/app_store/reddit's output."""
    clean_txt = clean_text(normalized.get("text"))
    clean_title = clean_text(normalized.get("title"))
    date_iso, year_month = normalize_date(normalized.get("date"))
    rating = normalize_rating(normalized.get("rating"))
    author = clean_text(normalized.get("author")) or None

    return {
        "record_id": make_record_id(normalized["platform"], author, date_iso, clean_txt),
        "platform": normalized["platform"],
        "author": author,
        "rating": rating,
        "title": clean_title or None,
        "text": clean_txt or None,
        "word_count": len(clean_txt.split()) if clean_txt else 0,
        "date": date_iso or None,
        "year_month": year_month or None,
        "country": normalized.get("country"),
        "subreddit": normalized.get("subreddit"),
        "app_version": normalized.get("app_version"),
        "thumbs_up": normalized.get("thumbs_up"),
        "reply_text": clean_text(normalized.get("reply_text")) or None,
        "url": normalized.get("url"),
    }


def dedupe(records):
    seen_reddit_ids = set()
    seen_composite = set()
    deduped = []
    dropped_empty = 0
    dropped_dupe = 0

    for r in records:
        if not r["text"] and not r["title"]:
            dropped_empty += 1
            continue

        if r["platform"] == "reddit" and r["url"]:
            if r["url"] in seen_reddit_ids:
                dropped_dupe += 1
                continue
            seen_reddit_ids.add(r["url"])

        composite = (r["platform"], r["author"], r["text"], r["date"])
        if composite in seen_composite:
            dropped_dupe += 1
            continue
        seen_composite.add(composite)

        deduped.append(r)

    return deduped, dropped_empty, dropped_dupe


def run(output_dir):
    print(f"Reading raw files from ./{output_dir}/ ...")
    play_raw = load_raw(output_dir, "play_store_raw.json")
    apple_raw = load_raw(output_dir, "app_store_raw.json")
    reddit_raw = load_raw(output_dir, "reddit_raw.json")
    youtube_raw = load_raw(output_dir, "youtube_raw.json")

    all_records = []
    all_records += [build_clean_record(normalize_play_store(r)) for r in play_raw]
    all_records += [build_clean_record(normalize_app_store(r)) for r in apple_raw]
    all_records += [build_clean_record(normalize_reddit(r)) for r in reddit_raw]
    all_records += [build_clean_record(normalize_youtube(r)) for r in youtube_raw]

    print(f"Loaded {len(all_records)} raw records "
          f"({len(play_raw)} Play Store, {len(apple_raw)} App Store, "
          f"{len(reddit_raw)} Reddit, {len(youtube_raw)} YouTube).")

    deduped, dropped_empty, dropped_dupe = dedupe(all_records)

    print(f"Dropped {dropped_empty} empty (no title/text) records.")
    print(f"Dropped {dropped_dupe} duplicate records.")
    print(f"Final cleaned dataset: {len(deduped)} records.")

    save_json(deduped, f"{output_dir}/cleaned_reviews.json")
    save_csv(deduped, f"{output_dir}/cleaned_reviews.csv", fieldnames=CLEANED_FIELDS)
    print(f"\nDone. Load output/cleaned_reviews.csv (or .json) into dashboard.html.")


def main():
    parser = argparse.ArgumentParser(description="Clean, normalize, and dedupe scraped review data.")
    parser.add_argument("--output-dir", default=config.OUTPUT_DIR, help="Folder with the raw *_raw.json files")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()

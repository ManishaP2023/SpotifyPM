"""
Scrapes Apple App Store reviews directly from Apple's public RSS-based
customer reviews JSON feed, across one or more country storefronts.
No API key, no third-party scraping package -- just a plain HTTP request:

    https://itunes.apple.com/{country}/rss/customerreviews/page={page}/sortby=mostrecent/id={app_id}/json

NOTE: this used to go through the `app_store_scraper` PyPI package, which
scrapes a different, undocumented endpoint (amp-api.apps.apple.com) via a
token it extracts from the App Store webpage. That token-extraction step
is fragile and breaks whenever Apple tweaks its page -- which is exactly
what was happening ("Expecting value: line 1 column 1" on every request).
The RSS feed used here is older, more stable, and needs no token at all.
Trade-off: it caps out at roughly MAX_PAGES x PAGE_SIZE reviews per
country, which is the same practical ceiling app_store_scraper hit anyway.
"""
import time

import requests

REVIEWS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/sortby=mostrecent/id={app_id}/json"
MAX_PAGES = 10  # Apple's feed doesn't reliably go further than this
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_PAGES = 0.5  # seconds -- avoid tripping Apple's rate limiting
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; review-scraper/1.0)"}


def _parse_entry(entry, country):
    # The feed occasionally includes a non-review metadata entry (missing
    # author/rating) -- skip anything that doesn't look like a real review.
    if "author" not in entry or "im:rating" not in entry:
        return None
    return {
        "id": entry.get("id", {}).get("label"),
        "userName": entry.get("author", {}).get("name", {}).get("label"),
        "rating": entry.get("im:rating", {}).get("label"),
        "title": entry.get("title", {}).get("label"),
        "review": entry.get("content", {}).get("label"),
        "date": entry.get("updated", {}).get("label"),
        "appVersion": entry.get("im:version", {}).get("label"),
        "voteSum": entry.get("im:voteSum", {}).get("label"),
        "voteCount": entry.get("im:voteCount", {}).get("label"),
        "_scraped_country": country,
    }


def _scrape_one_country(app_id, country, max_reviews):
    reviews = []
    seen_ids = set()

    for page in range(1, MAX_PAGES + 1):
        if max_reviews and len(reviews) >= max_reviews:
            break

        url = REVIEWS_URL.format(country=country, page=page, app_id=app_id)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[App Store] {country} page {page} failed, stopping there: {exc}")
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break  # no more pages available

        new_count = 0
        for entry in entries:
            parsed = _parse_entry(entry, country)
            if parsed and parsed["id"] not in seen_ids:
                seen_ids.add(parsed["id"])
                reviews.append(parsed)
                new_count += 1

        if new_count == 0:
            break  # nothing new on this page -- we've run out

        time.sleep(SLEEP_BETWEEN_PAGES)

    return reviews[:max_reviews] if max_reviews else reviews


def scrape_app_store_reviews(app_name, app_id, countries=None, how_many=100_000):
    """
    `app_name` is kept as a parameter for compatibility with the rest of
    the project (used only in print statements) -- this endpoint only
    actually needs `app_id`.
    """
    countries = countries or ["us"]
    all_reviews = []

    for country in countries:
        print(f"[App Store] Scraping reviews for '{app_name}' (id={app_id}, country={country}) ...")
        try:
            results = _scrape_one_country(app_id, country, how_many)
        except Exception as exc:
            print(f"[App Store] {country} failed, skipping: {exc}")
            continue
        print(f"[App Store] {country}: retrieved {len(results)} reviews.")
        all_reviews.extend(results)

    print(f"[App Store] Total across {len(countries)} countries: {len(all_reviews)} reviews.")
    return all_reviews

"""
Scrapes Google Play Store reviews for an app, across one or more
country storefronts, using google-play-scraper. No API key required --
it reads Google Play's public review endpoint.

pip install google-play-scraper
"""
from google_play_scraper import Sort, reviews, reviews_all

PAGE_SIZE = 200  # Google Play's own max reviews-per-request


def _scrape_one_country_capped(app_id, lang, country, max_reviews):
    """Paginates manually so we can stop after max_reviews -- reviews_all()
    has no such option, it always pulls everything."""
    collected = []
    token = None
    while len(collected) < max_reviews:
        batch, token = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=min(PAGE_SIZE, max_reviews - len(collected)),
            continuation_token=token,
        )
        if not batch:
            break
        collected.extend(batch)
        if token is None:  # no more pages available
            break
    return collected[:max_reviews]


def scrape_play_store_reviews(app_id, lang="en", countries=None, max_reviews_per_country=None):
    """
    Returns reviews for app_id/lang, across each country in `countries`.

    max_reviews_per_country:
        None  -> pulls EVERY review available (the "no cap" full-run behavior).
        int   -> stops after that many reviews per country -- use this for a
                 fast smoke test, since reviews_all() ignores any such limit.

    Each review dict gets an extra `_scraped_country` key so downstream code
    can use it as a geography field -- it's the storefront we asked for, not
    anything Google tells us about the reviewer's actual location.
    """
    countries = countries or ["us"]
    all_reviews = []

    for country in countries:
        cap_note = f" (capped at {max_reviews_per_country})" if max_reviews_per_country else ""
        print(f"[Play Store] Scraping reviews for {app_id} ({lang}/{country}){cap_note} ...")
        try:
            if max_reviews_per_country:
                results = _scrape_one_country_capped(app_id, lang, country, max_reviews_per_country)
            else:
                results = reviews_all(
                    app_id,
                    sleep_milliseconds=150,  # small delay between pages to avoid throttling
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                )
        except Exception as exc:
            print(f"[Play Store] {country} failed, skipping: {exc}")
            continue

        for r in results:
            r["_scraped_country"] = country
        print(f"[Play Store] {country}: retrieved {len(results)} reviews.")
        all_reviews.extend(results)

    print(f"[Play Store] Total across {len(countries)} countries: {len(all_reviews)} reviews.")
    return all_reviews

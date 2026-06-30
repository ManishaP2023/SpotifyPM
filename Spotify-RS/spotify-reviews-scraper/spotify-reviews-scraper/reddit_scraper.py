"""
Pulls Reddit posts (and optionally comments) mentioning Spotify via the
Apify actor `spry_wholemeal/reddit-scraper`. No Reddit login/API app
needed -- the actor itself scrapes Reddit's public JSON endpoints through
Apify's proxies.

pip install apify-client

Requires the APIFY_TOKEN environment variable (put it in a .env file --
see .env.example). Rotate your token at:
https://console.apify.com/account/integrations
"""
import os

from apify_client import ApifyClient

import config


def scrape_reddit_mentions(queries=None, max_posts_per_query=None, comments_mode=None):
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError(
            "APIFY_TOKEN is not set. Add it to a .env file in this folder "
            "(see .env.example) or export it in your shell before running."
        )

    queries = queries or config.REDDIT_QUERIES
    max_posts_per_query = max_posts_per_query or config.REDDIT_MAX_POSTS_PER_QUERY
    comments_mode = comments_mode or config.REDDIT_COMMENTS_MODE

    client = ApifyClient(token)

    run_input = {
        "mode": "search",
        "search": {
            "queries": queries,
            "sort": "relevance",
            "maxPostsPerQuery": max_posts_per_query,
        },
        "comments": {
            "mode": comments_mode,  # "none" | "all" | "high_engagement"
        },
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
        "tag": "spotify-review-scraper",
    }

    print(f"[Reddit] Starting actor '{config.REDDIT_ACTOR_ID}' for queries={queries} ...")
    run = client.actor(config.REDDIT_ACTOR_ID).call(run_input=run_input)

    dataset_id = _extract_dataset_id(run)
    items = _list_all_items(client.dataset(dataset_id))

    suffix = " (posts only)" if comments_mode == "none" else " (posts + comments)"
    print(f"[Reddit] Retrieved {len(items)} items{suffix}.")
    return items


def _extract_dataset_id(run):
    """
    Newer apify-client (2.x+) returns a typed Run object with snake_case
    attributes (run.default_dataset_id); older versions returned a plain
    dict with a camelCase key (run['defaultDatasetId']). Support both so
    this keeps working regardless of which apify-client version pip
    actually installed.
    """
    if hasattr(run, "default_dataset_id"):
        return run.default_dataset_id
    if isinstance(run, dict):
        value = run.get("defaultDatasetId") or run.get("default_dataset_id")
        if value:
            return value
    raise RuntimeError(f"Could not find a dataset ID on the Apify run result: {run!r}")


def _list_all_items(dataset_client):
    """Same story as above: support both the newer iterate_items()
    streaming method and the older list_items().items method."""
    if hasattr(dataset_client, "iterate_items"):
        return list(dataset_client.iterate_items())
    return dataset_client.list_items().items

"""
Maps each platform's native fields onto one common schema so the
combined CSV/JSON has consistent columns across all three sources.

Deliberately NOT included: gender, device. Neither Google Play, Apple's
App Store, nor Reddit's public data exposes reviewer demographics or
device info -- there's no real signal to put in those columns, so they're
left out rather than guessed at (e.g. from usernames).
"""
import re

_SUBREDDIT_RE = re.compile(r"^/r/([^/]+)/")


def normalize_play_store(item):
    return {
        "platform": "google_play",
        "id": item.get("reviewId"),
        "author": item.get("userName"),
        "rating": item.get("score"),
        "title": None,
        "text": item.get("content"),
        "date": item.get("at"),
        "thumbs_up": item.get("thumbsUpCount"),
        "app_version": item.get("reviewCreatedVersion") or item.get("appVersion"),
        "reply_text": item.get("replyContent"),
        "url": None,
        "country": item.get("_scraped_country"),
        "subreddit": None,
    }


def normalize_app_store(item):
    return {
        "platform": "app_store",
        "id": item.get("id") or f"{item.get('userName')}_{item.get('date')}",
        "author": item.get("userName"),
        "rating": item.get("rating"),
        "title": item.get("title"),
        "text": item.get("review"),
        "date": item.get("date"),
        "thumbs_up": item.get("voteSum"),
        "app_version": item.get("appVersion"),
        "reply_text": None,  # Apple's RSS feed doesn't include developer replies
        "url": None,
        "country": item.get("_scraped_country"),
        "subreddit": None,
    }


def normalize_reddit(item):
    # Posts carry a 'title'; comments generally don't -- used as a
    # lightweight way to tell them apart in the combined output.
    is_post = bool(item.get("title"))
    permalink = item.get("permalink")

    subreddit = None
    if permalink:
        match = _SUBREDDIT_RE.match(permalink)
        if match:
            subreddit = match.group(1)

    return {
        "platform": "reddit",
        "id": permalink or item.get("id"),
        "author": item.get("author"),
        "rating": None,
        "title": item.get("title") if is_post else None,
        "text": item.get("text"),
        "date": item.get("created_utc_iso"),
        "thumbs_up": item.get("score"),
        "app_version": None,
        "reply_text": None,
        "url": f"https://reddit.com{permalink}" if permalink else None,
        "country": None,  # Reddit doesn't expose reviewer geography
        "subreddit": subreddit,
    }

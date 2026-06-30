"""
Pulls comments from YouTube videos matching search queries (e.g. "Spotify
review"), using the official YouTube Data API v3. No scraping involved --
this is a sanctioned, documented API.

Requires a free Google Cloud API key (YOUTUBE_API_KEY env var). Get one at
https://console.cloud.google.com/apis/credentials after enabling
"YouTube Data API v3" for your project.

Quota notes (default free quota: 10,000 units/day):
  - search.list costs 100 units PER CALL, regardless of how many results
    you ask for (up to 50). Searches are the expensive part -- ration
    YOUTUBE_QUERIES and YOUTUBE_MAX_VIDEOS_PER_QUERY accordingly.
  - commentThreads.list costs only 1 unit per call (up to 100 comments
    per page). Comments are cheap once you have video IDs.
"""
import os
import time

import requests

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_CALLS = 0.2


def _search_videos(api_key, query, max_videos):
    video_ids = []
    page_token = None

    while len(video_ids) < max_videos:
        params = {
            "key": api_key,
            "q": query,
            "part": "id",
            "type": "video",
            "maxResults": min(50, max_videos - len(video_ids)),
            "order": "relevance",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            print(f"[YouTube] search failed for '{query}': {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                video_ids.append(vid)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:max_videos]


def _fetch_comments_for_video(api_key, video_id, max_comments):
    comments = []
    page_token = None

    while len(comments) < max_comments:
        params = {
            "key": api_key,
            "videoId": video_id,
            "part": "snippet",
            "maxResults": min(100, max_comments - len(comments)),
            "order": "relevance",
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(COMMENTS_URL, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            # Comments disabled on this video (common), or another error --
            # skip quietly rather than aborting the whole run.
            break

        data = resp.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comments.append({
                "id": item.get("id"),
                "videoId": video_id,
                "author": snippet.get("authorDisplayName"),
                "text": snippet.get("textDisplay"),
                "date": snippet.get("publishedAt"),
                "likeCount": snippet.get("likeCount"),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(SLEEP_BETWEEN_CALLS)

    return comments[:max_comments]


def scrape_youtube_comments(queries=None, max_videos_per_query=10, max_comments_per_video=50):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set. Enable 'YouTube Data API v3' and create a "
            "free API key at https://console.cloud.google.com/apis/credentials, "
            "then add it to your .env file."
        )

    queries = queries or ["Spotify review", "Spotify app"]
    all_comments = []
    seen_video_ids = set()

    for query in queries:
        print(f"[YouTube] Searching videos for: '{query}' ...")
        try:
            video_ids = _search_videos(api_key, query, max_videos_per_query)
        except requests.RequestException as exc:
            print(f"[YouTube] search request failed for '{query}': {exc}")
            continue

        print(f"[YouTube] Found {len(video_ids)} videos for '{query}'.")

        for vid in video_ids:
            if vid in seen_video_ids:
                continue
            seen_video_ids.add(vid)
            try:
                comments = _fetch_comments_for_video(api_key, vid, max_comments_per_video)
            except requests.RequestException as exc:
                print(f"[YouTube]   video {vid} failed, skipping: {exc}")
                continue
            print(f"[YouTube]   video {vid}: {len(comments)} comments")
            all_comments.extend(comments)

        time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"[YouTube] Total: {len(all_comments)} comments across {len(seen_video_ids)} videos.")
    return all_comments

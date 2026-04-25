"""
Unified API Integration Layer
==============================
Accepts any video URL and extracts platform metadata.
Supports: YouTube, Instagram, Twitter/X, TikTok, Facebook (via yt-dlp)
Also supports: YouTube Data API v3 (richer metadata when key available)

yt-dlp extracts without downloading the video — metadata only.
Install: pip install yt-dlp
"""

import asyncio
import json
import subprocess
from typing import Optional
from urllib.parse import urlparse

import httpx

from config.settings import settings


# ── Platform Detection ────────────────────────────────────────────────────────

def detect_platform(url: str) -> str:
    """Detect which social platform a URL belongs to."""
    if not url:
        return "unknown"
    try:
        domain = urlparse(url).netloc.lower()
        if "youtube.com" in domain or "youtu.be" in domain:
            return "youtube"
        if "instagram.com" in domain:
            return "instagram"
        if "twitter.com" in domain or "x.com" in domain:
            return "twitter"
        if "tiktok.com" in domain:
            return "tiktok"
        if "facebook.com" in domain or "fb.watch" in domain:
            return "facebook"
        if "reddit.com" in domain or "redd.it" in domain:
            return "reddit"
        if "t.me" in domain or "telegram.me" in domain:
            return "telegram"
        return "web"
    except Exception:
        return "unknown"


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from any YouTube URL format."""
    try:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/").split("?")[0]
        if "v=" in parsed.query:
            for param in parsed.query.split("&"):
                if param.startswith("v="):
                    return param[2:]
        return None
    except Exception:
        return None


def extract_twitter_id(url: str) -> Optional[str]:
    """Extract Tweet ID from any Twitter/X URL format."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        # format: /username/status/123456789
        parts = path.split("/")
        if "status" in parts:
            idx = parts.index("status")
            if len(parts) > idx + 1:
                return parts[idx + 1].split("?")[0]
        return None
    except Exception:
        return None


# ── yt-dlp Metadata Extraction ────────────────────────────────────────────────

async def _ytdlp_metadata(url: str) -> dict:
    """
    Extract video metadata using yt-dlp WITHOUT downloading the video.
    Works on YouTube, Instagram, Twitter, TikTok, Facebook, and 1000+ sites.
    No API key needed. Free.

    Install: pip install yt-dlp
    """
    if not url:
        return {}
    try:
        # Run yt-dlp in subprocess to avoid blocking event loop
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [
                    "yt-dlp",
                    "--dump-json",          # Print metadata as JSON only
                    "--no-download",        # Do NOT download the video
                    "--no-warnings",
                    "--skip-download",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        )
        if result.returncode != 0 or not result.stdout:
            return {}
        data = json.loads(result.stdout.strip().split("\n")[0])  # First video only
        return {
            "platform": data.get("extractor_key", "unknown").lower(),
            "video_id": data.get("id"),
            "title": data.get("title"),
            "description": data.get("description", "")[:500],
            "upload_date": data.get("upload_date"),    # Format: YYYYMMDD
            "timestamp": data.get("timestamp"),         # Unix timestamp
            "uploader": data.get("uploader"),
            "channel": data.get("channel"),
            "channel_url": data.get("channel_url"),
            "channel_follower_count": data.get("channel_follower_count"),
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "comment_count": data.get("comment_count"),
            "location": data.get("location"),
            "tags": data.get("tags", []),
            "categories": data.get("categories", []),
            "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"),
            "age_limit": data.get("age_limit"),
            "is_live": data.get("is_live", False),
            "was_live": data.get("was_live", False),
        }
    except Exception as e:
        print(f"[APIIntegrations/yt-dlp] Failed for {url}: {e}")
        return {}


# ── YouTube Data API v3 (Richer — requires key) ───────────────────────────────

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"

async def _youtube_api_metadata(video_id: str) -> dict:
    """
    Fetch YouTube video metadata via Data API v3.
    Richer than yt-dlp: includes recordingDetails, topicCategories, contentRating.
    Requires YOUTUBE_API_KEY — free tier.
    """
    if not settings.youtube_api_key or not video_id:
        return {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                YOUTUBE_API_URL,
                params={
                    "id": video_id,
                    "key": settings.youtube_api_key,
                    "part": "snippet,recordingDetails,statistics,topicDetails",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            if not items:
                return {}
            item = items[0]
            snippet = item.get("snippet", {})
            recording = item.get("recordingDetails", {})
            stats = item.get("statistics", {})
            return {
                "youtube_api": True,
                "title": snippet.get("title"),
                "description": snippet.get("description", "")[:500],
                "published_at": snippet.get("publishedAt"),
                "channel_title": snippet.get("channelTitle"),
                "channel_id": snippet.get("channelId"),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId"),
                "recording_date": recording.get("recordingDate"),
                "recording_location": recording.get("location"),
                "view_count": stats.get("viewCount"),
                "like_count": stats.get("likeCount"),
                "comment_count": stats.get("commentCount"),
            }
    except Exception as e:
        print(f"[APIIntegrations/YouTubeAPI] Failed for {video_id}: {e}")
        return {}


# ── X (Twitter) API v2 (Requires Bearer Token) ────────────────────────────────

TWITTER_API_URL = "https://api.twitter.com/2/tweets"

async def _twitter_api_metadata(tweet_id: str) -> dict:
    """
    Fetch Tweet metadata via X API v2.
    Requires X_BEARER_TOKEN.
    """
    if not settings.x_bearer_token or not tweet_id:
        return {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TWITTER_API_URL}/{tweet_id}",
                params={
                    "tweet.fields": "created_at,text,author_id,geo,public_metrics,lang",
                    "expansions": "author_id,geo.place_id",
                    "user.fields": "name,username,location,verified",
                    "place.fields": "full_name,geo",
                },
                headers={"Authorization": f"Bearer {settings.x_bearer_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            tweet = data.get("data", {})
            includes = data.get("includes", {})
            user = includes.get("users", [{}])[0]
            place = includes.get("places", [{}])[0]

            return {
                "twitter_api": True,
                "title": tweet.get("text", "")[:100],
                "description": tweet.get("text"),
                "published_at": tweet.get("created_at"),
                "uploader": user.get("name"),
                "channel": user.get("username"),
                "location": place.get("full_name") or user.get("location"),
                "view_count": tweet.get("public_metrics", {}).get("impression_count"),
                "like_count": tweet.get("public_metrics", {}).get("like_count"),
                "comment_count": tweet.get("public_metrics", {}).get("reply_count"),
                "lang": tweet.get("lang"),
            }
    except Exception as e:
        print(f"[APIIntegrations/TwitterAPI] Failed for {tweet_id}: {e}")
        return {}


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def extract_platform_metadata(url: str) -> dict:
    """
    Main entry point for API Integration Layer.
    Call this from Source Hunter and Context Analyser.

    1. Detect platform
    2. Extract via yt-dlp (always, no key)
    3. If YouTube + key available → also fetch from YouTube API v3
    4. Merge results (YouTube API takes precedence for overlapping fields)

    Returns unified metadata dict regardless of platform.
    """
    if not url:
        return {}

    platform = detect_platform(url)

    # Always try yt-dlp first
    ytdlp_meta = await _ytdlp_metadata(url)

    # If YouTube and API key available, enrich with API data
    youtube_api_meta = {}
    if platform == "youtube" and settings.youtube_api_key:
        video_id = extract_youtube_id(url)
        if video_id:
            youtube_api_meta = await _youtube_api_metadata(video_id)

    # If Twitter and Bearer Token available, enrich with API data
    twitter_api_meta = {}
    if platform == "twitter" and settings.x_bearer_token:
        tweet_id = extract_twitter_id(url)
        if tweet_id:
            twitter_api_meta = await _twitter_api_metadata(tweet_id)

    # Merge: API data enriches yt-dlp data
    merged = {**ytdlp_meta, **youtube_api_meta, **twitter_api_meta}
    merged["platform"] = platform
    merged["original_url"] = url

    # Normalise upload_date to ISO format (yt-dlp returns YYYYMMDD)
    upload_date_raw = merged.get("upload_date") or merged.get("published_at", "")
    if upload_date_raw and len(upload_date_raw) == 8 and upload_date_raw.isdigit():
        merged["upload_date_iso"] = (
            f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"
        )
    else:
        merged["upload_date_iso"] = upload_date_raw

    return merged

"""
Source Hunter Agent Node
=========================
Finds the earliest known source of a video on the internet.
Detects recirculation: same video shared with different location/date claims.

APIs used (all free tier):
  - Google Vision Web Detection (1000 req/month free)
  - TinEye (150 req/month free)
  - Bing Visual Search (free via Azure trial)
  - Wayback Machine (no key, always free)
  - yt-dlp (no key, always free — works on YouTube/Instagram/Twitter/TikTok)
  - ExifTool via subprocess (local, always free)
  - imagehash library (local, always free)
"""

import asyncio
import base64
import json
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
import imagehash
from langsmith import traceable
from PIL import Image

from agents.state import AgentFinding, AgentState
from agents.tools.api_integrations import extract_platform_metadata
from agents.tools.reverse_search import reverse_search_keyframes
from config.settings import settings

# ── Google Vision Web Detection ───────────────────────────────────────────────

GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"


async def _google_vision_search(frame_path: str) -> dict:
    """
    Sends a keyframe to Google Vision Web Detection.
    Returns dict with: web_entities, full_matches, partial_matches, pages
    Returns {} on failure.
    """
    if not settings.google_vision_api_key:
        return {}
    try:
        with open(frame_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "requests": [
                {
                    "image": {"content": image_b64},
                    "features": [{"type": "WEB_DETECTION", "maxResults": 10}],
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_VISION_URL,
                params={"key": settings.google_vision_api_key},
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            web = data.get("responses", [{}])[0].get("webDetection", {})
            return {
                "full_matches": web.get("fullMatchingImages", []),
                "partial_matches": web.get("partialMatchingImages", []),
                "pages": web.get("pagesWithMatchingImages", []),
                "entities": web.get("webEntities", []),
            }
    except Exception as e:
        print(f"[SourceHunter/GoogleVision] Failed: {e}")
        return {}


# ── TinEye ────────────────────────────────────────────────────────────────────

TINEYE_URL = "https://api.tineye.com/rest/search/"


async def _tineye_search(frame_path: str) -> dict:
    """
    Reverse image search via TinEye.
    Returns list of matches with first_seen dates.
    Returns {} on failure or if no API key.
    """
    if not settings.tineye_api_key:
        return {}
    try:
        with open(frame_path, "rb") as f:
            files = {"image": (Path(frame_path).name, f, "image/jpeg")}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TINEYE_URL,
                params={"api_key": settings.tineye_api_key},
                files=files,
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            matches = data.get("results", {}).get("matches", [])
            return {
                "match_count": len(matches),
                "matches": [
                    {
                        "domain": m.get("domain"),
                        "first_seen": m.get("image", {}).get("first_seen_date"),
                        "last_seen": m.get("image", {}).get("last_seen_date"),
                        "url": m.get("backlinks", [{}])[0].get("url")
                        if m.get("backlinks")
                        else None,
                    }
                    for m in matches[:5]  # Top 5 only
                ],
            }
    except Exception as e:
        print(f"[SourceHunter/TinEye] Failed: {e}")
        return {}


# ── Bing Visual Search ────────────────────────────────────────────────────────

BING_VISUAL_URL = "https://api.bing.microsoft.com/v7.0/images/visualsearch"


async def _bing_visual_search(frame_path: str) -> dict:
    """Bing Visual Search fallback. Free tier via Azure Cognitive Services."""
    if not settings.bing_search_api_key:
        return {}
    try:
        with open(frame_path, "rb") as f:
            files = {"image": (Path(frame_path).name, f, "image/jpeg")}
        headers = {"Ocp-Apim-Subscription-Key": settings.bing_search_api_key}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                BING_VISUAL_URL,
                headers=headers,
                files=files,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            # Extract image matches from Bing response
            tags = data.get("tags", [])
            pages = []
            for tag in tags:
                for action in tag.get("actions", []):
                    if action.get("actionType") == "PagesIncluding":
                        for item in action.get("data", {}).get("value", []):
                            pages.append(
                                {
                                    "url": item.get("contentUrl"),
                                    "name": item.get("name"),
                                    "date": item.get("datePublished"),
                                }
                            )
            return {"pages": pages[:10]}
    except Exception as e:
        print(f"[SourceHunter/Bing] Failed: {e}")
        return {}


# ── Wayback Machine ───────────────────────────────────────────────────────────

WAYBACK_URL = "http://archive.org/wayback/available"


async def _wayback_check(url: str) -> dict:
    """
    Check if a URL has been archived by the Wayback Machine.
    No API key needed. Use to verify claimed upload dates.
    """
    if not url:
        return {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WAYBACK_URL,
                params={"url": url},
                timeout=8.0,
            )
            response.raise_for_status()
            data = response.json()
            snapshot = data.get("archived_snapshots", {}).get("closest", {})
            return {
                "available": snapshot.get("available", False),
                "timestamp": snapshot.get("timestamp"),  # Format: YYYYMMDDHHmmss
                "url": snapshot.get("url"),
            }
    except Exception as e:
        print(f"[SourceHunter/Wayback] Failed: {e}")
        return {}


# ── EXIF + GPS Metadata ───────────────────────────────────────────────────────


def _extract_exif(video_path: str) -> dict:
    """
    Run ExifTool on the video file.
    Extracts: GPS coords, creation date, encoding software, camera model.
    ExifTool must be installed: sudo apt install exiftool (Linux) or brew install exiftool (Mac)
    """
    if not video_path or not Path(video_path).exists():
        return {}
    try:
        result = subprocess.run(
            ["exiftool", "-json", "-GPS*", "-Create*", "-Encode*", "-Software", video_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)
        if not data:
            return {}
        exif = data[0]
        return {
            "gps_lat": exif.get("GPSLatitude"),
            "gps_lon": exif.get("GPSLongitude"),
            "create_date": exif.get("CreateDate") or exif.get("TrackCreateDate"),
            "encoding_software": exif.get("EncodingSoftware") or exif.get("Software"),
            "suspicious_software": _is_ai_software(exif.get("EncodingSoftware", "")),
        }
    except Exception as e:
        print(f"[SourceHunter/EXIF] Failed: {e}")
        return {}


def _is_ai_software(software: str) -> bool:
    """Check if encoding software name suggests AI generation."""
    if not software:
        return False
    ai_tools = {
        "sora",
        "runway",
        "kling",
        "pika",
        "suno",
        "stable diffusion",
        "midjourney",
        "dall-e",
        "adobe firefly",
        "veo",
    }
    return any(tool in software.lower() for tool in ai_tools)


# ── Perceptual Hash ───────────────────────────────────────────────────────────


def _compute_phash(frame_path: str) -> str | None:
    """Compute perceptual hash of a frame for near-duplicate detection."""
    try:
        img = Image.open(frame_path)
        return str(imagehash.phash(img))
    except Exception:
        return None


# ── Earliest Date Helper ──────────────────────────────────────────────────────


def _find_earliest_date(results: dict) -> str | None:
    """Extract the earliest known appearance date from all search results."""
    dates = []
    for match in results.get("tineye", {}).get("matches", []):
        if match.get("first_seen"):
            dates.append(match["first_seen"])
    wayback = results.get("wayback", {})
    if wayback.get("timestamp"):
        ts = wayback["timestamp"]
        try:
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            dates.append(dt.isoformat())
        except Exception:
            pass
    platform_meta = results.get("platform_metadata", {})
    if platform_meta.get("upload_date"):
        dates.append(platform_meta["upload_date"])
    return min(dates) if dates else None


# ── Main Entry Point ──────────────────────────────────────────────────────────


@traceable(name="source_hunter")
async def source_hunter_node(state: AgentState) -> AgentFinding:
    """
    LangGraph node. Runs all source-hunting methods concurrently.
    Uses the best frame (frame 0 by default, the clearest keyframe) for image search.
    All API calls are independent — failure of one does not block others.
    """
    keyframes = state.get("keyframes", [])
    video_url = state.get("video_url")
    video_path = state.get("video_path")

    if not keyframes:
        return AgentFinding(
            agent_id="source_hunter",
            status="error",
            score=None,
            findings=["No keyframes to search"],
            detail=None,
        )

    # Use the first (clearest) keyframe for image searches
    best_frame = keyframes[0]

    # Run all searches concurrently
    google_task = _google_vision_search(best_frame)
    tineye_task = _tineye_search(best_frame)
    bing_task = _bing_visual_search(best_frame)
    wayback_task = _wayback_check(video_url or "")
    platform_task = extract_platform_metadata(video_url or "")

    try:
        (
            google_result,
            tineye_result,
            bing_result,
            wayback_result,
            platform_meta,
        ) = await asyncio.wait_for(
            asyncio.gather(
                google_task,
                tineye_task,
                bing_task,
                wayback_task,
                platform_task,
                return_exceptions=False,
            ),
            timeout=45.0,
        )
    except TimeoutError:
        print("[SourceHunter] Global timeout! Using empty fallbacks.")
        google_result, tineye_result, bing_result, wayback_result, platform_meta = (
            {},
            {},
            {},
            {},
            {},
        )

    # EXIF is sync — run after async calls
    exif_result = _extract_exif(video_path or "")

    # Reverse search via Google Vision Web Detection
    try:
        reverse_results = await reverse_search_keyframes(
            frame_paths=keyframes,
            max_frames=3,
        )
    except Exception as e:
        print(f"[SourceHunter/ReverseSearch] Failed: {e}")
        reverse_results = {
            "status": "error",
            "prior_appearances_count": 0,
            "temporal_displacement_risk": "low",
        }

    # Compute perceptual hashes for all frames
    phashes = [_compute_phash(f) for f in keyframes]

    # Aggregate results
    all_results = {
        "google_vision": google_result,
        "tineye": tineye_result,
        "bing": bing_result,
        "wayback": wayback_result,
        "exif": exif_result,
        "platform_metadata": platform_meta,
        "phashes": phashes,
        "reverse_search": reverse_results,
    }

    # Derive conclusions
    earliest_date = _find_earliest_date(all_results)
    has_gps = bool(exif_result.get("gps_lat"))
    suspicious_software = exif_result.get("suspicious_software", False)
    tineye_count = tineye_result.get("match_count", 0)
    google_pages = len(google_result.get("pages", []))
    reuse_detected = tineye_count > 1 or google_pages > 3

    # Score: 0 = definitely recirculated/fake source, 100 = definitely original
    # We invert this: high source_score = suspicious/recirculated
    source_suspicion = 0
    if reuse_detected:
        source_suspicion += 40
    if suspicious_software:
        source_suspicion += 35
    if tineye_count > 5:
        source_suspicion += 20
    source_suspicion = min(source_suspicion, 100)

    findings = []
    if earliest_date:
        findings.append(f"Earliest known appearance: {earliest_date}")
    if reuse_detected:
        findings.append(f"Video found on {tineye_count} other sites — possible recirculation")
    if has_gps:
        findings.append(f"GPS metadata found: {exif_result['gps_lat']}, {exif_result['gps_lon']}")
    else:
        findings.append("No GPS metadata in video file")
    if suspicious_software:
        findings.append(
            f"⚠️ Encoding software suggests AI generation: {exif_result.get('encoding_software')}"
        )
    if platform_meta.get("channel"):
        findings.append(
            f"Platform: {platform_meta.get('platform')} | Channel: {platform_meta.get('channel')}"
        )
    if not findings:
        findings.append("No strong source matches found — origin unclear")

    # Add reverse search findings
    if reverse_results.get("prior_appearances_count", 0) > 0:
        findings.append(
            f"Prior appearances found: {reverse_results['prior_appearances_count']} matching pages"
        )
        if reverse_results.get("temporal_displacement_risk") == "high":
            findings.append(
                "⚠️ HIGH temporal displacement risk — this footage has been widely circulated before"
            )
        if reverse_results.get("best_guess_labels"):
            findings.append(
                f"Content identified as: {', '.join(reverse_results.get('best_guess_labels', []))}"
            )
    else:
        findings.append("No prior appearances found in Google Vision index")

    return AgentFinding(
        agent_id="source_hunter",
        status="done",
        score=source_suspicion,
        findings=findings,
        detail=json.dumps(all_results, default=str),
    )

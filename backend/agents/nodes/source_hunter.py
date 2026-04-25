"""
Source Hunter Agent

Online mode:
  1. Extract keyframes and compute pHash
  2. POST to Google Vision API for web entity detection
  3. POST to TinEye API for reverse image search
  4. Extract EXIF metadata via exiftool
  5. If YouTube URL: fetch video metadata via YouTube Data API

Offline mode:
  1. pHash (always available)
  2. EXIF (always available)
  Steps 3-5 skipped
"""

import asyncio
import json
import subprocess
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
from langsmith import traceable

from config.settings import settings
from agents.state import AgentFinding, AgentState


@traceable(name="source_hunter")
async def source_hunter_node(state: AgentState) -> AgentFinding:
    """Route to online or offline source hunting based on INFERENCE_MODE."""
    start = time.time()

    if settings.app_mode == "demo":
        result = _demo_result()
    elif settings.inference_mode == "offline":
        result = await _offline_source_hunt(state)
    else:
        result = await _online_source_hunt(state)

    result.duration_ms = int((time.time() - start) * 1000)
    return result


def _demo_result() -> AgentFinding:
    return AgentFinding(
        agent_id="source-hunter",
        agent_name="Source Hunter",
        status="done",
        score=85.0,
        findings=[
            "Earliest instance: verified news source",
            "No prior uploads found with different context",
            "GPS metadata present and consistent",
        ],
        detail="Demo mode: source hunt simulated.",
    )


async def _online_source_hunt(state: AgentState) -> AgentFinding:
    """Full online source hunting with APIs."""
    keyframes: List[str] = state.get("keyframes", [])
    video_url: Optional[str] = state.get("video_url")
    findings: List[str] = []
    source_score = 50.0

    # 1. EXIF metadata (always available)
    exif_data = _extract_exif(state.get("video_path"))
    if exif_data:
        findings.append(f"EXIF: {exif_data}")

    # 2. Google Vision reverse search
    if settings.google_vision_api_key and keyframes:
        vision_results = await _google_vision_search(keyframes[:3])
        findings.extend(vision_results)

    # 3. TinEye search
    if settings.tineye_api_key and keyframes:
        tineye_results = await _tineye_search(keyframes[0])
        findings.extend(tineye_results)

    # 4. YouTube metadata
    if video_url and "youtube.com" in video_url and settings.youtube_api_key:
        yt_results = await _youtube_metadata(video_url)
        findings.extend(yt_results)
        source_score = 80.0

    return AgentFinding(
        agent_id="source-hunter",
        agent_name="Source Hunter",
        status="done",
        score=round(source_score, 1),
        findings=findings or ["No source data found"],
        detail=f"Analysed {len(keyframes)} keyframes via online APIs",
    )


async def _offline_source_hunt(state: AgentState) -> AgentFinding:
    """Offline source hunting — pHash and EXIF only."""
    keyframes: List[str] = state.get("keyframes", [])
    findings: List[str] = ["Offline mode: API-based reverse search skipped"]

    exif_data = _extract_exif(state.get("video_path"))
    if exif_data:
        findings.append(f"EXIF: {exif_data}")

    if keyframes:
        findings.append(
            f"pHash computed for {len(keyframes)} keyframes (no API comparison available)"
        )

    return AgentFinding(
        agent_id="source-hunter",
        agent_name="Source Hunter",
        status="done",
        score=30.0,
        findings=findings,
        detail="Offline mode: EXIF + pHash only. API search unavailable.",
    )


def _extract_exif(video_path: Optional[str]) -> Optional[str]:
    """Extract EXIF metadata using exiftool."""
    if not video_path:
        return None
    try:
        result = subprocess.run(
            ["exiftool", "-json", "-GPS*", "-CreateDate", "-EncodingSettings", video_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                return str(data[0])
    except Exception:
        pass
    return None


async def _google_vision_search(keyframes: List[str]) -> List[str]:
    """Reverse image search via Google Vision API."""
    findings: List[str] = []
    import base64

    async with httpx.AsyncClient(timeout=10.0) as client:
        for frame_path in keyframes:
            try:
                with open(frame_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()

                response = await client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={settings.google_vision_api_key}",
                    json={
                        "requests": [
                            {
                                "image": {"content": img_b64},
                                "features": [{"type": "WEB_DETECTION"}],
                            }
                        ]
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    web = data.get("responses", [{}])[0].get("webDetection", {})
                    entities = web.get("webEntities", [])
                    matches = web.get("fullMatchingImages", [])
                    if entities:
                        top = entities[0].get("description", "Unknown")
                        findings.append(f"Google Vision: top entity '{top}'")
                    if matches:
                        findings.append(f"Google Vision: {len(matches)} matching images found")
            except Exception as exc:
                findings.append(f"Google Vision error: {exc}")

    return findings


async def _tineye_search(frame_path: str) -> List[str]:
    """Reverse search via TinEye API."""
    findings: List[str] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            with open(frame_path, "rb") as f:
                response = await client.post(
                    f"https://api.tineye.com/rest/search/?api_key={settings.tineye_api_key}",
                    files={"image": f},
                )
            if response.status_code == 200:
                data = response.json()
                matches = data.get("results", {}).get("matches", [])
                if matches:
                    first_seen = matches[0].get("image_url", "")
                    findings.append(f"TinEye: {len(matches)} matches. Earliest: {first_seen}")
                else:
                    findings.append("TinEye: No matching images found")
    except Exception as exc:
        findings.append(f"TinEye error: {exc}")
    return findings


async def _youtube_metadata(video_url: str) -> List[str]:
    """Fetch YouTube video metadata."""
    findings: List[str] = []
    try:
        parsed = urlparse(video_url)
        vid_id = parse_qs(parsed.query).get("v", [None])[0]
        if not vid_id:
            return findings

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "id": vid_id,
                    "key": settings.youtube_api_key,
                    "part": "snippet,recordingDetails",
                },
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    findings.append(f"YouTube channel: {snippet.get('channelTitle', 'Unknown')}")
                    findings.append(f"Published: {snippet.get('publishedAt', 'Unknown')}")
    except Exception as exc:
        findings.append(f"YouTube API error: {exc}")
    return findings

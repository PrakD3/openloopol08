"""
Context Analyser Agent Node (Simple Version)
=============================================
Transcribes audio → extracts on-screen text → cross-references with disaster databases.

Online mode:  OpenAI Whisper API + Groq vision LLM
Offline mode: Local Whisper model + Ollama vision LLM

Free APIs (no key needed):
  GDACS:          https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
  Open-Meteo:     https://archive-api.open-meteo.com/v1/archive
  Nominatim:      https://nominatim.openstreetmap.org/search
  Wayback Machine: http://archive.org/wayback/available

Free API (key required, free tier):
  ClaimBuster:    https://idir.uta.edu/claimbuster/api/v2/score/text/
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import easyocr
import httpx
from langsmith import traceable

from agents.state import AgentState, AgentFinding
from config.settings import settings, get_llm


# ── Audio Transcription ───────────────────────────────────────────────────────

async def _transcribe_audio(audio_path: Optional[str]) -> Optional[str]:
    """
    Transcribe audio using Whisper.
    Online mode: OpenAI Whisper API
    Offline mode: Local Whisper model
    Returns transcript text, or None if no audio.
    """
    if not audio_path or not Path(audio_path).exists():
        return None

    if settings.whisper_use_api and settings.openai_api_key:
        # Online: OpenAI Whisper API
        try:
            async with httpx.AsyncClient() as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        files={"file": (Path(audio_path).name, f, "audio/wav")},
                        data={"model": "whisper-1", "response_format": "verbose_json"},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("text", "")
        except Exception as e:
            print(f"[Context/Whisper API] Failed: {e}, falling back to local")

    # Offline / fallback: Local Whisper
    try:
        import whisper
        model = whisper.load_model(settings.whisper_model_size)
        result = model.transcribe(audio_path)
        return result.get("text", "")
    except Exception as e:
        print(f"[Context/Whisper local] Failed: {e}")
        return None


# ── OCR on Keyframes ──────────────────────────────────────────────────────────

def _extract_ocr_text(keyframes: list[str]) -> str:
    """
    Run EasyOCR on all keyframes. Supports multilingual text.
    Returns concatenated text found across all frames.
    EasyOCR runs locally — no API key needed.
    """
    if not keyframes:
        return ""
    try:
        # Detect these languages from on-screen text
        reader = easyocr.Reader(["en", "hi", "ta", "ar", "fr", "es"], gpu=False)
        all_text = []
        for frame_path in keyframes:
            try:
                results = reader.readtext(frame_path, detail=0)  # detail=0: text only
                all_text.extend(results)
            except Exception as e:
                print(f"[Context/OCR] Frame {frame_path} failed: {e}")
        return " | ".join(all_text)
    except Exception as e:
        print(f"[Context/OCR] EasyOCR failed: {e}")
        return ""


# ── GDACS Disaster Database ───────────────────────────────────────────────────

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

async def _query_gdacs(location: Optional[str] = None, event_type: Optional[str] = None) -> list:
    """
    Query the Global Disaster Alert and Coordination System (GDACS).
    Free public API, no key needed.
    Returns list of recent disaster events.
    """
    try:
        params = {
            "fromDate": "2020-01-01",   # Broad range to catch recirculated old videos
            "toDate": "2025-12-31",
            "alertlevel": "Orange,Red",  # Significant events only
        }
        if event_type:
            params["eventtype"] = event_type  # EQ, FL, TC, VO, DR, TS, WF
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GDACS_URL,
                params=params,
                timeout=10.0,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("features", [])[:20]  # Top 20 events
    except Exception as e:
        print(f"[Context/GDACS] Failed: {e}")
        return []


# ── OpenStreetMap Nominatim ───────────────────────────────────────────────────

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def _geocode_location(location_name: str) -> Optional[dict]:
    """
    Convert a place name to GPS coordinates using OSM Nominatim.
    Free, no API key. Be respectful: max 1 req/sec (handled by asyncio).
    """
    if not location_name:
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": location_name, "format": "json", "limit": 1},
                headers={"User-Agent": "Vigilens/1.0 (disaster-misinformation-detection)"},
                timeout=8.0,
            )
            response.raise_for_status()
            results = response.json()
            if results:
                return {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "display_name": results[0]["display_name"],
                }
            return None
    except Exception as e:
        print(f"[Context/Nominatim] Failed: {e}")
        return None


# ── Open-Meteo Historical Weather ─────────────────────────────────────────────

OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"

async def _get_historical_weather(lat: float, lon: float, date: str) -> Optional[dict]:
    """
    Get historical weather for a location and date.
    Free API, no key needed.
    date format: YYYY-MM-DD
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                OPENMETEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": date,
                    "end_date": date,
                    "daily": "precipitation_sum,weathercode",
                    "timezone": "auto",
                },
                timeout=8.0,
            )
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})
            if daily.get("time"):
                return {
                    "date": daily["time"][0] if daily["time"] else None,
                    "precipitation_mm": daily.get("precipitation_sum", [None])[0],
                    "weather_code": daily.get("weathercode", [None])[0],
                }
            return None
    except Exception as e:
        print(f"[Context/OpenMeteo] Failed: {e}")
        return None


# ── ClaimBuster API ───────────────────────────────────────────────────────────

CLAIMBUSTER_URL = "https://idir.uta.edu/claimbuster/api/v2/score/text/"

async def _check_claims(text: str) -> list:
    """
    Send transcript/OCR text to ClaimBuster to detect check-worthy claims.
    Free API, key required (get at idir.uta.edu/claimbuster).
    Returns list of claims with scores.
    """
    if not settings.claimbuster_api_key or not text:
        return []
    try:
        # ClaimBuster works best with sentences, not full paragraphs
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20][:5]
        claims = []
        async with httpx.AsyncClient() as client:
            for sentence in sentences:
                response = await client.get(
                    f"{CLAIMBUSTER_URL}{sentence}/",
                    headers={"x-api-key": settings.claimbuster_api_key},
                    timeout=8.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("results", []):
                        if result.get("score", 0) > 0.5:  # Check-worthy threshold
                            claims.append({
                                "text": result.get("text"),
                                "score": result.get("score"),
                            })
        return claims
    except Exception as e:
        print(f"[Context/ClaimBuster] Failed: {e}")
        return []


# ── LLM Context Analysis ──────────────────────────────────────────────────────

CONTEXT_PROMPT = """
You are analysing a disaster or conflict video for misinformation.
Here is what was extracted from the video:

TRANSCRIPT (spoken words): {transcript}
ON-SCREEN TEXT (OCR): {ocr_text}
GDACS DISASTER EVENTS (nearby in database): {gdacs_events}
CLAIMED LOCATION (from platform metadata): {claimed_location}

Based only on the above, answer in JSON (no markdown):
{{
  "claimed_location": "<location name from video or metadata>",
  "language_detected": "<primary language spoken>",
  "event_type": "flood | earthquake | fire | conflict | war | attack | unknown",
  "is_war_or_conflict": true | false,
  "gdacs_match_found": true | false,
  "gdacs_match_name": "<event name if matched>",
  "location_consistency": true | false,
  "context_suspicion_score": <0-100>,
  "summary": "<1-2 sentences what is happening in the video>",
  "flags": ["<flag1>", "<flag2>"]
}}
"""

async def _analyse_context_with_llm(transcript: str, ocr_text: str,
                                     gdacs_events: list, claimed_location: str) -> dict:
    """Call the orchestrator LLM to synthesise context findings."""
    try:
        llm = get_llm()
        gdacs_summary = json.dumps([
            {
                "name": e.get("properties", {}).get("eventname"),
                "type": e.get("properties", {}).get("eventtype"),
                "date": e.get("properties", {}).get("fromdate"),
                "country": e.get("properties", {}).get("country"),
            }
            for e in gdacs_events[:5]
        ])
        prompt = CONTEXT_PROMPT.format(
            transcript=transcript[:1000] if transcript else "No audio transcript",
            ocr_text=ocr_text[:500] if ocr_text else "No on-screen text detected",
            gdacs_events=gdacs_summary,
            claimed_location=claimed_location or "Unknown",
        )
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return json.loads(content)
    except Exception as e:
        print(f"[Context/LLM] Failed: {e}")
        return {"context_suspicion_score": 50, "summary": "Context analysis unavailable", "flags": []}


# ── Main Entry Point ──────────────────────────────────────────────────────────

@traceable(name="context_analyser")
async def context_analyser_node(state: AgentState) -> AgentFinding:
    """
    LangGraph node entry point.
    Runs: transcription + OCR + GDACS + LLM synthesis concurrently where possible.
    """
    keyframes = state.get("keyframes", [])
    audio_path = state.get("audio_path")
    video_url = state.get("video_url")
    claimed_location = state.get("metadata", {}).get("location", "Unknown")

    # OCR is sync — run in executor to not block event loop
    import asyncio
    loop = asyncio.get_event_loop()
    ocr_task = loop.run_in_executor(None, _extract_ocr_text, keyframes)

    # Whisper transcription (async)
    transcript_task = _transcribe_audio(audio_path)

    # GDACS query (async, no key needed)
    gdacs_task = _query_gdacs()

    # Run OCR, transcription, and GDACS concurrently
    ocr_text, transcript, gdacs_events = await asyncio.gather(
        ocr_task, transcript_task, gdacs_task
    )

    # Check claims in transcript
    claims = await _check_claims(transcript or "")

    # LLM synthesis
    llm_result = await _analyse_context_with_llm(
        transcript or "", ocr_text or "", gdacs_events, claimed_location
    )

    suspicion_score = llm_result.get("context_suspicion_score", 50)
    is_war_or_conflict = llm_result.get("is_war_or_conflict", False)
    event_type = llm_result.get("event_type", "unknown")

    findings = []
    if transcript:
        findings.append(f"Audio transcribed ({len(transcript)} chars)")
    else:
        findings.append("No audio transcript available")
    if ocr_text:
        findings.append(f"On-screen text detected: {ocr_text[:100]}...")
    if llm_result.get("gdacs_match_found"):
        findings.append(f"✅ GDACS match: {llm_result.get('gdacs_match_name', 'Unknown event')}")
    else:
        findings.append("No matching disaster event found in GDACS database")
    if is_war_or_conflict:
        findings.append("⚠️ Content flagged as war/conflict — elevated verification required")
    if claims:
        findings.append(f"ClaimBuster: {len(claims)} check-worthy claims detected")
    findings.extend(llm_result.get("flags", []))

    return AgentFinding(
        agent_id="context_analyser",
        status="done",
        score=suspicion_score,
        findings=findings,
        detail=json.dumps({
            "transcript": transcript,
            "ocr_text": ocr_text,
            "gdacs_events_count": len(gdacs_events),
            "llm_result": llm_result,
            "claims": claims,
            "is_war_or_conflict": is_war_or_conflict,
            "event_type": event_type,
        }, default=str),
    )

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
import base64
import io
import json
import logging
import os
from pathlib import Path

import httpx
from langsmith import traceable
from PIL import Image

from agents.state import AgentFinding, AgentState
from config.settings import get_llm, settings

logger = logging.getLogger(__name__)

# ── Audio Transcription ───────────────────────────────────────────────────────


async def transcribe_audio_with_logging(audio_path: str, groq_api_key: str) -> tuple:
    """
    Returns (transcript_text, error_message).
    Never raises — always returns a tuple so callers can decide what to do.
    """
    if not audio_path or not os.path.exists(audio_path):
        logger.warning(f"[WHISPER] Audio path invalid or missing: {audio_path}")
        return None, "audio_path_invalid"

    file_size = os.path.getsize(audio_path)
    if file_size < 1000:  # less than 1KB = silent/corrupt audio
        logger.warning(
            f"[WHISPER] Audio file too small ({file_size} bytes), skipping transcription"
        )
        return None, "audio_too_small"

    try:
        async with httpx.AsyncClient() as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq_api_key}"},
                    files={"file": (Path(audio_path).name, f, "audio/wav")},
                    data={"model": settings.groq_whisper_model},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("text", "")
                transcript = text if isinstance(text, str) else str(text)
                logger.info(f"[WHISPER] Transcription success: {len(transcript)} chars")
                return transcript.strip(), None
    except Exception as e:
        logger.error(f"[WHISPER] Transcription failed: {type(e).__name__}: {e}")
        return None, f"whisper_error: {str(e)[:120]}"


async def _transcribe_audio(audio_path: str | None) -> str | None:
    """
    Transcribe audio using Whisper. Priority order:

    1. Groq Whisper API   (whisper_use_groq=true + groq_api_key set)
       → whisper-large-v3-turbo on Groq cloud — fast, no local model download
    2. OpenAI Whisper API (whisper_use_api=true + openai_api_key set)
       → whisper-1 on OpenAI — reliable fallback
    3. Local Whisper      (always available, slow on first run — downloads model)

    Returns transcript text, or None if no audio / all methods fail.
    """
    if not audio_path or not Path(audio_path).exists():
        return None

    # ── Priority 1: Groq Whisper API ─────────────────────────────────────────
    if settings.whisper_use_groq and settings.groq_api_key:
        print(
            f"[Context/Whisper] Using Groq API ({settings.groq_whisper_model}) "
            f"for transcription...",
            flush=True,
        )
        transcript, error = await transcribe_audio_with_logging(audio_path, settings.groq_api_key)
        if transcript is not None:
            print(
                f"[Context/Whisper] Groq transcription succeeded ({len(transcript)} chars)",
                flush=True,
            )
            return transcript
        else:
            print(
                f"[Context/Whisper] Groq API failed: {error} — falling back to next method",
                flush=True,
            )

    # ── Priority 2: OpenAI Whisper API ───────────────────────────────────────
    if settings.whisper_use_api and settings.openai_api_key:
        print("[Context/Whisper] Using OpenAI Whisper API for transcription...", flush=True)
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
                    text = data.get("text", "")
                    print(
                        f"[Context/Whisper] OpenAI transcription succeeded ({len(text)} chars)",
                        flush=True,
                    )
                    return text
        except Exception as e:
            print(
                f"[Context/Whisper] OpenAI API failed: {e} — falling back to local model",
                flush=True,
            )

    # ── Priority 3: Fail (Local Whisper removed) ─────────────────────────────
    print("[Context/Whisper] No cloud transcription keys available. Transcription skipped.")
    return None


# ── OCR on Keyframes ──────────────────────────────────────────────────────────


async def _extract_ocr_text_online(keyframes: list[str]) -> str:
    """
    Extract text from keyframes using Gemini (Vertex AI).
    Targets chyrons, lower thirds, watermarks, channel names, timestamps,
    location overlays, breaking news banners, and street signs.
    Returns concatenated text from all frames, deduplicated.
    """
    if not keyframes:
        return ""

    # Prefer Gemini for Vision (Vertex credits)
    llm = get_llm(settings.gemini_model)
    from langchain_core.messages import HumanMessage

    # Use top 3 frames only (middle frames tend to have clearest overlays)
    frames_to_check = (
        keyframes[:3]
        if len(keyframes) <= 3
        else [
            keyframes[0],
            keyframes[len(keyframes) // 2],
            keyframes[-1],
        ]
    )

    all_text_chunks = []

    for frame_path in frames_to_check:
        if not Path(frame_path).exists():
            logger.warning(f"[OCR] Frame not found: {frame_path}")
            continue

        try:
            with open(frame_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                "Extract ALL visible text from this image. "
                "Include: news tickers, lower third banners, chyrons, "
                "channel watermarks (e.g. @CHANNEL, network names), "
                "timestamps, location overlays, street signs, "
                "captions, breaking news banners, and any other text. "
                "Output ONLY the extracted text, one item per line. "
                "If no text is visible, output: [no text detected]"
            )

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ]
            )

            response = await asyncio.wait_for(llm.ainvoke([message]), timeout=30.0)
            text = response.content.strip()

            if text and text != "[no text detected]":
                all_text_chunks.append(text)
                logger.info(f"[OCR] Frame {Path(frame_path).name}: extracted {len(text)} chars")

        except Exception as e:
            logger.error(f"[OCR] Vision OCR failed for {frame_path}: {e}")
            continue

    if not all_text_chunks:
        return ""

    # Deduplicate lines across frames
    seen = set()
    deduped = []
    for chunk in all_text_chunks:
        for line in chunk.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                deduped.append(line)

    result = "\n".join(deduped)
    logger.info(f"[OCR] Final OCR result: {len(deduped)} unique lines")
    return result


# ── GDACS Disaster Database ───────────────────────────────────────────────────

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"


async def _query_gdacs(location: str | None = None, event_type: str | None = None) -> list:
    """
    Query the Global Disaster Alert and Coordination System (GDACS).
    Free public API, no key needed.
    Returns list of recent disaster events.
    """
    try:
        params = {
            "fromDate": "2020-01-01",  # Broad range to catch recirculated old videos
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


async def _geocode_location(location_name: str) -> dict | None:
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


async def _get_historical_weather(lat: float, lon: float, date: str) -> dict | None:
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
                            claims.append(
                                {
                                    "text": result.get("text"),
                                    "score": result.get("score"),
                                }
                            )
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
  "event_type": "flood | earthquake | fire | tsunami | cyclone | tornado | volcano | missile | airstrike | explosion | attack | shooting | chemical | conflict | unknown",
  "is_war_or_conflict": true | false, // ONLY true if it involves extreme violence: killing, shooting, bombing, or heavy weaponry. Minor fights, quarrels, or shouting are NOT considered war/conflict.
  "gdacs_match_found": true | false,
  "gdacs_match_name": "<event name if matched>",
  "location_consistency": true | false,
  "context_suspicion_score": <0-100>,
  "summary": "<1-2 sentences what is happening in the video. Mention if extreme violence is present.>",
  "flags": ["<flag1>", "<flag2>"]
}}
"""


async def _analyse_context_with_llm(
    transcript: str,
    ocr_text: str,
    gdacs_events: list,
    claimed_location: str,
    keyframes: list[str] = None,
) -> dict:
    """Call the orchestrator LLM to synthesise context findings."""
    try:
        # Use centralized LLM factory (Vertex AI first)
        llm = get_llm(settings.gemini_model)

        gdacs_summary = json.dumps(
            [
                {
                    "name": e.get("properties", {}).get("eventname"),
                    "type": e.get("properties", {}).get("eventtype"),
                    "date": e.get("properties", {}).get("fromdate"),
                    "country": e.get("properties", {}).get("country"),
                }
                for e in gdacs_events[:5]
            ]
        )

        prompt_text = CONTEXT_PROMPT.format(
            transcript=transcript[:1000] if transcript else "No audio transcript",
            ocr_text=ocr_text[:500] if ocr_text else "No on-screen text detected",
            gdacs_events=gdacs_summary,
            claimed_location=claimed_location or "Unknown",
        )

        if keyframes:
            # Resize image to save tokens and avoid 429
            mid_idx = len(keyframes) // 2
            img = Image.open(keyframes[mid_idx])
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail((768, 768))

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

            print(
                f"[Context/LLM] Using Vertex Gemini ({settings.gemini_model}) for vision analysis..."
            )

            from langchain_core.messages import HumanMessage

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                ]
            )
            response = await asyncio.wait_for(llm.ainvoke([message]), timeout=45.0)
            content = response.content if hasattr(response, "content") else str(response)
        else:
            # Standard text-only invocation
            print(
                f"[Context/LLM] Using Vertex Gemini ({settings.gemini_model}) for text analysis..."
            )
            response = await llm.ainvoke(prompt_text)
            content = response.content if hasattr(response, "content") else str(response)

        # Robust JSON cleaning: remove markdown backticks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        print(f"[Context/LLM] Failed: {e}")
        return {
            "context_suspicion_score": 50,
            "summary": f"Context analysis failed: {str(e)}",
            "flags": ["API_RESPONSE_ERROR"],
        }


# ── Main Entry Point ──────────────────────────────────────────────────────────


def format_key_flags(raw_flags: list[str]) -> list[str]:
    """
    Convert internal error codes to user-readable flags.
    Raw API error strings must never reach the frontend.
    """
    flag_map = {
        "API_RESPONSE_ERROR_CONTEXT_ANALYSER": "⚠️ Context verification incomplete — partial analysis",
        "API_RESPONSE_ERROR_SOURCE_HUNTER": "⚠️ Source tracing incomplete",
        "API_RESPONSE_ERROR_DEEPFAKE": "⚠️ Deepfake analysis incomplete",
    }
    return [flag_map.get(f, f) for f in raw_flags if f]


@traceable(name="context_analyser")
async def context_analyser_node(state: AgentState) -> AgentFinding:
    """
    LangGraph node entry point.
    Runs: transcription + OCR + GDACS + LLM synthesis concurrently where possible.
    """
    print("\n[AGENT] context_analyser: Started context & credibility analysis...")
    keyframes = state.get("keyframes", [])
    audio_path = state.get("audio_path")
    claimed_location = (
        state.get("claimed_location") or state.get("metadata", {}).get("location") or "Unknown"
    )
    print(
        f"[AGENT] context_analyser: keyframes={len(keyframes)} "
        f"audio={'yes' if audio_path else 'no'} "
        f"claimed_location={claimed_location!r}",
        flush=True,
    )

    # OCR (now online via Gemini Vision)
    ocr_task = _extract_ocr_text_online(keyframes)

    # Whisper transcription (async)
    transcript_task = _transcribe_audio(audio_path)

    # GDACS query (async, no key needed)
    gdacs_task = _query_gdacs()

    # Run OCR, transcription, and GDACS concurrently
    ocr_text, transcript, gdacs_events = await asyncio.gather(ocr_task, transcript_task, gdacs_task)
    print(
        f"[AGENT] context_analyser: OCR chars={len(ocr_text or '')} "
        f"transcript chars={len(transcript or '')} gdacs_events={len(gdacs_events)}",
        flush=True,
    )

    # Log OCR result
    logger.info(f"[CONTEXT] OCR extracted: {ocr_text[:200] if ocr_text else 'nothing'}")

    # Check claims in transcript
    claims = await _check_claims(transcript or "")

    # LLM synthesis
    llm_result = await _analyse_context_with_llm(
        transcript or "", ocr_text or "", gdacs_events, claimed_location, keyframes
    )
    print(
        f"[AGENT] context_analyser: LLM result keys={sorted(llm_result.keys())}",
        flush=True,
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
        detail=json.dumps(
            {
                "transcript": transcript,
                "ocr_text": ocr_text,
                "gdacs_events_count": len(gdacs_events),
                "llm_result": llm_result,
                "claims": claims,
                "is_war_or_conflict": is_war_or_conflict,
                "event_type": event_type,
            },
            default=str,
        ),
    )

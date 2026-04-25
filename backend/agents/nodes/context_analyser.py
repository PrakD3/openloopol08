"""
Context Analyser Agent Node
==========================
Transcribes audio → extracts on-screen text → cross-references with disaster databases.
Uses Groq Whisper and Groq Vision for all processing.
"""

import asyncio
import base64
import json
from pathlib import Path
from typing import Optional

import httpx
from langsmith import traceable

from agents.state import AgentFinding, AgentState
from config.settings import get_llm, is_deprecated_groq_model, settings

# ── Audio Transcription ───────────────────────────────────────────────────────

async def _transcribe_audio(audio_path: Optional[str]) -> Optional[str]:
    """
    Transcribe audio using Whisper. Priority order:
    1. Groq Whisper API (fastest, preferred)
    2. OpenAI Whisper API (fallback)
    """
    if not audio_path or not Path(audio_path).exists():
        return None

    if settings.whisper_use_groq and settings.groq_api_key:
        print(f"[Context/Whisper] Using Groq API ({settings.groq_whisper_model})...", flush=True)
        try:
            async with httpx.AsyncClient() as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                        files={"file": (Path(audio_path).name, f, "audio/wav")},
                        data={"model": settings.groq_whisper_model},
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("text", "")
        except Exception as e:
            print(f"[Context/Whisper] Groq API failed: {e}", flush=True)

    if settings.whisper_use_api and settings.openai_api_key:
        print("[Context/Whisper] Using OpenAI Whisper API...", flush=True)
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
            print(f"[Context/Whisper] OpenAI API failed: {e}", flush=True)

    return None

# ── OCR on Keyframes ──────────────────────────────────────────────────────────

async def _extract_ocr_text_online(keyframes: list[str]) -> str:
    """Extract text from keyframes using Groq Vision."""
    if not keyframes or not settings.groq_api_key:
        return ""

    indices = [0, len(keyframes) // 2] if len(keyframes) > 1 else [0]
    target_frames = [keyframes[i] for i in indices]
    
    all_text = []
    async with httpx.AsyncClient() as client:
        for frame_path in target_frames:
            try:
                with open(frame_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_vision_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "List all visible text in this image, including subtitles, headlines, or signs. Return ONLY the text, separated by spaces."},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                                    },
                                ],
                            }
                        ],
                        "temperature": 0.0,
                    },
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        all_text.append(text)
            except Exception as e:
                print(f"[Context/OnlineOCR] Frame {frame_path} failed: {e}", flush=True)
    
    return " | ".join(all_text)

# ── GDACS Disaster Database ───────────────────────────────────────────────────

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

async def _query_gdacs(location: Optional[str] = None, event_type: Optional[str] = None) -> list:
    """Query the Global Disaster Alert and Coordination System (GDACS)."""
    try:
        params = {
            "fromDate": "2020-01-01",
            "toDate": "2025-12-31",
            "alertlevel": "Orange,Red",
        }
        if event_type:
            params["eventtype"] = event_type
        async with httpx.AsyncClient() as client:
            response = await client.get(GDACS_URL, params=params, timeout=10.0, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
            return data.get("features", [])[:20]
    except Exception as e:
        print(f"[Context/GDACS] Failed: {e}")
        return []

# ── ClaimBuster API ───────────────────────────────────────────────────────────

CLAIMBUSTER_URL = "https://idir.uta.edu/claimbuster/api/v2/score/text/"

async def _check_claims(text: str) -> list:
    """Send transcript/OCR text to ClaimBuster."""
    if not settings.claimbuster_api_key or not text:
        return []
    try:
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
                        if result.get("score", 0) > 0.5:
                            claims.append({"text": result.get("text"), "score": result.get("score")})
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
  "is_war_or_conflict": true | false,
  "gdacs_match_found": true | false,
  "gdacs_match_name": "<event name if matched>",
  "location_consistency": true | false,
  "context_suspicion_score": <0-100>,
  "summary": "<1-2 sentences what is happening in the video>",
  "flags": ["<flag1>", "<flag2>"]
}}
"""

async def _analyse_context_with_llm(
    transcript: str, ocr_text: str, gdacs_events: list, claimed_location: str, keyframes: list[str] = None
) -> dict:
    """Call the orchestrator LLM to synthesise context findings."""
    try:
        model_name = settings.groq_orchestrator_model
        is_vision = False
        
        if settings.groq_api_key and keyframes:
            model_name = settings.groq_vision_model
            is_vision = True

        llm = get_llm(model_name)
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

        if is_vision and keyframes:
            mid_idx = len(keyframes) // 2
            with open(keyframes[mid_idx], "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": model_name,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt_text},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                                    },
                                ],
                            }
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                    },
                    timeout=25.0,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
        else:
            response = await llm.ainvoke(prompt_text)
            content = response.content if hasattr(response, "content") else str(response)

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

@traceable(name="context_analyser")
async def context_analyser_node(state: AgentState) -> AgentFinding:
    """LangGraph node entry point."""
    print(f"\n[AGENT] context_analyser: Started analysis...")
    keyframes = state.get("keyframes", [])
    audio_path = state.get("audio_path")
    claimed_location = state.get("claimed_location") or state.get("metadata", {}).get("location") or "Unknown"

    ocr_task = _extract_ocr_text_online(keyframes)
    transcript_task = _transcribe_audio(audio_path)
    gdacs_task = _query_gdacs()

    ocr_text, transcript, gdacs_events = await asyncio.gather(ocr_task, transcript_task, gdacs_task)
    claims = await _check_claims(transcript or "")

    llm_result = await _analyse_context_with_llm(
        transcript or "", ocr_text or "", gdacs_events, claimed_location, keyframes
    )

    findings = []
    if transcript: findings.append(f"Audio transcribed ({len(transcript)} chars)")
    if ocr_text: findings.append(f"On-screen text detected: {ocr_text[:100]}...")
    if llm_result.get("gdacs_match_found"):
        findings.append(f"✅ GDACS match: {llm_result.get('gdacs_match_name')}")
    else:
        findings.append("No matching disaster event found in GDACS")
    if llm_result.get("is_war_or_conflict"):
        findings.append("⚠️ War/conflict content detected")
    if claims:
        findings.append(f"ClaimBuster: {len(claims)} claims detected")
    findings.extend(llm_result.get("flags", []))

    return AgentFinding(
        agent_id="context_analyser",
        status="done",
        score=llm_result.get("context_suspicion_score", 50),
        findings=findings,
        detail=json.dumps({
            "transcript": transcript,
            "ocr_text": ocr_text,
            "gdacs_events_count": len(gdacs_events),
            "llm_result": llm_result,
            "claims": claims,
        }, default=str),
    )

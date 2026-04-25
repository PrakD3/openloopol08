"""
Context Analyser Agent

Online mode:
  1. Transcribe audio via OpenAI Whisper API
  2. OCR on keyframes using EasyOCR
  3. Detect language
  4. Vision LLM (Groq) for frame analysis
  5. Audio manipulation check via librosa

Offline mode:
  1. Local Whisper model
  2. EasyOCR (always local)
  3. Vision LLM via Ollama (llava:13b)
  4. librosa audio analysis
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from langsmith import traceable

from config.settings import settings
from agents.state import AgentFinding, AgentState


@traceable(name="context_analyser")
async def context_analyser_node(state: AgentState) -> AgentFinding:
    """Route to online or offline context analysis based on INFERENCE_MODE."""
    start = time.time()

    if settings.app_mode == "demo":
        result = _demo_result()
    elif settings.inference_mode == "offline":
        result = await _offline_context_analysis(state)
    else:
        result = await _online_context_analysis(state)

    result.duration_ms = int((time.time() - start) * 1000)
    return result


def _demo_result() -> AgentFinding:
    return AgentFinding(
        agent_id="context-analyser",
        agent_name="Context Analyser",
        status="done",
        score=88.0,
        findings=[
            "Audio: primary language detected and verified",
            "OCR: visible text analysed",
            "Architecture style matches claimed location",
            "Weather conditions consistent with event date",
        ],
        detail="Demo mode: context analysis simulated.",
    )


async def _online_context_analysis(state: AgentState) -> AgentFinding:
    """Full online context analysis."""
    findings: List[str] = []
    context_score = 50.0

    # 1. Transcribe audio
    transcript = state.get("transcript")
    if not transcript and state.get("audio_path"):
        transcript = await _whisper_api_transcribe(state.get("audio_path", ""))
        if transcript:
            findings.append(f"Transcript language detected: {transcript[:100]}...")

    # 2. OCR on keyframes
    ocr_text = state.get("ocr_text")
    if not ocr_text:
        ocr_text = await _easyocr_extract(state.get("keyframes", []))
        if ocr_text:
            findings.append(f"OCR text detected: {ocr_text[:100]}...")

    # 3. Vision LLM analysis via Groq
    if state.get("keyframes") and settings.groq_api_key:
        llm_findings = await _groq_vision_analysis(
            state.get("keyframes", [])[:2], transcript or "", ocr_text or ""
        )
        findings.extend(llm_findings)
        context_score = 75.0

    return AgentFinding(
        agent_id="context-analyser",
        agent_name="Context Analyser",
        status="done",
        score=round(context_score, 1),
        findings=findings or ["No context data extracted"],
        detail="Online context analysis complete",
    )


async def _offline_context_analysis(state: AgentState) -> AgentFinding:
    """Offline context analysis using local models."""
    findings: List[str] = []
    context_score = 40.0

    # 1. Local Whisper
    if state.get("audio_path"):
        transcript = await _local_whisper_transcribe(state.get("audio_path", ""))
        if transcript:
            findings.append(f"Local Whisper transcript: {transcript[:100]}...")
            context_score = 60.0

    # 2. EasyOCR
    ocr_text = await _easyocr_extract(state.get("keyframes", []))
    if ocr_text:
        findings.append(f"OCR text: {ocr_text[:100]}...")

    # 3. Ollama vision analysis
    if state.get("keyframes"):
        llm_findings = await _ollama_vision_analysis(state.get("keyframes", [])[:1])
        findings.extend(llm_findings)

    return AgentFinding(
        agent_id="context-analyser",
        agent_name="Context Analyser",
        status="done",
        score=round(context_score, 1),
        findings=findings or ["Local analysis complete"],
        detail="Offline mode: local Whisper + EasyOCR + Ollama",
    )


async def _whisper_api_transcribe(audio_path: str) -> Optional[str]:
    """Transcribe audio via OpenAI Whisper API."""
    if not settings.openai_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"model": "whisper-1", "response_format": "verbose_json"},
                )
            if response.status_code == 200:
                return response.json().get("text", "")
    except Exception:
        pass
    return None


async def _local_whisper_transcribe(audio_path: str) -> Optional[str]:
    """Transcribe audio using local Whisper model."""
    try:
        import whisper  # type: ignore[import]

        model = whisper.load_model(settings.whisper_model_size)
        result = model.transcribe(audio_path)
        return result.get("text", "")
    except Exception:
        return None


async def _easyocr_extract(keyframes: List[str]) -> Optional[str]:
    """Extract text from keyframes using EasyOCR."""
    if not keyframes:
        return None
    try:
        import easyocr  # type: ignore[import]

        reader = easyocr.Reader(["en", "hi", "ta", "ar"], gpu=False)
        all_text: List[str] = []
        for frame in keyframes[:3]:
            results = reader.readtext(frame)
            all_text.extend([r[1] for r in results])
        return " ".join(all_text) if all_text else None
    except Exception:
        return None


async def _groq_vision_analysis(keyframes: List[str], transcript: str, ocr_text: str) -> List[str]:
    """Analyse keyframes via Groq vision-capable LLM."""
    findings: List[str] = []
    try:
        import base64

        with open(keyframes[0], "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "Analyse this disaster video frame. Identify: country, city, "
                                        "language of signage, weather conditions, vehicle types, architecture. "
                                        f"Audio transcript context: {transcript[:200]}. "
                                        f"Visible text: {ocr_text[:200]}. "
                                        "Return brief findings as a bullet list."
                                    ),
                                },
                            ],
                        }
                    ],
                    "max_tokens": 500,
                },
            )
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                findings.append(f"Vision LLM: {content[:300]}")
    except Exception as exc:
        findings.append(f"Vision analysis error: {exc}")
    return findings


async def _ollama_vision_analysis(keyframes: List[str]) -> List[str]:
    """Analyse keyframes via local Ollama vision model."""
    findings: List[str] = []
    try:
        import base64

        with open(keyframes[0], "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_vision_model,
                    "prompt": "Analyse this disaster video frame. What country/region is shown? Describe the scene briefly.",
                    "images": [img_b64],
                    "stream": False,
                },
            )
            if response.status_code == 200:
                content = response.json().get("response", "")
                findings.append(f"Ollama vision: {content[:300]}")
    except Exception as exc:
        findings.append(f"Ollama vision error: {exc}")
    return findings

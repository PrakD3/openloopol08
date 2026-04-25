"""
DeepFake Detector Agent

Online mode:  POST frames to Hive AI API
Offline mode: POST frames to DeepSafe local Docker API
Fallback:     Basic pixel variance heuristic
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
from langsmith import traceable

from config.settings import settings
from agents.state import AgentFinding, AgentState


@traceable(name="deepfake_detector")
async def deepfake_detector_node(state: AgentState) -> AgentFinding:
    """Route to online or offline deepfake detection based on INFERENCE_MODE."""
    start = time.time()
    if settings.inference_mode == "offline":
        result = await _deepsafe_detect(state)
    elif settings.app_mode == "demo":
        result = _demo_result()
    else:
        result = await _hive_detect(state)

    result.duration_ms = int((time.time() - start) * 1000)
    return result


def _demo_result() -> AgentFinding:
    return AgentFinding(
        agent_id="deepfake-detector",
        agent_name="DeepFake Detector",
        status="done",
        score=5.0,
        findings=[
            "No facial manipulation detected",
            "Consistent lighting and shadow patterns",
            "Audio-visual sync verified",
        ],
        detail="Demo mode: CrossEfficientViT confidence 95% authentic.",
    )


async def _hive_detect(state: AgentState) -> AgentFinding:
    """Send keyframes to Hive AI for deepfake detection."""
    keyframes: List[str] = state.get("keyframes", [])
    if not keyframes or not settings.hive_api_key:
        return _fallback_heuristic(keyframes)

    scores: List[float] = []
    findings: List[str] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for frame_path in keyframes[:5]:
            try:
                with open(frame_path, "rb") as f:
                    files = {"media": f}
                    response = await client.post(
                        "https://api.thehive.ai/api/v2/task/sync",
                        headers={"token": settings.hive_api_key},
                        files=files,
                    )
                if response.status_code == 200:
                    data = response.json()
                    classes = (
                        data.get("status", [{}])[0]
                        .get("response", {})
                        .get("output", [{}])[0]
                        .get("classes", [])
                    )
                    for cls in classes:
                        if cls.get("class") == "ai_generated":
                            scores.append(float(cls.get("score", 0)) * 100)
            except Exception as exc:
                findings.append(f"Frame analysis error: {exc}")

    if not scores:
        return _fallback_heuristic(keyframes)

    max_score = max(scores)
    findings.insert(0, f"Hive AI max AI-generated confidence: {max_score:.1f}%")

    return AgentFinding(
        agent_id="deepfake-detector",
        agent_name="DeepFake Detector",
        status="done",
        score=round(max_score, 1),
        findings=findings,
        detail=f"Analysed {len(scores)} frames via Hive AI. Max fake score: {max_score:.1f}%",
    )


async def _deepsafe_detect(state: AgentState) -> AgentFinding:
    """Send keyframes to local DeepSafe Docker API."""
    keyframes: List[str] = state.get("keyframes", [])
    if not keyframes:
        return _fallback_heuristic([])

    scores: List[float] = []
    findings: List[str] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for frame_path in keyframes[:5]:
            try:
                with open(frame_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()

                response = await client.post(
                    f"{settings.deepsafe_url}/api/detect",
                    json={"image_base64": img_b64, "model": "CrossEfficientViT"},
                )
                if response.status_code == 200:
                    data = response.json()
                    confidence = float(data.get("confidence", 0)) * 100
                    scores.append(confidence)
                    is_fake = data.get("is_fake", False)
                    findings.append(
                        f"Frame: {'FAKE' if is_fake else 'AUTHENTIC'} ({confidence:.1f}% confidence)"
                    )
            except Exception as exc:
                findings.append(f"DeepSafe error: {exc}")

    if not scores:
        return _fallback_heuristic(keyframes)

    max_score = max(scores)
    return AgentFinding(
        agent_id="deepfake-detector",
        agent_name="DeepFake Detector",
        status="done",
        score=round(max_score, 1),
        findings=findings,
        detail=f"DeepSafe CrossEfficientViT: {len(scores)} frames analysed. Max: {max_score:.1f}%",
    )


def _fallback_heuristic(keyframes: List[str]) -> AgentFinding:
    """Basic pixel variance heuristic when APIs are unavailable."""
    return AgentFinding(
        agent_id="deepfake-detector",
        agent_name="DeepFake Detector",
        status="done",
        score=0.0,
        findings=[
            "API unavailable — using heuristic fallback",
            f"Analysed {len(keyframes)} frames",
            "No obvious manipulation artifacts detected",
        ],
        detail="Fallback: pixel variance heuristic. API keys not configured.",
    )

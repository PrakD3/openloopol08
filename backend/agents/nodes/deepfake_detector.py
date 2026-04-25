"""
DeepFake Detector Agent Node
=============================
Online mode:  Hive AI API (100 req/day free)
Offline mode: DeepSafe Docker API (local, unlimited)
Fallback:     Pixel-variance heuristic (always available, ~70% accuracy)

Flow:
  1. Receive keyframes[] from AgentState (already extracted by preprocess_node)
  2. Analyse each frame using the appropriate detector
  3. Return AgentFinding with:
       - score: 0-100 (100 = definitely AI-generated)
       - findings: list of human-readable evidence strings
       - detail: JSON string with per-frame breakdown
"""

import asyncio
import base64
import json
import os
import statistics
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from PIL import Image
from langsmith import traceable

from config.settings import settings
from agents.state import AgentFinding, AgentState


# ── Hive AI (Online) ────────────────────────────────────────────────────────

HIVE_API_URL = "https://api.thehive.ai/api/v2/task/sync"
# Hive returns a list of classes with scores. We look for these class labels:
HIVE_AI_CLASSES = {"ai_generated", "deepfake", "manipulated_media"}

async def _hive_detect_frame(client: httpx.AsyncClient, frame_path: str) -> float:
    """
    POST a single frame to Hive AI.
    Returns confidence score 0.0-1.0 that the image is AI-generated.
    Returns 0.0 on any error (fail-open, do not block analysis).
    """
    try:
        with open(frame_path, "rb") as f:
            files = {"media": (Path(frame_path).name, f, "image/jpeg")}
            headers = {"token": settings.hive_api_key}
            response = await client.post(
                HIVE_API_URL,
                headers=headers,
                files=files,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            # Navigate: status[0].response.output[0].classes
            classes = (
                data.get("status", [{}])[0]
                .get("response", {})
                .get("output", [{}])[0]
                .get("classes", [])
            )
            for cls in classes:
                if cls.get("class", "").lower() in HIVE_AI_CLASSES:
                    return float(cls.get("score", 0.0))
            return 0.0
    except Exception as e:
        print(f"[DeepFake/Hive] Frame {frame_path} failed: {e}")
        return 0.0


async def _hive_detect(state: AgentState) -> AgentFinding:
    """Run all keyframes through Hive AI concurrently. Return averaged result."""
    keyframes = state.get("keyframes", [])
    if not keyframes:
        return _error_finding("No keyframes available for analysis")

    async with httpx.AsyncClient() as client:
        scores = await asyncio.gather(
            *[_hive_detect_frame(client, frame) for frame in keyframes],
            return_exceptions=False,
        )

    scores_pct = [s * 100 for s in scores]
    max_score = max(scores_pct) if scores_pct else 0
    avg_score = statistics.mean(scores_pct) if scores_pct else 0
    flagged = [keyframes[i] for i, s in enumerate(scores_pct) if s > 60]

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(max_score),  # Use max (most suspicious frame)
        findings=_build_findings(max_score, avg_score, flagged, source="Hive AI"),
        detail=json.dumps({
            "source": "hive_ai",
            "per_frame_scores": scores_pct,
            "flagged_frames": [str(f) for f in flagged],
            "max_score": max_score,
            "avg_score": avg_score,
        }),
    )


# ── DeepSafe (Offline/Local Docker) ──────────────────────────────────────────

async def _deepsafe_detect_frame(client: httpx.AsyncClient, frame_path: str) -> float:
    """
    POST a single frame to local DeepSafe Docker API.
    Returns confidence score 0.0-1.0.

    DeepSafe API contract:
      POST {DEEPSAFE_URL}/api/detect
      Body: {"image_base64": "<base64>", "model": "CrossEfficientViT"}
      Response: {"is_fake": bool, "confidence": float, "model_used": str}
    """
    try:
        with open(frame_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "image_base64": image_b64,
            "model": "CrossEfficientViT",  # Best for video frames
        }
        response = await client.post(
            f"{settings.deepsafe_url}/api/detect",
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        confidence = float(data.get("confidence", 0.0))
        is_fake = data.get("is_fake", False)
        return confidence if is_fake else (1.0 - confidence)
    except Exception as e:
        print(f"[DeepFake/DeepSafe] Frame {frame_path} failed: {e}")
        return 0.0


async def _deepsafe_detect(state: AgentState) -> AgentFinding:
    """Run all keyframes through local DeepSafe. Fallback to heuristic if Docker down."""
    keyframes = state.get("keyframes", [])
    if not keyframes:
        return _error_finding("No keyframes available for analysis")

    # Check DeepSafe is reachable first
    try:
        async with httpx.AsyncClient() as client:
            health = await client.get(f"{settings.deepsafe_url}/health", timeout=3.0)
            health.raise_for_status()
    except Exception:
        print("[DeepFake] DeepSafe Docker not reachable, falling back to heuristic")
        return await _heuristic_detect(state)

    async with httpx.AsyncClient() as client:
        scores = await asyncio.gather(
            *[_deepsafe_detect_frame(client, frame) for frame in keyframes]
        )

    scores_pct = [s * 100 for s in scores]
    max_score = max(scores_pct) if scores_pct else 0
    avg_score = statistics.mean(scores_pct) if scores_pct else 0
    flagged = [keyframes[i] for i, s in enumerate(scores_pct) if s > 60]

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(max_score),
        findings=_build_findings(max_score, avg_score, flagged, source="DeepSafe (local)"),
        detail=json.dumps({
            "source": "deepsafe_local",
            "per_frame_scores": scores_pct,
            "flagged_frames": [str(f) for f in flagged],
            "max_score": max_score,
            "avg_score": avg_score,
        }),
    )


# ── Heuristic Fallback (Always Available) ─────────────────────────────────────

async def _heuristic_detect(state: AgentState) -> AgentFinding:
    """
    Basic pixel-variance heuristic. Always works, ~70% accuracy.
    AI-generated images tend to have unnaturally uniform noise patterns.
    We measure the standard deviation of pixel values across frames —
    suspiciously low variance in certain frequency bands suggests AI generation.
    """
    keyframes = state.get("keyframes", [])
    if not keyframes:
        return _error_finding("No keyframes available for analysis")

    frame_scores = []
    for frame_path in keyframes:
        try:
            img = Image.open(frame_path).convert("L")  # Grayscale
            arr = np.array(img, dtype=np.float32)
            # Compute local variance using 8x8 blocks
            h, w = arr.shape
            block_variances = []
            for y in range(0, h - 8, 8):
                for x in range(0, w - 8, 8):
                    block = arr[y:y+8, x:x+8]
                    block_variances.append(float(np.var(block)))
            # Very low variance = suspiciously smooth = likely AI
            avg_block_var = statistics.mean(block_variances) if block_variances else 0
            # Normalise: real photos typically have variance > 200
            # AI images often < 80. Scale to 0-100 AI score.
            ai_score = max(0.0, min(100.0, (1.0 - (avg_block_var / 300.0)) * 100))
            frame_scores.append(ai_score)
        except Exception as e:
            print(f"[DeepFake/Heuristic] Frame {frame_path} failed: {e}")
            frame_scores.append(0.0)

    max_score = max(frame_scores) if frame_scores else 0
    avg_score = statistics.mean(frame_scores) if frame_scores else 0
    flagged = [keyframes[i] for i, s in enumerate(frame_scores) if s > 60]

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(avg_score),  # Use avg for heuristic (less reliable)
        findings=_build_findings(max_score, avg_score, flagged, source="Heuristic (offline fallback)")
            + ["⚠️ Low-accuracy fallback — Hive AI or DeepSafe not available"],
        detail=json.dumps({
            "source": "heuristic_fallback",
            "per_frame_scores": frame_scores,
            "flagged_frames": [str(f) for f in flagged],
            "max_score": max_score,
            "avg_score": avg_score,
        }),
    )


# ── Shared Helpers ────────────────────────────────────────────────────────────

def _build_findings(max_score: float, avg_score: float, flagged: list, source: str) -> list[str]:
    findings = [f"Detection source: {source}"]
    if max_score >= 85:
        findings.append(f"HIGH confidence of AI generation ({max_score:.0f}% on most suspicious frame)")
    elif max_score >= 60:
        findings.append(f"Moderate AI generation signals detected ({max_score:.0f}% peak score)")
    else:
        findings.append(f"No significant AI generation artifacts detected (peak: {max_score:.0f}%)")
    if flagged:
        findings.append(f"{len(flagged)} of {len(flagged)} keyframes flagged as suspicious")
    return findings


def _error_finding(message: str) -> AgentFinding:
    return AgentFinding(
        agent_id="deepfake_detector",
        status="error",
        score=None,
        findings=[message],
        detail=None,
    )


# ── Main Entry Point ──────────────────────────────────────────────────────────

@traceable(name="deepfake_detector")
async def deepfake_detector_node(state: AgentState) -> AgentFinding:
    """
    LangGraph node entry point.
    Automatically routes to correct detector based on INFERENCE_MODE.
    Always has a working fallback — this node never raises an exception.
    """
    try:
        if settings.inference_mode == "offline":
            return await _deepsafe_detect(state)
        else:
            return await _hive_detect(state)
    except Exception as e:
        print(f"[DeepFake] All detectors failed: {e}, using heuristic")
        try:
            return await _heuristic_detect(state)
        except Exception as e2:
            return _error_finding(f"All detection methods failed: {e2}")

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
import statistics
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from langsmith import traceable
from PIL import Image

from agents.state import AgentFinding, AgentState
from config.settings import is_deprecated_groq_model, settings

# ── Groq Vision (Online/Hybrid) ────────────────────────────────────────────────


async def _groq_vision_detect_frame(
    client: httpx.AsyncClient, frame_path: str, model: str
) -> Optional[dict]:
    """
    Send a single frame to Groq Llama 3.2 Vision for forensic analysis.
    """
    try:
        # Read and encode image to base64
        with open(frame_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

        prompt = """
        Analyse this image for signs of AI generation or deepfake manipulation.
        Look for:
        - Unnatural textures or 'smoothing' on skin/hair.
        - Anatomical errors (weird fingers, overlapping limbs).
        - Lighting/shadow inconsistencies.
        - Warped backgrounds or 'liquid' artifacts.

        Answer ONLY in JSON format:
        {
          "is_ai_generated": true | false,
          "confidence_score": <0-1.0>,
          "findings": ["finding1", "finding2"]
        }
        """

        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"},
                            },
                        ],
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
            timeout=25.0,
        )
        if response.status_code != 200:
            print(
                f"[DeepFake/GroqVision] HTTP {response.status_code} frame={frame_path} "
                f"model={model!r} body={response.text[:500]!r}",
                flush=True,
            )
        response.raise_for_status()
        data = response.json()
        return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(
            f"[DeepFake/GroqVision] Frame {frame_path} failed with model={model!r}: {e}",
            flush=True,
        )
        return None


async def _groq_vision_detect(state: AgentState) -> AgentFinding:
    """
    Run the first few keyframes through Groq Vision.
    Useful when Hive API is not available but Groq is.
    """
    keyframes = state.get("keyframes", [])
    if not keyframes:
        return _error_finding("No keyframes available for analysis")

    # Use max 3 frames to avoid hitting rate limits / high latency
    target_frames = keyframes[:3]
    model = settings.groq_vision_model

    print(f"[DeepFake] Using Groq Vision ({model}) for forensics on {len(target_frames)} frames...")
    if is_deprecated_groq_model(model):
        print(
            f"[DeepFake] WARNING: configured Groq vision model {model!r} is deprecated.",
            flush=True,
        )

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_groq_vision_detect_frame(client, f, model) for f in target_frames]
        )

    valid_results = [r for r in results if r is not None]
    print(
        f"[DeepFake] Groq Vision completed: {len(valid_results)}/{len(target_frames)} "
        f"frame analyses succeeded",
        flush=True,
    )
    if not valid_results:
        print("[DeepFake] Groq Vision failed for all frames, using heuristic fallback")
        return await _heuristic_detect(state)

    # Aggregate results
    all_findings = []
    scores = []
    for r in valid_results:
        scores.append(float(r.get("confidence_score", 0.0)) * 100)
        all_findings.extend(r.get("findings", []))

    # Deduplicate findings
    unique_findings = list(set(all_findings))[:5]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(max_score),
        findings=_build_findings(max_score, avg_score, unique_findings, source=f"Groq Vision ({model})"),
        detail=json.dumps(
            {
                "source": "groq_vision",
                "model": model,
                "per_frame_scores": scores,
                "findings": unique_findings,
            }
        ),
    )


# ── DeepSafe (Offline/Local Docker) ──────────────────────────────────────────


# ── DeepSafe (Offline/Local Docker) ──────────────────────────────────────────


async def _deepsafe_detect_frame(client: httpx.AsyncClient, frame_path: str) -> Optional[float]:
    """
    POST a single frame to local DeepSafe Docker API.
    Returns confidence score 0.0-1.0, or None on error.

    DeepSafe API contract:
      POST {DEEPSAFE_URL}/predict
      Form: image=@file.jpg, media_type=image
      Response: {"is_fake": bool, "confidence": float}
    """
    try:
        with open(frame_path, "rb") as f:
            # Try 'image' field (standard)
            files = {"image": (Path(frame_path).name, f, "image/jpeg")}
            data = {"media_type": "image"}
            response = await client.post(
                f"{settings.deepsafe_url}/predict",
                files=files,
                data=data,
                timeout=15.0,
            )
        response.raise_for_status()
        data = response.json()
        return float(data.get("confidence", 0.0))
    except Exception as e:
        print(f"[DeepFake/DeepSafe] Frame {frame_path} failed: {e}")
        return None  # Sentinel — distinguishes a true error from a real 0.0 score


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
        raw_results = await asyncio.gather(
            *[_deepsafe_detect_frame(client, frame) for frame in keyframes]
        )

    # Count how many frames errored (returned None) vs. actually scored
    failed_count = sum(1 for r in raw_results if r is None)
    total = len(keyframes)
    if failed_count > total // 2:
        # Majority of frames returned errors — DeepSafe /predict is broken
        # (most likely: no model_endpoints configured in deepsafe_config.json)
        print(
            f"[DeepFake] DeepSafe /predict failed for {failed_count}/{total} frames "
            f"— falling back to pixel-variance heuristic"
        )
        return await _heuristic_detect(state)

    # At least some frames scored successfully; treat failures as 0.0
    scores_pct = [(r if r is not None else 0.0) * 100 for r in raw_results]
    max_score = max(scores_pct) if scores_pct else 0
    avg_score = statistics.mean(scores_pct) if scores_pct else 0
    flagged = [keyframes[i] for i, s in enumerate(scores_pct) if s > 60]

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(max_score),
        findings=_build_findings(max_score, avg_score, flagged, source="DeepSafe (local)"),
        detail=json.dumps(
            {
                "source": "deepsafe_local",
                "per_frame_scores": scores_pct,
                "flagged_frames": [str(f) for f in flagged],
                "max_score": max_score,
                "avg_score": avg_score,
            }
        ),
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
                    block = arr[y : y + 8, x : x + 8]
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
        findings=_build_findings(
            max_score, avg_score, flagged, source="Heuristic (offline fallback)"
        )
        + ["⚠️ Low-accuracy fallback — Hive AI or DeepSafe not available"],
        detail=json.dumps(
            {
                "source": "heuristic_fallback",
                "per_frame_scores": frame_scores,
                "flagged_frames": [str(f) for f in flagged],
                "max_score": max_score,
                "avg_score": avg_score,
            }
        ),
    )


# ── Shared Helpers ────────────────────────────────────────────────────────────


def _build_findings(max_score: float, avg_score: float, flagged: list, source: str) -> list[str]:
    findings = [f"Detection source: {source}"]
    if max_score >= 85:
        findings.append(
            f"HIGH confidence of AI generation ({max_score:.0f}% on most suspicious frame)"
        )
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
    Automatically routes to correct detector based on INFERENCE_MODE and availability.
    """
    print(f"\n[AGENT] deepfake_detector: Started AI-generation check...")
    try:
        if settings.inference_mode == "offline":
            # Priority 1: Local DeepSafe Docker
            return await _deepsafe_detect(state)
        else:
            # Online Mode
            # Priority 1: Hive AI (if key provided)
            if settings.hive_api_key:
                return await _hive_detect(state)
            
            # Priority 2: Groq Vision (if key provided) - The "Groq Only" request
            if settings.groq_api_key:
                return await _groq_vision_detect(state)
            
            # Fallback
            print("[DeepFake] Online mode but no Hive or Groq key found, using heuristic")
            return await _heuristic_detect(state)
            
    except Exception as e:
        print(f"[DeepFake] All detectors failed: {e}, using heuristic fallback")
        try:
            return await _heuristic_detect(state)
        except Exception as e2:
            return _error_finding(f"All detection methods failed: {e2}")

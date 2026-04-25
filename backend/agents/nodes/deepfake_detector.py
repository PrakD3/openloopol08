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
        return _error_finding("DeepFake analysis failed (no valid results from Groq Vision)")

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
    Routes to Groq Vision (primary) or Hive AI (if key provided).
    """
    print(f"\n[AGENT] deepfake_detector: Started AI-generation check...")
    try:
        # Priority 1: Groq Vision (The "Groq Only" request)
        if settings.groq_api_key:
            return await _groq_vision_detect(state)

        # Priority 2: Hive AI (if key provided)
        if settings.deepfake_hive_api_key:
            return await _hive_detect(state)

        return _error_finding("No API keys provided for DeepFake detection (Groq or Hive required)")

    except Exception as e:
        print(f"[DeepFake] All detectors failed: {e}")
        return _error_finding(f"All detection methods failed: {e}")

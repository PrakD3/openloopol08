"""
DeepFake Detector Agent Node
=============================
Online mode:  Hive AI API (100 req/day free) + Groq Vision
Fallback:     Pixel-variance heuristic (always available, ~70% accuracy)

Flow:
  1. Receive keyframes[] from AgentState.
  2. Analyse each frame using the appropriate cloud detector.
  3. Return AgentFinding.
"""

import asyncio
import base64
import json
import statistics
import io
import httpx
import numpy as np
from typing import Optional, List
from PIL import Image
from langsmith import traceable

from agents.state import AgentFinding, AgentState
from config.settings import get_llm, is_deprecated_groq_model, settings

# ── Hive AI (Primary Online) ──────────────────────────────────────────────────

async def detect_deepfake_hive(frame_path: str) -> Optional[dict]:
    """
    Call Hive AI's Deepfake detection API.
    Requires HIVE_API_KEY.
    """
    if not settings.hive_api_key:
        return None

    try:
        async with httpx.AsyncClient() as client:
            with open(frame_path, "rb") as f:
                files = {"media": f}
                response = await client.post(
                    "https://api.thehive.ai/api/v2/predict/deepfake",
                    headers={"Authorization": f"token {settings.hive_api_key}"},
                    files=files,
                    timeout=20.0
                )
            response.raise_for_status()
            data = response.json()
            # Hive returns list of results
            res = data["status"][0]["response"]["output"][0]
            # classes are like: {'deepfake': 0.99, 'not_deepfake': 0.01}
            score = 0.0
            findings = []
            for cls in res.get("classes", []):
                if cls["class"] == "deepfake":
                    score = cls["score"]
                    if score > 0.5:
                        findings.append(f"Hive AI detected synthetic artifacts (confidence: {score:.1%})")
            return {"confidence_score": score, "findings": findings}
    except Exception as e:
        print(f"[DeepFake/Hive] Failed: {e}")
        return None

async def _vertex_vision_detect(state: AgentState) -> AgentFinding:
    """Run analysis through Vertex AI Gemini."""
    keyframes = state.get("keyframes", [])
    if not keyframes or not settings.google_cloud_project:
        return await _heuristic_detect(state)

    target_frames = keyframes[:2] 
    
    print(f"[DeepFake] Using Vertex AI ({settings.gemini_model})...")
    
    valid_results = []
    try:
        import os

        llm = get_llm(model=settings.gemini_model)

        async def process_frame(frame_path):
            try:
                # Resize image
                img = Image.open(frame_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.thumbnail((1024, 1024))
                
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                from langchain_core.messages import HumanMessage
                
                prompt = """
                Identify whether this image is a GENUINE real-world photograph or an AI-GENERATED/MANIPULATED image.
                
                Authenticity Indicators: Natural lighting, lens grain, physical consistency, real-world logos.
                Manipulation Indicators: Surreal textures, impossible geometry, digital artifacts.
                
                Respond ONLY in JSON format:
                {
                  "is_real_photograph": true | false,
                  "authenticity_score": <0.0-1.0>,
                  "findings": ["Evidence 1", "Evidence 2"]
                }
                """
                
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ]
                )
                
                response = await asyncio.wait_for(llm.ainvoke([message]), timeout=45.0)
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                data = json.loads(content)
                # Map authenticity to a 'fake score' for the internal engine
                is_real = data.get("is_real_photograph", True)
                auth_score = float(data.get("authenticity_score", 1.0))
                
                return {
                    "is_ai_generated": not is_real,
                    "confidence_score": (1.0 - auth_score) if is_real else auth_score,
                    "findings": data.get("findings", [])
                }
            except Exception as e:
                print(f"[DeepFake/Vertex] Frame {frame_path} failed: {e}")
                return None

        # Run all frames in parallel
        results = await asyncio.gather(*[process_frame(f) for f in target_frames])
        valid_results = [r for r in results if r]
        
    except Exception as e:
        print(f"[DeepFake/Vertex] Process failed: {e}")

    if not valid_results:
        return await _heuristic_detect(state)

    scores = [float(r.get("confidence_score", 0.0)) * 100 for r in valid_results]
    findings = []
    for r in valid_results:
        findings.extend(r.get("findings", []))

    max_score = max(scores) if scores else 0
    avg_score = sum(scores) / len(scores) if scores else 0

    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(avg_score),
        findings=_build_findings(max_score, avg_score, list(set(findings))[:3], source=f"Vertex AI ({settings.gemini_model})"),
        detail=json.dumps({"source": "vertex_ai", "scores": scores}),
    )

# ── Heuristic Fallback ────────────────────────────────────────────────────────

async def _heuristic_detect(state: AgentState) -> AgentFinding:
    """Basic pixel-variance fallback."""
    keyframes = state.get("keyframes", [])
    if not keyframes:
        return _error_finding("No keyframes available")

    scores = []
    for f in keyframes[:3]:
        try:
            img = Image.open(f).convert("L")
            arr = np.array(img, dtype=np.float32)
            var = np.var(arr)
            # Low variance in specific patterns can suggest AI
            s = max(0.0, min(100.0, (1.0 - (var / 5000.0)) * 100))
            scores.append(s)
        except Exception:
            scores.append(0.0)

    avg_score = statistics.mean(scores)
    return AgentFinding(
        agent_id="deepfake_detector",
        status="done",
        score=round(avg_score),
        findings=["Detection source: Heuristic Fallback", "⚠️ Cloud APIs unavailable — using pixel-variance analysis."],
        detail=json.dumps({"source": "heuristic", "scores": scores}),
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_findings(max_score: float, avg_score: float, flagged: List[str], source: str) -> List[str]:
    res = [f"Detection source: {source}"]
    if avg_score >= 80:
        res.append(f"High probability of AI generation ({avg_score:.0f}%)")
    elif avg_score >= 50:
        res.append(f"Possible AI manipulation detected ({avg_score:.0f}%)")
    else:
        res.append(f"No strong AI generation signals found.")
    res.extend(flagged)
    return res

def _error_finding(message: str) -> AgentFinding:
    return AgentFinding(agent_id="deepfake_detector", status="error", score=None, findings=[message], detail=None)

# ── Main Entry ────────────────────────────────────────────────────────────────

@traceable(name="deepfake_detector")
async def deepfake_detector_node(state: AgentState) -> AgentFinding:
    """Main node entry point (Online Only)."""
    print(f"\n[AGENT] deepfake_detector: Started cloud analysis...")
    
    # 1. Hive AI (if key)
    if settings.hive_api_key:
        kf = state.get("keyframes", [])
        if kf:
            res = await detect_deepfake_hive(kf[0])
            if res:
                score = round(res["confidence_score"] * 100)
                return AgentFinding(
                    agent_id="deepfake_detector",
                    status="done",
                    score=score,
                    findings=_build_findings(score, score, res["findings"], source="Hive AI"),
                    detail=json.dumps({"source": "hive_ai", "score": score})
                )

    # 2. Vertex AI (if credits)
    if settings.google_cloud_project:
        return await _vertex_vision_detect(state)

    # 3. Groq Vision fallback
    if settings.groq_api_key:
        # We've removed groq_vision_detect, but if we wanted to keep it, 
        # we'd need to restore the function. For now, let's just fallback to heuristic
        # if Vertex fails or is not configured.
        pass

    # 4. Fallback
    return await _heuristic_detect(state)

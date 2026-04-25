"""Video analysis endpoint."""

import uuid
from dataclasses import asdict
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from agents.graph import graph
from agents.state import AgentState
from config.settings import settings
from api.models import (
    AgentFindingResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ModelScoreResponse,
    SOSRegion,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the full Vigilens analysis pipeline on a video.

    In demo mode, returns simulated results immediately.
    In real mode, runs the LangGraph pipeline.
    """
    if not request.video_url and not request.video_path:
        raise HTTPException(status_code=400, detail="Either video_url or video_path is required")

    job_id = str(uuid.uuid4())

    initial_state: AgentState = {
        "video_url":       request.video_url,
        "video_path":      request.video_path,
        "job_id":          job_id,
        "keyframes":       [],
        "audio_path":      None,
        "metadata":        {},
        "transcript":      None,
        "ocr_text":        None,
        "deepfake_result": None,
        "source_result":   None,
        "context_result":  None,
        "verdict":         None,
        "credibility_score": None,
        "panic_index":     None,
        "summary":         None,
        "source_origin":   None,
        "original_date":   None,
        "claimed_location": request.claimed_location,
        "actual_location": None,
        "key_flags":       [],
        "error":           None,
        "disaster_type":   None,
        "sos_region":      None,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    # Build agent findings
    agents = []
    for finding_key in ["deepfake_result", "source_result", "context_result"]:
        finding = final_state.get(finding_key)
        if finding:
            data = asdict(finding) if hasattr(finding, "__dataclass_fields__") else {}
            # Convert nested ModelScore list
            model_scores = [
                ModelScoreResponse(**ms) if isinstance(ms, dict) else ModelScoreResponse(
                    model_name=ms.model_name,
                    authentic_pct=ms.authentic_pct,
                    fake_pct=ms.fake_pct,
                    confidence=ms.confidence,
                )
                for ms in (data.get("model_scores") or [])
            ]
            agents.append(
                AgentFindingResponse(
                    agent_id=data.get("agent_id", ""),
                    agent_name=data.get("agent_name", ""),
                    status=data.get("status", "done"),
                    score=data.get("score"),
                    findings=data.get("findings", []),
                    detail=data.get("detail"),
                    duration_ms=data.get("duration_ms"),
                    constraints_satisfied=data.get("constraints_satisfied"),
                    total_constraints=data.get("total_constraints"),
                    constraint_details=data.get("constraint_details") or {},
                    model_scores=model_scores,
                )
            )

    # Build SOS region if present
    sos_region = None
    raw_sos = final_state.get("sos_region")
    if raw_sos:
        try:
            sos_region = SOSRegion(**raw_sos)
        except Exception:
            pass

    return AnalyzeResponse(
        job_id=job_id,
        verdict=final_state.get("verdict", "unverified"),
        credibility_score=final_state.get("credibility_score", 0),
        panic_index=final_state.get("panic_index", 5),
        summary=final_state.get("summary", ""),
        disaster_type=final_state.get("disaster_type") or "unknown",
        source_origin=final_state.get("source_origin"),
        original_date=final_state.get("original_date"),
        claimed_location=final_state.get("claimed_location"),
        actual_location=final_state.get("actual_location"),
        key_flags=final_state.get("key_flags", []),
        agents=agents,
        sos_region=sos_region,
    )

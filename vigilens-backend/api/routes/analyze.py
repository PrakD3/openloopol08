import asyncio
from fastapi import APIRouter, HTTPException, status
from uuid import uuid4
from models.schemas import (
    AnalyzeRequest, 
    AnalyzeResponse, 
    AnalysisResult, 
    AnalysisDetails,
    DeepfakeDetail,
    SourceDetail,
    ContextDetail,
    TemporalDetail
)
from services.preprocess import extract_keyframes, extract_audio
from services.orchestrator import run_orchestrator
from services.agents.deepfake_agent import run_deepfake_agent
from services.agents.source_agent import run_source_agent
from services.agents.context_agent import run_context_agent
from services.agents.temporal_agent import run_temporal_agent

analyze_router = APIRouter()

@analyze_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    """
    Endpoint to trigger video analysis.
    Validates video_url, runs pipeline (preprocess → agents in parallel → orchestrator), 
    and returns synthesized results.
    """
    if not request.video_url or request.video_url.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_url is required"
        )

    # Step 1: Preprocess
    frames = extract_keyframes(request.video_url)
    audio = extract_audio(request.video_url)

    # Step 2: Agent Layer (Run in Parallel)
    deepfake_task = run_deepfake_agent(frames)
    source_task = run_source_agent(request.video_url)
    context_task = run_context_agent(frames)
    temporal_task = run_temporal_agent(request.video_url, frames)

    deepfake_results, source_results, context_results, temporal_results = await asyncio.gather(
        deepfake_task,
        source_task,
        context_task,
        temporal_task
    )

    agent_outputs = {
        "deepfake": deepfake_results,
        "source": source_results,
        "context": context_results,
        "temporal": temporal_results
    }

    # Step 3: Orchestrate analysis
    orchestration = run_orchestrator(agent_outputs)

    return AnalyzeResponse(
        job_id=uuid4(),
        status="completed",
        analysis=AnalysisResult(
            verdict=orchestration["verdict"],
            confidence=orchestration["confidence"],
            details=AnalysisDetails(
                deepfake=DeepfakeDetail(**deepfake_results),
                source=SourceDetail(**source_results),
                context=ContextDetail(**context_results),
                temporal=TemporalDetail(**temporal_results)
            )
        )
    )

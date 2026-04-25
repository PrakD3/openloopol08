import asyncio
import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from uuid import uuid4

from services.preprocess import extract_keyframes, extract_audio
from services.orchestrator import run_orchestrator
from services.agents.deepfake_agent import run_deepfake_agent
from services.agents.source_agent import run_source_agent
from services.agents.context_agent import run_context_agent
from services.agents.temporal_agent import run_temporal_agent

stream_router = APIRouter()

@stream_router.get("/analyze/stream")
async def analyze_stream(video_url: str = Query(..., description="The URL of the video to analyze")):
    """
    Real-time analysis pipeline using Server-Sent Events (SSE).
    Executes preprocess, agents in parallel, and orchestration, 
    yielding updates at each stage.
    """
    async def event_generator():
        # Step 1: Preprocess
        yield "data: preprocess_started\n\n"
        frames = extract_keyframes(video_url)
        audio = extract_audio(video_url)
        yield "data: preprocess_done\n\n"

        # Step 2: Agent Layer (Run in Parallel)
        agent_tasks = {
            "deepfake": asyncio.create_task(run_deepfake_agent(frames)),
            "source": asyncio.create_task(run_source_agent(video_url)),
            "context": asyncio.create_task(run_context_agent(frames)),
            "temporal": asyncio.create_task(run_temporal_agent(video_url, frames))
        }

        agent_results = {}
        
        # Monitor completion incrementally
        pending = set(agent_tasks.values())
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                for name, t in agent_tasks.items():
                    if t == task:
                        agent_results[name] = task.result()
                        yield f"data: agent_{name}_done\n\n"

        # Step 3: Orchestrate
        yield "data: orchestrator_started\n\n"
        orchestration = run_orchestrator(agent_results)
        yield "data: orchestrator_done\n\n"

        # Final Result Result
        final_response = {
            "job_id": str(uuid4()),
            "status": "completed",
            "analysis": {
                "verdict": orchestration["verdict"],
                "confidence": orchestration["confidence"],
                "details": agent_results
            }
        }
        yield f"data: {json.dumps(final_response)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

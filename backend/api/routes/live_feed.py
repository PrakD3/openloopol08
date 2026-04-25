import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from services.video_registry import get_live_verdicts, get_verdict_event

router = APIRouter()

@router.get("/live-feed")
async def live_feed(request: Request):
    """
    SSE endpoint that streams new verdicts to the client in real-time.
    """
    async def event_generator():
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Wait for a new verdict to be registered
            event = get_verdict_event()
            await event.wait()

            # Send the latest verdict
            latest = get_live_verdicts()[-1] if get_live_verdicts() else {}
            yield {
                "event": "update",
                "data": json.dumps(latest)
            }
            
            # Brief sleep to prevent tight loop
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/recent-verdicts")
async def get_recent():
    """Rest endpoint for initial load."""
    return get_live_verdicts()

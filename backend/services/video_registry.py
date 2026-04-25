from typing import Set, Dict, Any
import asyncio

# In-memory set of analyzed video IDs (from YouTube/X/etc)
_analyzed_ids: Set[str] = set()

# Last 10 verdicts for the live feed
_live_verdicts: list[Dict[str, Any]] = []

# Event to notify the SSE route of new verdicts
_verdict_event = asyncio.Event()

def is_analyzed(video_id: str) -> bool:
    return video_id in _analyzed_ids

def mark_analyzed(video_id: str, verdict_data: Dict[str, Any]):
    _analyzed_ids.add(video_id)
    # Add to live feed
    _live_verdicts.append(verdict_data)
    if len(_live_verdicts) > 20:
        _live_verdicts.pop(0)
    
    # Trigger SSE update
    _verdict_event.set()
    _verdict_event.clear()

def get_live_verdicts():
    return _live_verdicts

def get_verdict_event():
    return _verdict_event

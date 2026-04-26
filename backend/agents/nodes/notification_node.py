"""
Notification LangGraph Node.
Runs AFTER the orchestrator. Reads the final verdict and fires SMS alerts if appropriate.
"""

import json

from langsmith import traceable

from agents.state import AgentState
from config.settings import settings
from notifications.sms_service import dispatch_proximity_alerts


@traceable(name="notification_node")
async def notification_node(state: AgentState) -> AgentState:
    """
    Reads final verdict from state.
    If verified real disaster/conflict → dispatch SMS to nearby users.
    """
    verdict = state.get("verdict", "unverified")
    credibility_score = state.get("credibility_score", 0)
    if state.get("error"):
        return {
            **state,
            "notification_result": {"sent": False, "reason": f"Pipeline error: {state['error']}"},
        }

    # Helper to safely extract detail from AgentFinding or None
    def get_detail(finding):
        if not finding or not hasattr(finding, "detail") or not finding.detail:
            return {}
        try:
            return json.loads(finding.detail)
        except Exception:
            return {}

    context_detail = get_detail(state.get("context_result"))
    source_detail = get_detail(state.get("source_result"))

    # Extract location from source hunter (GPS from EXIF or platform metadata)
    exif = source_detail.get("exif", {})
    platform_meta = source_detail.get("platform_metadata", {})
    event_lat = exif.get("gps_lat") or state.get("metadata", {}).get("lat")
    event_lon = exif.get("gps_lon") or state.get("metadata", {}).get("lon")

    # Safely navigate context_detail nested structure
    llm_res = context_detail.get("llm_result", {})
    event_location_name = (
        platform_meta.get("location") or llm_res.get("claimed_location") or "Unknown location"
    )
    event_type = llm_res.get("event_type", "unknown")
    is_war_or_conflict = llm_res.get("is_war_or_conflict", False)

    notification_result = {"sent": False, "reason": "No GPS coordinates available"}

    if event_lat and event_lon:
        notification_result = await dispatch_proximity_alerts(
            event_lat=float(event_lat),
            event_lon=float(event_lon),
            event_location_name=event_location_name,
            event_type=event_type,
            verdict=verdict,
            credibility_score=credibility_score or 0,
            is_war_or_conflict=is_war_or_conflict,
            app_mode=settings.app_mode,
        )

    return {
        **state,
        "notification_result": notification_result,
    }

"""
Twilio SMS Dispatcher.
Sends evacuation alerts to users near a verified real disaster or conflict event.

Free tier: Twilio trial gives ~$15.50 credit = ~1000 SMS messages.
Get started: https://www.twilio.com/try-twilio

SAFETY: This module checks all safety gates before sending any SMS.
        A wrongly-fired evacuation alert is itself a form of harm.
"""

import asyncio
from typing import Optional

from langsmith import traceable

from config.settings import settings
from notifications.geofence import UserLocation, find_users_in_radius
from notifications.user_registry import get_all_users


# ── SMS Message Templates ─────────────────────────────────────────────────────

def _build_sms_message(
    event_type: str,
    event_location: str,
    credibility_score: int,
    verdict: str,
    is_war_or_conflict: bool,
) -> str:
    """Build the SMS alert message sent to nearby users."""
    if is_war_or_conflict:
        alert_type = "⚠️ SECURITY ALERT"
        action = "Move to a safe location immediately and follow official guidance."
    else:
        alert_type = "🚨 DISASTER ALERT"
        action = "Follow evacuation orders and official emergency services guidance."

    return (
        f"{alert_type} — Vigilens\n"
        f"A verified {event_type} has been detected near your location: {event_location}.\n"
        f"Confidence: {credibility_score}%\n"
        f"{action}\n"
        f"Check vigilens.app for details. Reply STOP to unsubscribe."
    )[:1600]  # SMS limit


# ── Safety Gate ───────────────────────────────────────────────────────────────

def _passes_safety_gate(
    verdict: str,
    credibility_score: int,
    app_mode: str,
) -> tuple[bool, str]:
    """
    All conditions must be True before ANY SMS is sent.
    Returns (can_send: bool, reason: str)
    """
    if app_mode == "demo":
        return False, "Demo mode — SMS blocked"
    if not settings.notification_enabled:
        return False, "Notifications disabled (NOTIFICATION_ENABLED=false)"
    if verdict != "real":
        return False, f"Verdict is '{verdict}' — only 'real' events trigger alerts"
    if credibility_score < settings.notification_confidence_threshold:
        return False, f"Score {credibility_score}% < threshold {settings.notification_confidence_threshold}%"
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return False, "Twilio credentials not configured"
    return True, "All safety checks passed"


# ── Twilio Sender ─────────────────────────────────────────────────────────────

async def _send_sms(to_number: str, message: str) -> bool:
    """
    Send a single SMS via Twilio REST API.
    Returns True on success, False on failure.
    Twilio REST API: POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
    """
    try:
        import httpx
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        data = {
            "To": to_number,
            "From": settings.twilio_from_number,
            "Body": message,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=10.0,
            )
            if response.status_code in (200, 201):
                print(f"[Notifications] SMS sent to {to_number[:6]}****")
                return True
            else:
                print(f"[Notifications] Twilio error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        print(f"[Notifications] SMS failed to {to_number[:6]}****: {e}")
        return False


# ── Main Dispatcher ───────────────────────────────────────────────────────────

@traceable(name="notification_dispatcher")
async def dispatch_proximity_alerts(
    event_lat: float,
    event_lon: float,
    event_location_name: str,
    event_type: str,
    verdict: str,
    credibility_score: int,
    is_war_or_conflict: bool,
    app_mode: str,
) -> dict:
    """
    Main entry point for the notification system.
    Called by notification_node after orchestrator produces a verdict.

    Returns summary of what was sent (or why it was blocked).
    """
    can_send, reason = _passes_safety_gate(verdict, credibility_score, app_mode)

    if not can_send:
        return {
            "sent": False,
            "reason": reason,
            "recipients_count": 0,
            "blocked": True,
        }

    # Find all registered users within 10km
    all_users = get_all_users()
    nearby_users = find_users_in_radius(event_lat, event_lon, all_users)

    if not nearby_users:
        return {
            "sent": False,
            "reason": "No registered users within notification radius",
            "recipients_count": 0,
            "blocked": False,
        }

    message = _build_sms_message(
        event_type=event_type,
        event_location=event_location_name,
        credibility_score=credibility_score,
        verdict=verdict,
        is_war_or_conflict=is_war_or_conflict,
    )

    # Send all SMS concurrently (but cap at 50 to avoid rate limits on free tier)
    targets = nearby_users[:50]
    results = await asyncio.gather(
        *[_send_sms(user.phone_number, message) for user in targets],
        return_exceptions=False,
    )

    sent_count = sum(1 for r in results if r)
    return {
        "sent": True,
        "recipients_count": sent_count,
        "total_nearby": len(nearby_users),
        "message_preview": message[:100] + "...",
        "blocked": False,
        "reason": f"Alerts sent to {sent_count} users within {settings.notification_radius_km}km",
    }

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

EVENT_MESSAGES = {
    "earthquake": {
        "emoji": "🌍",
        "alert": "EARTHQUAKE ALERT",
        "action": "Drop, cover, and hold on. Move away from buildings after shaking stops. Do NOT use elevators.",
    },
    "flood": {
        "emoji": "🌊",
        "alert": "FLOOD ALERT",
        "action": "Move to higher ground immediately. Do NOT walk or drive through floodwater.",
    },
    "fire": {
        "emoji": "🔥",
        "alert": "WILDFIRE ALERT",
        "action": "Evacuate in the direction away from the fire. Close all windows and doors before leaving.",
    },
    "tsunami": {
        "emoji": "🌊",
        "alert": "TSUNAMI ALERT",
        "action": "Move inland and to high ground immediately. Do NOT return to the coast until officials say it is safe.",
    },
    "cyclone": {
        "emoji": "🌀",
        "alert": "CYCLONE / STORM ALERT",
        "action": "Seek shelter in a sturdy building away from windows. Do NOT go outside during the storm.",
    },
    "tornado": {
        "emoji": "🌪️",
        "alert": "TORNADO ALERT",
        "action": "Move to an interior room on the lowest floor. Stay away from windows.",
    },
    "volcano": {
        "emoji": "🌋",
        "alert": "VOLCANIC ACTIVITY ALERT",
        "action": "Evacuate the area. Avoid river valleys and low-lying areas. Wear a mask if ash is present.",
    },
    "missile": {
        "emoji": "🚨",
        "alert": "MISSILE ATTACK ALERT",
        "action": "Move to a designated shelter or lowest floor interior room immediately. Stay away from windows.",
    },
    "airstrike": {
        "emoji": "🚨",
        "alert": "AIRSTRIKE ALERT",
        "action": "Seek underground shelter immediately. Move to the lowest floor of a sturdy building.",
    },
    "explosion": {
        "emoji": "💥",
        "alert": "EXPLOSION ALERT",
        "action": "Move away from the area immediately. Avoid the blast zone and wait for official all-clear.",
    },
    "attack": {
        "emoji": "⚠️",
        "alert": "SECURITY ATTACK ALERT",
        "action": "Move to a safe location immediately and follow official security guidance.",
    },
    "shooting": {
        "emoji": "⚠️",
        "alert": "ACTIVE SHOOTER ALERT",
        "action": "Run, hide, or fight if no other option. Call emergency services when safe.",
    },
    "chemical": {
        "emoji": "☣️",
        "alert": "CHEMICAL HAZARD ALERT",
        "action": "Move upwind and away from the area. Seal windows/doors if indoors. Do NOT touch any substance.",
    },
    "conflict": {
        "emoji": "⚠️",
        "alert": "SECURITY ALERT",
        "action": "Move to a safe location immediately and follow official guidance.",
    },
    "unknown": {
        "emoji": "🚨",
        "alert": "EMERGENCY ALERT",
        "action": "Follow evacuation orders and official emergency services guidance.",
    },
}

def _build_sms_message(
    event_type: str,
    event_location: str,
    credibility_score: int,
    verdict: str,
    is_war_or_conflict: bool,
) -> str:
    """Build a category-specific SMS alert message."""
    key = (event_type or "unknown").lower().strip()
    category = EVENT_MESSAGES.get(key)
    if not category:
        for k in EVENT_MESSAGES:
            if k in key or key in k:
                category = EVENT_MESSAGES[k]
                break
    if not category:
        category = EVENT_MESSAGES["conflict"] if is_war_or_conflict else EVENT_MESSAGES["unknown"]
    return (
        f"{category['emoji']} {category['alert']} — Vigilens\n"
        f"Verified event near your location: {event_location}\n"
        f"Confidence: {credibility_score}%\n"
        f"{category['action']}\n"
        f"vigilens.app for details. Reply STOP to unsubscribe."
    )[:1600]


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

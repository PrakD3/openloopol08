"""
In-memory user location registry.
In production: replace with Supabase/PostgreSQL query.
For hackathon: stores registered users in memory.

Users register by:
  1. Visiting the Vigilens site
  2. Clicking "Get Alerts" and granting GPS permission
  3. Entering their phone number (verified via Twilio)
  4. POST /api/register-location from Next.js API route
"""

from notifications.geofence import UserLocation

# In-memory store: user_id → UserLocation
_registry: dict[str, UserLocation] = {}


def register_user(user_id: str, phone: str, lat: float, lon: float, area: str | None = None):
    """Register or update a user's location."""
    _registry[user_id] = UserLocation(
        user_id=user_id,
        phone_number=phone,
        latitude=lat,
        longitude=lon,
        area_name=area,
    )


def get_all_users() -> list[UserLocation]:
    """Return all registered users."""
    return list(_registry.values())


def deregister_user(user_id: str):
    """Remove a user from the registry."""
    _registry.pop(user_id, None)

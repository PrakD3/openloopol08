"""
SOS Region Engine — OpenStreetMap / Nominatim
================================================
When a genuine disaster is confirmed (verdict='real', panic_index >= 5),
this engine:
  1. Geocodes the claimed/actual location via Nominatim (free, no API key needed)
  2. Calculates an impact radius (km) based on disaster type + panic index
  3. Returns a SOS region dict ready for OpenStreetMap rendering on the frontend

No API key required — uses OSM Nominatim with a polite User-Agent header.
Rate limit: 1 request/second (we only call this once per analysis).
"""

from __future__ import annotations

from typing import TypedDict

import httpx


class RadiusConfig(TypedDict):
    base_km: int
    scale_km: int
    color: str


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "Vigilens-Disaster-Verifier/1.0 (hackathon@openloop.dev)"

# Impact radius formula per disaster type:
#   radius_km = base_km + panic_index * scale_km
IMPACT_RADIUS_CONFIG: dict[str, RadiusConfig] = {
    "flood": {"base_km": 8, "scale_km": 4, "color": "#3b82f6"},  # blue
    "earthquake": {"base_km": 25, "scale_km": 18, "color": "#f97316"},  # orange
    "cyclone": {"base_km": 60, "scale_km": 28, "color": "#8b5cf6"},  # purple
    "tsunami": {"base_km": 35, "scale_km": 22, "color": "#06b6d4"},  # cyan
    "wildfire": {"base_km": 6, "scale_km": 6, "color": "#ef4444"},  # red
    "landslide": {"base_km": 5, "scale_km": 4, "color": "#84cc16"},  # lime
    "unknown": {"base_km": 15, "scale_km": 8, "color": "#f59e0b"},  # amber
}


async def get_sos_region(
    location: str,
    disaster_type: str,
    panic_index: int,
) -> dict | None:
    """
    Geocode *location* and compute the SOS impact zone.

    Returns dict:
    {
        "lat": float,
        "lng": float,
        "radius_km": float,
        "center_name": str,
        "disaster_type": str,
        "panic_index": int,
        "color": str,          # hex colour for map circle
        "sos_active": bool,
    }
    or None if geocoding fails.
    """
    if not location or not location.strip():
        return None

    cfg = IMPACT_RADIUS_CONFIG.get(disaster_type, IMPACT_RADIUS_CONFIG["unknown"])
    radius_km = cfg["base_km"] + panic_index * cfg["scale_km"]

    try:
        coords = await _geocode(location)
        if coords is None:
            return None

        lat, lng, display_name = coords
        return {
            "lat": lat,
            "lng": lng,
            "radius_km": round(radius_km, 1),
            "center_name": display_name,
            "disaster_type": disaster_type,
            "panic_index": panic_index,
            "color": cfg["color"],
            "sos_active": True,
        }
    except Exception:
        return None


async def _geocode(location: str):
    """
    Use Nominatim to get (lat, lng, display_name) for a free-text location.
    Returns None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": location,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 0,
                },
                headers={"User-Agent": NOMINATIM_USER_AGENT},
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    hit = data[0]
                    return (
                        float(hit["lat"]),
                        float(hit["lon"]),
                        hit.get("display_name", location),
                    )
    except Exception:
        pass
    return None

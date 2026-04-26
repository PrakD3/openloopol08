"""
Haversine-based geofence calculator.
Finds all registered users within NOTIFICATION_RADIUS_KM of an event.
"""

import math
from dataclasses import dataclass

from config.settings import settings


@dataclass
class UserLocation:
    user_id: str
    phone_number: str  # E.164 format: +971xxxxxxxx
    latitude: float
    longitude: float
    area_name: str | None = None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two GPS points in kilometres.
    Uses the Haversine formula.
    """
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_users_in_radius(
    event_lat: float,
    event_lon: float,
    all_users: list[UserLocation],
    radius_km: float = None,
) -> list[UserLocation]:
    """
    Returns all users within radius_km of the event location.
    radius_km defaults to NOTIFICATION_RADIUS_KM from settings.
    """
    radius = radius_km or settings.notification_radius_km
    return [
        user
        for user in all_users
        if haversine_distance_km(event_lat, event_lon, user.latitude, user.longitude) <= radius
    ]

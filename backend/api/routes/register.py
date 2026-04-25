from fastapi import APIRouter
from pydantic import BaseModel
from notifications.user_registry import register_user

router = APIRouter()

class LocationRegistration(BaseModel):
    user_id: str
    phone: str
    lat: float
    lon: float
    area: str = ""

@router.post("/register-location")
async def register_location(data: LocationRegistration):
    """Register a user's location for proximity SMS alerts."""
    register_user(
        user_id=data.user_id,
        phone=data.phone,
        lat=data.lat,
        lon=data.lon,
        area=data.area or None,
    )
    return {"registered": True, "radius_km": 10}

"""Health check endpoint."""

from fastapi import APIRouter

from config.settings import settings
from api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return API health status and current mode configuration."""
    return HealthResponse(
        status="ok",
        mode=settings.inference_mode,
        app_mode=settings.app_mode,
    )

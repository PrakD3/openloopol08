from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("/health")
async def health_check():
    """Health check endpoint to monitor Vigilens API status."""
    return {"status": "healthy"}

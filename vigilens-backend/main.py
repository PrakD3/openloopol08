import logging
from fastapi import FastAPI
from api.routes.health import health_router
from api.routes.analyze import analyze_router
from api.routes.stream import stream_router

# Initialize basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Vigilens")

app = FastAPI(title="Vigilens API")

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(stream_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint for Vigilens API."""
    logger.info("Root endpoint accessed")
    return {"message": "Vigilens API running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Vigilens API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

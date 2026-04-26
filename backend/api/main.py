"""Vigilens FastAPI application entry point."""

import asyncio
import os
import sys

# CRITICAL WINDOWS FIX: Force ProactorEventLoop to support subprocesses (FFmpeg/yt-dlp)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

try:
    from api.routes.analyze import router as analyze_router
    from api.routes.health import router as health_router
    from api.routes.register import router as register_router
    from api.routes.status import router as status_router
except Exception as e:
    print(f"\n[CRITICAL ERROR] Failed to import routers: {e}", flush=True)
    import traceback

    traceback.print_exc()
    # Dummy router to allow startup
    from fastapi import APIRouter

    analyze_router = APIRouter()
    health_router = APIRouter()
    status_router = APIRouter()
    register_router = APIRouter()

# Enable LangSmith tracing if configured
if settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = settings.langsmith_tracing_v2
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

app = FastAPI(
    title="Vigilens API",
    description="Disaster video misinformation detection pipeline",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[BACKEND] Incoming {request.method} request to {request.url.path}", flush=True)
    response = await call_next(request)
    print(
        f"[BACKEND] Finished {request.method} request to {request.url.path} with status {response.status_code}",
        flush=True,
    )
    return response


# Get allowed origins from settings or default to wildcard for flexible deployment
allowed_origins = (
    settings.cors_allowed_origins.split(",")
    if hasattr(settings, "cors_allowed_origins") and settings.cors_allowed_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(status_router)
app.include_router(register_router)

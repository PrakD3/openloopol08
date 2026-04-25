"""Vigilens FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from api.routes.analyze import router as analyze_router
from api.routes.health import router as health_router
from api.routes.status import router as status_router

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://vigilens.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(status_router)

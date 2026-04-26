"""Vigilens settings — single source of truth for all configuration."""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Mode ──────────────────────────────────────────────────────────────────
    app_mode: Literal["demo", "real"] = "demo"

    # ── Groq (LLM + Whisper) ──────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_orchestrator_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_fast_model: str = "llama-3.1-8b-instant"

    # ── Google Gemini ─────────────────────────────────────────────────────────
    google_api_key: str = ""

    # Groq Speech-to-Text (replaces local Whisper on cold-start)
    # Models available: whisper-large-v3, whisper-large-v3-turbo
    whisper_use_groq: bool = True
    whisper_use_api: bool = False
    whisper_model_size: str = "small"
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # ── LangSmith ─────────────────────────────────────────────────────────────
    langsmith_api_key: str = ""
    langsmith_project: str = "vigilens"
    langsmith_tracing_v2: str = "true"

    # ── Source hunting ────────────────────────────────────────────────────────
    google_vision_api_key: str = ""
    tineye_api_key: str = ""
    youtube_api_key: str = ""
    x_bearer_token: str = ""
    google_cloud_project: str = "gdg-project-481105"
    google_cloud_location: str = "us-central1"
    google_cloud_key_path: str = "gcp-key.json"
    gemini_model: str = "gemini-2.5-flash"
    bing_search_api_key: str = ""

    # ── Context analyser ──────────────────────────────────────────────────────
    claimbuster_api_key: str = ""

    # ── Telegram Alerts ───────────────────────────────────────────────────────
    telegram_bot_token: str | None = None
    telegram_channel_id: str | None = None  # e.g. "@vigilens_alerts" or numeric chat_id

    # ── Custom Model ──────────────────────────────────────────────────────────
    custom_model_enabled: bool = True

    # ── Orchestrator model alias ──────────────────────────────────────────────
    orchestrator_model: str = "llama-3.3-70b-versatile"

    # ── Notifications ─────────────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    notification_radius_km: float = 10.0
    notification_confidence_threshold: int = 85
    notification_enabled: bool = True

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# ── Auto-configure GCP Credentials ────────────────────────────────────────────


def _find_gcp_key():
    # Try local, then parent (root), then explicit backend
    candidates = [
        Path(settings.google_cloud_key_path),
        Path("..") / settings.google_cloud_key_path,
        Path("backend") / settings.google_cloud_key_path,
    ]
    for p in candidates:
        if p.exists():
            return str(p.absolute())
    return None


key_path = _find_gcp_key()
if key_path:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    # Update settings to the absolute path for explicit loading later
    settings.google_cloud_key_path = key_path
    print(f"[SETTINGS] Found GCP key at: {key_path}")
else:
    print("[SETTINGS] WARNING: gcp-key.json not found in root or backend folder.")


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def is_deprecated_groq_model(model_name: str | None) -> bool:
    deprecated = {
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-1b-preview",
        "llama-3.2-3b-preview",
    }
    return bool(model_name and model_name in deprecated)


def log_runtime_configuration() -> None:
    groq_key_present = "yes" if settings.groq_api_key else "no"
    print(
        f"[{_ts()}] [SETTINGS] "
        f"app_mode={settings.app_mode!r} "
        f"groq_key={groq_key_present} "
        f"orchestrator_model={settings.groq_orchestrator_model!r} "
        f"vision_model={settings.groq_vision_model!r} "
        f"whisper_model={settings.groq_whisper_model!r}",
        flush=True,
    )
    if is_deprecated_groq_model(settings.groq_vision_model):
        print(
            f"[{_ts()}] [SETTINGS] WARNING: configured Groq vision model "
            f"{settings.groq_vision_model!r} is deprecated.",
            flush=True,
        )


def get_llm(model: str | None = None):
    """
    Return ChatVertexAI (if credits available) or ChatGroq.
    """
    # ── Priority 1: Google AI Studio (API Key) ──────────────────────────────
    if settings.google_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.gemini_model, google_api_key=settings.google_api_key, temperature=0.1
            )
        except Exception as e:
            print(f"[SETTINGS] Google AI Studio load failed: {e}. Trying Vertex...")

    # ── Priority 2: Vertex AI (GCP Project) ──────────────────────────────────
    if settings.google_cloud_project:
        try:
            from google.oauth2 import service_account
            from langchain_google_vertexai import ChatVertexAI

            creds = None
            if settings.google_cloud_key_path and os.path.exists(settings.google_cloud_key_path):
                creds = service_account.Credentials.from_service_account_file(
                    os.path.abspath(settings.google_cloud_key_path)
                )

            return ChatVertexAI(
                model_name=settings.gemini_model,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
                credentials=creds,
                temperature=0.1,
            )
        except Exception as e:
            print(f"[SETTINGS] Vertex AI load failed: {e}. Falling back to Groq...")

    # ── Priority 2: Groq (API Key) ────────────────────────────────────────────
    from langchain_groq import ChatGroq

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    selected_model = model or settings.groq_orchestrator_model
    return ChatGroq(model=selected_model, groq_api_key=settings.groq_api_key, temperature=0.1)

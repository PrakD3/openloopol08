"""Vigilens settings — single source of truth for all configuration."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Mode ──────────────────────────────────────────────────────────────────
    inference_mode: Literal["online", "offline"] = "online"
    app_mode: Literal["demo", "real"] = "demo"

    # ── Groq (LLM + Whisper) ──────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_orchestrator_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_fast_model: str = "llama-3.1-8b-instant"

    # Groq Speech-to-Text (replaces local Whisper on cold-start)
    # Models available: whisper-large-v3, whisper-large-v3-turbo
    whisper_use_groq: bool = True
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # ── Offline LLM (Ollama) ──────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_orchestrator_model: str = "llama3.3"
    ollama_vision_model: str = "llava:13b"

    # ── LangSmith ─────────────────────────────────────────────────────────────
    langsmith_api_key: str = ""
    langsmith_project: str = "vigilens"
    langsmith_tracing_v2: str = "true"

    # ── Deepfake detection ────────────────────────────────────────────────────
    hive_api_key: str = ""
    deepsafe_url: str = "http://localhost:8001"

    # ── Whisper (legacy / local fallback) ─────────────────────────────────────
    # whisper_use_groq=true takes priority over both of these.
    # whisper_use_api=true + openai_api_key → OpenAI Whisper API
    # otherwise                              → local openai-whisper package
    whisper_use_api: bool = True
    openai_api_key: str = ""
    whisper_model_size: str = "medium"

    # ── Source hunting ────────────────────────────────────────────────────────
    google_vision_api_key: str = ""
    tineye_api_key: str = ""
    youtube_api_key: str = ""
    x_bearer_token: str = ""
    bing_search_api_key: str = ""

    # ── Context analyser ──────────────────────────────────────────────────────
    claimbuster_api_key: str = ""

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


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def is_deprecated_groq_model(model_name: Optional[str]) -> bool:
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
        f"[{_ts()}] [SETTINGS] inference_mode={settings.inference_mode!r} "
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


def get_llm(model: Optional[str] = None):
    """
    Return the appropriate LLM based on INFERENCE_MODE.

    Priority:
      offline → Ollama (local Docker container)
      online  → Groq ChatGroq (cloud, no Docker needed)
    """
    if settings.inference_mode == "offline":
        from langchain_community.llms import Ollama  # type: ignore[import]

        return Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_orchestrator_model,
        )

    # online (Groq)
    from langchain_groq import ChatGroq  # type: ignore[import]

    if not settings.groq_api_key:
        raise RuntimeError(
            "INFERENCE_MODE=online but GROQ_API_KEY is not set in .env. "
            "Add your key or switch INFERENCE_MODE=offline."
        )

    selected_model = model or settings.groq_orchestrator_model
    if is_deprecated_groq_model(selected_model):
        print(
            f"[{_ts()}] [SETTINGS] WARNING: creating ChatGroq with deprecated "
            f"model={selected_model!r}",
            flush=True,
        )

    return ChatGroq(api_key=settings.groq_api_key, model=selected_model)

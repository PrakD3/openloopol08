from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Mode
    inference_mode: Literal["online", "offline"] = "online"
    app_mode: Literal["demo", "real"] = "demo"

    # Online LLM
    groq_api_key: str = ""
    groq_orchestrator_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"

    # Offline LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_orchestrator_model: str = "llama3.3"
    ollama_vision_model: str = "llava:13b"

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "vigilens"
    langsmith_tracing_v2: str = "true"

    # Deepfake
    hive_api_key: str = ""
    deepsafe_url: str = "http://localhost:8001"

    # Whisper
    whisper_use_api: bool = True
    openai_api_key: str = ""
    whisper_model_size: str = "medium"

    # Source hunting
    google_vision_api_key: str = ""
    tineye_api_key: str = ""
    youtube_api_key: str = ""
    x_bearer_token: str = ""
    bing_search_api_key: str = ""

    # Context analyser
    claimbuster_api_key: str = ""

    # Notifications
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    notification_radius_km: float = 10.0
    notification_confidence_threshold: int = 85
    notification_enabled: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


def get_llm():
    """Returns the appropriate LLM based on INFERENCE_MODE."""
    if settings.inference_mode == "offline":
        from langchain_community.llms import Ollama  # type: ignore[import]

        return Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_orchestrator_model,
        )
    else:
        from langchain_groq import ChatGroq  # type: ignore[import]

        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_orchestrator_model,
        )

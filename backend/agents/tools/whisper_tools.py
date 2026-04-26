"""Whisper transcription tools (local and API)."""

from typing import Optional

from ...config.settings import settings


async def transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Transcribe audio using Whisper (API or local based on settings).

    Args:
        audio_path: Path to audio file

    Returns:
        Transcribed text, or None
    """
    if not audio_path:
        return None

    if settings.whisper_use_api and settings.openai_api_key:
        return await _api_transcribe(audio_path)
    else:
        return await _local_transcribe(audio_path)


async def _api_transcribe(audio_path: str) -> Optional[str]:
    """Transcribe via OpenAI Whisper API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"model": "whisper-1"},
                )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return str(data.get("text", ""))
        return None
    except Exception:
        pass
    return None


async def _local_transcribe(audio_path: str) -> Optional[str]:
    """Transcribe via local Whisper model."""
    try:
        import whisper  # type: ignore[import]

        model = whisper.load_model(settings.whisper_model_size)
        result = model.transcribe(audio_path)
        if isinstance(result, dict):
            return str(result.get("text", ""))
        return None
    except Exception:
        return None

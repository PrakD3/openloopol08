"""pytest configuration and fixtures."""

import pytest

from config.settings import settings


@pytest.fixture(autouse=True)
def set_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force demo mode for all tests — no external API calls."""
    monkeypatch.setattr(settings, "app_mode", "demo")
    monkeypatch.setattr(settings, "inference_mode", "online")

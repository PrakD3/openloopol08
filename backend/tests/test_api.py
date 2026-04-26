"""API endpoint tests."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Health endpoint returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mode" in data
    assert "app_mode" in data


def test_analyze_requires_url() -> None:
    """Analyze endpoint returns 400 when no URL provided."""
    response = client.post("/analyze", json={})
    assert response.status_code == 400


def test_analyze_demo_mode() -> None:
    """Analyze endpoint returns result in demo mode."""
    response = client.post(
        "/analyze",
        json={"video_url": "https://www.youtube.com/watch?v=test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "verdict" in data
    assert data["verdict"] in ["real", "misleading", "ai-generated", "unverified"]

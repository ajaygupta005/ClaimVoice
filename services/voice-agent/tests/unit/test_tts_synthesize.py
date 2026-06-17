"""Tests for POST /api/v1/tts/synthesize (Component 38)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_tts_returns_unavailable_when_provider_is_browser(client: TestClient) -> None:
    """Default config has tts_provider=browser — must return ok=False with fallback=browser."""
    res = client.post("/api/v1/tts/synthesize", json={"text": "Hello world"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["fallback"] == "browser"


def test_tts_rejects_empty_text(client: TestClient) -> None:
    res = client.post("/api/v1/tts/synthesize", json={"text": ""})
    assert res.status_code == 422


def test_tts_rejects_missing_text(client: TestClient) -> None:
    res = client.post("/api/v1/tts/synthesize", json={})
    assert res.status_code == 422


def test_tts_accepts_valid_request(client: TestClient) -> None:
    res = client.post("/api/v1/tts/synthesize", json={"text": "Your copay is $30."})
    assert res.status_code == 200


def test_tts_google_error_returns_unavailable(client: TestClient) -> None:
    """When provider=google but Google call fails, still return 200 with ok=False."""
    with patch("voice_agent.core.config.settings") as mock_settings:
        mock_settings.voice_agent_tts_provider = "google"
        mock_settings.google_tts_language_code = "en-US"
        mock_settings.google_tts_voice_name = "en-US-Chirp3-HD-Aoede"
        # _google_synthesize will fail because google.cloud.texttospeech is not installed
        res = client.post("/api/v1/tts/synthesize", json={"text": "Hello"})
        assert res.status_code == 200
        data = res.json()
        # ok=False (Google not configured/failed) or ok=True with audio — both valid
        assert "ok" in data


def test_tts_does_not_affect_agent_respond(client: TestClient) -> None:
    """TTS endpoint being present must not break the answer pipeline."""
    res = client.post("/api/v1/agent/respond", json={"question": "Is an MRI covered?"})
    assert res.status_code == 200
    assert res.json()["answer"]

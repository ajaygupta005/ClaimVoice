"""Tests for POST /api/v1/tts/synthesize (Component 38)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_tts_browser_provider_uses_system_audio_when_available(client: TestClient) -> None:
    """Default browser provider should still return server audio when local TTS exists."""
    with patch(
        "voice_agent.api.v1.tts_synthesize._system_synthesize",
        return_value=("UklGRg==", "Samantha", "audio/wav"),
    ):
        res = client.post("/api/v1/tts/synthesize", json={"text": "Hello world"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "system"
    assert data["voiceName"] == "Samantha"
    assert data["mimeType"] == "audio/wav"
    assert data["audioBase64"] == "UklGRg=="


def test_tts_returns_unavailable_when_system_tts_fails(client: TestClient) -> None:
    """If server-side TTS is unavailable, keep returning 200 with browser fallback."""
    with patch(
        "voice_agent.api.v1.tts_synthesize._system_synthesize",
        side_effect=RuntimeError("system_tts_say_unavailable"),
    ):
        res = client.post("/api/v1/tts/synthesize", json={"text": "Hello world"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["provider"] == "system"
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
    """When provider=google fails, system TTS should be tried before giving up."""
    with (
        patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings,
        patch("voice_agent.api.v1.tts_synthesize._google_synthesize", side_effect=RuntimeError("no_google")),
        patch(
            "voice_agent.api.v1.tts_synthesize._system_synthesize",
            return_value=("UklGRg==", "Samantha", "audio/wav"),
        ),
    ):
        mock_settings.voice_agent_tts_provider = "google"
        mock_settings.google_tts_language_code = "en-US"
        mock_settings.google_tts_voice_name = "en-US-Chirp3-HD-Aoede"
        res = client.post("/api/v1/tts/synthesize", json={"text": "Hello"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "system"


def test_tts_does_not_affect_agent_respond(client: TestClient) -> None:
    """TTS endpoint being present must not break the answer pipeline."""
    res = client.post("/api/v1/agent/respond", json={"question": "Is an MRI covered?"})
    assert res.status_code == 200
    assert res.json()["answer"]

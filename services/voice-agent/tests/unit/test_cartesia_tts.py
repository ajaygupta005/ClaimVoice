"""Unit tests for Cartesia Skylar TTS (Component 55)."""
from __future__ import annotations

import base64
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _mock_cartesia_settings(mock_settings: MagicMock, *, api_key: str = "test-key") -> None:
    """Set all Cartesia-related settings on a mock settings object."""
    mock_settings.voice_agent_tts_provider = "cartesia"
    mock_settings.cartesia_api_key = api_key
    mock_settings.cartesia_tts_model = "sonic-3.5"
    mock_settings.cartesia_voice_id = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
    mock_settings.cartesia_voice_name = "Skylar"
    mock_settings.cartesia_tts_language = "en"
    mock_settings.cartesia_tts_sample_rate = 44100
    mock_settings.cartesia_tts_container = "wav"
    mock_settings.cartesia_tts_encoding = "pcm_s16le"
    mock_settings.cartesia_tts_speed = 1.0
    mock_settings.cartesia_tts_volume = 1.0
    mock_settings.google_tts_language_code = "en-US"
    mock_settings.google_tts_voice_name = "en-US-Chirp3-HD-Aoede"
    mock_settings.system_tts_voice_name = "Samantha"


def test_cartesia_missing_key_returns_ok_false(client: TestClient) -> None:
    """When CARTESIA_API_KEY is absent, synthesize must not 500."""
    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings:
        _mock_cartesia_settings(mock_settings, api_key="")
        res = client.post("/api/v1/tts/synthesize", json={"text": "Your copay is $30."})
    assert res.status_code == 200
    # key must never appear
    assert "cartesia_api_key" not in res.text
    assert "api_key" not in res.text


def test_cartesia_success_returns_wav(client: TestClient) -> None:
    """A successful Cartesia response must return ok=True, provider=cartesia, mimeType=audio/wav."""
    fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 16 + b"data\x04\x00\x00\x00\x00\x00\x00\x00"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_wav

    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_response):
        _mock_cartesia_settings(mock_settings)
        res = client.post("/api/v1/tts/synthesize", json={"text": "Your copay is $30."})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "cartesia"
    assert data["mimeType"] == "audio/wav"
    assert data["voiceName"] == "Skylar"
    assert len(data["audioBase64"]) > 0
    assert "api_key" not in str(data)
    assert "cartesia_api_key" not in str(data)


def test_cartesia_http_error_falls_back(client: TestClient) -> None:
    """A non-200 from Cartesia must not 500 — system fallback or ok=False."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.content = b'{"error": "invalid key"}'

    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_response):
        _mock_cartesia_settings(mock_settings, api_key="bad-key")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200


def test_cartesia_timeout_falls_back(client: TestClient) -> None:
    """A timeout from Cartesia must not 500."""
    import httpx as _httpx

    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post",
               side_effect=_httpx.TimeoutException("timeout")):
        _mock_cartesia_settings(mock_settings)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200


def test_cartesia_never_leaks_api_key(client: TestClient) -> None:
    """The synthesize response must never contain the API key."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"RIFF\x00\x00\x00\x00WAVEdata\x00\x00\x00\x00"

    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_response):
        _mock_cartesia_settings(mock_settings, api_key="secret-cartesia-key-do-not-leak")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert "secret-cartesia-key-do-not-leak" not in res.text


def test_cartesia_request_error_falls_back(client: TestClient) -> None:
    """A network error (RequestError) from Cartesia must not 500."""
    import httpx as _httpx

    with patch("voice_agent.api.v1.tts_synthesize.settings") as mock_settings, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post",
               side_effect=_httpx.RequestError("connection refused")):
        _mock_cartesia_settings(mock_settings)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200


def test_runtime_status_includes_tts_provider(client: TestClient) -> None:
    """GET /api/v1/runtime/status must include tts_provider and tts_voice_name fields."""
    res = client.get("/api/v1/runtime/status")
    assert res.status_code == 200
    data = res.json()
    assert "tts_provider" in data
    assert "tts_voice_name" in data
    # must never contain api keys
    assert "cartesia_api_key" not in res.text
    assert "CARTESIA_API_KEY" not in res.text


def test_runtime_status_cartesia_returns_voice_name(client: TestClient) -> None:
    """When tts_provider=cartesia, tts_voice_name must be 'Skylar'."""
    with patch("voice_agent.api.v1.runtime_status.settings") as mock_settings:
        mock_settings.claimvoice_voice_runtime = "browser"
        mock_settings.voice_agent_tts_provider = "cartesia"
        mock_settings.cartesia_voice_name = "Skylar"
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_settings.gemini_live_voice = "Zephyr"
        res = client.get("/api/v1/runtime/status")

    assert res.status_code == 200
    data = res.json()
    assert data["tts_provider"] == "cartesia"
    assert data["tts_voice_name"] == "Skylar"

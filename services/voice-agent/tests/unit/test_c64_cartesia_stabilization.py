"""
Component 64 — Cartesia TTS Stabilization tests.

Covers:
- Cartesia success returns ok=True, provider=cartesia, errorCode=""
- Cartesia timeout returns ok=False with errorCode=cartesia_timeout
- Cartesia HTTP 401 returns ok=False with errorCode=cartesia_http_401
- Cartesia network error returns ok=False with errorCode=cartesia_request_error
- Cartesia missing key returns ok=False with errorCode=cartesia_key_missing
- Cartesia empty audio returns ok=False
- System TTS fallback used when Cartesia fails
- ok=False response always has fallback="browser"
- CARTESIA_API_KEY never appears in any response
- next turn works after Cartesia failure (endpoint stays 200)
- runtime status always shows Cartesia tts_provider when configured
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import httpx as _httpx

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _cartesia_settings(mock_settings: MagicMock, *, api_key: str = "sk-test") -> None:
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


_FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 16 + b"data\x04\x00\x00\x00\x00\x00\x00\x00"


# ── Success path ──────────────────────────────────────────────────────────────

def test_cartesia_success_ok_true(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = _FAKE_WAV

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "Your copay is $30."})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "cartesia"
    assert data["voiceName"] == "Skylar"
    assert data["mimeType"] == "audio/wav"
    assert len(data["audioBase64"]) > 0
    assert data["errorCode"] == ""


def test_cartesia_success_api_key_not_in_response(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = _FAKE_WAV

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp):
        _cartesia_settings(ms, api_key="super-secret-cartesia-key")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert "super-secret-cartesia-key" not in res.text


# ── Timeout ───────────────────────────────────────────────────────────────────

def test_cartesia_timeout_error_code(client: TestClient) -> None:
    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post",
               side_effect=_httpx.TimeoutException("timed out")), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               side_effect=RuntimeError("no_say")):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["errorCode"] == "cartesia_timeout"
    assert data["fallback"] == "browser"
    assert "super-secret" not in res.text


def test_cartesia_timeout_uses_system_fallback_when_available(client: TestClient) -> None:
    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post",
               side_effect=_httpx.TimeoutException("timed out")), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               return_value=("UklGRg==", "Samantha", "audio/wav")):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "system"


# ── HTTP error codes ──────────────────────────────────────────────────────────

def test_cartesia_http_401_error_code(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.content = b'{"error": "Unauthorized"}'

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               side_effect=RuntimeError("no_say")):
        _cartesia_settings(ms, api_key="bad-key")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["errorCode"] == "cartesia_http_401"
    assert data["fallback"] == "browser"


def test_cartesia_http_500_error_code(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.content = b'{"error": "Internal Server Error"}'

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               side_effect=RuntimeError("no_say")):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["errorCode"] == "cartesia_http_500"


# ── Network error ─────────────────────────────────────────────────────────────

def test_cartesia_request_error_code(client: TestClient) -> None:
    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post",
               side_effect=_httpx.RequestError("connection refused")), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               side_effect=RuntimeError("no_say")):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["errorCode"] == "cartesia_request_error"


# ── Missing key ───────────────────────────────────────────────────────────────

def test_cartesia_missing_key_error_code(client: TestClient) -> None:
    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               side_effect=RuntimeError("no_say")):
        _cartesia_settings(ms, api_key="")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["errorCode"] == "cartesia_key_missing"


def test_cartesia_missing_key_falls_back_to_system(client: TestClient) -> None:
    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               return_value=("UklGRg==", "Samantha", "audio/wav")):
        _cartesia_settings(ms, api_key="")
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "system"


# ── Cancellation (empty audio body from Cartesia) ─────────────────────────────

def test_cartesia_empty_audio_falls_back(client: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b""

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp), \
         patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
               return_value=("UklGRg==", "Samantha", "audio/wav")):
        _cartesia_settings(ms)
        res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "system"


# ── Next-turn recovery (endpoint always returns 200) ─────────────────────────

def test_cartesia_failure_does_not_500(client: TestClient) -> None:
    """Any Cartesia failure must not result in a 5xx — UI must always be able to continue."""
    scenarios = [
        _httpx.TimeoutException("timeout"),
        _httpx.RequestError("refused"),
        RuntimeError("unexpected"),
    ]
    for exc in scenarios:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b""

        with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
             patch("voice_agent.api.v1.tts_synthesize.httpx.post", side_effect=exc), \
             patch("voice_agent.api.v1.tts_synthesize._system_synthesize",
                   side_effect=RuntimeError("no_say")):
            _cartesia_settings(ms)
            res = client.post("/api/v1/tts/synthesize", json={"text": "test"})

        assert res.status_code == 200, f"Got 5xx for: {exc}"
        assert res.json()["fallback"] == "browser"


def test_back_to_back_requests_both_succeed(client: TestClient) -> None:
    """Two consecutive TTS calls must both return 200 regardless of order."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = _FAKE_WAV

    with patch("voice_agent.api.v1.tts_synthesize.settings") as ms, \
         patch("voice_agent.api.v1.tts_synthesize.httpx.post", return_value=mock_resp):
        _cartesia_settings(ms)
        r1 = client.post("/api/v1/tts/synthesize", json={"text": "First answer."})
        r2 = client.post("/api/v1/tts/synthesize", json={"text": "Second answer."})

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["ok"] is True
    assert r2.json()["ok"] is True


# ── Runtime status ────────────────────────────────────────────────────────────

def test_runtime_status_shows_cartesia_as_primary(client: TestClient) -> None:
    with patch("voice_agent.api.v1.runtime_status.settings") as ms:
        ms.claimvoice_voice_runtime = "browser"
        ms.voice_agent_tts_provider = "cartesia"
        ms.cartesia_voice_name = "Skylar"
        ms.gemini_api_key = ""
        ms.gemini_live_model = "gemini-3.1-flash-live-preview"
        ms.gemini_live_voice = "Zephyr"
        res = client.get("/api/v1/runtime/status")

    assert res.status_code == 200
    data = res.json()
    assert data["tts_provider"] == "cartesia"
    assert data["tts_voice_name"] == "Skylar"
    assert "cartesia_api_key" not in res.text
    assert "CARTESIA_API_KEY" not in res.text


def test_runtime_status_gemini_not_default(client: TestClient) -> None:
    """When runtime=browser (default), Gemini should not appear as active."""
    with patch("voice_agent.api.v1.runtime_status.settings") as ms:
        ms.claimvoice_voice_runtime = "browser"
        ms.voice_agent_tts_provider = "cartesia"
        ms.cartesia_voice_name = "Skylar"
        ms.gemini_api_key = ""
        ms.gemini_live_model = "gemini-3.1-flash-live-preview"
        ms.gemini_live_voice = "Zephyr"
        res = client.get("/api/v1/runtime/status")

    data = res.json()
    assert data["runtime"] == "browser"
    assert "gemini-live-configured" not in data["runtime"]

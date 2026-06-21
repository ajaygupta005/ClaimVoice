"""Tests for GET /api/v1/runtime/status (Component 50)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_default_runtime_is_browser(client: TestClient) -> None:
    """Default config (no env overrides) must return runtime=browser."""
    with patch("voice_agent.api.v1.runtime_status.settings") as mock_settings:
        mock_settings.claimvoice_voice_runtime = "browser"
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_settings.gemini_live_voice = "Zephyr"
        mock_settings.voice_agent_tts_provider = "browser"
        mock_settings.cartesia_voice_name = "Skylar"
        res = client.get("/api/v1/runtime/status")
        assert res.status_code == 200
        data = res.json()
        assert data["runtime"] == "browser"
        # Key must never appear in the response
        assert "gemini_api_key" not in data
        assert "api_key" not in str(data).lower() or "gemini_api_key" not in data


def test_runtime_response_has_required_fields(client: TestClient) -> None:
    res = client.get("/api/v1/runtime/status")
    data = res.json()
    assert "runtime" in data
    assert "model" in data
    assert "voice" in data
    assert "note" in data


def test_gemini_live_with_key_returns_configured(client: TestClient) -> None:
    """When runtime=gemini-live and key is present, return gemini-live-configured."""
    with patch("voice_agent.api.v1.runtime_status.settings") as mock_settings, \
         patch("voice_agent.api.v1.runtime_status._gemini_sdk_available", return_value=True):
        mock_settings.claimvoice_voice_runtime = "gemini-live"
        mock_settings.gemini_api_key = "fake-key-abc123"
        mock_settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_settings.gemini_live_voice = "Zephyr"
        mock_settings.voice_agent_tts_provider = "browser"
        mock_settings.cartesia_voice_name = "Skylar"
        res = client.get("/api/v1/runtime/status")
        assert res.status_code == 200
        data = res.json()
        assert data["runtime"] == "gemini-live-configured"
        assert data["model"] == "gemini-3.1-flash-live-preview"
        assert data["voice"] == "Zephyr"
        # The key must never be echoed back
        assert "fake-key" not in str(data)


def test_gemini_live_with_key_but_missing_sdk_returns_unavailable(client: TestClient) -> None:
    """A key alone is not enough; the runtime is unavailable without google-genai."""
    with patch("voice_agent.api.v1.runtime_status.settings") as mock_settings, \
         patch("voice_agent.api.v1.runtime_status._gemini_sdk_available", return_value=False):
        mock_settings.claimvoice_voice_runtime = "gemini-live"
        mock_settings.gemini_api_key = "fake-key-abc123"
        mock_settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_settings.gemini_live_voice = "Zephyr"
        mock_settings.voice_agent_tts_provider = "browser"
        mock_settings.cartesia_voice_name = "Skylar"
        res = client.get("/api/v1/runtime/status")
        assert res.status_code == 200
        data = res.json()
        assert data["runtime"] == "gemini-live-unavailable"
        assert "google-genai" in data["note"]
        assert "fake-key" not in str(data)


def test_gemini_live_without_key_returns_unavailable(client: TestClient) -> None:
    """When runtime=gemini-live but key is missing, return gemini-live-unavailable."""
    with patch("voice_agent.api.v1.runtime_status.settings") as mock_settings:
        mock_settings.claimvoice_voice_runtime = "gemini-live"
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_settings.gemini_live_voice = "Zephyr"
        mock_settings.voice_agent_tts_provider = "browser"
        mock_settings.cartesia_voice_name = "Skylar"
        res = client.get("/api/v1/runtime/status")
        assert res.status_code == 200
        data = res.json()
        assert data["runtime"] == "gemini-live-unavailable"


def test_existing_agent_respond_unaffected(client: TestClient) -> None:
    """Adding the runtime endpoint must not break the answer pipeline."""
    res = client.post("/api/v1/agent/respond", json={"question": "What is my copay?"})
    assert res.status_code == 200
    assert res.json()["answer"]

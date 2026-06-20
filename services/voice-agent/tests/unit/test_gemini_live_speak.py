"""Tests for POST /api/v1/gemini-live/speak and speak_text bridge method (C53)."""

from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from voice_agent.main import app
from voice_agent.streaming.gemini_live_bridge import (
    MockGeminiLiveSession,
    _UnavailableBridge,
    _UnavailableSession,
)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── HTTP endpoint ─────────────────────────────────────────────────────────────

def test_speak_returns_unavailable_when_bridge_not_configured(client: TestClient) -> None:
    """Default env has no Gemini key — endpoint must return ok=False."""
    res = client.post("/api/v1/gemini-live/speak", json={"text": "Your copay is $30."})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["fallback"] == "browser"
    # Key must not appear
    assert "gemini_api_key" not in str(data)


def test_speak_rejects_empty_text(client: TestClient) -> None:
    res = client.post("/api/v1/gemini-live/speak", json={"text": ""})
    assert res.status_code == 422


def test_speak_rejects_missing_text(client: TestClient) -> None:
    res = client.post("/api/v1/gemini-live/speak", json={})
    assert res.status_code == 422


def test_speak_with_mock_bridge_returns_audio(client: TestClient) -> None:
    """When the bridge is available (mocked), the endpoint must return ok=True with audio."""
    from voice_agent.streaming.gemini_live_bridge import MockGeminiLiveBridge

    with patch("voice_agent.api.v1.gemini_live_speak.build_gemini_bridge") as mock_factory:
        mock_factory.return_value = MockGeminiLiveBridge()
        res = client.post("/api/v1/gemini-live/speak", json={"text": "Your copay is $30."})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider"] == "gemini-live"
    assert data["mimeType"] == "audio/wav"
    assert len(data["audioBase64"]) > 0
    assert "gemini_api_key" not in str(data)


def test_speak_existing_agent_unaffected(client: TestClient) -> None:
    """Adding the speak endpoint must not break the main answer pipeline."""
    res = client.post("/api/v1/agent/respond", json={"question": "What is my copay?"})
    assert res.status_code == 200
    assert res.json()["answer"]


# ── Bridge speak_text method ──────────────────────────────────────────────────

def test_unavailable_session_speak_text_returns_empty() -> None:
    async def _run() -> bytes:
        session = _UnavailableSession("no key")
        return await session.speak_text("hello")
    result = asyncio.run(_run())
    assert result == b""


def test_mock_session_speak_text_returns_pcm() -> None:
    async def _run() -> bytes:
        session = MockGeminiLiveSession()
        return await session.speak_text("Your copay is $30.")
    pcm = asyncio.run(_run())
    # MockGeminiLiveSession returns 100 ms of silence = 2400 PCM16 samples = 4800 bytes
    assert len(pcm) > 0
    assert len(pcm) % 2 == 0  # PCM16 = even byte count


def test_mock_session_speak_text_pcm_is_silence() -> None:
    """The mock must return all-zero (silent) PCM so tests don't get noise."""
    async def _run() -> bytes:
        session = MockGeminiLiveSession()
        return await session.speak_text("test")
    pcm = asyncio.run(_run())
    assert all(b == 0 for b in pcm)


def test_wav_header_is_valid() -> None:
    """The WAV container produced by _pcm16_to_wav must have correct RIFF header."""
    from voice_agent.api.v1.gemini_live_speak import _pcm16_to_wav
    pcm = b"\x00\x00" * 24_000  # 1 s of silence
    wav = _pcm16_to_wav(pcm)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "
    assert wav[36:40] == b"data"

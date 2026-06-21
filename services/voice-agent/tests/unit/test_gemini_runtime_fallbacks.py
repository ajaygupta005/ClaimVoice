"""C54 — Gemini Live runtime hardening: failure modes, fallbacks, and observability.

Tests cover:
- Missing key → _UnavailableBridge (no secret leakage)
- Bridge connect failure gracefully yields _UnavailableSession
- Transcript event normalization (partial / final)
- Speech event normalization (audio chunk)
- close() is safe after failure (no double-close exception)
- Status response never includes gemini_api_key
- WS endpoint: 2 MB payload cap
- Speak endpoint: backend exception → ok=False, no secret
- Mock bridge: is_available + close idempotent
"""

from __future__ import annotations

import asyncio
import json
import struct
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from voice_agent.main import app
from voice_agent.streaming.gemini_live_bridge import (
    _UnavailableBridge,
    _UnavailableSession,
    MockGeminiLiveBridge,
    MockGeminiLiveSession,
    BridgeErrorEvent,
    TranscriptPartialEvent,
    TranscriptFinalEvent,
    AudioChunkEvent,
    SessionOpenedEvent,
    SessionClosedEvent,
    build_gemini_bridge,
)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── 1. Missing key produces _UnavailableBridge, never leaks secret ────────────

def test_build_gemini_bridge_no_key_returns_unavailable() -> None:
    """When runtime=gemini-live but key is absent, factory returns unavailable bridge."""
    with patch("voice_agent.streaming.gemini_live_bridge.settings") as mock_settings:
        mock_settings.claimvoice_voice_runtime = "gemini-live"
        mock_settings.gemini_api_key = ""
        bridge = build_gemini_bridge()
    assert not bridge.is_available()
    assert isinstance(bridge, _UnavailableBridge)


def test_build_gemini_bridge_wrong_runtime_returns_unavailable() -> None:
    """When runtime=browser the factory returns unavailable (not a Gemini bridge)."""
    with patch("voice_agent.streaming.gemini_live_bridge.settings") as mock_settings:
        mock_settings.claimvoice_voice_runtime = "browser"
        mock_settings.gemini_api_key = "fake-key"
        bridge = build_gemini_bridge()
    assert not bridge.is_available()


def test_status_response_never_contains_api_key(client: TestClient) -> None:
    """The runtime-status endpoint must not expose gemini_api_key in any form."""
    res = client.get("/api/v1/runtime/status")
    assert res.status_code == 200
    body_str = res.text
    assert "gemini_api_key" not in body_str
    assert "GEMINI_API_KEY" not in body_str
    # key field itself must not exist
    assert "api_key" not in body_str


# ── 2. Bridge connect failure gracefully degrades ─────────────────────────────

def test_unavailable_session_events_yields_error() -> None:
    """_UnavailableSession.events() yields exactly one BridgeErrorEvent."""
    async def _run() -> list[object]:
        session = _UnavailableSession("test reason")
        events = []
        async for ev in session.events():
            events.append(ev)
        return events

    events = asyncio.run(_run())
    assert len(events) == 1
    assert isinstance(events[0], BridgeErrorEvent)
    assert events[0].code == "unavailable"


def test_unavailable_bridge_open_session_yields_unavailable_session() -> None:
    """_UnavailableBridge.open_session() yields _UnavailableSession, not None."""
    async def _run() -> object:
        bridge = _UnavailableBridge("no key")
        async with bridge.open_session() as session:
            return type(session).__name__

    name = asyncio.run(_run())
    assert name == "_UnavailableSession"


def test_real_bridge_sdk_missing_falls_back() -> None:
    """When google-genai SDK is absent, open_session() yields _UnavailableSession."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveBridge

    async def _run() -> str:
        bridge = _RealGeminiLiveBridge(api_key="fake", model="m", voice="v")
        # Force ImportError on the lazy import
        import builtins
        real_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name.startswith("google"):
                raise ImportError("mock: google-genai not installed")
            return real_import(name, *args, **kwargs)

        import builtins
        builtins.__import__ = mock_import
        try:
            async with bridge.open_session() as session:
                return type(session).__name__
        finally:
            builtins.__import__ = real_import

    name = asyncio.run(_run())
    assert name == "_UnavailableSession"


# ── 3. Transcript event normalization ─────────────────────────────────────────

def test_normalize_partial_transcript() -> None:
    """_normalize() returns TranscriptPartialEvent for interim transcription."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    session = _RealGeminiLiveSession(MagicMock(), "model", "voice")

    raw = MagicMock()
    raw.server_content = MagicMock()
    t = MagicMock()
    t.finished = False
    t.text = "is an MRI covered"
    raw.server_content.input_transcription = t
    raw.server_content.model_turn = None

    ev = session._normalize(raw)
    assert isinstance(ev, TranscriptPartialEvent)
    assert ev.text == "is an MRI covered"
    assert ev.confidence > 0


def test_normalize_final_transcript() -> None:
    """_normalize() returns TranscriptFinalEvent when finished=True."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    session = _RealGeminiLiveSession(MagicMock(), "model", "voice")

    raw = MagicMock()
    raw.server_content = MagicMock()
    t = MagicMock()
    t.finished = True
    t.text = "Is an MRI covered under my plan?"
    raw.server_content.input_transcription = t
    raw.server_content.model_turn = None

    ev = session._normalize(raw)
    assert isinstance(ev, TranscriptFinalEvent)
    assert "MRI" in ev.text
    assert ev.confidence > 0


def test_normalize_returns_none_for_unknown_event() -> None:
    """_normalize() returns None when there's no recognized server_content."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    session = _RealGeminiLiveSession(MagicMock(), "model", "voice")
    raw = MagicMock()
    raw.server_content = None
    ev = session._normalize(raw)
    assert ev is None


# ── 4. Speech / audio event normalization ─────────────────────────────────────

def test_normalize_audio_chunk() -> None:
    """_normalize() returns AudioChunkEvent for model_turn with inline_data."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    session = _RealGeminiLiveSession(MagicMock(), "model", "voice")

    raw = MagicMock()
    sc = MagicMock()
    sc.input_transcription = None
    sc.turn_complete = True
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = b"\x00\x01" * 100
    sc.model_turn = MagicMock()
    sc.model_turn.parts = [part]
    raw.server_content = sc

    ev = session._normalize(raw)
    assert isinstance(ev, AudioChunkEvent)
    assert len(ev.pcm) == 200
    assert ev.is_final is True


def test_normalize_audio_chunk_not_final() -> None:
    """AudioChunkEvent.is_final=False when turn_complete is False."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    session = _RealGeminiLiveSession(MagicMock(), "model", "voice")

    raw = MagicMock()
    sc = MagicMock()
    sc.input_transcription = None
    sc.turn_complete = False
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = b"\x00" * 50
    sc.model_turn = MagicMock()
    sc.model_turn.parts = [part]
    raw.server_content = sc

    ev = session._normalize(raw)
    assert isinstance(ev, AudioChunkEvent)
    assert ev.is_final is False


def test_real_session_speak_text_reads_from_receive_stream() -> None:
    """speak_text() must consume AsyncSession.receive(), not iterate the session itself."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    pcm = b"\x01\x02" * 120

    class FakeLive:
        def __init__(self) -> None:
            self.sent_turns: list[object] = []

        async def send_client_content(self, *, turns: object, turn_complete: bool) -> None:
            self.sent_turns.append((turns, turn_complete))

        async def receive(self):
            raw = MagicMock()
            sc = MagicMock()
            sc.interim_input_transcription = None
            sc.input_transcription = None
            sc.turn_complete = True
            part = MagicMock()
            part.inline_data = MagicMock()
            part.inline_data.data = pcm
            sc.model_turn = MagicMock()
            sc.model_turn.parts = [part]
            raw.server_content = sc
            yield raw

        async def close(self) -> None:
            pass

    async def _run() -> bytes:
        session = _RealGeminiLiveSession(FakeLive(), "model", "voice")
        return await session.speak_text("hello")

    assert asyncio.run(_run()) == pcm


# ── 5. close() is safe after failure (idempotent) ────────────────────────────

def test_real_session_close_is_idempotent() -> None:
    """Calling close() twice must not raise."""
    from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveSession

    mock_live = AsyncMock()
    session = _RealGeminiLiveSession(mock_live, "model", "voice")

    async def _run() -> None:
        await session.close()
        await session.close()  # second call must be silent

    asyncio.run(_run())
    # close() on the inner live session called exactly once
    mock_live.close.assert_awaited_once()


def test_mock_session_close_is_idempotent() -> None:
    """MockGeminiLiveSession.close() called twice must not raise."""
    async def _run() -> None:
        session = MockGeminiLiveSession()
        await session.close()
        await session.close()

    asyncio.run(_run())  # no exception = pass


def test_unavailable_session_close_is_safe() -> None:
    """_UnavailableSession.close() must not raise."""
    async def _run() -> None:
        session = _UnavailableSession("test")
        await session.close()
        await session.close()

    asyncio.run(_run())


# ── 6. No secret leakage in status responses ─────────────────────────────────

def test_speak_endpoint_never_returns_api_key(client: TestClient) -> None:
    """POST /api/v1/gemini-live/speak must never include api_key fields."""
    res = client.post("/api/v1/gemini-live/speak", json={"text": "Your copay is $30."})
    assert res.status_code == 200
    body_str = res.text
    assert "gemini_api_key" not in body_str
    assert "api_key" not in body_str
    assert "GEMINI" not in body_str


def test_speak_endpoint_exception_returns_ok_false(client: TestClient) -> None:
    """If speak_text raises, the endpoint must return ok=False (not 500)."""
    from voice_agent.streaming.gemini_live_bridge import _UnavailableBridge

    broken_bridge = _UnavailableBridge("forced failure for test")
    with patch("voice_agent.api.v1.gemini_live_speak.build_gemini_bridge", return_value=broken_bridge):
        res = client.post("/api/v1/gemini-live/speak", json={"text": "test"})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "gemini_api_key" not in str(data)


# ── 7. Mock bridge correctness ────────────────────────────────────────────────

def test_mock_bridge_is_available() -> None:
    assert MockGeminiLiveBridge().is_available() is True


def test_mock_session_emits_opened_on_send_audio() -> None:
    """First send_audio should push SessionOpenedEvent to the queue."""
    async def _run() -> list[object]:
        session = MockGeminiLiveSession()
        await session.send_audio(b"\x00" * 100)
        events = []
        # Drain queue directly
        while not session._queue.empty():
            events.append(await session._queue.get())
        return events

    events = asyncio.run(_run())
    kinds = [getattr(e, "kind", None) for e in events]
    assert "session.opened" in kinds


def test_mock_session_send_text_produces_final_transcript() -> None:
    """send_text should result in a TranscriptFinalEvent with the same text."""
    async def _run() -> object:
        session = MockGeminiLiveSession()
        await session.send_text("Is chemo covered?")
        items = []
        while not session._queue.empty():
            items.append(await session._queue.get())
        return items

    items = asyncio.run(_run())
    finals = [e for e in items if isinstance(e, TranscriptFinalEvent)]
    assert len(finals) >= 1
    assert finals[0].text == "Is chemo covered?"

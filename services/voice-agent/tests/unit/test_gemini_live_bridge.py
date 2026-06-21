"""Tests for the Gemini Live session bridge (Component 51)."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import patch

from voice_agent.streaming.gemini_live_bridge import (
    AudioChunkEvent,
    BridgeErrorEvent,
    GeminiLiveBridge,
    MockGeminiLiveBridge,
    MockGeminiLiveSession,
    SessionClosedEvent,
    SessionOpenedEvent,
    TranscriptFinalEvent,
    TranscriptPartialEvent,
    _UnavailableBridge,
    build_gemini_bridge,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _collect_events(session, limit: int = 10) -> list:
    events = []
    async for ev in session.events():
        events.append(ev)
        if len(events) >= limit:
            break
    return events


# ── Factory tests ─────────────────────────────────────────────────────────────

def test_missing_key_returns_unavailable_bridge() -> None:
    """When GEMINI_API_KEY is absent, factory must return an unavailable bridge."""
    with patch("voice_agent.streaming.gemini_live_bridge.settings") as mock_cfg:
        mock_cfg.claimvoice_voice_runtime = "gemini-live"
        mock_cfg.gemini_api_key = ""
        mock_cfg.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_cfg.gemini_live_voice = "Zephyr"
        bridge = build_gemini_bridge()
    assert isinstance(bridge, _UnavailableBridge)
    assert not bridge.is_available()


def test_non_gemini_runtime_returns_unavailable_bridge() -> None:
    """When runtime != gemini-live, factory returns unavailable regardless of key."""
    with patch("voice_agent.streaming.gemini_live_bridge.settings") as mock_cfg:
        mock_cfg.claimvoice_voice_runtime = "browser"
        mock_cfg.gemini_api_key = "some-key"
        bridge = build_gemini_bridge()
    assert isinstance(bridge, _UnavailableBridge)
    assert not bridge.is_available()


def test_key_present_returns_real_bridge() -> None:
    """When runtime=gemini-live and key is set, factory returns a configured real bridge."""
    with patch("voice_agent.streaming.gemini_live_bridge.settings") as mock_cfg:
        mock_cfg.claimvoice_voice_runtime = "gemini-live"
        mock_cfg.gemini_api_key = "fake-key-xyz"
        mock_cfg.gemini_live_model = "gemini-3.1-flash-live-preview"
        mock_cfg.gemini_live_voice = "Zephyr"
        from voice_agent.streaming.gemini_live_bridge import _RealGeminiLiveBridge
        bridge = build_gemini_bridge()
    assert isinstance(bridge, _RealGeminiLiveBridge)
    assert bridge.is_available()


# ── Unavailable session ───────────────────────────────────────────────────────

def test_unavailable_session_emits_error_event() -> None:
    """open_session() on an unavailable bridge yields a BridgeErrorEvent."""
    async def _run() -> None:
        bridge = _UnavailableBridge("no key")
        async with bridge.open_session() as session:
            events = []
            async for ev in session.events():
                events.append(ev)
                break  # one event is enough
        assert len(events) == 1
        assert isinstance(events[0], BridgeErrorEvent)
        assert events[0].code == "unavailable"

    asyncio.run(_run())


# ── Mock session ──────────────────────────────────────────────────────────────

def test_mock_session_open_emits_session_opened() -> None:
    async def _run() -> list:
        session = MockGeminiLiveSession()
        events: list = []

        async def consume() -> None:
            async for ev in session.events():
                events.append(ev)
                if isinstance(ev, SessionClosedEvent):
                    break

        t = asyncio.create_task(consume())
        await asyncio.sleep(0.02)
        await session.close()
        await t
        return events

    events = asyncio.run(_run())
    kinds = [e.kind for e in events]
    assert "session.opened" in kinds
    assert "session.closed" in kinds


def test_mock_session_send_text_emits_transcript_final() -> None:
    async def _run() -> TranscriptFinalEvent | None:
        session = MockGeminiLiveSession()
        final: TranscriptFinalEvent | None = None

        async def consume() -> None:
            nonlocal final
            async for ev in session.events():
                if isinstance(ev, TranscriptFinalEvent):
                    final = ev
                    break

        t = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        await session.send_text("Is my MRI covered?")
        await asyncio.sleep(0.05)
        await session.close()
        await t
        return final

    result = asyncio.run(_run())
    assert result is not None
    assert result.kind == "transcript.final"
    assert result.text == "Is my MRI covered?"
    assert result.confidence == 0.99


def test_mock_session_send_audio_emits_partial_transcript() -> None:
    async def _run() -> list:
        session = MockGeminiLiveSession()
        partials: list = []

        async def consume() -> None:
            async for ev in session.events():
                if isinstance(ev, TranscriptPartialEvent):
                    partials.append(ev)
                    break

        t = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        await session.send_audio(b"\x00" * 1024)
        await asyncio.sleep(0.05)
        await session.close()
        await t
        return partials

    partials = asyncio.run(_run())
    assert len(partials) >= 1
    assert partials[0].kind == "transcript.partial"


def test_mock_session_close_is_idempotent() -> None:
    """Calling close() multiple times must not raise."""
    async def _run() -> None:
        session = MockGeminiLiveSession()
        await session.close()
        await session.close()
        await session.close()

    asyncio.run(_run())  # no exception = pass


def test_mock_bridge_is_available() -> None:
    bridge = MockGeminiLiveBridge()
    assert bridge.is_available() is True


def test_mock_bridge_open_session_yields_session() -> None:
    async def _run() -> None:
        bridge = MockGeminiLiveBridge()
        async with bridge.open_session() as session:
            assert isinstance(session, MockGeminiLiveSession)

    asyncio.run(_run())


# ── Event type checks ─────────────────────────────────────────────────────────

def test_normalized_event_kind_fields() -> None:
    """All event dataclasses must have the correct literal kind field."""
    assert SessionOpenedEvent().kind == "session.opened"
    assert SessionClosedEvent().kind == "session.closed"
    assert TranscriptPartialEvent().kind == "transcript.partial"
    assert TranscriptFinalEvent().kind == "transcript.final"
    assert AudioChunkEvent().kind == "audio.chunk"
    assert BridgeErrorEvent().kind == "error"


def test_audio_chunk_event_defaults() -> None:
    ev = AudioChunkEvent(pcm=b"\x01\x02", sample_rate=16_000, is_final=True)
    assert ev.pcm == b"\x01\x02"
    assert ev.sample_rate == 16_000
    assert ev.is_final is True

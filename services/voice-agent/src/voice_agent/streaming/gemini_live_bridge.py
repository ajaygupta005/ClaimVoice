"""Gemini Live session bridge (Component 51).

Architecture
------------
This module provides a thin abstraction over the Gemini Live SDK so that:

- The rest of the voice-agent codebase sees only normalized internal events.
- Vendor-specific SDK types never leak past this file.
- The module is importable (and testable) without a GEMINI_API_KEY or the
  google-genai SDK installed.
- Gemini is only a voice I/O runtime — it does NOT answer insurance questions,
  call ClaimVoice tools, or bypass Claude / the hallucination guard.

Usage
-----
    from voice_agent.streaming.gemini_live_bridge import build_gemini_bridge

    bridge = build_gemini_bridge()     # returns real or mock session manager
    async with bridge.open_session() as session:
        await session.send_text("hello")
        async for event in session.events():
            if isinstance(event, TranscriptFinalEvent):
                ...           # hand transcript to ClaimVoice agent graph
            elif isinstance(event, AudioChunkEvent):
                ...           # forward PCM to browser / telephony
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from voice_agent.core.config import settings
from voice_agent.lib.logger import logger

# ── Normalized event types ────────────────────────────────────────────────────


@dataclass(frozen=True)
class SessionOpenedEvent:
    """Emitted once when the Gemini Live session is established."""
    kind: Literal["session.opened"] = field(default="session.opened", init=False)
    session_id: str = ""


@dataclass(frozen=True)
class SessionClosedEvent:
    """Emitted when the session ends (normally or due to an error)."""
    kind: Literal["session.closed"] = field(default="session.closed", init=False)
    reason: str = "normal"


@dataclass(frozen=True)
class TranscriptPartialEvent:
    """Interim ASR text from Gemini Live (may change)."""
    kind: Literal["transcript.partial"] = field(default="transcript.partial", init=False)
    text: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class TranscriptFinalEvent:
    """Final ASR text from Gemini Live. Hand this to the ClaimVoice agent graph."""
    kind: Literal["transcript.final"] = field(default="transcript.final", init=False)
    text: str = ""
    confidence: float = 0.0
    duration_ms: int = 0


@dataclass(frozen=True)
class AudioChunkEvent:
    """PCM16 audio output chunk from Gemini Live (TTS / voice response)."""
    kind: Literal["audio.chunk"] = field(default="audio.chunk", init=False)
    # Raw PCM16 LE bytes at the sample rate negotiated during session open.
    pcm: bytes = b""
    sample_rate: int = 24_000
    is_final: bool = False


@dataclass(frozen=True)
class BridgeErrorEvent:
    """Normalized error — vendor detail is logged but not forwarded."""
    kind: Literal["error"] = field(default="error", init=False)
    code: str = "unknown"
    message: str = ""


GeminiLiveEvent = (
    SessionOpenedEvent
    | SessionClosedEvent
    | TranscriptPartialEvent
    | TranscriptFinalEvent
    | AudioChunkEvent
    | BridgeErrorEvent
)


# ── Bridge interface ──────────────────────────────────────────────────────────


class GeminiLiveSession(ABC):
    """A single Gemini Live session.  Obtained via GeminiLiveBridge.open_session()."""

    @abstractmethod
    async def send_audio(self, pcm: bytes) -> None:
        """Send a PCM16 audio frame to Gemini Live (from the browser mic)."""

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Send a text turn to Gemini Live (for testing / typed input)."""

    @abstractmethod
    async def speak_text(self, text: str) -> bytes:
        """Request Gemini Live to synthesise `text` as speech.

        Returns concatenated raw PCM16 LE bytes (24 kHz, 1 channel).
        Returns empty bytes if synthesis fails or is unavailable.
        The text must be the final ClaimVoice-grounded answer — Gemini
        only voices the answer, it never generates or modifies it.
        """

    @abstractmethod
    def events(self) -> AsyncIterator[GeminiLiveEvent]:
        """Async iterator of normalized events from the session."""

    @abstractmethod
    async def close(self) -> None:
        """Close the session.  Safe to call multiple times."""


class GeminiLiveBridge(ABC):
    """Factory that creates and manages Gemini Live sessions."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the bridge is properly configured."""

    @abstractmethod
    @asynccontextmanager
    async def open_session(self) -> AsyncIterator[GeminiLiveSession]:
        """Context manager that yields an open session and closes it on exit."""


# ── Unavailable sentinel ──────────────────────────────────────────────────────


class _UnavailableBridge(GeminiLiveBridge):
    """Returned by build_gemini_bridge() when the key or SDK is missing."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def is_available(self) -> bool:
        return False

    @asynccontextmanager
    async def open_session(self) -> AsyncIterator[GeminiLiveSession]:  # type: ignore[override]
        yield _UnavailableSession(self._reason)


class _UnavailableSession(GeminiLiveSession):
    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def send_audio(self, pcm: bytes) -> None:
        pass

    async def send_text(self, text: str) -> None:
        pass

    async def speak_text(self, text: str) -> bytes:
        return b""

    async def events(self) -> AsyncIterator[GeminiLiveEvent]:  # type: ignore[override]
        yield BridgeErrorEvent(code="unavailable", message=self._reason)

    async def close(self) -> None:
        pass


# ── Mock bridge (for tests and dev without a key) ────────────────────────────


class MockGeminiLiveSession(GeminiLiveSession):
    """Deterministic mock that emits scripted events without network calls."""

    def __init__(self, session_id: str = "mock-session-001") -> None:
        self._session_id = session_id
        self._closed = False
        self._queue: asyncio.Queue[GeminiLiveEvent | None] = asyncio.Queue()
        self._opened = False

    async def _enqueue_opened(self) -> None:
        if not self._opened:
            self._opened = True
            await self._queue.put(SessionOpenedEvent(session_id=self._session_id))

    async def send_audio(self, pcm: bytes) -> None:
        """Simulate receiving audio — emit a partial transcript after 3 frames."""
        await self._enqueue_opened()
        await self._queue.put(
            TranscriptPartialEvent(text="is an MRI covered", confidence=0.72)
        )

    async def send_text(self, text: str) -> None:
        """Simulate text input — echo as a final transcript."""
        await self._enqueue_opened()
        await self._queue.put(
            TranscriptFinalEvent(text=text, confidence=0.99, duration_ms=500)
        )

    async def speak_text(self, text: str) -> bytes:
        """Simulate TTS — return minimal valid PCM16 silence (100 ms @ 24 kHz)."""
        samples = 24_000 // 10  # 100 ms worth of silence
        return b"\x00\x00" * samples

    async def events(self) -> AsyncIterator[GeminiLiveEvent]:  # type: ignore[override]
        await self._enqueue_opened()
        while not self._closed:
            try:
                ev = await asyncio.wait_for(self._queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            if ev is None:
                break
            yield ev

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._queue.put(SessionClosedEvent(reason="normal"))
            await self._queue.put(None)  # sentinel to break events() loop


class MockGeminiLiveBridge(GeminiLiveBridge):
    def is_available(self) -> bool:
        return True

    @asynccontextmanager
    async def open_session(self) -> AsyncIterator[GeminiLiveSession]:  # type: ignore[override]
        session = MockGeminiLiveSession()
        try:
            yield session
        finally:
            await session.close()


# ── Real bridge (lazy-imports google-genai SDK) ───────────────────────────────


class _RealGeminiLiveSession(GeminiLiveSession):
    """
    Wraps the google.genai live session.

    The google-genai SDK is lazy-imported so the module remains importable
    in fallback/test environments. If the SDK is absent, the runtime status
    reports Gemini Live unavailable and the UI falls back to browser voice.

    Gemini Live is used exclusively as a voice I/O layer:
    - audio in  → ASR transcript → hand to ClaimVoice agent graph
    - audio out ← TTS synthesis  ← final Claude-grounded answer text
    Gemini never sees insurance questions or tool results directly.
    """

    def __init__(self, live_session: object, model: str, voice: str) -> None:
        self._live = live_session  # google.genai.live.LiveSession (opaque)
        self._model = model
        self._voice = voice
        self._closed = False
        self._queue: asyncio.Queue[GeminiLiveEvent | None] = asyncio.Queue()

    async def send_audio(self, pcm: bytes) -> None:
        try:
            # google.genai live API: send_realtime_input with audio blob
            await self._live.send_realtime_input(  # type: ignore[attr-defined]
                audio={"data": pcm, "mime_type": "audio/pcm;rate=16000"}
            )
        except Exception as exc:
            logger.warning("gemini_live.send_audio_error", error=str(exc))
            await self._queue.put(BridgeErrorEvent(code="send_audio_failed", message=str(exc)))

    async def send_text(self, text: str) -> None:
        try:
            await self._live.send_client_content(  # type: ignore[attr-defined]
                turns=[{"role": "user", "parts": [{"text": text}]}],
                turn_complete=True,
            )
        except Exception as exc:
            logger.warning("gemini_live.send_text_error", error=str(exc))
            await self._queue.put(BridgeErrorEvent(code="send_text_failed", message=str(exc)))

    async def speak_text(self, text: str) -> bytes:
        """Send answer text to Gemini Live for TTS and collect all audio chunks.

        Opens a fresh turn with turn_complete=True so Gemini speaks the text
        without interpreting it as a user question. Collects all AudioChunkEvent
        PCM bytes until turn_complete, then returns the concatenation.
        """
        pcm_parts: list[bytes] = []
        logger.info("gemini_live.speak_text_start", text_len=len(text))
        try:
            await self._live.send_client_content(  # type: ignore[attr-defined]
                turns=[{"role": "user", "parts": [{"text": text}]}],
                turn_complete=True,
            )
            async for raw in self._live.receive():  # type: ignore[attr-defined]
                ev = self._normalize(raw)
                if isinstance(ev, AudioChunkEvent):
                    pcm_parts.append(ev.pcm)
                    if ev.is_final:
                        break
                elif isinstance(ev, (SessionClosedEvent, BridgeErrorEvent)):
                    break
        except Exception as exc:
            logger.warning(f"gemini_live.speak_text_error: {type(exc).__name__}: {exc}")
        total_bytes = sum(len(p) for p in pcm_parts)
        logger.info("gemini_live.speak_text_done", pcm_bytes=total_bytes)
        return b"".join(pcm_parts)

    async def events(self) -> AsyncIterator[GeminiLiveEvent]:  # type: ignore[override]
        yield SessionOpenedEvent(session_id=id(self._live).__str__())
        try:
            async for raw in self._live.receive():  # type: ignore[attr-defined]
                event = self._normalize(raw)
                if event is not None:
                    yield event
        except Exception as exc:
            # Log vendor detail at DEBUG only — never forward raw SDK error text upward
            logger.debug("gemini_live.receive_error", error=str(exc))
            yield BridgeErrorEvent(code="receive_error", message="Gemini Live receive failed")
        finally:
            yield SessionClosedEvent(reason="stream_end")

    def _normalize(self, raw: object) -> GeminiLiveEvent | None:
        """Map a vendor SDK response object to a normalized event."""
        try:
            # google.genai ServerContent carries server_content.model_turn.parts
            sc = getattr(raw, "server_content", None)
            if sc is None:
                return None

            # Low-latency transcription preview while the user is still speaking.
            if getattr(sc, "interim_input_transcription", None) is not None:
                t = sc.interim_input_transcription
                raw_text = getattr(t, "text", "")
                text = raw_text if isinstance(raw_text, str) else ""
                if text:
                    return TranscriptPartialEvent(text=text, confidence=0.7)

            # Final/regular transcription (input audio → text)
            if getattr(sc, "input_transcription", None) is not None:
                t = sc.input_transcription
                raw_text = getattr(t, "text", "")
                text = raw_text if isinstance(raw_text, str) else ""
                if getattr(t, "finished", False):
                    return TranscriptFinalEvent(
                        text=text,
                        confidence=0.9,
                        duration_ms=0,
                    )
                if text:
                    return TranscriptPartialEvent(text=text, confidence=0.7)

            # Audio output (TTS from Gemini — used only for ClaimVoice-approved answers)
            model_turn = getattr(sc, "model_turn", None)
            if model_turn:
                for part in getattr(model_turn, "parts", []):
                    blob = getattr(part, "inline_data", None)
                    if blob and getattr(blob, "data", None):
                        return AudioChunkEvent(
                            pcm=blob.data,
                            sample_rate=24_000,
                            is_final=bool(getattr(sc, "turn_complete", False)),
                        )

            return None
        except Exception as exc:
            logger.debug("gemini_live.normalize_error", error=str(exc))
            return None

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                await self._live.close()  # type: ignore[attr-defined]
            except Exception:
                pass


class _RealGeminiLiveBridge(GeminiLiveBridge):
    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice

    def is_available(self) -> bool:
        return bool(self._api_key)

    @asynccontextmanager
    async def open_session(self) -> AsyncIterator[GeminiLiveSession]:  # type: ignore[override]
        # Lazy-import to keep the module importable without the SDK installed
        try:
            from google import genai as _genai  # type: ignore[import-untyped]
            from google.genai import types as _types  # type: ignore[import-untyped]
        except ImportError as exc:
            logger.error("gemini_live.sdk_missing", error=str(exc))
            yield _UnavailableSession("google-genai SDK not installed")
            return

        client = _genai.Client(api_key=self._api_key)
        config = _types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=_types.SpeechConfig(
                voice_config=_types.VoiceConfig(
                    prebuilt_voice_config=_types.PrebuiltVoiceConfig(
                        voice_name=self._voice
                    )
                )
            ),
            input_audio_transcription=_types.AudioTranscriptionConfig(),
        )

        session_obj = None
        try:
            async with client.aio.live.connect(model=self._model, config=config) as live:
                session_obj = _RealGeminiLiveSession(live, self._model, self._voice)
                logger.info(
                    "gemini_live.session_opened",
                    model=self._model,
                    voice=self._voice,
                    # api_key deliberately omitted
                )
                try:
                    yield session_obj
                finally:
                    await session_obj.close()
        except Exception as exc:
            logger.error("gemini_live.open_error", error=str(exc))
            if session_obj is None:
                yield _UnavailableSession(f"session open failed: {type(exc).__name__}")


# ── Factory ───────────────────────────────────────────────────────────────────


def build_gemini_bridge() -> GeminiLiveBridge:
    """Return a bridge configured from settings.

    - Real bridge when CLAIMVOICE_VOICE_RUNTIME=gemini-live and GEMINI_API_KEY is set.
    - MockGeminiLiveBridge when CLAIMVOICE_VOICE_RUNTIME=gemini-live but key is absent
      (allows integration tests without credentials).
    - _UnavailableBridge for all other runtime modes.
    """
    if settings.claimvoice_voice_runtime != "gemini-live":
        return _UnavailableBridge("voice runtime is not gemini-live")

    if not settings.gemini_api_key:
        logger.warning("gemini_live.key_missing", note="falling back to mock bridge")
        return _UnavailableBridge("GEMINI_API_KEY not configured")

    return _RealGeminiLiveBridge(
        api_key=settings.gemini_api_key,
        model=settings.gemini_live_model,
        voice=settings.gemini_live_voice,
    )

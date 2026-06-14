"""
TTS adapter interface and mock implementation.

StreamingTTS protocol
---------------------
  synthesize(text, call_sid, stream_sid) -> list[TtsAudioEvent]

  Accepts plain text and returns one or more TtsAudioEvent objects — one
  per sentence-level chunk. The last event always has isFinal=True.
  Returns a single TtsErrorEvent (in a list) for empty / unsafe input.

MockStreamingTTS
----------------
  Deterministic stand-in — no network calls. Generates silent PCM16 24 kHz
  buffers scaled to a realistic duration estimate (≈ 100 ms per word at 150
  words-per-minute speaking rate). Real Cartesia / ElevenLabs / OpenAI TTS
  adapters can replace this by implementing the same interface.

Chunking
--------
  Long answers are split on sentence boundaries (`. `, `? `, `! `) so each
  chunk maps naturally to one TTS synthesis call, which keeps latency low
  when streaming audio back to the caller.
"""

from __future__ import annotations

import base64
import re
import struct
from abc import ABC, abstractmethod

from voice_agent.schemas.tts import TtsAudioEvent, TtsErrorEvent

# ── Constants ─────────────────────────────────────────────────────────────────

_SAMPLE_RATE = 24_000        # Hz
_BYTES_PER_SAMPLE = 2        # int16 LE
_WORDS_PER_MINUTE = 150
_MS_PER_WORD = 60_000 / _WORDS_PER_MINUTE   # ≈ 400 ms
_MAX_CHUNK_CHARS = 200       # split answer into chunks no longer than this

# ── Text chunking ─────────────────────────────────────────────────────────────

_SENTENCE_SPLIT = re.compile(r'(?<=[.?!])\s+')


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """
    Split text on sentence boundaries, then hard-split any remaining runs
    that exceed max_chars. Returns at least one chunk even for short text.
    """
    sentences = _SENTENCE_SPLIT.split(text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence
    if current:
        chunks.append(current.strip())
    # Hard split any oversized chunks
    result: list[str] = []
    for chunk in chunks:
        while len(chunk) > max_chars:
            result.append(chunk[:max_chars].strip())
            chunk = chunk[max_chars:].strip()
        if chunk:
            result.append(chunk)
    return result or [""]


# ── Mock PCM generation ───────────────────────────────────────────────────────

def _mock_pcm(text: str) -> bytes:
    """
    Generate silent PCM16 24 kHz bytes of a duration proportional to the
    word count in `text`. Silence is correct here — a real TTS provider
    fills these bytes with actual speech.
    """
    word_count = max(1, len(text.split()))
    duration_ms = int(word_count * _MS_PER_WORD)
    n_samples = (_SAMPLE_RATE * duration_ms) // 1000
    return struct.pack(f"<{n_samples}h", *([0] * n_samples))


# ── Interface ─────────────────────────────────────────────────────────────────

class StreamingTTS(ABC):
    """Abstract base for all TTS adapters."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        call_sid: str,
        stream_sid: str,
    ) -> list[TtsAudioEvent | TtsErrorEvent]:
        """Convert text to a sequence of TtsAudioEvent (or a TtsErrorEvent list)."""


# ── Mock implementation ───────────────────────────────────────────────────────

class MockStreamingTTS(StreamingTTS):
    """
    Deterministic mock TTS. Produces silent PCM16 24 kHz audio scaled to
    realistic speaking duration. Empty or whitespace-only text returns a
    TtsErrorEvent instead of audio.
    """

    def synthesize(
        self,
        text: str,
        call_sid: str,
        stream_sid: str,
    ) -> list[TtsAudioEvent | TtsErrorEvent]:
        if not text or not text.strip():
            return [TtsErrorEvent(callSid=call_sid, streamSid=stream_sid, reason="empty_text")]

        chunks = _chunk_text(text)
        total = len(chunks)
        events: list[TtsAudioEvent | TtsErrorEvent] = []

        for idx, chunk in enumerate(chunks):
            pcm = _mock_pcm(chunk)
            events.append(
                TtsAudioEvent(
                    callSid=call_sid,
                    streamSid=stream_sid,
                    chunkIndex=idx,
                    totalChunks=total,
                    isFinal=(idx == total - 1),
                    pcm24k=base64.b64encode(pcm).decode(),
                )
            )

        return events

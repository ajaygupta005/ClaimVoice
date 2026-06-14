"""
STT adapter interface and mock implementation.

The abstract protocol defines what any future STT provider (Deepgram Nova-2,
Whisper, etc.) must implement. MockStreamingSTT is a deterministic stand-in
that generates plausible transcript events without network calls.

Interface contract
------------------
- `push_audio(pcm: bytes) -> list[PartialTranscriptEvent]`
  Feed a PCM16 24 kHz frame. May return zero or more partial events.
- `flush() -> FinalTranscriptEvent | None`
  Signal end-of-stream. Returns a final transcript if any audio was received,
  or None if the session was silent.

Thread / async safety: all methods are synchronous. Wrap in asyncio.to_thread
if calling from async code with a real blocking provider.
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from typing import Optional

from voice_agent.schemas.transcript import FinalTranscriptEvent, PartialTranscriptEvent

# ── Interface ─────────────────────────────────────────────────────────────────

class StreamingSTT(ABC):
    """Abstract base for all STT adapters."""

    @abstractmethod
    def push_audio(self, pcm: bytes) -> list[PartialTranscriptEvent]:
        """Accept one PCM16 24 kHz frame; return any partial transcript events."""

    @abstractmethod
    def flush(self) -> Optional[FinalTranscriptEvent]:
        """Signal end of stream; return the final transcript or None if silent."""


# ── Mock implementation ───────────────────────────────────────────────────────

# A small pool of realistic insurance-question fragments used by the mock.
_PARTIAL_PHRASES: list[str] = [
    "is",
    "is an",
    "is an MRI",
    "is an MRI covered",
    "is an MRI covered under",
    "is an MRI covered under my plan",
]

_FINAL_PHRASES: list[str] = [
    "Is an MRI of the brain covered under my plan?",
    "What is my urgent care copay?",
    "Is physical therapy covered?",
    "How much is my deductible?",
    "Do I need a referral to see a specialist?",
]

_PCM_SAMPLE_RATE = 24_000  # samples/sec
_PCM_BYTES_PER_SAMPLE = 2  # int16


def _energy(pcm: bytes) -> float:
    """RMS energy of a PCM16 LE buffer; returns 0.0 for empty input."""
    if len(pcm) < 2:
        return 0.0
    samples = struct.unpack_from(f"<{len(pcm) // 2}h", pcm)
    return (sum(s * s for s in samples) / len(samples)) ** 0.5


class MockStreamingSTT(StreamingSTT):
    """
    Deterministic mock STT.

    Emits one partial transcript event every `partial_every_n` frames that
    contain non-silence audio. Advances through a fixed phrase list so
    consecutive tests get different text without randomness.
    """

    SILENCE_THRESHOLD = 50  # RMS below this is treated as silence
    PARTIAL_EVERY_N = 5     # emit a partial after every Nth non-silent frame

    def __init__(self, call_sid: str, stream_sid: str) -> None:
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self._frame_count = 0          # total frames pushed
        self._non_silent_frames = 0    # frames with energy above threshold
        self._total_bytes = 0
        self._partial_idx = 0          # cycles through _PARTIAL_PHRASES
        self._final_idx = 0            # cycles through _FINAL_PHRASES

    # Shared counters so each instance gets distinct phrases
    _global_partial = 0
    _global_final = 0

    def push_audio(self, pcm: bytes) -> list[PartialTranscriptEvent]:
        if not pcm:
            return []

        self._frame_count += 1
        self._total_bytes += len(pcm)

        if _energy(pcm) < self.SILENCE_THRESHOLD:
            return []

        self._non_silent_frames += 1
        if self._non_silent_frames % self.PARTIAL_EVERY_N != 0:
            return []

        phrase_idx = MockStreamingSTT._global_partial % len(_PARTIAL_PHRASES)
        MockStreamingSTT._global_partial += 1

        # confidence grows as more audio arrives (capped at 0.95)
        confidence = min(0.60 + 0.05 * (self._non_silent_frames // self.PARTIAL_EVERY_N), 0.95)

        return [
            PartialTranscriptEvent(
                callSid=self.call_sid,
                streamSid=self.stream_sid,
                text=_PARTIAL_PHRASES[phrase_idx],
                confidence=round(confidence, 2),
            )
        ]

    def flush(self) -> Optional[FinalTranscriptEvent]:
        if self._non_silent_frames == 0:
            return None

        phrase_idx = MockStreamingSTT._global_final % len(_FINAL_PHRASES)
        MockStreamingSTT._global_final += 1

        # Estimate duration from total bytes (PCM16 24 kHz)
        total_samples = self._total_bytes // _PCM_BYTES_PER_SAMPLE
        duration_ms = int(total_samples / _PCM_SAMPLE_RATE * 1000)

        confidence = min(0.75 + 0.01 * self._non_silent_frames, 0.99)

        return FinalTranscriptEvent(
            callSid=self.call_sid,
            streamSid=self.stream_sid,
            text=_FINAL_PHRASES[phrase_idx],
            confidence=round(confidence, 2),
            duration_ms=duration_ms,
        )

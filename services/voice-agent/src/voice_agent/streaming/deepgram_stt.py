"""Real Deepgram Nova-2 STT adapter (key-gated; mock fallback handled by the factory).

Implements the synchronous StreamingSTT contract by buffering PCM16 24 kHz frames and
transcribing the buffer on flush() via Deepgram's prerecorded API (simpler and more
robust than a streaming WebSocket behind a sync push/flush interface). The SDK is
imported lazily so importing this module never requires deepgram-sdk to be installed.
"""

from __future__ import annotations

from typing import Optional

from voice_agent.schemas.transcript import FinalTranscriptEvent, PartialTranscriptEvent
from voice_agent.streaming.stt_adapter import StreamingSTT, _energy

_SAMPLE_RATE = 24_000
_BYTES_PER_SAMPLE = 2
_SILENCE_THRESHOLD = 50


class DeepgramStreamingSTT(StreamingSTT):
    def __init__(self, call_sid: str, stream_sid: str, api_key: str, model: str = "nova-2") -> None:
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self._api_key = api_key
        self._model = model
        self._buf = bytearray()
        self._non_silent = 0

    def push_audio(self, pcm: bytes) -> list[PartialTranscriptEvent]:
        if not pcm:
            return []
        self._buf.extend(pcm)
        if _energy(pcm) >= _SILENCE_THRESHOLD:
            self._non_silent += 1
        return []  # Deepgram transcribes on flush; no interim partials in this adapter.

    def flush(self) -> Optional[FinalTranscriptEvent]:
        if self._non_silent == 0 or not self._buf:
            return None

        from deepgram import DeepgramClient, PrerecordedOptions  # lazy import

        client = DeepgramClient(self._api_key)
        source = {"buffer": bytes(self._buf), "mimetype": "audio/l16;rate=24000"}
        options = PrerecordedOptions(model=self._model, smart_format=True, language="en-US")
        resp = client.listen.prerecorded.v("1").transcribe_file(source, options)

        alt = resp["results"]["channels"][0]["alternatives"][0]
        text = alt.get("transcript", "").strip()
        confidence = float(alt.get("confidence", 0.0))
        duration_ms = int((len(self._buf) // _BYTES_PER_SAMPLE) / _SAMPLE_RATE * 1000)
        if not text:
            return None
        return FinalTranscriptEvent(
            callSid=self.call_sid,
            streamSid=self.stream_sid,
            text=text,
            confidence=round(confidence, 2),
            duration_ms=duration_ms,
        )

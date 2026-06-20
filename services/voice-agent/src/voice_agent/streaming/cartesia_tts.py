"""Real Cartesia Sonic TTS adapter (key-gated; mock fallback handled by the factory).

Implements StreamingTTS.synthesize by calling Cartesia per sentence chunk and returning
TtsAudioEvent objects carrying base64 PCM16 24 kHz. The SDK is imported lazily so this
module imports fine without the cartesia package installed.
"""

from __future__ import annotations

import base64

from voice_agent.schemas.tts import TtsAudioEvent, TtsErrorEvent
from voice_agent.streaming.tts_adapter import _chunk_text

_SAMPLE_RATE = 24_000
_DEFAULT_VOICE = "a0e99841-438c-4a64-b679-ae501e7d6091"  # Cartesia "Sonic" default voice


class CartesiaStreamingTTS:
    def __init__(self, api_key: str, voice_id: str = _DEFAULT_VOICE, model: str = "sonic-2") -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model = model

    def synthesize(
        self, text: str, call_sid: str, stream_sid: str
    ) -> list[TtsAudioEvent | TtsErrorEvent]:
        if not text or not text.strip():
            return [TtsErrorEvent(callSid=call_sid, streamSid=stream_sid, reason="empty_text")]

        from cartesia import Cartesia  # lazy import

        client = Cartesia(api_key=self._api_key)
        chunks = _chunk_text(text)
        total = len(chunks)
        events: list[TtsAudioEvent | TtsErrorEvent] = []
        for idx, chunk in enumerate(chunks):
            pcm = self._synth_chunk(client, chunk)
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

    def _synth_chunk(self, client, chunk: str) -> bytes:
        audio = bytearray()
        output_format = {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": _SAMPLE_RATE,
        }
        for frame in client.tts.bytes(
            model_id=self._model,
            transcript=chunk,
            voice={"mode": "id", "id": self._voice_id},
            output_format=output_format,
        ):
            audio.extend(frame)
        return bytes(audio)

"""Unit tests for the MockStreamingTTS adapter and TTS WebSocket integration."""

import base64
import struct

import pytest
from fastapi.testclient import TestClient

from voice_agent.main import app
from voice_agent.schemas.tts import TtsAudioEvent, TtsErrorEvent
from voice_agent.streaming.tts_adapter import MockStreamingTTS, _chunk_text


# ── Text chunking helper ──────────────────────────────────────────────────────

def test_short_text_produces_one_chunk() -> None:
    chunks = _chunk_text("Hello world.")
    assert len(chunks) == 1


def test_long_text_splits_on_sentence_boundary() -> None:
    text = "Yes, MRI is covered. Prior authorization is required. Allow 3 to 5 business days."
    # Use a small max_chars to force sentence-boundary splitting
    chunks = _chunk_text(text, max_chars=40)
    assert len(chunks) >= 2


def test_very_long_sentence_hard_splits() -> None:
    # 250 chars with no sentence boundary
    text = "a" * 250
    chunks = _chunk_text(text, max_chars=200)
    assert all(len(c) <= 200 for c in chunks)
    assert len(chunks) >= 2


def test_empty_string_returns_one_empty_chunk() -> None:
    chunks = _chunk_text("")
    assert len(chunks) == 1
    assert chunks[0] == ""


# ── MockStreamingTTS.synthesize ───────────────────────────────────────────────

tts = MockStreamingTTS()


def test_short_answer_produces_one_audio_chunk() -> None:
    events = tts.synthesize("Your copay is $30.", "CA001", "SM001")
    assert len(events) == 1
    assert isinstance(events[0], TtsAudioEvent)


def test_audio_chunk_has_correct_metadata() -> None:
    events = tts.synthesize("Your copay is $30.", "CA001", "SM001")
    ev = events[0]
    assert isinstance(ev, TtsAudioEvent)
    assert ev.type == "tts.audio"
    assert ev.callSid == "CA001"
    assert ev.streamSid == "SM001"
    assert ev.chunkIndex == 0
    assert ev.totalChunks == 1
    assert ev.isFinal is True


def test_last_chunk_is_final() -> None:
    long_text = (
        "Yes, MRI is covered. Since you have not met your deductible, you will pay the "
        "negotiated rate up to your remaining deductible. Prior authorization is required. "
        "Please have your provider submit the request before scheduling."
    )
    events = tts.synthesize(long_text, "CA002", "SM002")
    audio_events = [e for e in events if isinstance(e, TtsAudioEvent)]
    assert audio_events[-1].isFinal is True
    for ev in audio_events[:-1]:
        assert ev.isFinal is False


def test_multi_chunk_indices_are_sequential() -> None:
    long_text = (
        "Yes, MRI is covered. Prior authorization is required. "
        "Please allow 3 to 5 business days for approval."
    )
    events = tts.synthesize(long_text, "CA003", "SM003")
    audio_events = [e for e in events if isinstance(e, TtsAudioEvent)]
    indices = [e.chunkIndex for e in audio_events]
    assert indices == list(range(len(audio_events)))


def test_pcm24k_is_valid_base64() -> None:
    events = tts.synthesize("Your copay is $30.", "CA004", "SM004")
    for ev in events:
        if isinstance(ev, TtsAudioEvent):
            raw = base64.b64decode(ev.pcm24k)
            assert len(raw) > 0
            assert len(raw) % 2 == 0  # PCM16 = 2 bytes per sample


def test_pcm24k_is_valid_pcm16() -> None:
    events = tts.synthesize("Your copay is $30.", "CA005", "SM005")
    ev = events[0]
    assert isinstance(ev, TtsAudioEvent)
    raw = base64.b64decode(ev.pcm24k)
    n_samples = len(raw) // 2
    samples = struct.unpack(f"<{n_samples}h", raw)
    assert all(-32768 <= s <= 32767 for s in samples)


def test_empty_text_returns_tts_error() -> None:
    events = tts.synthesize("", "CA006", "SM006")
    assert len(events) == 1
    assert isinstance(events[0], TtsErrorEvent)
    assert events[0].reason == "empty_text"


def test_whitespace_only_returns_tts_error() -> None:
    events = tts.synthesize("   \n\t  ", "CA007", "SM007")
    assert isinstance(events[0], TtsErrorEvent)


def test_total_chunks_matches_event_count() -> None:
    text = (
        "Yes, coverage applies. Prior auth is required. "
        "Your provider must submit the request."
    )
    events = tts.synthesize(text, "CA008", "SM008")
    audio_events = [e for e in events if isinstance(e, TtsAudioEvent)]
    for ev in audio_events:
        assert ev.totalChunks == len(audio_events)


# ── WebSocket integration ─────────────────────────────────────────────────────

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _loud_b64(n_samples: int = 48) -> str:
    pcm = struct.pack(f"<{n_samples}h", *([8000] * n_samples))
    return base64.b64encode(pcm).decode()


def test_ws_emits_tts_audio_after_answer(client: TestClient) -> None:
    """After start + audio + stop, at least one tts.audio event must appear."""
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA300&streamSid=SM300") as ws:
        ws.send_json({"type": "start", "callSid": "CA300", "streamSid": "SM300"})
        ws.receive_json()  # start ack

        for _ in range(3):
            ws.send_json({
                "type": "audio", "callSid": "CA300", "streamSid": "SM300",
                "pcm24k": _loud_b64(),
            })
            ws.receive_json()  # audio ack

        ws.send_json({"type": "stop", "callSid": "CA300", "streamSid": "SM300"})

        messages = []
        for _ in range(20):  # drain until stop ack
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    types = [m.get("type") or m.get("ack") for m in messages]
    assert "tts.audio" in types


def test_ws_last_tts_chunk_is_final(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA301&streamSid=SM301") as ws:
        ws.send_json({"type": "start", "callSid": "CA301", "streamSid": "SM301"})
        ws.receive_json()

        for _ in range(3):
            ws.send_json({
                "type": "audio", "callSid": "CA301", "streamSid": "SM301",
                "pcm24k": _loud_b64(),
            })
            ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA301", "streamSid": "SM301"})

        messages = []
        for _ in range(20):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    tts_msgs = [m for m in messages if m.get("type") == "tts.audio"]
    assert tts_msgs  # at least one
    assert tts_msgs[-1]["isFinal"] is True

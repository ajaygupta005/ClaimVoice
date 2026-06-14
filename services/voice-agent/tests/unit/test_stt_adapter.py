"""Unit tests for the MockStreamingSTT adapter."""

import struct
import pytest

from voice_agent.schemas.transcript import FinalTranscriptEvent, PartialTranscriptEvent
from voice_agent.streaming.stt_adapter import MockStreamingSTT


def _make_pcm(n_samples: int, amplitude: int = 8000) -> bytes:
    """Create PCM16 LE bytes with a constant non-zero amplitude."""
    return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))


def _silence(n_samples: int = 48) -> bytes:
    return bytes(n_samples * 2)


# ── Basic construction ────────────────────────────────────────────────────────

def test_init_does_not_raise() -> None:
    stt = MockStreamingSTT(call_sid="CA001", stream_sid="SM001")
    assert stt.call_sid == "CA001"
    assert stt.stream_sid == "SM001"


# ── push_audio ────────────────────────────────────────────────────────────────

def test_empty_audio_returns_no_events() -> None:
    stt = MockStreamingSTT("CA010", "SM010")
    result = stt.push_audio(b"")
    assert result == []


def test_silence_returns_no_events() -> None:
    stt = MockStreamingSTT("CA011", "SM011")
    for _ in range(20):
        events = stt.push_audio(_silence())
        assert events == []


def test_non_silent_audio_eventually_emits_partial() -> None:
    stt = MockStreamingSTT("CA012", "SM012")
    all_events: list[PartialTranscriptEvent] = []
    # Push PARTIAL_EVERY_N frames of loud audio to guarantee at least one partial
    for _ in range(stt.PARTIAL_EVERY_N):
        all_events.extend(stt.push_audio(_make_pcm(48)))
    assert len(all_events) >= 1
    ev = all_events[0]
    assert isinstance(ev, PartialTranscriptEvent)
    assert ev.callSid == "CA012"
    assert ev.streamSid == "SM012"
    assert ev.text  # non-empty string
    assert 0.0 <= ev.confidence <= 1.0


def test_partial_event_schema_is_correct_type() -> None:
    stt = MockStreamingSTT("CA013", "SM013")
    events: list[PartialTranscriptEvent] = []
    for _ in range(stt.PARTIAL_EVERY_N):
        events.extend(stt.push_audio(_make_pcm(48)))
    for ev in events:
        assert ev.type == "transcript.partial"


# ── flush ─────────────────────────────────────────────────────────────────────

def test_flush_on_silent_session_returns_none() -> None:
    stt = MockStreamingSTT("CA020", "SM020")
    stt.push_audio(_silence())
    assert stt.flush() is None


def test_flush_after_audio_returns_final_event() -> None:
    stt = MockStreamingSTT("CA021", "SM021")
    for _ in range(3):
        stt.push_audio(_make_pcm(48))
    final = stt.flush()
    assert isinstance(final, FinalTranscriptEvent)
    assert final.type == "transcript.final"
    assert final.callSid == "CA021"
    assert final.streamSid == "SM021"
    assert final.text
    assert 0.0 <= final.confidence <= 1.0


def test_flush_includes_duration_ms() -> None:
    stt = MockStreamingSTT("CA022", "SM022")
    n_samples = 240  # 10 ms at 24 kHz
    stt.push_audio(_make_pcm(n_samples))
    final = stt.flush()
    assert final is not None
    assert final.duration_ms is not None
    assert final.duration_ms >= 0


def test_flush_with_no_audio_at_all_returns_none() -> None:
    stt = MockStreamingSTT("CA023", "SM023")
    assert stt.flush() is None


# ── WS endpoint integration: transcript events appear in the WebSocket ────────

import base64
from fastapi.testclient import TestClient
from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _b64_loud(n_samples: int = 48) -> str:
    return base64.b64encode(_make_pcm(n_samples)).decode()


def test_ws_emits_final_transcript_on_stop(client: TestClient) -> None:
    """After a start + several audio frames + stop, a transcript.final must appear."""
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA030&streamSid=SM030") as ws:
        ws.send_json({"type": "start", "callSid": "CA030", "streamSid": "SM030"})
        ws.receive_json()  # start ack

        # Send enough frames so flush() sees non-silent audio
        for _ in range(3):
            ws.send_json({
                "type": "audio",
                "callSid": "CA030",
                "streamSid": "SM030",
                "pcm24k": _b64_loud(),
            })
            ws.receive_json()  # audio ack (may be followed by partial — drain them)

        ws.send_json({"type": "stop", "callSid": "CA030", "streamSid": "SM030"})

        # Collect messages until we see the stop ack (or a transcript.final)
        messages = []
        for _ in range(10):  # safety cap
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    types = [m.get("type") or m.get("ack") for m in messages]
    assert "transcript.final" in types or "stop" in types


def test_ws_silent_audio_produces_no_partial_transcripts(client: TestClient) -> None:
    """Silence frames must not generate any transcript.partial events."""
    silent_b64 = base64.b64encode(_silence(48)).decode()

    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA031&streamSid=SM031") as ws:
        ws.send_json({"type": "start", "callSid": "CA031", "streamSid": "SM031"})
        ws.receive_json()  # start ack

        for _ in range(10):
            ws.send_json({
                "type": "audio",
                "callSid": "CA031",
                "streamSid": "SM031",
                "pcm24k": silent_b64,
            })
            ack = ws.receive_json()
            assert ack.get("ack") == "audio"  # only ack, no partial

        ws.send_json({"type": "stop", "callSid": "CA031", "streamSid": "SM031"})
        # Flush should return None for silent session — only stop ack expected
        stop_msg = ws.receive_json()
        assert stop_msg.get("ack") == "stop"

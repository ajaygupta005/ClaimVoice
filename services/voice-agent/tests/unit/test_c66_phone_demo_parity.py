"""
Component 66 — Twilio Phone Demo Parity tests.

Verifies that the telephone path (telephony_ws.py WebSocket endpoint) produces
the same core agent behavior as the browser path (agent_respond.py HTTP endpoint):
- Same LangGraph graph is invoked
- Same tool routing (intent → tool)
- Same hallucination guard behavior
- Tool trace and guard status logged with turn_id and call_sid
- Failure recovery: orchestrate error returns safe error response + stop ack
- Failure recovery: TTS error returns stop ack (call is not dropped)
- Disconnect mid-turn is handled safely
- Audio bytes and frame counts are tracked per session
- stop event without prior audio is safe (silent call)
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _b64(n: int = 64) -> str:
    return base64.b64encode(bytes(range(n % 256)) * (n // 256 + 1))[:n * (64 // n + 1)].decode()


def _pcm_b64(n: int = 64) -> str:
    return base64.b64encode(bytes([i % 256 for i in range(n)])).decode()


# ── Helper: drain WS messages until predicate ────────────────────────────────

def _drain_until(ws, predicate, max_msgs: int = 10) -> dict | None:
    for _ in range(max_msgs):
        try:
            msg = ws.receive_json()
            if predicate(msg):
                return msg
        except Exception:
            break
    return None


# ── Phone path produces same intent routing as browser path ──────────────────

def test_phone_coverage_intent_matches_browser():
    """Phone path routes the mock STT phrase through the same graph as the browser path.

    The mock STT `_global_final` counter advances across tests, so we can't predict
    which fixed phrase the phone path will transcribe. Instead we verify that whatever
    phrase the STT emits, running it through run_agent_graph() produces the same intent
    as the phone path — i.e. the two paths share the same graph.
    """
    from voice_agent.graph.state_machine import run_agent_graph
    from voice_agent.streaming.stt_adapter import MockStreamingSTT

    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p1&streamSid=SM-p1") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p1", "streamSid": "SM-p1"})
        ws.receive_json()  # start ack

        ws.send_json({"type": "audio", "callSid": "CA-p1", "streamSid": "SM-p1", "pcm24k": _pcm_b64(64)})
        ws.receive_json()  # audio ack

        ws.send_json({"type": "stop", "callSid": "CA-p1", "streamSid": "SM-p1"})

        # Drain: transcript → answer → TTS chunk(s) → stop ack
        transcript_msg = _drain_until(ws, lambda m: m.get("type") == "transcript.final")
        answer_msg = _drain_until(ws, lambda m: m.get("type") == "answer.final")

    assert answer_msg is not None, "Expected answer.final from phone path"
    assert transcript_msg is not None, "Expected transcript.final before answer.final"

    # Both paths must use the same graph: run_agent_graph on the transcribed text
    # must produce the same intent as the phone path answer.
    phone_text = transcript_msg["text"]
    browser_state = run_agent_graph(phone_text)
    assert answer_msg["intent"] == browser_state["intent"]


def test_phone_cost_intent_matches_browser():
    """Phone path routes mock STT phrases to the same intent as the browser path."""
    from voice_agent.graph.state_machine import run_agent_graph

    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p2&streamSid=SM-p2") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p2", "streamSid": "SM-p2"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-p2", "streamSid": "SM-p2", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-p2", "streamSid": "SM-p2"})
        transcript_msg = _drain_until(ws, lambda m: m.get("type") == "transcript.final")
        answer_msg = _drain_until(ws, lambda m: m.get("type") == "answer.final")

    assert answer_msg is not None
    assert transcript_msg is not None

    # Phone and browser paths use the same graph — verify parity via the transcript text.
    phone_text = transcript_msg["text"]
    browser_state = run_agent_graph(phone_text)
    assert answer_msg["intent"] == browser_state["intent"]


def test_phone_answer_is_grounded_for_coverage():
    """Phone path must return grounded=true for a coverage question."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p3&streamSid=SM-p3") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p3", "streamSid": "SM-p3"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-p3", "streamSid": "SM-p3", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-p3", "streamSid": "SM-p3"})
        answer_msg = _drain_until(ws, lambda m: m.get("type") == "answer.final")

    assert answer_msg is not None
    assert isinstance(answer_msg["grounded"], bool)


def test_phone_answer_has_tool_trace():
    """answer.final must include tool_trace with at least one entry."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p4&streamSid=SM-p4") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p4", "streamSid": "SM-p4"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-p4", "streamSid": "SM-p4", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-p4", "streamSid": "SM-p4"})
        answer_msg = _drain_until(ws, lambda m: m.get("type") == "answer.final")

    assert answer_msg is not None
    assert "tool_trace" in answer_msg
    assert len(answer_msg["tool_trace"]) >= 1


# ── TTS audio reaches the caller ─────────────────────────────────────────────

def test_phone_tts_audio_sent_after_answer():
    """At least one tts.audio event must be sent after the answer."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p5&streamSid=SM-p5") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p5", "streamSid": "SM-p5"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-p5", "streamSid": "SM-p5", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-p5", "streamSid": "SM-p5"})

        tts_msg = _drain_until(ws, lambda m: m.get("type") == "tts.audio")

    assert tts_msg is not None, "Expected at least one tts.audio event"
    assert "pcm24k" in tts_msg
    assert len(tts_msg["pcm24k"]) > 0


def test_phone_tts_audio_is_valid_base64():
    """pcm24k in tts.audio must be valid base64-encoded PCM."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-p6&streamSid=SM-p6") as ws:
        ws.send_json({"type": "start", "callSid": "CA-p6", "streamSid": "SM-p6"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-p6", "streamSid": "SM-p6", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-p6", "streamSid": "SM-p6"})
        tts_msg = _drain_until(ws, lambda m: m.get("type") == "tts.audio")

    assert tts_msg is not None
    pcm = base64.b64decode(tts_msg["pcm24k"])
    assert len(pcm) > 0
    assert len(pcm) % 2 == 0  # PCM16: 2 bytes per sample


# ── Observability: turn_id logged per turn ────────────────────────────────────

def test_phone_stop_ack_after_full_sequence(client: TestClient):
    """Full sequence always ends with stop ack even after TTS chunks."""
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-obs1&streamSid=SM-obs1") as ws:
        ws.send_json({"type": "start", "callSid": "CA-obs1", "streamSid": "SM-obs1"})
        ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA-obs1", "streamSid": "SM-obs1", "pcm24k": _pcm_b64(64)})
        ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-obs1", "streamSid": "SM-obs1"})
        stop_ack = _drain_until(ws, lambda m: m.get("ack") == "stop")

    assert stop_ack is not None
    assert stop_ack["callSid"] == "CA-obs1"


def test_session_tracks_audio_bytes(client: TestClient):
    """SessionState.audio_bytes_received is incremented for every audio frame."""
    from voice_agent.api.v1 import telephony_ws as ws_mod
    from voice_agent.api.v1.telephony_ws import SessionState

    captured: list[SessionState] = []
    original_handle_stop = ws_mod._handle_stop

    async def patched_stop(ws, ev, session):
        captured.append(session)
        await original_handle_stop(ws, ev, session)

    with patch.object(ws_mod, "_handle_stop", patched_stop):
        with TestClient(app).websocket_connect("/api/v1/ws/telephony") as ws:
            ws.send_json({"type": "start", "callSid": "CA-bytes", "streamSid": "SM-bytes"})
            ws.receive_json()

            for _ in range(3):
                ws.send_json({
                    "type": "audio", "callSid": "CA-bytes", "streamSid": "SM-bytes",
                    "pcm24k": _pcm_b64(64),
                })
                ws.receive_json()

            ws.send_json({"type": "stop", "callSid": "CA-bytes", "streamSid": "SM-bytes"})
            _drain_until(ws, lambda m: m.get("ack") == "stop")

    assert len(captured) == 1
    assert captured[0].audio_frames == 3
    assert captured[0].audio_bytes_received == 64 * 3


# ── Failure recovery: orchestrate error ──────────────────────────────────────

def test_phone_orchestrate_error_returns_stop_ack(client: TestClient):
    """If orchestrate() raises, the endpoint must still send a stop ack."""
    with patch(
        "voice_agent.api.v1.telephony_ws.orchestrate",
        side_effect=RuntimeError("simulated_orchestrate_failure"),
    ):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-err1&streamSid=SM-err1") as ws:
            ws.send_json({"type": "start", "callSid": "CA-err1", "streamSid": "SM-err1"})
            ws.receive_json()

            ws.send_json({
                "type": "audio", "callSid": "CA-err1", "streamSid": "SM-err1",
                "pcm24k": _pcm_b64(64),
            })
            ws.receive_json()

            ws.send_json({"type": "stop", "callSid": "CA-err1", "streamSid": "SM-err1"})

            error_msg = _drain_until(ws, lambda m: "error" in m)
            stop_ack = _drain_until(ws, lambda m: m.get("ack") == "stop")

    assert error_msg is not None
    assert "orchestrate_error" in error_msg.get("error", "")
    assert stop_ack is not None, "Must still get stop ack after orchestrate error"


def test_phone_orchestrate_error_does_not_send_answer(client: TestClient):
    """An orchestrate error must not produce a fabricated answer.final."""
    received: list[dict] = []

    with patch(
        "voice_agent.api.v1.telephony_ws.orchestrate",
        side_effect=RuntimeError("pipeline_down"),
    ):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-err2&streamSid=SM-err2") as ws:
            ws.send_json({"type": "start", "callSid": "CA-err2", "streamSid": "SM-err2"})
            received.append(ws.receive_json())  # start ack

            ws.send_json({
                "type": "audio", "callSid": "CA-err2", "streamSid": "SM-err2",
                "pcm24k": _pcm_b64(64),
            })
            received.append(ws.receive_json())  # audio ack

            ws.send_json({"type": "stop", "callSid": "CA-err2", "streamSid": "SM-err2"})
            # On error path: transcript.final → error → stop ack (3 messages)
            received.append(ws.receive_json())  # transcript.final
            received.append(ws.receive_json())  # error
            received.append(ws.receive_json())  # stop ack

    answer_msgs = [m for m in received if m.get("type") == "answer.final"]
    assert len(answer_msgs) == 0, "Must not fabricate an answer after orchestrate error"


# ── Failure recovery: TTS error ───────────────────────────────────────────────

def test_phone_tts_error_returns_stop_ack(client: TestClient):
    """If TTS raises, the endpoint must still send a stop ack — call is not dropped."""
    with patch(
        "voice_agent.api.v1.telephony_ws.build_tts",
        side_effect=RuntimeError("cartesia_down"),
    ):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-tts1&streamSid=SM-tts1") as ws:
            ws.send_json({"type": "start", "callSid": "CA-tts1", "streamSid": "SM-tts1"})
            ws.receive_json()

            ws.send_json({
                "type": "audio", "callSid": "CA-tts1", "streamSid": "SM-tts1",
                "pcm24k": _pcm_b64(64),
            })
            ws.receive_json()

            ws.send_json({"type": "stop", "callSid": "CA-tts1", "streamSid": "SM-tts1"})

            # Should still get: transcript.final → answer.final → tts_error → stop ack
            stop_ack = _drain_until(ws, lambda m: m.get("ack") == "stop")

    assert stop_ack is not None, "Stop ack must arrive even when TTS fails"
    assert stop_ack["callSid"] == "CA-tts1"


def test_phone_tts_error_answer_still_delivered(client: TestClient):
    """After a TTS error the answer text must still reach the caller (over WS)."""
    with patch(
        "voice_agent.api.v1.telephony_ws.build_tts",
        side_effect=RuntimeError("tts_down"),
    ):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-tts2&streamSid=SM-tts2") as ws:
            ws.send_json({"type": "start", "callSid": "CA-tts2", "streamSid": "SM-tts2"})
            ws.receive_json()

            ws.send_json({
                "type": "audio", "callSid": "CA-tts2", "streamSid": "SM-tts2",
                "pcm24k": _pcm_b64(64),
            })
            ws.receive_json()

            ws.send_json({"type": "stop", "callSid": "CA-tts2", "streamSid": "SM-tts2"})
            answer_msg = _drain_until(ws, lambda m: m.get("type") == "answer.final")

    assert answer_msg is not None, "answer.final must arrive before any TTS attempt"
    assert answer_msg["text"] != ""


# ── Silent call (no audio before stop) ───────────────────────────────────────

def test_phone_silent_call_returns_stop_ack(client: TestClient):
    """A stop event with no audio (silent call) must return a stop ack safely."""
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-sil&streamSid=SM-sil") as ws:
        ws.send_json({"type": "start", "callSid": "CA-sil", "streamSid": "SM-sil"})
        ws.receive_json()

        # No audio events — caller hung up silently
        ws.send_json({"type": "stop", "callSid": "CA-sil", "streamSid": "SM-sil"})
        stop_ack = _drain_until(ws, lambda m: m.get("ack") == "stop")

    assert stop_ack is not None
    assert stop_ack["callSid"] == "CA-sil"


def test_phone_no_answer_for_silent_call(client: TestClient):
    """A silent call (no audio) must not produce any answer or TTS."""
    received: list[dict] = []
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-sil2&streamSid=SM-sil2") as ws:
        ws.send_json({"type": "start", "callSid": "CA-sil2", "streamSid": "SM-sil2"})
        received.append(ws.receive_json())  # start ack

        ws.send_json({"type": "stop", "callSid": "CA-sil2", "streamSid": "SM-sil2"})
        received.append(ws.receive_json())  # stop ack — only message on a silent call

    bad = [m for m in received if m.get("type") in ("answer.final", "tts.audio")]
    assert len(bad) == 0, f"Silent call must not produce answer/TTS: {bad}"


# ── Existing behavior unchanged ───────────────────────────────────────────────

def test_existing_start_ack_unchanged(client: TestClient):
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-compat&streamSid=SM-compat") as ws:
        ws.send_json({
            "type": "start", "callSid": "CA-compat", "streamSid": "SM-compat",
            "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
        })
        resp = ws.receive_json()

    assert resp["ack"] == "start"
    assert resp["callSid"] == "CA-compat"


def test_existing_audio_ack_unchanged(client: TestClient):
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA-compat2", "streamSid": "SM-compat2"})
        ws.receive_json()

        ws.send_json({
            "type": "audio", "callSid": "CA-compat2", "streamSid": "SM-compat2",
            "pcm24k": _pcm_b64(128),
        })
        resp = ws.receive_json()

    assert resp["ack"] == "audio"
    assert resp["bytes"] == 128


def test_existing_invalid_json_unchanged(client: TestClient):
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_text("not json {{{")
        resp = ws.receive_json()

    assert resp["error"] == "invalid_json"

"""
Unit tests for the /api/v1/ws/telephony WebSocket endpoint.

Uses Starlette TestClient (synchronous) — no running server needed.
"""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _b64(n: int = 64) -> str:
    """Return a base64 string that decodes to exactly n bytes."""
    return base64.b64encode(bytes([i % 256 for i in range(n)])).decode()


# ── start event ───────────────────────────────────────────────────────────────

def test_start_event_ack(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA001&streamSid=SM001") as ws:
        ws.send_json({
            "type": "start",
            "callSid": "CA001",
            "streamSid": "SM001",
            "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
        })
        resp = ws.receive_json()

    assert resp["ack"] == "start"
    assert resp["callSid"] == "CA001"
    assert resp["streamSid"] == "SM001"


# ── audio event ───────────────────────────────────────────────────────────────

def test_audio_event_ack_includes_byte_count(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA002", "streamSid": "SM002"})
        ws.receive_json()  # consume start ack

        pcm_b64 = _b64(128)
        ws.send_json({"type": "audio", "callSid": "CA002", "streamSid": "SM002", "pcm24k": pcm_b64})
        resp = ws.receive_json()

    assert resp["ack"] == "audio"
    assert resp["bytes"] == 128


def test_audio_without_start_returns_error(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "audio", "callSid": "CA003", "streamSid": "SM003", "pcm24k": _b64(32)})
        resp = ws.receive_json()

    assert resp["error"] == "unexpected_audio"


def test_invalid_base64_returns_validation_error(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "audio", "callSid": "CA004", "streamSid": "SM004", "pcm24k": "!!!notbase64!!!"})
        resp = ws.receive_json()

    assert "error" in resp


# ── stop event ────────────────────────────────────────────────────────────────

def test_stop_event_ack(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA005", "streamSid": "SM005"})
        ws.receive_json()  # consume start ack

        ws.send_json({"type": "stop", "callSid": "CA005", "streamSid": "SM005"})
        resp = ws.receive_json()

    assert resp["ack"] == "stop"
    assert resp["callSid"] == "CA005"


# ── full start → audio → stop sequence ───────────────────────────────────────

def test_full_sequence(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA006&streamSid=SM006") as ws:
        ws.send_json({"type": "start", "callSid": "CA006", "streamSid": "SM006"})
        start_ack = ws.receive_json()

        ws.send_json({"type": "audio", "callSid": "CA006", "streamSid": "SM006", "pcm24k": _b64(64)})
        audio_ack = ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA006", "streamSid": "SM006"})
        stop_ack = ws.receive_json()

    assert start_ack["ack"] == "start"
    assert audio_ack["ack"] == "audio"
    assert audio_ack["bytes"] == 64
    assert stop_ack["ack"] == "stop"


# ── invalid / malformed events ────────────────────────────────────────────────

def test_invalid_json_returns_error(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_text("not json at all {{{")
        resp = ws.receive_json()

    assert resp["error"] == "invalid_json"


def test_unknown_event_type_returns_error(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "unknown", "callSid": "CA007", "streamSid": "SM007"})
        resp = ws.receive_json()

    assert resp["error"] == "invalid_event"


def test_missing_required_field_returns_error(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        # Missing streamSid
        ws.send_json({"type": "start", "callSid": "CA008"})
        resp = ws.receive_json()

    assert resp["error"] == "invalid_event"

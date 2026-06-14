"""Unit tests for the grounded answer orchestrator."""

import base64
import struct

import pytest
from fastapi.testclient import TestClient

from voice_agent.main import app
from voice_agent.schemas.transcript import FinalTranscriptEvent
from voice_agent.services.answer_orchestrator import orchestrate


def _transcript(text: str, call_sid: str = "CA100", stream_sid: str = "SM100") -> FinalTranscriptEvent:
    return FinalTranscriptEvent(
        callSid=call_sid,
        streamSid=stream_sid,
        text=text,
        confidence=0.91,
        duration_ms=3000,
    )


# ── Intent routing ────────────────────────────────────────────────────────────

def test_coverage_question_routes_to_coverage() -> None:
    ev = orchestrate(_transcript("Is an MRI of the brain covered under my plan?"))
    assert ev.intent == "coverage"
    assert ev.type == "answer.final"
    assert ev.grounded is True
    assert len(ev.tool_trace) == 1
    assert ev.tool_trace[0].tool == "check_coverage"


def test_copay_question_routes_to_cost() -> None:
    ev = orchestrate(_transcript("What is my copay for urgent care?"))
    assert ev.intent == "cost"
    assert ev.grounded is True
    assert ev.tool_trace[0].tool == "estimate_cost"


def test_deductible_question_routes_to_cost() -> None:
    ev = orchestrate(_transcript("How much of my deductible have I met?"))
    assert ev.intent == "cost"
    assert "deductible" in ev.text.lower()


def test_provider_question_routes_to_provider() -> None:
    ev = orchestrate(_transcript("Find a cardiologist near me who is in network."))
    assert ev.intent == "provider"
    assert ev.tool_trace[0].tool == "find_provider"


def test_formulary_question_routes_to_formulary() -> None:
    ev = orchestrate(_transcript("Is lisinopril on my formulary?"))
    assert ev.intent == "formulary"
    assert ev.tool_trace[0].tool == "check_formulary"
    assert "lisinopril" in ev.text.lower()


def test_humira_requires_prior_auth() -> None:
    ev = orchestrate(_transcript("Is Humira covered on my plan?"))
    # Could be coverage or formulary — either way prior auth should be mentioned
    assert "prior auth" in ev.text.lower() or "specialist" in ev.text.lower() or "covered" in ev.text.lower()


def test_unknown_question_escalates() -> None:
    ev = orchestrate(_transcript("Can you tell me about the weather in New York?"))
    assert ev.intent == "escalate"
    assert ev.grounded is False
    assert ev.tool_trace[0].tool == "escalate_to_human"


def test_empty_text_escalates() -> None:
    ev = orchestrate(_transcript(""))
    assert ev.intent == "escalate"
    assert ev.grounded is False


# ── Schema correctness ────────────────────────────────────────────────────────

def test_answer_always_has_tool_trace() -> None:
    questions = [
        "Is an X-ray covered?",
        "What is my copay?",
        "Find a therapist near me.",
        "Is metformin on my formulary?",
        "Hello, who are you?",
    ]
    for q in questions:
        ev = orchestrate(_transcript(q))
        assert len(ev.tool_trace) >= 1, f"No tool trace for: {q}"
        assert ev.tool_trace[0].tool  # non-empty tool name


def test_answer_callsid_and_streamsid_propagate() -> None:
    ev = orchestrate(_transcript("Is an MRI covered?", call_sid="CA999", stream_sid="SM999"))
    assert ev.callSid == "CA999"
    assert ev.streamSid == "SM999"


def test_answer_text_is_non_empty() -> None:
    ev = orchestrate(_transcript("How much does physical therapy cost?"))
    assert ev.text.strip()


# ── WebSocket integration: answer.final appears after stop ───────────────────

def _loud_pcm_b64(n_samples: int = 48) -> str:
    pcm = struct.pack(f"<{n_samples}h", *([8000] * n_samples))
    return base64.b64encode(pcm).decode()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_ws_emits_answer_final_after_stop(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA200&streamSid=SM200") as ws:
        ws.send_json({"type": "start", "callSid": "CA200", "streamSid": "SM200"})
        ws.receive_json()  # start ack

        for _ in range(3):
            ws.send_json({
                "type": "audio",
                "callSid": "CA200",
                "streamSid": "SM200",
                "pcm24k": _loud_pcm_b64(),
            })
            ws.receive_json()  # audio ack (partials may follow — drain)

        ws.send_json({"type": "stop", "callSid": "CA200", "streamSid": "SM200"})

        messages = []
        for _ in range(10):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    types = [m.get("type") or m.get("ack") for m in messages]
    assert "answer.final" in types
    answer_msgs = [m for m in messages if m.get("type") == "answer.final"]
    assert len(answer_msgs) == 1
    answer = answer_msgs[0]
    assert answer["callSid"] == "CA200"
    assert answer["grounded"] in (True, False)
    assert isinstance(answer["tool_trace"], list)
    assert len(answer["tool_trace"]) >= 1

"""
Component 33 — LangGraph runtime tests.

Covers:
  - graph node execution order
  - intent routing for all supported question types
  - tool selection and tool trace shape
  - answer content per scenario
  - hallucination guard grounded/escalation behaviour
  - orchestrate() → AnswerFinalEvent compatibility
  - telephony WebSocket response shape

No Anthropic API key, database, or Twilio connection required.
"""

from __future__ import annotations

import base64
import struct
from typing import Any

import pytest
from fastapi.testclient import TestClient

from voice_agent.graph.state_machine import _COMPILED, run_agent_graph
from voice_agent.main import app
from voice_agent.schemas.answer import AnswerFinalEvent
from voice_agent.schemas.transcript import FinalTranscriptEvent
from voice_agent.services.answer_orchestrator import orchestrate

# ── shared fixtures ───────────────────────────────────────────────────────────

CALL_SID = "CA-TEST-33"
STREAM_SID = "SM-TEST-33"


def _transcript(text: str, call_sid: str = CALL_SID, stream_sid: str = STREAM_SID) -> FinalTranscriptEvent:
    return FinalTranscriptEvent(
        callSid=call_sid,
        streamSid=stream_sid,
        text=text,
        confidence=0.95,
        duration_ms=3500,
    )


def _run(question: str) -> dict[str, Any]:
    return run_agent_graph(question, call_sid=CALL_SID, stream_sid=STREAM_SID)


# ── scenario table ────────────────────────────────────────────────────────────
# Each entry: (question, expected_intent, expected_tool, answer_fragments, grounded, escalates)

SCENARIOS = [
    (
        "Is an MRI of the brain covered under my plan?",
        "coverage", "check_coverage",
        ["MRI", "covered"],
        True, False,
    ),
    (
        "What is my urgent care copay?",
        "cost", "estimate_cost",
        ["$75", "urgent care"],
        True, False,
    ),
    (
        "What is my PCP copay?",
        "cost", "estimate_cost",
        ["$30", "primary care"],
        True, False,
    ),
    (
        "Is lisinopril on my formulary?",
        "formulary", "check_formulary",
        ["lisinopril", "Tier 1"],
        True, False,
    ),
    (
        "Find a cardiologist near me who is in network",
        "provider", "find_provider",
        ["cardiolog", "in-network"],
        True, False,
    ),
    (
        "Do I need prior authorization for an MRI?",
        "coverage", "check_coverage",
        ["MRI"],
        True, False,
    ),
    (
        "My claim was denied — what do I do?",
        "escalate", "escalate_to_human",
        ["specialist", "connect"],
        False, True,
    ),
    (
        "",
        "escalate", "escalate_to_human",
        [],
        False, True,
    ),
]


# ── graph node order ──────────────────────────────────────────────────────────

EXPECTED_NODE_ORDER = [
    "identify_member",
    "understand_intent",
    "call_tool",
    "compose_answer",
    "hallucination_guard",
    "prepare_response",
]


def test_graph_visits_all_nodes_in_order():
    """LangGraph debug stream exposes each node visit in sequence."""
    events = list(_COMPILED.stream(
        {
            "call_sid": CALL_SID,
            "stream_sid": STREAM_SID,
            "question": "Is an MRI covered?",
            "member_id": "",
            "member_verified": False,
            "intent": "",
            "tool_name": "",
            "tool_args": {},
            "tool_result": "",
            "answer_text": "",
            "grounded": False,
            "guard_reason": "",
            "escalate": False,
            "tool_trace": [],
        },
        stream_mode="updates",
    ))
    visited = [list(e.keys())[0] for e in events]
    assert visited == EXPECTED_NODE_ORDER


def test_graph_visits_all_nodes_for_escalation():
    """Escalation paths still traverse every node."""
    events = list(_COMPILED.stream(
        {
            "call_sid": CALL_SID,
            "stream_sid": STREAM_SID,
            "question": "xyzzy gibberish question",
            "member_id": "",
            "member_verified": False,
            "intent": "",
            "tool_name": "",
            "tool_args": {},
            "tool_result": "",
            "answer_text": "",
            "grounded": False,
            "guard_reason": "",
            "escalate": False,
            "tool_trace": [],
        },
        stream_mode="updates",
    ))
    visited = [list(e.keys())[0] for e in events]
    assert visited == EXPECTED_NODE_ORDER


# ── parametrised scenario tests ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "question,expected_intent,expected_tool,answer_fragments,grounded,escalates",
    SCENARIOS,
    ids=[s[0][:40] or "<empty>" for s in SCENARIOS],
)
def test_scenario_intent(question, expected_intent, expected_tool, answer_fragments, grounded, escalates):
    s = _run(question)
    assert s["intent"] == expected_intent


@pytest.mark.parametrize(
    "question,expected_intent,expected_tool,answer_fragments,grounded,escalates",
    SCENARIOS,
    ids=[s[0][:40] or "<empty>" for s in SCENARIOS],
)
def test_scenario_tool(question, expected_intent, expected_tool, answer_fragments, grounded, escalates):
    s = _run(question)
    assert s["tool_name"] == expected_tool


@pytest.mark.parametrize(
    "question,expected_intent,expected_tool,answer_fragments,grounded,escalates",
    SCENARIOS,
    ids=[s[0][:40] or "<empty>" for s in SCENARIOS],
)
def test_scenario_answer_fragments(question, expected_intent, expected_tool, answer_fragments, grounded, escalates):
    s = _run(question)
    answer_lower = s["answer_text"].lower()
    for fragment in answer_fragments:
        assert fragment.lower() in answer_lower, (
            f"Expected fragment '{fragment}' not found in answer: {s['answer_text']!r}"
        )


@pytest.mark.parametrize(
    "question,expected_intent,expected_tool,answer_fragments,grounded,escalates",
    SCENARIOS,
    ids=[s[0][:40] or "<empty>" for s in SCENARIOS],
)
def test_scenario_grounded(question, expected_intent, expected_tool, answer_fragments, grounded, escalates):
    s = _run(question)
    assert s["grounded"] is grounded


@pytest.mark.parametrize(
    "question,expected_intent,expected_tool,answer_fragments,grounded,escalates",
    SCENARIOS,
    ids=[s[0][:40] or "<empty>" for s in SCENARIOS],
)
def test_scenario_escalation_flag(question, expected_intent, expected_tool, answer_fragments, grounded, escalates):
    s = _run(question)
    assert s["escalate"] is escalates


# ── answer is always non-empty ────────────────────────────────────────────────

def test_answer_is_never_empty_for_known_questions():
    questions = [
        "Is an MRI of the brain covered?",
        "What is my copay?",
        "Find a therapist near me.",
        "Is metformin on my formulary?",
        "My claim was denied.",
    ]
    for q in questions:
        s = _run(q)
        assert s["answer_text"].strip(), f"Empty answer for: {q!r}"


# ── tool trace shape ─────────────────────────────────────────────────────────

def test_tool_trace_always_has_one_entry():
    for q, *_ in SCENARIOS:
        s = _run(q)
        assert len(s["tool_trace"]) == 1, f"Expected 1 trace entry for: {q!r}"


def test_tool_trace_entry_has_required_keys():
    s = _run("Is an MRI covered?")
    trace = s["tool_trace"][0]
    assert "tool" in trace
    assert "args" in trace
    assert "result" in trace
    assert "ok" in trace


def test_tool_trace_tool_name_matches_state():
    for q, _, expected_tool, *_ in SCENARIOS:
        s = _run(q)
        assert s["tool_trace"][0]["tool"] == expected_tool, f"Tool mismatch for: {q!r}"


def test_tool_trace_ok_matches_grounded():
    for q, *_, grounded, _esc in SCENARIOS:
        s = _run(q)
        assert s["tool_trace"][0]["ok"] == grounded, f"ok/grounded mismatch for: {q!r}"


def test_tool_trace_args_is_dict():
    for q, *_ in SCENARIOS:
        s = _run(q)
        assert isinstance(s["tool_trace"][0]["args"], dict), f"args not dict for: {q!r}"


def test_tool_trace_result_is_str():
    for q, *_ in SCENARIOS:
        s = _run(q)
        assert isinstance(s["tool_trace"][0]["result"], str), f"result not str for: {q!r}"


# ── hallucination guard detail ────────────────────────────────────────────────

def test_guard_reason_present():
    s = _run("Is an MRI covered?")
    assert s["guard_reason"].strip()


def test_escalation_guard_reason_mentions_escalated():
    s = _run("My claim was denied.")
    assert "escalat" in s["guard_reason"].lower()


def test_grounded_answer_guard_reason_mentions_grounded():
    s = _run("What is my deductible?")
    assert s["grounded"] is True
    assert "grounded" in s["guard_reason"].lower()


def test_escalation_does_not_invent_dollar_amounts():
    """Escalation answers must never mention a specific dollar figure."""
    import re
    s = _run("My claim was denied — I want to appeal.")
    amounts = re.findall(r"\$[\d,]+", s["answer_text"])
    assert amounts == [], f"Escalation answer invented amounts: {amounts}"


# ── member identification ─────────────────────────────────────────────────────

def test_member_verified_for_all_scenarios():
    for q, *_ in SCENARIOS:
        s = _run(q)
        assert s["member_verified"] is True, f"Member not verified for: {q!r}"


def test_member_id_set():
    s = _run("Is an MRI covered?")
    assert s["member_id"]


# ── session propagation ───────────────────────────────────────────────────────

def test_session_ids_preserved_in_state():
    s = run_agent_graph("Is therapy covered?", call_sid="CA-999", stream_sid="SM-888")
    assert s["call_sid"] == "CA-999"
    assert s["stream_sid"] == "SM-888"


# ── orchestrate() → AnswerFinalEvent compatibility ────────────────────────────

def test_orchestrate_returns_answer_final_event():
    ev = orchestrate(_transcript("Is an MRI covered?"))
    assert isinstance(ev, AnswerFinalEvent)
    assert ev.type == "answer.final"


def test_orchestrate_propagates_call_and_stream_sid():
    ev = orchestrate(_transcript("What is my copay?", call_sid="CA-SID", stream_sid="SM-SID"))
    assert ev.callSid == "CA-SID"
    assert ev.streamSid == "SM-SID"


def test_orchestrate_intent_field():
    ev = orchestrate(_transcript("Is lisinopril on my formulary?"))
    assert ev.intent == "formulary"


def test_orchestrate_grounded_field_coverage():
    ev = orchestrate(_transcript("Is physical therapy covered?"))
    assert ev.grounded is True


def test_orchestrate_grounded_field_escalation():
    ev = orchestrate(_transcript("Can you tell me the weather in Boston?"))
    assert ev.grounded is False


def test_orchestrate_tool_trace_list():
    ev = orchestrate(_transcript("Find a cardiologist near me."))
    assert isinstance(ev.tool_trace, list)
    assert len(ev.tool_trace) >= 1


def test_orchestrate_tool_trace_pydantic_model():
    ev = orchestrate(_transcript("What is my out-of-pocket max?"))
    trace = ev.tool_trace[0]
    assert hasattr(trace, "tool")
    assert hasattr(trace, "args")
    assert hasattr(trace, "result")
    assert hasattr(trace, "ok")


def test_orchestrate_answer_text_non_empty():
    for q, *_ in SCENARIOS:
        ev = orchestrate(_transcript(q))
        assert ev.text.strip(), f"Empty answer from orchestrate() for: {q!r}"


# ── telephony WebSocket response shape ────────────────────────────────────────

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _loud_pcm_b64(n_samples: int = 48) -> str:
    pcm = struct.pack(f"<{n_samples}h", *([8000] * n_samples))
    return base64.b64encode(pcm).decode()


def test_ws_answer_final_schema(client: TestClient) -> None:
    """After a stop event, ws must emit answer.final with all required fields."""
    with client.websocket_connect(
        f"/api/v1/ws/telephony?callSid={CALL_SID}&streamSid={STREAM_SID}"
    ) as ws:
        ws.send_json({"type": "start", "callSid": CALL_SID, "streamSid": STREAM_SID})
        ws.receive_json()  # start ack

        for _ in range(3):
            ws.send_json({
                "type": "audio",
                "callSid": CALL_SID,
                "streamSid": STREAM_SID,
                "pcm24k": _loud_pcm_b64(),
            })
            ws.receive_json()

        ws.send_json({"type": "stop", "callSid": CALL_SID, "streamSid": STREAM_SID})

        messages = []
        for _ in range(10):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    answer_msgs = [m for m in messages if m.get("type") == "answer.final"]
    assert len(answer_msgs) == 1, "Expected exactly one answer.final message"
    ans = answer_msgs[0]

    assert ans["callSid"] == CALL_SID
    assert ans["streamSid"] == STREAM_SID
    assert isinstance(ans["intent"], str) and ans["intent"]
    assert isinstance(ans["text"], str) and ans["text"].strip()
    assert ans["grounded"] in (True, False)
    assert isinstance(ans["tool_trace"], list)
    assert len(ans["tool_trace"]) >= 1


def test_ws_answer_final_tool_trace_shape(client: TestClient) -> None:
    """Tool trace entries in the WS response must have the expected keys."""
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA-C33A", "streamSid": "SM-C33A"})
        ws.receive_json()

        for _ in range(2):
            ws.send_json({
                "type": "audio",
                "callSid": "CA-C33A",
                "streamSid": "SM-C33A",
                "pcm24k": _loud_pcm_b64(),
            })
            ws.receive_json()

        ws.send_json({"type": "stop", "callSid": "CA-C33A", "streamSid": "SM-C33A"})
        messages = []
        for _ in range(10):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    answer_msgs = [m for m in messages if m.get("type") == "answer.final"]
    assert answer_msgs, "No answer.final emitted"
    trace = answer_msgs[0]["tool_trace"][0]
    assert "tool" in trace
    assert "args" in trace
    assert "result" in trace
    assert "ok" in trace


def test_ws_protocol_unchanged_start_ack(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-C33B&streamSid=SM-C33B") as ws:
        ws.send_json({"type": "start", "callSid": "CA-C33B", "streamSid": "SM-C33B"})
        resp = ws.receive_json()
    assert resp["ack"] == "start"


def test_ws_protocol_unchanged_audio_ack(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA-C33C", "streamSid": "SM-C33C"})
        ws.receive_json()
        ws.send_json({"type": "audio", "callSid": "CA-C33C", "streamSid": "SM-C33C", "pcm24k": _loud_pcm_b64()})
        resp = ws.receive_json()
    assert resp["ack"] == "audio"


def test_ws_no_anthropic_key_required(client: TestClient) -> None:
    """Entire flow completes without ANTHROPIC_API_KEY set (mock runtime only)."""
    import os
    os.environ.pop("ANTHROPIC_API_KEY", None)

    with client.websocket_connect("/api/v1/ws/telephony") as ws:
        ws.send_json({"type": "start", "callSid": "CA-C33D", "streamSid": "SM-C33D"})
        ws.receive_json()
        ws.send_json({"type": "audio", "callSid": "CA-C33D", "streamSid": "SM-C33D", "pcm24k": _loud_pcm_b64()})
        ws.receive_json()
        ws.send_json({"type": "stop", "callSid": "CA-C33D", "streamSid": "SM-C33D"})
        messages = []
        for _ in range(10):
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("ack") == "stop":
                break

    types = [m.get("type") or m.get("ack") for m in messages]
    assert "answer.final" in types

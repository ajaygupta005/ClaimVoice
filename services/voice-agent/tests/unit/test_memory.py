"""Tests for conversation memory + member threading."""

from __future__ import annotations

from voice_agent.graph.state_machine import run_agent_graph
from voice_agent.services import session_memory as mem


def test_session_memory_store():
    mem.clear("S1")
    assert mem.get_history("S1") == []
    mem.append_turn("S1", "q1", "a1")
    mem.append_turn("S1", "q2", "a2")
    h = mem.get_history("S1")
    assert [t["question"] for t in h] == ["q1", "q2"]
    assert h[1]["answer"] == "a2"
    mem.clear("S1")


def test_member_threading_default_is_demo():
    # Placeholder member ID is resolved to demo member in demo_mode=True
    s = run_agent_graph("Is an MRI covered?")
    assert s["member_id"] == "CVX-0042-MT"


def test_member_threading_explicit():
    s = run_agent_graph("Is an MRI covered?", member_id="CVX-0042-MT")
    assert s["member_id"] == "CVX-0042-MT"


def test_history_threaded_into_state():
    s = run_agent_graph(
        "Is an MRI covered?", history=[{"question": "prev", "answer": "ans"}]
    )
    assert s["history"][0]["question"] == "prev"


def test_agent_respond_memory_accumulates_across_turns():
    from fastapi.testclient import TestClient

    from voice_agent.main import app

    mem.clear("SESS-1")
    client = TestClient(app)
    r1 = client.post(
        "/api/v1/agent/respond", json={"question": "Is an MRI covered?", "sessionId": "SESS-1"}
    )
    r2 = client.post(
        "/api/v1/agent/respond", json={"question": "What is my deductible?", "sessionId": "SESS-1"}
    )
    assert r1.status_code == 200 and r2.status_code == 200
    h = mem.get_history("SESS-1")
    assert [t["question"] for t in h] == ["Is an MRI covered?", "What is my deductible?"]
    mem.clear("SESS-1")

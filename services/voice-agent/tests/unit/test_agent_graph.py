"""
Unit tests for the LangGraph mock runtime (Component 32).

No Anthropic API key, no database, no Twilio — purely deterministic.
"""

import pytest

from voice_agent.graph.state_machine import run_agent_graph


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(question: str):
    return run_agent_graph(question, call_sid="CA-test", stream_sid="SM-test")


# ── member identification ──────────────────────────────────────────────────────

def test_member_is_always_verified():
    s = _run("Is an MRI covered?")
    assert s["member_verified"] is True
    assert s["member_id"] == "MOCK-MEMBER-001"


# ── intent routing ─────────────────────────────────────────────────────────────

def test_mri_coverage_routes_to_coverage():
    s = _run("Is an MRI of the brain covered under my plan?")
    assert s["intent"] == "coverage"
    assert s["tool_name"] == "check_coverage"


def test_urgent_care_copay_routes_to_cost():
    s = _run("What is my urgent care copay?")
    assert s["intent"] == "cost"
    assert s["tool_name"] == "estimate_cost"


def test_pcp_copay_routes_to_cost():
    s = _run("What is my PCP copay?")
    assert s["intent"] == "cost"
    assert s["tool_name"] == "estimate_cost"


def test_lisinopril_routes_to_formulary():
    s = _run("Is lisinopril on my formulary?")
    assert s["intent"] == "formulary"
    assert s["tool_name"] == "check_formulary"


def test_cardiologist_routes_to_provider():
    s = _run("Find a cardiologist near me who is in network")
    assert s["intent"] == "provider"
    assert s["tool_name"] == "find_provider"


def test_prior_auth_routes_to_coverage():
    s = _run("Do I need prior authorization for an MRI?")
    assert s["intent"] == "coverage"


def test_unsupported_question_escalates():
    s = _run("What is the weather in New York?")
    assert s["intent"] == "escalate"
    assert s["tool_name"] == "escalate_to_human"
    assert s["escalate"] is True


def test_empty_question_escalates():
    s = _run("")
    assert s["intent"] == "escalate"
    assert s["grounded"] is False


# ── answer quality ─────────────────────────────────────────────────────────────

def test_mri_answer_is_non_empty():
    s = _run("Is an MRI covered?")
    assert s["answer_text"].strip()


def test_copay_answer_mentions_amount():
    s = _run("What is my urgent care copay?")
    assert "$" in s["answer_text"]


def test_deductible_answer_mentions_deductible():
    s = _run("How much of my deductible have I met?")
    assert "deductible" in s["answer_text"].lower()


def test_lisinopril_answer_mentions_drug():
    s = _run("Is lisinopril on my formulary?")
    assert "lisinopril" in s["answer_text"].lower()


def test_cardiologist_answer_mentions_specialty():
    s = _run("Find a cardiologist near me who is in network")
    assert "cardiolog" in s["answer_text"].lower()


# ── hallucination guard ───────────────────────────────────────────────────────

def test_coverage_answer_is_grounded():
    s = _run("Is physical therapy covered?")
    assert s["grounded"] is True


def test_cost_answer_is_grounded():
    s = _run("What is my copay for urgent care?")
    assert s["grounded"] is True


def test_formulary_answer_is_grounded():
    s = _run("Is metformin on my formulary?")
    assert s["grounded"] is True


def test_escalation_is_not_grounded():
    s = _run("xyzzy purple elephant")
    assert s["grounded"] is False


# ── tool trace ────────────────────────────────────────────────────────────────

def test_tool_trace_has_one_entry():
    s = _run("Is an MRI covered?")
    assert len(s["tool_trace"]) == 1


def test_tool_trace_schema():
    s = _run("What is my deductible?")
    trace = s["tool_trace"][0]
    assert "tool" in trace
    assert "args" in trace
    assert "result" in trace
    assert "ok" in trace


def test_tool_trace_ok_matches_grounded():
    for question in [
        "Is surgery covered?",
        "What is my OOP max?",
        "Find a dermatologist near me",
        "Is insulin on my formulary?",
    ]:
        s = _run(question)
        assert s["tool_trace"][0]["ok"] == s["grounded"], f"mismatch for: {question}"


# ── session fields ─────────────────────────────────────────────────────────────

def test_call_sid_propagates():
    s = run_agent_graph("Is an MRI covered?", call_sid="CA-XYZ", stream_sid="SM-XYZ")
    assert s["call_sid"] == "CA-XYZ"
    assert s["stream_sid"] == "SM-XYZ"

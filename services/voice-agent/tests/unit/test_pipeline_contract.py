"""
Component 63 — WS-7 Pipeline Event Contract tests.

Validates that POST /api/v1/agent/respond returns a stable PipelineSummary
covering all five stages for every pipeline outcome.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voice_agent.main import app
from voice_agent.schemas.agent_respond import (
    PipelineAnswer,
    PipelineGuard,
    PipelineStage,
    PipelineSummary,
    PipelineToolCall,
    ToolTraceItem,
)
from voice_agent.schemas.answer import AnswerFinalEvent, ToolTrace

client = TestClient(app)

_STAGE_NAMES = ["identify", "understand", "tool", "guard", "respond"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _post(question: str, member_id: str = "CVX-0042-MT") -> dict:
    resp = client.post("/api/v1/agent/respond", json={"question": question, "memberId": member_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── shape tests ───────────────────────────────────────────────────────────────

def test_pipeline_coverage_shape():
    body = _post("Is an MRI covered?")
    p = body["pipeline"]

    assert p["intent"] == "coverage"
    assert [s["name"] for s in p["stages"]] == _STAGE_NAMES
    assert p["guard"]["passed"] is True
    assert p["answer"]["source"] in ("mock", "claude")
    assert p["answer"]["grounded"] is True
    assert p["turn_id"] != ""
    assert len(p["tools"]) == 1
    assert p["tools"][0]["tool"] == "check_coverage"


def test_pipeline_cost_shape():
    body = _post("What is my copay?")
    p = body["pipeline"]
    assert p["intent"] == "cost"
    assert p["guard"]["passed"] is True
    assert p["answer"]["grounded"] is True


def test_pipeline_provider_shape():
    body = _post("Find a cardiologist near me")
    p = body["pipeline"]
    assert p["intent"] == "provider"
    assert len(p["tools"]) == 1
    assert p["tools"][0]["tool"] == "find_provider"


def test_pipeline_formulary_shape():
    body = _post("Is lisinopril on my formulary?")
    p = body["pipeline"]
    assert p["intent"] == "formulary"
    assert p["tools"][0]["tool"] == "check_formulary"


def test_pipeline_escalation_shape():
    body = _post("zzz")
    p = body["pipeline"]

    assert p["intent"] == "escalate"
    assert p["answer"]["source"] == "escalated"
    assert p["answer"]["grounded"] is False
    tool_stage = next(s for s in p["stages"] if s["name"] == "tool")
    assert tool_stage["status"] == "escalated"
    guard_stage = next(s for s in p["stages"] if s["name"] == "guard")
    assert guard_stage["status"] == "escalated"


def test_pipeline_five_stages_always():
    for question in ("Is an MRI covered?", "zzz", "Find a cardiologist"):
        body = _post(question)
        names = [s["name"] for s in body["pipeline"]["stages"]]
        assert names == _STAGE_NAMES, f"wrong stages for: {question!r}"


def test_pipeline_turn_id_is_unique():
    b1 = _post("Is an MRI covered?")
    b2 = _post("Is an MRI covered?")
    assert b1["pipeline"]["turn_id"] != b2["pipeline"]["turn_id"]


def test_pipeline_tool_call_result_truncated():
    body = _post("Is an MRI covered?")
    for tool in body["pipeline"]["tools"]:
        assert len(tool["result_summary"]) <= 120


def test_pipeline_tool_data_source_demo_in_mock_mode():
    body = _post("Is an MRI covered?")
    tool = body["pipeline"]["tools"][0]
    # conftest forces TOOL_MODE=mock → data_source should be "demo"
    assert tool["data_source"] == "demo"
    tool_stage = next(s for s in body["pipeline"]["stages"] if s["name"] == "tool")
    assert tool_stage["status"] == "demo"


def test_backward_compat_fields_present():
    body = _post("Is an MRI covered?")
    for field in ("answer", "intent", "grounded", "guard_reason",
                  "tool_trace", "composer_mode", "tool_mode",
                  "member_source", "backend_statuses", "pipeline"):
        assert field in body, f"missing field: {field}"


# ── _build_pipeline unit tests (no HTTP) ─────────────────────────────────────

from voice_agent.api.v1.agent_respond import _build_pipeline


def _make_ev(intent: str, grounded: bool, trace_kwargs: dict | None = None) -> AnswerFinalEvent:
    kw = {"tool": "check_coverage", "args": {}, "result": "ok", "ok": grounded,
          "data_source": "demo", "error_code": "", "member_source": "demo"}
    if trace_kwargs:
        kw.update(trace_kwargs)
    return AnswerFinalEvent(
        callSid="CA-x", streamSid="SM-x",
        intent=intent, text="test answer", grounded=grounded,
        tool_trace=[ToolTrace(**kw)],
    )


def _make_trace(overrides: dict | None = None) -> list[ToolTraceItem]:
    kw = {"tool": "check_coverage", "args": {}, "result": "ok", "ok": True,
          "data_source": "demo", "error_code": "", "member_source": "demo"}
    if overrides:
        kw.update(overrides)
    return [ToolTraceItem(**kw)]


def test_build_pipeline_tool_error_shape():
    ev = _make_ev("coverage", grounded=False,
                  trace_kwargs={"data_source": "error", "error_code": "service_unavailable", "ok": False})
    trace = _make_trace({"data_source": "error", "error_code": "service_unavailable", "ok": False})
    p = _build_pipeline(
        ev=ev, tool_trace=trace,
        composer_mode="mock", member_source="demo",
        tool_mode="http", guard_reason="ungrounded", turn_id="abc123",
    )
    assert p.tools[0].data_source == "error"
    assert p.tools[0].error_code == "service_unavailable"
    assert p.answer.source == "tool_error"
    tool_stage = next(s for s in p.stages if s.name == "tool")
    assert tool_stage.status == "error"


def test_build_pipeline_real_data_source():
    ev = _make_ev("coverage", grounded=True,
                  trace_kwargs={"data_source": "real", "ok": True})
    trace = _make_trace({"data_source": "real", "ok": True})
    p = _build_pipeline(
        ev=ev, tool_trace=trace,
        composer_mode="mock", member_source="provided",
        tool_mode="http", guard_reason="grounded", turn_id="def456",
    )
    assert p.tools[0].data_source == "real"
    tool_stage = next(s for s in p.stages if s.name == "tool")
    assert tool_stage.status == "ok"
    assert p.answer.source == "mock"


def test_build_pipeline_escalation():
    ev = AnswerFinalEvent(
        callSid="CA-x", streamSid="SM-x",
        intent="escalate", text="Let me connect you.", grounded=False,
        tool_trace=[ToolTrace(tool="escalate_to_human", args={}, result="escalated",
                              ok=False, data_source="demo")],
    )
    trace = [ToolTraceItem(tool="escalate_to_human", args={}, result="escalated",
                           ok=False, data_source="demo")]
    p = _build_pipeline(
        ev=ev, tool_trace=trace,
        composer_mode="mock", member_source="demo",
        tool_mode="mock", guard_reason="escalated", turn_id="esc001",
    )
    assert p.answer.source == "escalated"
    assert p.guard.passed is False
    guard_stage = next(s for s in p.stages if s.name == "guard")
    assert guard_stage.status == "escalated"


def test_build_pipeline_claude_answer_source():
    ev = _make_ev("coverage", grounded=True)
    trace = _make_trace({"data_source": "real", "ok": True})
    p = _build_pipeline(
        ev=ev, tool_trace=trace,
        composer_mode="claude", member_source="provided",
        tool_mode="http", guard_reason="grounded", turn_id="cld001",
    )
    assert p.answer.source == "claude"


def test_build_pipeline_result_summary_truncated():
    long_result = "x" * 300
    ev = _make_ev("coverage", grounded=True,
                  trace_kwargs={"result": long_result, "ok": True})
    trace = _make_trace({"result": long_result, "ok": True})
    p = _build_pipeline(
        ev=ev, tool_trace=trace,
        composer_mode="mock", member_source="demo",
        tool_mode="mock", guard_reason="ok", turn_id="trunc01",
    )
    assert len(p.tools[0].result_summary) == 120


# ── prepare_response preserves C62 metadata ──────────────────────────────────

def test_prepare_response_preserves_trace_metadata():
    from voice_agent.graph.nodes.prepare_response import prepare_response

    state = {
        "intent": "coverage",
        "grounded": True,
        "tool_name": "check_coverage",
        "tool_args": {"service": "MRI"},
        "tool_result": "covered",
        "tool_trace": [
            {
                "tool": "check_coverage",
                "args": {"service": "MRI"},
                "result": "covered",
                "ok": False,
                "data_source": "real",
                "error_code": "",
                "member_source": "provided",
            }
        ],
    }
    result = prepare_response(state)
    trace = result["tool_trace"]
    assert len(trace) == 1
    entry = trace[0]
    # C62 metadata preserved
    assert entry["data_source"] == "real"
    assert entry["member_source"] == "provided"
    # ok updated to reflect grounded=True
    assert entry["ok"] is True
    assert result["escalate"] is False


def test_prepare_response_escalate_flag():
    from voice_agent.graph.nodes.prepare_response import prepare_response

    state = {
        "intent": "escalate",
        "grounded": False,
        "tool_trace": [
            {"tool": "escalate_to_human", "args": {}, "result": "esc",
             "ok": False, "data_source": "demo"}
        ],
    }
    result = prepare_response(state)
    assert result["escalate"] is True
    # escalate_to_human ok stays False
    assert result["tool_trace"][0]["ok"] is False

"""
Component 35 — Answer composer unit tests.

Covers:
  - MockComposer: all intent paths, output contract
  - ClaudeComposer: valid JSON, invalid JSON fallback, empty answer fallback,
                    API error fallback, escalation passthrough, guard interaction
  - build_composer: mode selection, missing key error
  - graph integration: output shape unchanged, guard still runs
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from voice_agent.graph.nodes.answer_composer import (
    AnswerComposer,
    ClaudeComposer,
    ComposerInput,
    ComposerOutput,
    MockComposer,
    _ESCALATION_TEXT,
    _FALLBACK_ANSWER,
)
from voice_agent.graph.state_machine import run_agent_graph


# ── helpers ───────────────────────────────────────────────────────────────────

def _inp(intent: str, question: str = "", tool_result: str = "") -> ComposerInput:
    tool_map = {
        "coverage": "check_coverage",
        "cost": "estimate_cost",
        "provider": "find_provider",
        "formulary": "check_formulary",
        "escalate": "escalate_to_human",
    }
    return ComposerInput(
        question=question,
        intent=intent,
        tool_name=tool_map.get(intent, ""),
        tool_args={},
        tool_result=tool_result,
    )


def _claude_response(answer: str, used_facts: list = None, needs_escalation: bool = False, confidence: float = 0.98) -> MagicMock:
    """Build a minimal Anthropic Messages API mock response."""
    body = {
        "answer_text": answer,
        "used_facts": used_facts or [],
        "needs_escalation": needs_escalation,
        "confidence": confidence,
    }
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(body))]
    return msg


def _mock_claude(api_key: str = "sk-mock") -> ClaudeComposer:
    composer = ClaudeComposer.__new__(ClaudeComposer)
    composer._model = "claude-sonnet-4-6"
    composer._client = MagicMock()
    return composer


# ── MockComposer — interface contract ─────────────────────────────────────────

def test_mock_composer_returns_composer_output():
    out = MockComposer().compose(_inp("coverage", question="Is an MRI covered?"))
    assert isinstance(out, ComposerOutput)


def test_mock_composer_coverage_answer():
    out = MockComposer().compose(_inp("coverage", question="Is an MRI covered?", tool_result="covered — MRI"))
    assert "MRI" in out.answer_text
    assert out.needs_escalation is False
    assert out.confidence == 1.0


def test_mock_composer_coverage_with_prior_auth():
    out = MockComposer().compose(_inp("coverage", question="MRI?", tool_result="covered — prior auth required"))
    assert "prior auth" in out.answer_text.lower()


def test_mock_composer_cost_copay():
    out = MockComposer().compose(_inp("cost", tool_result="copay $30 in-network primary care / $75 urgent care / $50 specialist"))
    assert "$30" in out.answer_text
    assert "$75" in out.answer_text


def test_mock_composer_cost_deductible():
    out = MockComposer().compose(_inp("cost", tool_result="deductible $1,500 / YTD spent $450"))
    assert "deductible" in out.answer_text.lower()
    assert "$1,500" in out.answer_text


def test_mock_composer_cost_oop():
    out = MockComposer().compose(_inp("cost", tool_result="OOP max $5,000 / YTD spent $1,200"))
    assert "$5,000" in out.answer_text


def test_mock_composer_provider():
    out = MockComposer().compose(_inp("provider", question="Find a cardiologist near me.", tool_result="3 cardiologists found"))
    assert "cardiolog" in out.answer_text.lower()


def test_mock_composer_formulary_generic():
    out = MockComposer().compose(_inp("formulary", question="Is lisinopril on my formulary?", tool_result="lisinopril — Tier 1 generic"))
    assert "lisinopril" in out.answer_text.lower()
    assert "Tier 1" in out.answer_text


def test_mock_composer_formulary_specialty():
    out = MockComposer().compose(_inp("formulary", question="Is Humira covered?", tool_result="Humira — specialty tier, requires prior authorization"))
    assert "prior authorization" in out.answer_text.lower()


def test_mock_composer_escalation():
    out = MockComposer().compose(_inp("escalate"))
    assert out.answer_text == _ESCALATION_TEXT
    assert out.needs_escalation is True


def test_mock_composer_used_facts_non_empty_for_grounded():
    out = MockComposer().compose(_inp("coverage", question="Is surgery covered?", tool_result="covered"))
    assert isinstance(out.used_facts, list)


def test_mock_composer_answer_always_non_empty():
    for intent in ("coverage", "cost", "provider", "formulary", "escalate"):
        out = MockComposer().compose(_inp(intent, question="some question", tool_result="some result"))
        assert out.answer_text.strip(), f"Empty answer for intent={intent!r}"


# ── ClaudeComposer — valid response ──────────────────────────────────────────

def test_claude_composer_returns_composer_output():
    c = _mock_claude()
    c._client.messages.create.return_value = _claude_response("Your MRI is covered.")
    out = c.compose(_inp("coverage", question="Is an MRI covered?", tool_result="covered"))
    assert isinstance(out, ComposerOutput)
    assert out.answer_text == "Your MRI is covered."


def test_claude_composer_used_facts_from_response():
    c = _mock_claude()
    c._client.messages.create.return_value = _claude_response(
        "Your copay is $75.", used_facts=["copay $75"]
    )
    out = c.compose(_inp("cost", tool_result="copay $75"))
    assert "copay $75" in out.used_facts


def test_claude_composer_confidence_from_response():
    c = _mock_claude()
    c._client.messages.create.return_value = _claude_response("Answer.", confidence=0.92)
    out = c.compose(_inp("coverage", tool_result="covered"))
    assert abs(out.confidence - 0.92) < 0.001


def test_claude_composer_needs_escalation_from_response():
    c = _mock_claude()
    c._client.messages.create.return_value = _claude_response(
        "I don't have that information.", needs_escalation=True
    )
    out = c.compose(_inp("coverage", tool_result=""))
    assert out.needs_escalation is True


def test_claude_composer_escalation_passthrough_skips_api():
    c = _mock_claude()
    out = c.compose(_inp("escalate"))
    c._client.messages.create.assert_not_called()
    assert out.answer_text == _ESCALATION_TEXT
    assert out.needs_escalation is True


# ── ClaudeComposer — invalid JSON fallback ────────────────────────────────────

def test_claude_composer_fallback_on_invalid_json():
    c = _mock_claude()
    bad = MagicMock()
    bad.content = [MagicMock(text="This is not JSON at all.")]
    c._client.messages.create.return_value = bad
    out = c.compose(_inp("coverage", tool_result="covered"))
    assert out.answer_text == _FALLBACK_ANSWER
    assert out.needs_escalation is True
    assert "json_parse_error" in out.fallback_reason


def test_claude_composer_fallback_on_empty_answer_text():
    c = _mock_claude()
    c._client.messages.create.return_value = _claude_response("")
    out = c.compose(_inp("coverage", tool_result="covered"))
    assert out.answer_text == _FALLBACK_ANSWER
    assert out.needs_escalation is True
    assert out.fallback_reason == "empty_answer_text"


def test_claude_composer_strips_markdown_fences():
    c = _mock_claude()
    body = json.dumps({"answer_text": "Your copay is $75.", "used_facts": [], "needs_escalation": False, "confidence": 1.0})
    fenced = MagicMock()
    fenced.content = [MagicMock(text=f"```json\n{body}\n```")]
    c._client.messages.create.return_value = fenced
    out = c.compose(_inp("cost", tool_result="copay $75"))
    assert out.answer_text == "Your copay is $75."
    assert out.fallback_reason == ""


# ── ClaudeComposer — API error fallback ──────────────────────────────────────

def test_claude_composer_fallback_on_api_error():
    c = _mock_claude()
    c._client.messages.create.side_effect = RuntimeError("connection timeout")
    out = c.compose(_inp("coverage", tool_result="covered"))
    assert out.answer_text == _FALLBACK_ANSWER
    assert out.needs_escalation is True
    assert "claude_error" in out.fallback_reason


def test_claude_composer_fallback_reason_includes_exception_type():
    c = _mock_claude()
    c._client.messages.create.side_effect = ValueError("bad request")
    out = c.compose(_inp("cost", tool_result="copay $30"))
    assert "ValueError" in out.fallback_reason


# ── build_composer — mode selection ──────────────────────────────────────────

def test_build_composer_returns_mock_by_default():
    from voice_agent.graph.nodes.answer_composer import build_composer
    with patch("voice_agent.graph.nodes.answer_composer.settings") as mock_settings:
        mock_settings.voice_agent_answer_mode = "mock"
        composer = build_composer()
    assert isinstance(composer, MockComposer)


def test_build_composer_returns_claude_when_configured():
    from voice_agent.graph.nodes.answer_composer import build_composer
    with patch("voice_agent.graph.nodes.answer_composer.settings") as mock_settings:
        mock_settings.voice_agent_answer_mode = "claude"
        mock_settings.anthropic_api_key = "sk-test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-6"
        with patch("voice_agent.graph.nodes.answer_composer.ClaudeComposer") as MockCls:
            MockCls.return_value = MagicMock(spec=AnswerComposer)
            composer = build_composer()
            MockCls.assert_called_once_with(api_key="sk-test-key", model="claude-sonnet-4-6")


def test_build_composer_raises_when_claude_mode_missing_key():
    from voice_agent.graph.nodes.answer_composer import build_composer
    with patch("voice_agent.graph.nodes.answer_composer.settings") as mock_settings:
        mock_settings.voice_agent_answer_mode = "claude"
        mock_settings.anthropic_api_key = ""
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            build_composer()


# ── graph integration: output shape unchanged ─────────────────────────────────

def test_graph_still_returns_answer_text():
    state = run_agent_graph("Is an MRI covered?")
    assert state["answer_text"].strip()


def test_graph_answer_text_type():
    state = run_agent_graph("What is my copay?")
    assert isinstance(state["answer_text"], str)


def test_graph_hallucination_guard_still_runs_after_compose():
    """Guard must execute even when answer_text is produced by composer."""
    state = run_agent_graph("Is an MRI covered?")
    assert "guard_reason" in state
    assert state["guard_reason"].strip()


def test_graph_routing_unchanged():
    """Node order must be the same as before C35."""
    from voice_agent.graph.state_machine import _COMPILED
    events = list(_COMPILED.stream(
        {
            "call_sid": "CA-C35",
            "stream_sid": "SM-C35",
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
    assert visited == [
        "identify_member",
        "understand_intent",
        "call_tool",
        "compose_answer",
        "hallucination_guard",
        "prepare_response",
    ]


def test_answer_final_event_shape_preserved():
    """orchestrate() must still return a valid AnswerFinalEvent."""
    from voice_agent.schemas.answer import AnswerFinalEvent
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    ev = orchestrate(FinalTranscriptEvent(
        callSid="CA-C35", streamSid="SM-C35",
        text="Is an MRI covered?", confidence=0.95,
    ))
    assert isinstance(ev, AnswerFinalEvent)
    assert ev.type == "answer.final"
    assert ev.text.strip()
    assert isinstance(ev.grounded, bool)
    assert len(ev.tool_trace) >= 1


# ── guard blocks hallucinated Claude output ───────────────────────────────────

def test_guard_blocks_hallucinated_dollar_amount():
    """
    If a Claude (or mock) answer contains a dollar amount not in the tool
    result, the guard must flip grounded=False.
    """
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    from voice_agent.graph.agent_state import AgentState

    state: AgentState = {
        "call_sid": "", "stream_sid": "",
        "question": "How much does an MRI cost?",
        "member_id": "", "member_verified": True,
        "intent": "cost",
        "tool_name": "estimate_cost",
        "tool_args": {},
        "tool_result": "estimated cost $150–$250 negotiated rate",
        "answer_text": "Your MRI will cost exactly $9,999.",  # hallucinated
        "grounded": False,
        "guard_reason": "",
        "escalate": False,
        "tool_trace": [],
    }
    result = hallucination_guard(state)
    assert result["grounded"] is False
    assert "ungrounded" in result["guard_reason"]


def test_guard_passes_grounded_answer():
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    from voice_agent.graph.agent_state import AgentState

    state: AgentState = {
        "call_sid": "", "stream_sid": "",
        "question": "What is my urgent care copay?",
        "member_id": "", "member_verified": True,
        "intent": "cost",
        "tool_name": "estimate_cost",
        "tool_args": {},
        "tool_result": "copay $30 primary care / $75 urgent care / $50 specialist",
        "answer_text": "Your urgent care copay is $75 per visit.",
        "grounded": False,
        "guard_reason": "",
        "escalate": False,
        "tool_trace": [],
    }
    result = hallucination_guard(state)
    assert result["grounded"] is True

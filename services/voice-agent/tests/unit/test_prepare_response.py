"""Unit tests for prepare_response — 'narrate only if grounded' for benefit figures.

Suppression is scoped to cost/coverage/formulary (answers that assert copays,
deductibles, tiers, or coverage decisions). Provider listings are not gated, so
a flaky guard flag never escalates a legitimate directory result.
"""

from __future__ import annotations

import pytest

from voice_agent.graph.nodes.prepare_response import _UNVERIFIED_FALLBACK, prepare_response


@pytest.mark.parametrize("intent", ["cost", "coverage", "formulary"])
def test_ungrounded_benefit_answer_is_replaced_and_escalated(intent: str) -> None:
    """A cost/coverage/formulary answer that failed the guard must not surface the claim."""
    state = {
        "intent": intent,
        "grounded": False,
        "answer_text": "Your out-of-network ER copay is $250.",
        "tool_trace": [{"tool": "estimate_cost", "ok": True}],
    }
    out = prepare_response(state)

    assert out["answer_text"] == _UNVERIFIED_FALLBACK
    assert "$250" not in out["answer_text"]
    assert out["escalate"] is True
    assert out["tool_trace"][0]["ok"] is False  # guard result reflected onto the entry


def test_ungrounded_provider_answer_is_not_suppressed() -> None:
    """Provider listings are not gated — a flaky guard flag must not escalate them."""
    answer = "I found three cardiologists near you: James Whitfield, Henry Cho, Maria Reyes."
    state = {
        "intent": "provider",
        "grounded": False,
        "answer_text": answer,
        "tool_trace": [{"tool": "find_provider", "ok": True}],
    }
    out = prepare_response(state)

    assert out["answer_text"] == answer  # the directory result is still shown
    assert out["escalate"] is False
    assert out["tool_trace"][0]["ok"] is False  # guard verdict still reflected


def test_grounded_benefit_answer_is_preserved() -> None:
    """Grounded answers pass through unchanged and do not escalate."""
    answer = "Yes, an MRI is covered at 20% coinsurance, prior authorization required."
    state = {
        "intent": "coverage",
        "grounded": True,
        "answer_text": answer,
        "tool_trace": [{"tool": "check_coverage", "ok": True}],
    }
    out = prepare_response(state)

    assert out["answer_text"] == answer
    assert out["escalate"] is False
    assert out["tool_trace"][0]["ok"] is True


def test_escalate_intent_answer_is_left_untouched() -> None:
    """Genuine escalations already carry a safe message — don't overwrite it."""
    escalation = "Let me connect you with a benefits specialist who can help."
    state = {
        "intent": "escalate",
        "grounded": False,
        "answer_text": escalation,
        "tool_trace": [{"tool": "escalate_to_human", "ok": False}],
    }
    out = prepare_response(state)

    assert out["answer_text"] == escalation  # not replaced with the unverified fallback
    assert out["escalate"] is True
    assert out["tool_trace"][0]["ok"] is False  # escalate_to_human stays ok=False

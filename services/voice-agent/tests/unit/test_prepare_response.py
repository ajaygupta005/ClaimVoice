"""Unit tests for prepare_response — enforces 'Claude narrates only if grounded'."""

from __future__ import annotations

from voice_agent.graph.nodes.prepare_response import _UNVERIFIED_FALLBACK, prepare_response


def test_ungrounded_factual_answer_is_replaced_and_escalated() -> None:
    """A factual intent whose answer failed the guard must not surface the claim."""
    state = {
        "intent": "cost",
        "grounded": False,
        "answer_text": "Your out-of-network ER copay is $250.",
        "tool_trace": [{"tool": "estimate_cost", "ok": True}],
    }
    out = prepare_response(state)

    assert out["answer_text"] == _UNVERIFIED_FALLBACK
    assert "$250" not in out["answer_text"]
    assert out["escalate"] is True
    # guard result is reflected onto the real-tool entry
    assert out["tool_trace"][0]["ok"] is False


def test_grounded_factual_answer_is_preserved() -> None:
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

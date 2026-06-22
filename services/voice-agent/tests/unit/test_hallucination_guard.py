"""Unit tests for the hallucination guard (in-process matcher + http + fallback)."""

from __future__ import annotations

import voice_agent.guards.hallucination as g
from voice_agent.graph.nodes.hallucination_guard import hallucination_guard


def test_grounded_amount():
    result = g.check_in_process("Your copay is $75.", ["urgent care copay $75"])
    assert result.grounded and result.unsupported_claims == []


def test_ungrounded_amount():
    result = g.check_in_process("It costs $999.", ["copay $75"])
    assert not result.grounded and "$999" in result.unsupported_claims


def test_grounded_tier():
    result = g.check_in_process("Lisinopril is Tier 1.", ["Lisinopril is on formulary, Tier 1"])
    assert result.grounded


def test_ungrounded_tier():
    result = g.check_in_process("Humira is Tier 2.", ["Humira is on formulary, Tier 4"])
    assert not result.grounded and any("Tier 2" in u for u in result.unsupported_claims)


def test_prior_auth_ungrounded_when_facts_silent():
    result = g.check_in_process("Prior authorization required.", ["MRI is covered"])
    assert not result.grounded


def test_fact_check_http(monkeypatch):
    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"grounded": False, "guardReason": "ungrounded claims: ['$999']"}

    monkeypatch.setattr(g.httpx, "post", lambda *a, **k: _R())
    result = g.fact_check("It costs $999.", ["copay $75"], "http", "http://x")
    assert result.grounded is False
    assert "ungrounded" in result.reason


def test_fact_check_http_falls_back(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("backend down")

    monkeypatch.setattr(g.httpx, "post", boom)
    result = g.fact_check("It costs $999.", ["copay $75"], "http", "http://x")
    assert result.grounded is False  # in-process fallback still flags it


def _provider_state(data_source: str, ok: bool) -> dict:
    return {
        "intent": "provider",
        "answer_text": "I found three cardiologists near you: James Whitfield, Henry Cho, Maria Reyes.",
        "tool_result": "3 cardiologist providers found near you — James Whitfield 0.2 km",
        "tool_facts": ["James Whitfield 0.2 km (in-network)"],
        "tool_trace": [{"tool": "find_provider", "data_source": data_source, "ok": ok}],
        "rag_chunks": [],
        "guard_reason_code": "",
        "guard_supported_by": [],
        "guard_unsupported_claims": [],
        "guard_rag_facts_used": 0,
    }


def test_node_provider_real_directory_is_grounded():
    """A successful real directory result is grounded without invoking the judge."""
    s = hallucination_guard(_provider_state("real", True))
    assert s["grounded"] is True
    assert s["guard_supported_by"] == ["structured_tool"]
    assert s["guard_unsupported_claims"] == []


def test_node_provider_demo_falls_through_to_matcher():
    """Demo-mode providers don't hit the real-directory shortcut (still grounded via matcher)."""
    s = hallucination_guard(_provider_state("demo", True))
    # No $/tier/coverage claims in the listing → in-process matcher passes it too,
    # but via the normal path, not the real-directory shortcut.
    assert s["grounded"] is True
    assert s["guard_reason"] != "provider listing sourced from the real directory"


def test_node_escalate_passes():
    s = hallucination_guard({
        "intent": "escalate",
        "answer_text": "x",
        "tool_result": "",
        "tool_facts": [],
        "rag_chunks": [],
        "guard_reason_code": "",
        "guard_supported_by": [],
        "guard_unsupported_claims": [],
        "guard_rag_facts_used": 0,
    })
    assert s["grounded"] is False
    assert "escalat" in s["guard_reason"].lower()

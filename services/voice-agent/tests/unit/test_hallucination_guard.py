"""Unit tests for the hallucination guard (in-process matcher + http + fallback)."""

from __future__ import annotations

import voice_agent.guards.hallucination as g
from voice_agent.graph.nodes.hallucination_guard import hallucination_guard


def test_grounded_amount():
    ok, ung = g.check_in_process("Your copay is $75.", ["urgent care copay $75"])
    assert ok and ung == []


def test_ungrounded_amount():
    ok, ung = g.check_in_process("It costs $999.", ["copay $75"])
    assert not ok and "$999" in ung


def test_grounded_tier():
    ok, _ = g.check_in_process("Lisinopril is Tier 1.", ["Lisinopril is on formulary, Tier 1"])
    assert ok


def test_ungrounded_tier():
    ok, ung = g.check_in_process("Humira is Tier 2.", ["Humira is on formulary, Tier 4"])
    assert not ok and any("Tier 2" in u for u in ung)


def test_prior_auth_ungrounded_when_facts_silent():
    ok, _ = g.check_in_process("Prior authorization required.", ["MRI is covered"])
    assert not ok


def test_fact_check_http(monkeypatch):
    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"grounded": False, "guardReason": "ungrounded claims: ['$999']"}

    monkeypatch.setattr(g.httpx, "post", lambda *a, **k: _R())
    grounded, reason = g.fact_check("It costs $999.", ["copay $75"], "http", "http://x")
    assert grounded is False
    assert "ungrounded" in reason


def test_fact_check_http_falls_back(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("backend down")

    monkeypatch.setattr(g.httpx, "post", boom)
    grounded, _ = g.fact_check("It costs $999.", ["copay $75"], "http", "http://x")
    assert grounded is False  # in-process fallback still flags it


def test_node_escalate_passes():
    s = hallucination_guard({"intent": "escalate", "answer_text": "x", "tool_result": ""})
    assert s["grounded"] is False
    assert "escalat" in s["guard_reason"].lower()

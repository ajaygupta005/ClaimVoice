"""Unit tests for Component 37 — strengthened intent routing and tool dispatch."""

from __future__ import annotations

import pytest

from voice_agent.graph.nodes.understand_intent import understand_intent
from voice_agent.graph.nodes.call_tool import call_tool


# ── Helpers ────────────────────────────────────────────────────────────────────

def _intent(question: str) -> str:
    state = understand_intent(
        {"question": question, "member_id": "CVX-0042-MT", "member_verified": True}
    )
    return state["intent"]


def _tool_result(question: str) -> str:
    state = understand_intent(
        {"question": question, "member_id": "CVX-0042-MT", "member_verified": True}
    )
    state = call_tool(state)
    return state["tool_result"]


# ── Intent routing tests ───────────────────────────────────────────────────────

def test_where_can_i_get_xray_not_escalate():
    """Dual-signal: 'where can I get an x-ray' must not route to escalate."""
    result = _intent("where can I get an x-ray")
    assert result in ("coverage", "provider"), (
        f"Expected 'coverage' or 'provider', got '{result}'"
    )


def test_find_primary_care_doctor():
    result = _intent("find a primary care doctor near me")
    assert result == "provider"


def test_dental_cleaning_covered():
    result = _intent("is dental cleaning covered")
    assert result == "coverage"


def test_annual_physical_free():
    result = _intent("is annual physical free")
    assert result == "coverage"


def test_what_can_you_help_me_with():
    result = _intent("what can you help me with")
    assert result == "help"


def test_claim_denied_escalates():
    result = _intent("my claim was denied")
    assert result == "escalate"


# ── call_tool tests ────────────────────────────────────────────────────────────

def test_coverage_xray_contains_covered():
    result = _tool_result("is an x-ray covered under my plan")
    assert "covered" in result.lower(), f"Expected 'covered' in result, got: {result}"


def test_coverage_dental_contains_dental():
    result = _tool_result("is dental cleaning covered")
    assert "dental" in result.lower(), f"Expected 'dental' in result, got: {result}"


def test_provider_primary_care_contains_primary_care():
    result = _tool_result("find a primary care doctor near me")
    assert "primary care" in result.lower(), f"Expected 'primary care' in result, got: {result}"


def test_provider_xray_contains_imaging():
    result = _tool_result("where can I get an x-ray near me")
    assert "imaging" in result.lower(), f"Expected 'imaging' in result, got: {result}"

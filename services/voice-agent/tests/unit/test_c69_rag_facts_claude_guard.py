"""
Component 69 — RAG Facts for Claude and Guard tests.

Tests:
- check_in_process: pass with structured tool facts only
- check_in_process: pass with RAG chunk facts only (no structured facts)
- check_in_process: pass with both structured + RAG facts
- check_in_process: fail on unsupported dollar amount
- check_in_process: fail on unsupported coverage status
- check_in_process: fail on unsupported prior auth claim
- check_in_process: fail on unsupported tier
- check_in_process: no_facts_available when both fact sets are empty
- GuardResult.reason_code distinguishes structured vs RAG sources
- GuardResult.supported_by populated correctly
- GuardResult.rag_facts_used counts RAG chunks consumed
- hallucination_guard node passes guard_reason_code, guard_supported_by into state
- compose_answer passes rag_chunks to ComposerInput
- ClaudeComposer user payload includes sbc_chunks when chunks present
- ClaudeComposer user payload has empty sbc_chunks when no chunks
- run_agent_graph returns guard metadata fields
- /api/v1/agent/respond includes guardReasonCode, supportedBy, guardPassed
- supportedBy contains "structured_tool" for normal mock-mode answers
- unsupportedClaims populated on guard failure
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from voice_agent.guards.hallucination import GuardResult, check_in_process, fact_check
from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── Synthetic RAG chunk helpers ───────────────────────────────────────────────

def _chunk(text: str, section: str = "Benefits") -> dict:
    return {"chunk_text": text, "section_name": section, "source_file": "sbc.pdf", "distance": 0.1}


# ── check_in_process: structured tool facts only ─────────────────────────────

def test_guard_pass_structured_facts_only():
    result = check_in_process(
        "Your copay is $30 for a primary care visit.",
        facts=["copay $30 primary care"],
    )
    assert result.grounded is True
    assert result.reason_code == "supported_by_structured_tool"
    assert "structured_tool" in result.supported_by
    assert result.unsupported_claims == []


def test_guard_pass_dollar_amount_in_facts():
    result = check_in_process(
        "Your deductible is $1,500.",
        facts=["annual deductible $1,500"],
    )
    assert result.grounded is True
    assert result.unsupported_claims == []


def test_guard_fail_dollar_amount_not_in_facts():
    result = check_in_process(
        "Your deductible is $9,999.",
        facts=["annual deductible $1,500"],
    )
    assert result.grounded is False
    assert result.reason_code == "unsupported_claim"
    assert "$9,999" in result.unsupported_claims


def test_guard_fail_unsupported_coverage_status():
    result = check_in_process(
        "MRI is not covered under your plan.",
        facts=["MRI is covered"],
    )
    assert result.grounded is False
    assert "not covered" in result.unsupported_claims


def test_guard_fail_unsupported_prior_auth():
    # Guard triggers on the exact phrase "prior authorization required" or "prior auth required"
    result = check_in_process(
        "Prior authorization required before scheduling this service.",
        facts=["service is covered"],
    )
    assert result.grounded is False
    assert "prior authorization required" in result.unsupported_claims


def test_guard_pass_prior_authorization_full_phrase():
    result = check_in_process(
        "Prior authorization required before scheduling this service.",
        facts=["MRI is covered", "prior authorization required"],
    )
    assert result.grounded is True
    assert result.unsupported_claims == []


def test_guard_fail_unsupported_tier():
    result = check_in_process(
        "Lisinopril is a Tier 3 medication.",
        facts=["lisinopril is covered"],
    )
    assert result.grounded is False
    assert any("Tier 3" in c or "tier 3" in c.lower() for c in result.unsupported_claims)


# ── check_in_process: RAG chunks as grounding ─────────────────────────────────

def test_guard_pass_rag_chunk_facts_only():
    """Amount and coverage status are in RAG chunks, not structured facts."""
    chunks = [_chunk("copay is $30 for urgent care visits", "Cost Sharing")]
    result = check_in_process(
        "Your copay is $30 for urgent care.",
        facts=[],       # no structured facts
        rag_chunks=chunks,
    )
    assert result.grounded is True
    assert result.reason_code == "supported_by_sbc_rag"
    assert "sbc_rag" in result.supported_by
    assert "structured_tool" not in result.supported_by
    assert result.rag_facts_used == 1


def test_guard_pass_both_structured_and_rag():
    chunks = [_chunk("MRI imaging covered after prior auth", "Imaging")]
    result = check_in_process(
        "MRI is covered under your plan and $200 applies toward your deductible.",
        facts=["MRI covered, deductible $200"],
        rag_chunks=chunks,
    )
    assert result.grounded is True
    assert "structured_tool" in result.supported_by
    assert "sbc_rag" in result.supported_by
    assert result.rag_facts_used == 1


def test_guard_rag_not_used_when_answer_grounded_by_structured():
    """When structured facts alone ground the answer, rag_facts_used still counts chunks."""
    chunks = [_chunk("some supplementary text")]
    result = check_in_process(
        "Your copay is $30.",
        facts=["copay $30"],
        rag_chunks=chunks,
    )
    assert result.grounded is True
    # Both sources present — both in supported_by
    assert "structured_tool" in result.supported_by
    assert result.rag_facts_used == 1


def test_guard_no_facts_available():
    result = check_in_process(
        "Your copay is $30.",
        facts=[],
        rag_chunks=[],
    )
    assert result.grounded is False
    assert result.reason_code == "no_facts_available"
    assert result.rag_facts_used == 0


def test_guard_fail_amount_not_in_rag_either():
    chunks = [_chunk("copay is $30 for urgent care")]
    result = check_in_process(
        "Your deductible is $9,999.",
        facts=[],
        rag_chunks=chunks,
    )
    assert result.grounded is False
    assert "$9,999" in result.unsupported_claims


# ── fact_check (http mode falls back to in-process) ──────────────────────────

def test_fact_check_mock_mode_returns_guard_result():
    result = fact_check(
        "Your copay is $30.",
        facts=["copay $30"],
        mode="mock",
        base_url="http://localhost:8002",
    )
    assert isinstance(result, GuardResult)
    assert result.grounded is True
    assert result.reason_code == "supported_by_structured_tool"


def test_fact_check_http_mode_falls_back_on_connection_error():
    with patch("httpx.post", side_effect=Exception("connection refused")):
        result = fact_check(
            "Your copay is $30.",
            facts=["copay $30"],
            mode="http",
            base_url="http://localhost:8002",
        )
    assert result.grounded is True  # falls back to in-process


def test_fact_check_passes_rag_facts_to_in_process():
    chunks = [_chunk("$30 urgent care copay")]
    result = fact_check(
        "Your copay is $30.",
        facts=[],
        mode="mock",
        base_url="http://localhost:8002",
        rag_chunks=chunks,
    )
    assert result.grounded is True
    assert result.reason_code == "supported_by_sbc_rag"


# ── hallucination_guard node ──────────────────────────────────────────────────

def _guard_state(answer: str, facts: list[str], rag_chunks: list[dict] | None = None) -> dict:
    return {
        "intent": "coverage",
        "answer_text": answer,
        "tool_result": "",
        "tool_facts": facts,
        "rag_chunks": rag_chunks or [],
        "guard_reason_code": "",
        "guard_supported_by": [],
        "guard_unsupported_claims": [],
        "guard_rag_facts_used": 0,
    }


def test_hallucination_guard_node_populates_reason_code():
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    state = hallucination_guard(_guard_state("Your copay is $30.", ["copay $30"]))
    assert state["grounded"] is True
    assert state["guard_reason_code"] == "supported_by_structured_tool"
    assert "structured_tool" in state["guard_supported_by"]


def test_hallucination_guard_node_reason_code_unsupported():
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    state = hallucination_guard(_guard_state("Your deductible is $9,999.", ["deductible $1,500"]))
    assert state["grounded"] is False
    assert state["guard_reason_code"] == "unsupported_claim"
    assert "$9,999" in state["guard_unsupported_claims"]


def test_hallucination_guard_node_rag_chunks_used():
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    chunks = [_chunk("copay $30 urgent care")]
    state = hallucination_guard(_guard_state("Your copay is $30.", [], chunks))
    assert state["grounded"] is True
    assert state["guard_rag_facts_used"] == 1
    assert "sbc_rag" in state["guard_supported_by"]


def test_hallucination_guard_node_escalate_bypass():
    from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
    state = hallucination_guard({
        "intent": "escalate",
        "answer_text": "Let me connect you with a specialist.",
        "tool_result": "",
        "tool_facts": [],
        "rag_chunks": [],
        "guard_reason_code": "",
        "guard_supported_by": [],
        "guard_unsupported_claims": [],
        "guard_rag_facts_used": 0,
    })
    assert state["grounded"] is False
    assert "escalated" in state["guard_reason"]


# ── compose_answer passes rag_chunks ─────────────────────────────────────────

def test_compose_answer_passes_rag_chunks_to_input():
    """compose_answer must thread rag_chunks into ComposerInput."""
    from voice_agent.graph.nodes import compose_answer as ca_mod
    from voice_agent.graph.nodes.answer_composer import ComposerInput

    captured: list[ComposerInput] = []

    class _SpyComposer:
        def compose(self, inp: ComposerInput):
            captured.append(inp)
            from voice_agent.graph.nodes.answer_composer import ComposerOutput
            return ComposerOutput(answer_text="ok")

    original = ca_mod._composer
    try:
        ca_mod._composer = _SpyComposer()
        ca_mod.compose_answer({
            "question": "Is MRI covered?",
            "intent": "coverage",
            "tool_name": "check_coverage",
            "tool_args": {},
            "tool_result": "covered",
            "rag_chunks": [_chunk("MRI is covered per plan SBC")],
        })
    finally:
        ca_mod._composer = original

    assert len(captured) == 1
    assert len(captured[0].rag_chunks) == 1
    assert captured[0].rag_chunks[0]["chunk_text"] == "MRI is covered per plan SBC"


def test_compose_answer_empty_rag_chunks_when_none_in_state():
    from voice_agent.graph.nodes import compose_answer as ca_mod
    from voice_agent.graph.nodes.answer_composer import ComposerInput

    captured: list[ComposerInput] = []

    class _SpyComposer:
        def compose(self, inp: ComposerInput):
            captured.append(inp)
            from voice_agent.graph.nodes.answer_composer import ComposerOutput
            return ComposerOutput(answer_text="ok")

    original = ca_mod._composer
    try:
        ca_mod._composer = _SpyComposer()
        ca_mod.compose_answer({
            "question": "Is MRI covered?",
            "intent": "coverage",
            "tool_name": "check_coverage",
            "tool_args": {},
            "tool_result": "covered",
            # rag_chunks intentionally absent
        })
    finally:
        ca_mod._composer = original

    assert captured[0].rag_chunks == []


# ── ClaudeComposer user payload ───────────────────────────────────────────────

def test_claude_composer_payload_includes_sbc_chunks():
    """When rag_chunks are present, the user payload must contain sbc_chunks."""
    from voice_agent.graph.nodes.answer_composer import ClaudeComposer, ComposerInput

    captured_payloads: list[str] = []

    class _FakeMsg:
        content = [MagicMock(text='{"answer_text":"ok","used_facts":[],"needs_escalation":false,"confidence":1.0}')]

    class _FakeClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                captured_payloads.append(kwargs["messages"][0]["content"])
                return _FakeMsg()

    composer = ClaudeComposer.__new__(ClaudeComposer)
    composer._client = _FakeClient()
    composer._model = "claude-sonnet-4-6"

    inp = ComposerInput(
        question="Is MRI covered?",
        intent="coverage",
        tool_name="check_coverage",
        tool_args={},
        tool_result="MRI is covered",
        rag_chunks=[_chunk("MRI requires prior authorization per plan document")],
    )
    composer.compose(inp)

    import json
    payload = json.loads(captured_payloads[0])
    assert "sbc_chunks" in payload
    assert len(payload["sbc_chunks"]) == 1
    assert payload["sbc_chunks"][0]["chunkText"] == "MRI requires prior authorization per plan document"


def test_claude_composer_payload_empty_chunks_when_none():
    from voice_agent.graph.nodes.answer_composer import ClaudeComposer, ComposerInput

    captured_payloads: list[str] = []

    class _FakeMsg:
        content = [MagicMock(text='{"answer_text":"ok","used_facts":[],"needs_escalation":false,"confidence":1.0}')]

    class _FakeClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                captured_payloads.append(kwargs["messages"][0]["content"])
                return _FakeMsg()

    composer = ClaudeComposer.__new__(ClaudeComposer)
    composer._client = _FakeClient()
    composer._model = "claude-sonnet-4-6"

    inp = ComposerInput(
        question="Is MRI covered?",
        intent="coverage",
        tool_name="check_coverage",
        tool_args={},
        tool_result="MRI is covered",
        rag_chunks=[],  # empty
    )
    composer.compose(inp)

    import json
    payload = json.loads(captured_payloads[0])
    assert "sbc_chunks" in payload
    assert payload["sbc_chunks"] == []


# ── Graph integration ─────────────────────────────────────────────────────────

def test_run_agent_graph_returns_guard_metadata_fields():
    from voice_agent.graph.state_machine import run_agent_graph
    state = run_agent_graph("Is an MRI covered?")
    assert "guard_reason_code" in state
    assert "guard_supported_by" in state
    assert "guard_unsupported_claims" in state
    assert "guard_rag_facts_used" in state


def test_run_agent_graph_normal_answer_passes_guard():
    from voice_agent.graph.state_machine import run_agent_graph
    state = run_agent_graph("Is an MRI covered?")
    assert state["grounded"] is True
    assert state["guard_reason_code"] == "supported_by_structured_tool"
    assert "structured_tool" in state["guard_supported_by"]


# ── HTTP endpoint ─────────────────────────────────────────────────────────────

def test_agent_respond_includes_guard_metadata(client: TestClient):
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    assert resp.status_code == 200
    data = resp.json()
    rag = data["rag"]
    assert "guardPassed" in rag
    assert "guardReasonCode" in rag
    assert "supportedBy" in rag
    assert "unsupportedClaims" in rag
    assert "ragFactsUsed" in rag


def test_agent_respond_guard_passed_true_for_coverage_answer(client: TestClient):
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    data = resp.json()
    rag = data["rag"]
    assert rag["guardPassed"] is True
    assert rag["guardReasonCode"] == "supported_by_structured_tool"
    assert "structured_tool" in rag["supportedBy"]
    assert rag["unsupportedClaims"] == []


def test_agent_respond_guard_reason_code_present_for_cost_answer(client: TestClient):
    resp = client.post("/api/v1/agent/respond", json={
        "question": "What is my copay?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    data = resp.json()
    rag = data["rag"]
    assert rag["guardReasonCode"] != ""

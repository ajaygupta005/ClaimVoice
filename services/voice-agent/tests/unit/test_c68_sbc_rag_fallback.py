"""
Component 68 — SBC RAG Tool Fallback tests.

Tests:
- RagResult dataclass and to_dict() produce correct metadata
- should_attempt_rag: coverage always → True, formulary on failure → True, others → False
- retrieve(): successful response with chunks
- retrieve(): empty chunks (200 + chunks=[])
- retrieve(): 503 missing VOYAGE_API_KEY → rag_key_missing
- retrieve(): timeout → rag_timeout
- retrieve(): request error → rag_service_unavailable
- retrieve(): missing plan_id → missing_plan_id
- retrieve(): HTTP 500 → rag_http_500
- sbc_rag_fallback node: mock mode → no-op (rag_mock_mode)
- sbc_rag_fallback node: http mode, coverage → calls retrieve
- sbc_rag_fallback node: http mode, formulary, tool_ok → not attempted
- sbc_rag_fallback node: http mode, formulary, tool error → calls retrieve
- sbc_rag_fallback node: cost intent → not attempted
- sbc_rag_fallback node: provider intent → not attempted
- run_agent_graph returns RAG metadata fields
- Structured tools still work when RAG is unavailable (mock mode baseline)
- /api/v1/agent/respond response includes rag metadata
- rag.ragAttempted=False when tool_mode=mock
- rag does not expose secrets or raw chunks in HTTP response
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import httpx
from fastapi.testclient import TestClient

from voice_agent.main import app
from voice_agent.tools.sbc_rag_client import (
    RagResult,
    SBCChunk,
    _NOT_ATTEMPTED,
    retrieve,
    should_attempt_rag,
)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── RagResult dataclass ───────────────────────────────────────────────────────

def test_rag_result_default_not_attempted():
    r = RagResult()
    assert r.attempted is False
    assert r.available is False
    assert r.chunks == []
    assert r.chunks_count == 0
    assert r.fallback_reason == ""


def test_rag_result_to_dict_structure():
    r = RagResult(
        attempted=True,
        available=True,
        chunks=[SBCChunk("text", "section", "file.pdf", 0.1)],
        fallback_reason="",
        source="eligibility-sbc-rag",
    )
    d = r.to_dict()
    assert d["ragAttempted"] is True
    assert d["ragAvailable"] is True
    assert d["ragChunksCount"] == 1
    assert d["ragFallbackReason"] == ""
    assert d["ragSource"] == "eligibility-sbc-rag"


def test_rag_result_to_dict_no_secrets():
    r = RagResult(attempted=True, available=False, fallback_reason="rag_key_missing")
    d = r.to_dict()
    serialized = json.dumps(d)
    # Must not contain any credential-like values
    assert "key" not in serialized.lower() or "key_missing" in serialized
    assert "voyage" not in serialized.lower()
    assert "api_key" not in serialized.lower()


# ── should_attempt_rag ────────────────────────────────────────────────────────

def test_coverage_always_attempts_rag():
    assert should_attempt_rag("coverage", tool_ok=True) is True
    assert should_attempt_rag("coverage", tool_ok=False) is True


def test_formulary_attempts_rag_only_on_failure():
    assert should_attempt_rag("formulary", tool_ok=False) is True
    assert should_attempt_rag("formulary", tool_ok=True) is False


def test_cost_never_attempts_rag():
    assert should_attempt_rag("cost", tool_ok=True) is False
    assert should_attempt_rag("cost", tool_ok=False) is False


def test_provider_never_attempts_rag():
    assert should_attempt_rag("provider", tool_ok=True) is False


def test_escalate_never_attempts_rag():
    assert should_attempt_rag("escalate", tool_ok=False) is False


def test_empty_intent_never_attempts_rag():
    assert should_attempt_rag("", tool_ok=False) is False


# ── retrieve() ────────────────────────────────────────────────────────────────

def _mock_response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body)


def test_retrieve_success_with_chunks():
    chunks_payload = {
        "planId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "query": "Is an MRI covered?",
        "chunks": [
            {"chunkText": "MRI is covered", "sectionName": "Imaging", "sourceFile": "sbc.pdf", "distance": 0.1},
            {"chunkText": "Prior auth required", "sectionName": "Imaging", "sourceFile": "sbc.pdf", "distance": 0.2},
        ],
    }
    with patch("httpx.post", return_value=_mock_response(200, chunks_payload)):
        result = retrieve("plan-uuid-123", "Is an MRI covered?", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is True
    assert result.chunks_count == 2
    assert result.chunks[0].chunk_text == "MRI is covered"
    assert result.chunks[0].section_name == "Imaging"
    assert result.fallback_reason == ""
    assert result.source == "eligibility-sbc-rag"


def test_retrieve_empty_chunks():
    payload = {"planId": "plan-uuid", "query": "q", "chunks": []}
    with patch("httpx.post", return_value=_mock_response(200, payload)):
        result = retrieve("plan-uuid", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is True
    assert result.chunks_count == 0
    assert result.fallback_reason == "rag_empty_chunks"
    assert result.source == "eligibility-sbc-rag"


def test_retrieve_503_key_missing():
    with patch("httpx.post", return_value=_mock_response(503, {"detail": "VOYAGE_API_KEY missing"})):
        result = retrieve("plan-uuid", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is False
    assert result.fallback_reason == "rag_key_missing"


def test_retrieve_timeout():
    with patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
        result = retrieve("plan-uuid", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is False
    assert result.fallback_reason == "rag_timeout"


def test_retrieve_request_error():
    with patch("httpx.post", side_effect=httpx.RequestError("connection refused")):
        result = retrieve("plan-uuid", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is False
    assert result.fallback_reason == "rag_service_unavailable"


def test_retrieve_missing_plan_id():
    result = retrieve("", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is False
    assert result.fallback_reason == "missing_plan_id"


def test_retrieve_http_500():
    with patch("httpx.post", return_value=_mock_response(500, {"detail": "internal error"})):
        result = retrieve("plan-uuid", "q", base_url="http://localhost:8002")

    assert result.attempted is True
    assert result.available is False
    assert "rag_http_500" in result.fallback_reason


# ── sbc_rag_fallback node ─────────────────────────────────────────────────────

def _base_state(intent: str, tool_ok: bool = True, plan_id: str = "") -> dict:
    return {
        "call_sid": "CA-test",
        "stream_sid": "SM-test",
        "question": "Is an MRI covered?",
        "member_id": "CVX-0042-MT",
        "intent": intent,
        "tool_name": "check_coverage",
        "tool_result": "covered" if tool_ok else "",
        "tool_facts": ["covered"] if tool_ok else [],
        "plan_id": plan_id,
        "rag_attempted": False,
        "rag_available": False,
        "rag_chunks_count": 0,
        "rag_fallback_reason": "",
        "rag_source": "",
        "rag_chunks": [],
    }


def test_sbc_rag_fallback_noop_in_mock_mode():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "mock"
        result = sbc_rag_fallback(_base_state("coverage"))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is False
    assert result["rag_fallback_reason"] == "rag_mock_mode"


def test_sbc_rag_fallback_coverage_http_mode_calls_retrieve():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        mock_result = RagResult(
            attempted=True, available=True,
            chunks=[SBCChunk("MRI covered", "Imaging", "sbc.pdf", 0.1)],
            source="eligibility-sbc-rag",
        )
        with patch("voice_agent.graph.nodes.sbc_rag_fallback.retrieve", return_value=mock_result):
            result = sbc_rag_fallback(_base_state("coverage", tool_ok=True, plan_id="plan-uuid-123"))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is True
    assert result["rag_available"] is True
    assert result["rag_chunks_count"] == 1
    assert result["rag_source"] == "eligibility-sbc-rag"
    assert len(result["rag_chunks"]) == 1


def test_sbc_rag_fallback_formulary_ok_not_attempted():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        result = sbc_rag_fallback(_base_state("formulary", tool_ok=True))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is False
    assert result["rag_fallback_reason"] == "rag_not_applicable"


def test_sbc_rag_fallback_formulary_failed_attempts_rag():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        mock_result = RagResult(attempted=True, available=False, fallback_reason="rag_key_missing")
        with patch("voice_agent.graph.nodes.sbc_rag_fallback.retrieve", return_value=mock_result):
            result = sbc_rag_fallback(_base_state("formulary", tool_ok=False, plan_id="plan-uuid-123"))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is True
    assert result["rag_fallback_reason"] == "rag_key_missing"


def test_sbc_rag_fallback_cost_not_attempted():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        result = sbc_rag_fallback(_base_state("cost"))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is False
    assert result["rag_fallback_reason"] == "rag_not_applicable"


def test_sbc_rag_fallback_provider_not_attempted():
    from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.tool_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        result = sbc_rag_fallback(_base_state("provider"))
    finally:
        cfg_mod.settings.tool_mode = original

    assert result["rag_attempted"] is False


# ── Graph integration ─────────────────────────────────────────────────────────

def test_run_agent_graph_returns_rag_fields():
    """run_agent_graph() must always return rag_* fields (mock mode: not attempted)."""
    from voice_agent.graph.state_machine import run_agent_graph
    state = run_agent_graph("Is an MRI covered?")

    assert "rag_attempted" in state
    assert "rag_available" in state
    assert "rag_chunks_count" in state
    assert "rag_fallback_reason" in state
    assert "rag_source" in state
    assert "rag_chunks" in state


def test_run_agent_graph_mock_mode_rag_not_attempted():
    """In mock mode RAG is never attempted — not_applicable or rag_mock_mode."""
    from voice_agent.graph.state_machine import run_agent_graph
    state = run_agent_graph("Is an MRI covered?")
    assert state["rag_attempted"] is False
    assert state["rag_chunks_count"] == 0


def test_structured_tools_work_without_rag():
    """Structured tool path still works and returns grounded answer when RAG is unavailable."""
    from voice_agent.graph.state_machine import run_agent_graph
    state = run_agent_graph("Is an MRI covered?")
    assert state["tool_result"] != ""
    assert state["intent"] == "coverage"
    assert isinstance(state["grounded"], bool)


# ── HTTP endpoint ─────────────────────────────────────────────────────────────

def test_agent_respond_includes_rag_metadata(client: TestClient):
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "rag" in data
    rag = data["rag"]
    assert "ragAttempted" in rag
    assert "ragAvailable" in rag
    assert "ragChunksCount" in rag
    assert "ragFallbackReason" in rag
    assert "ragSource" in rag


def test_agent_respond_rag_not_attempted_in_mock_mode(client: TestClient):
    """Mock tool_mode means RAG is never attempted."""
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    data = resp.json()
    rag = data["rag"]
    assert rag["ragAttempted"] is False
    assert rag["ragChunksCount"] == 0


def test_agent_respond_rag_no_raw_chunks_in_response(client: TestClient):
    """The HTTP response must not include raw chunk texts — only metadata."""
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    data = resp.json()
    rag = data["rag"]
    # No raw chunk text fields in the response
    assert "chunks" not in rag
    assert "chunkText" not in str(rag)


def test_agent_respond_evidence_filters_to_contextual_chunk():
    """MRI evidence should not include unrelated formulary or urgent-care chunks."""
    from voice_agent.api.v1.agent_respond import _build_evidence_items
    from voice_agent.schemas.agent_respond import ToolTraceItem
    from voice_agent.schemas.answer import AnswerFinalEvent, RagMeta

    ev = AnswerFinalEvent(
        callSid="CA-test",
        streamSid="SM-test",
        intent="coverage",
        text="MRI is covered with prior authorization.",
        grounded=True,
        tool_trace=[],
        rag=RagMeta(ragAvailable=True, ragChunksCount=3),
        rag_chunks=[
            {
                "chunk_text": "MRI and diagnostic imaging are covered with prior authorization.",
                "section_name": "Medical Benefits",
                "source_file": "demo.txt",
                "distance": 0.41,
            },
            {
                "chunk_text": "Lisinopril is Tier 1. Humira requires prior authorization.",
                "section_name": "Prescription Drug Coverage",
                "source_file": "demo.txt",
                "distance": 0.65,
            },
            {
                "chunk_text": "Urgent care has a $75 copay.",
                "section_name": "Office and Urgent Care Visits",
                "source_file": "demo.txt",
                "distance": 0.74,
            },
        ],
    )
    trace = [
        ToolTraceItem(
            tool="check_coverage",
            args={"service": "MRI"},
            result="MRI is covered",
            ok=True,
        )
    ]

    evidence = _build_evidence_items("Is an MRI covered?", ev, trace)

    assert len(evidence) == 1
    assert evidence[0].sectionName == "Medical Benefits"
    assert "MRI" in evidence[0].text


def test_agent_respond_evidence_hides_unknown_service_chunks():
    """Bad STT entities should not display unrelated best-effort RAG chunks."""
    from voice_agent.api.v1.agent_respond import _build_evidence_items
    from voice_agent.schemas.agent_respond import ToolTraceItem
    from voice_agent.schemas.answer import AnswerFinalEvent, RagMeta

    ev = AnswerFinalEvent(
        callSid="CA-test",
        streamSid="SM-test",
        intent="coverage",
        text="The requested service is not covered.",
        grounded=True,
        tool_trace=[],
        rag=RagMeta(ragAvailable=True, ragChunksCount=1),
        rag_chunks=[
            {
                "chunk_text": "MRI and diagnostic imaging are covered with prior authorization.",
                "section_name": "Medical Benefits",
                "source_file": "demo.txt",
                "distance": 0.41,
            }
        ],
    )
    trace = [
        ToolTraceItem(
            tool="check_coverage",
            args={"service": "the requested service"},
            result="not covered",
            ok=True,
        )
    ]

    evidence = _build_evidence_items("Is an Emirate covered?", ev, trace)

    assert evidence == []

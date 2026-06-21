"""
Component 62 — Agent real tool mode hardening.

Tests:
- mock mode produces demo data_source
- http mode with real member produces real data_source on success
- http mode with real member returns error data_source on service failure
- http mode with real member returns error data_source on timeout
- http mode with real member returns member_not_found on 404
- http mode without member in demo_mode falls back to demo member
- http mode without member in real mode (demo_mode=False) returns missing_member error
- call_tool node populates data_source and member_source in trace
- find_provider returns no_results data_source on empty list
- ToolResult defaults: data_source="demo", error_code=""
"""

from __future__ import annotations

import pytest

import voice_agent.tools.check_coverage as cc
import voice_agent.tools.check_formulary as cf
import voice_agent.tools.estimate_cost as ec
import voice_agent.tools.find_provider as fp
from voice_agent.tools.schemas import ToolResult


# ── httpx mock helper ─────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, data, status=200):
        self._d = data
        self.status_code = status

    @property
    def is_success(self):
        return self.status_code < 400

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._d


# ── ToolResult defaults ────────────────────────────────────────────────────────

def test_tool_result_defaults():
    r = ToolResult(result="ok", args={})
    assert r.data_source == "demo"
    assert r.error_code == ""
    assert r.ok is True


# ── Mock mode → data_source="demo" ────────────────────────────────────────────

def test_coverage_mock_data_source():
    r = cc.run("Is an MRI covered?", member_id="X", mode="mock", base_url="http://x")
    assert r.data_source == "demo"
    assert r.ok is True


def test_cost_mock_data_source():
    r = ec.run("What is my deductible?", member_id="X", mode="mock", base_url="http://x")
    assert r.data_source == "demo"
    assert r.ok is True


def test_formulary_mock_data_source():
    r = cf.run("Is lisinopril covered?", member_id="X", mode="mock", base_url="http://x")
    assert r.data_source == "demo"
    assert r.ok is True


def test_provider_mock_data_source():
    r = fp.run("Find a cardiologist near me", member_id="X", mode="mock", base_url="http://x")
    assert r.data_source == "demo"
    assert r.ok is True


# ── HTTP mode success → data_source="real" ────────────────────────────────────

def test_coverage_http_real_data_source(monkeypatch):
    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: _Resp({
        "covered": True, "matchedBenefit": "MRI", "copayAmountCents": None,
        "coinsurancePercentage": 20.0, "requiresPriorAuth": True,
        "facts": ["MRI is covered", "20% coinsurance"],
    }))
    r = cc.run("Is an MRI covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "real"
    assert r.ok is True
    assert r.error_code == ""


def test_cost_http_real_data_source(monkeypatch):
    monkeypatch.setattr(ec.httpx, "post", lambda *a, **k: _Resp({
        "facts": ["deductible $1,500 total", "deductible $1,050 remaining"]
    }))
    r = ec.run("How much of my deductible is left?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "real"
    assert r.ok is True


def test_formulary_http_real_data_source(monkeypatch):
    monkeypatch.setattr(cf.httpx, "get", lambda *a, **k: _Resp({
        "match": {"drugName": "Humira", "formularyTier": 4, "priorAuthRequired": True},
        "facts": ["Humira is on formulary, Tier 4"],
    }))
    r = cf.run("Is Humira covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "real"
    assert r.ok is True


def test_provider_http_real_data_source(monkeypatch):
    monkeypatch.setattr(fp.httpx, "get", lambda *a, **k: _Resp({"providers": [
        {"firstName": "Rachel", "lastName": "Kim", "distanceKm": 0.4, "inNetwork": True},
    ]}))
    r = fp.run("Find a cardiologist", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "real"
    assert r.ok is True


# ── HTTP mode service failure → data_source="error" ──────────────────────────

def test_coverage_http_service_error(monkeypatch):
    import httpx as _httpx
    def boom(*a, **k):
        raise _httpx.RequestError("ECONNREFUSED")
    monkeypatch.setattr(cc.httpx, "get", boom)
    r = cc.run("Is an MRI covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.ok is False
    assert r.error_code == "service_unavailable"
    # Safe response — no fabricated coverage claim
    assert "unable" in r.result.lower() or "reach" in r.result.lower()


def test_cost_http_service_error(monkeypatch):
    import httpx as _httpx
    def boom(*a, **k):
        raise _httpx.RequestError("down")
    monkeypatch.setattr(ec.httpx, "post", boom)
    r = ec.run("What is my deductible?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.ok is False
    assert r.error_code == "service_unavailable"


def test_formulary_http_service_error(monkeypatch):
    import httpx as _httpx
    def boom(*a, **k):
        raise _httpx.RequestError("down")
    monkeypatch.setattr(cf.httpx, "get", boom)
    r = cf.run("Is lisinopril on my formulary?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.ok is False
    assert r.error_code == "service_unavailable"


def test_provider_http_service_error(monkeypatch):
    import httpx as _httpx
    def boom(*a, **k):
        raise _httpx.RequestError("down")
    monkeypatch.setattr(fp.httpx, "get", boom)
    r = fp.run("Find a cardiologist", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.ok is False
    assert r.error_code == "service_unavailable"


# ── HTTP timeout → error_code="service_unavailable" ──────────────────────────

def test_coverage_http_timeout(monkeypatch):
    import httpx as _httpx
    def boom(*a, **k):
        raise _httpx.TimeoutException("timed out")
    monkeypatch.setattr(cc.httpx, "get", boom)
    r = cc.run("Is an MRI covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.error_code == "service_unavailable"
    assert "timed out" in r.result.lower() or "unable" in r.result.lower()


# ── 404 → error_code="member_not_found" ──────────────────────────────────────

def test_coverage_http_404(monkeypatch):
    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: _Resp({}, 404))
    r = cc.run("Is an MRI covered?", member_id="BAD-ID", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.error_code == "member_not_found"
    assert r.ok is False


def test_formulary_http_404(monkeypatch):
    monkeypatch.setattr(cf.httpx, "get", lambda *a, **k: _Resp({}, 404))
    r = cf.run("Is lisinopril covered?", member_id="BAD-ID", mode="http", base_url="http://x")
    assert r.data_source == "error"
    assert r.error_code == "member_not_found"


# ── find_provider empty results → error_code="no_results", ok=True ────────────

def test_provider_http_no_results(monkeypatch):
    monkeypatch.setattr(fp.httpx, "get", lambda *a, **k: _Resp({"providers": []}))
    r = fp.run("Find a cardiologist", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert r.data_source == "real"
    assert r.ok is True
    assert r.error_code == "no_results"
    assert "not" in r.result.lower() or "no" in r.result.lower()


# ── call_tool node — member context enforcement ───────────────────────────────

def test_call_tool_demo_mode_fallback(monkeypatch):
    """In demo_mode=True, missing member falls back to CVX-0042-MT."""
    from voice_agent.graph.nodes import call_tool as ct_mod
    monkeypatch.setattr(ct_mod.settings, "tool_mode", "mock")
    monkeypatch.setattr(ct_mod.settings, "demo_mode", True)

    state = {"question": "Is an MRI covered?", "member_id": "", "tool_name": "check_coverage"}
    result = ct_mod.call_tool(state)

    assert result["member_id"] == "CVX-0042-MT"
    trace = result["tool_trace"]
    assert len(trace) == 1
    assert trace[0]["member_source"] == "demo"


def test_call_tool_real_mode_missing_member(monkeypatch):
    """In demo_mode=False + http mode, missing member returns safe error."""
    from voice_agent.graph.nodes import call_tool as ct_mod
    monkeypatch.setattr(ct_mod.settings, "tool_mode", "http")
    monkeypatch.setattr(ct_mod.settings, "demo_mode", False)

    state = {"question": "Is an MRI covered?", "member_id": "", "tool_name": "check_coverage"}
    result = ct_mod.call_tool(state)

    trace = result["tool_trace"]
    assert len(trace) == 1
    assert trace[0]["data_source"] == "error"
    assert trace[0]["error_code"] == "missing_member"
    assert trace[0]["member_source"] == "missing"
    assert result["tool_result"] != ""
    # Verify no fabricated coverage claim in the safe error text
    assert "MRI" not in result["tool_result"] or "unable" in result["tool_result"].lower()


def test_call_tool_real_mode_provided_member(monkeypatch):
    """In demo_mode=False + http mode, a real member_id goes through to the tool."""
    from voice_agent.graph.nodes import call_tool as ct_mod
    monkeypatch.setattr(ct_mod.settings, "tool_mode", "http")
    monkeypatch.setattr(ct_mod.settings, "demo_mode", False)
    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: _Resp({
        "covered": True, "matchedBenefit": "MRI",
        "copayAmountCents": None, "coinsurancePercentage": 20.0,
        "requiresPriorAuth": False, "facts": ["MRI is covered"],
    }))

    state = {"question": "Is an MRI covered?", "member_id": "REAL-001", "tool_name": "check_coverage"}
    result = ct_mod.call_tool(state)

    trace = result["tool_trace"]
    assert trace[0]["data_source"] == "real"
    assert trace[0]["member_source"] == "provided"
    assert result["member_id"] == "REAL-001"


def test_call_tool_trace_includes_data_source(monkeypatch):
    """call_tool always adds data_source and error_code to the trace."""
    from voice_agent.graph.nodes import call_tool as ct_mod
    monkeypatch.setattr(ct_mod.settings, "tool_mode", "mock")
    monkeypatch.setattr(ct_mod.settings, "demo_mode", True)

    state = {"question": "What is my copay?", "member_id": "CVX-0042-MT", "tool_name": "estimate_cost"}
    result = ct_mod.call_tool(state)

    trace = result["tool_trace"]
    assert len(trace) == 1
    entry = trace[0]
    assert "data_source" in entry
    assert "error_code" in entry
    assert "member_source" in entry
    assert entry["data_source"] == "demo"

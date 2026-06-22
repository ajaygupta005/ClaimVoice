"""Unit tests for the typed tool clients: mock preservation, http parsing, fallback."""

from __future__ import annotations

import voice_agent.tools.check_coverage as cc
import voice_agent.tools.check_formulary as cf
import voice_agent.tools.estimate_cost as ec
import voice_agent.tools.find_provider as fp


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


# ── mock mode preserves the deterministic strings ──────────────────────────────

def test_coverage_mock_preserved():
    r = cc.run("Is an MRI covered?", member_id="X", mode="mock", base_url="http://x")
    assert r.result.startswith("covered — MRI")
    assert r.facts == [r.result]


def test_cost_mock_preserved():
    r = ec.run("What is my urgent care copay?", member_id="X", mode="mock", base_url="http://x")
    assert "$30" in r.result and "urgent care" in r.result


# ── http mode parses WS-4/WS-5 responses ───────────────────────────────────────

def test_coverage_http_parses(monkeypatch):
    monkeypatch.setattr(
        cc.httpx, "get",
        lambda *a, **k: _Resp({
            "covered": True, "matchedBenefit": "MRI / Diagnostic Imaging",
            "copayAmountCents": None, "coinsurancePercentage": 20.0, "requiresPriorAuth": True,
            "facts": ["MRI is covered", "20% coinsurance", "prior authorization required"],
        }),
    )
    r = cc.run("Is an MRI covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert "prior authorization required" in r.result
    assert "20% coinsurance" in r.facts


def test_cost_http_parses(monkeypatch):
    monkeypatch.setattr(
        ec.httpx, "post",
        lambda *a, **k: _Resp({"facts": ["deductible $1,500 total", "deductible $1,050 remaining"]}),
    )
    r = ec.run("How much of my deductible is left?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert any("$1,050" in f for f in r.facts)


def test_formulary_http_parses(monkeypatch):
    monkeypatch.setattr(
        cf.httpx, "get",
        lambda *a, **k: _Resp({
            "match": {"drugName": "Humira", "formularyTier": 4, "priorAuthRequired": True},
            "facts": ["Humira is on formulary, Tier 4", "prior authorization required"],
        }),
    )
    r = cf.run("Is Humira covered?", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert "Tier 4" in r.result
    assert "prior authorization required" in r.facts


def test_find_provider_extracts_seeded_specialties():
    assert fp._mock("Find an internal medicine doctor near me").args["specialty"] == "internal medicine"
    assert fp._mock("I need a pediatrician").args["specialty"].startswith("pediatric")
    assert "cardiolog" in fp._mock("Find a cardiologist near me").args["specialty"].lower()


def test_provider_http_parses(monkeypatch):
    monkeypatch.setattr(
        fp.httpx, "get",
        lambda *a, **k: _Resp({"providers": [
            {"firstName": "Rachel", "lastName": "Kim", "distanceKm": 0.4, "inNetwork": True},
            {"organizationName": "City Cardiology", "distanceKm": 3.2, "inNetwork": False},
        ]}),
    )
    r = fp.run("Find a cardiologist near me", member_id="CVX-0042-MT", mode="http", base_url="http://x")
    assert "providers found near you" in r.result
    assert len(r.facts) == 2


# ── http errors return safe typed error (no silent mock fallback) ─────────────

def test_coverage_http_error_is_safe(monkeypatch):
    import httpx as _httpx
    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(_httpx.RequestError("down")))
    r = cc.run("Is an MRI covered?", member_id="X", mode="http", base_url="http://x")
    assert r.ok is False
    assert r.data_source == "error"
    assert r.error_code == "service_unavailable"
    # Must NOT fabricate a coverage claim
    assert not r.result.startswith("covered — MRI")

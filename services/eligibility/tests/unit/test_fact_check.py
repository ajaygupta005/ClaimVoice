"""Unit tests for the structured fact-check (mock mode, no DB / no key)."""

from __future__ import annotations

from eligibility.services.fact_check import fact_check


def test_endpoint_merges_rag_facts(monkeypatch):
    from eligibility.api.v1 import fact_check as fact_check_api
    from eligibility.schemas.fact_check import FactCheckRequest, FactCheckResponse

    captured: dict[str, list[str]] = {}

    def fake_fact_check(answer, facts, claim_types, mode, api_key, model):
        captured["facts"] = facts
        return FactCheckResponse(
            grounded=True,
            guardReason="all claims grounded in facts",
            ungroundedClaims=[],
            mode="mock",
        )

    monkeypatch.setattr(fact_check_api, "fact_check", fake_fact_check)

    fact_check_api.fact_check_endpoint(
        FactCheckRequest(
            answer="MRI requires prior authorization.",
            facts=["MRI is covered"],
            ragFacts=["prior authorization required"],
        )
    )

    assert captured["facts"] == ["MRI is covered", "prior authorization required"]


def test_grounded_amount():
    r = fact_check("Your urgent care copay is $75.", ["urgent care copay $75"], ["amount"])
    assert r.grounded is True
    assert r.mode == "mock"
    assert r.ungroundedClaims == []


def test_ungrounded_amount():
    r = fact_check("Your copay is $200.", ["urgent care copay $75"], ["amount"])
    assert r.grounded is False
    assert "$200" in r.ungroundedClaims


def test_comma_amount_grounded():
    r = fact_check(
        "You have $1,050 left on your deductible.",
        ["deductible $1,050 remaining"],
        ["amount"],
    )
    assert r.grounded is True


def test_tier_grounded():
    r = fact_check("Lisinopril is Tier 1.", ["Lisinopril is on formulary, Tier 1"], ["tier"])
    assert r.grounded is True


def test_tier_ungrounded():
    r = fact_check("Humira is Tier 2.", ["Humira is on formulary, Tier 4"], ["tier"])
    assert r.grounded is False
    assert any("Tier 2" in c for c in r.ungroundedClaims)


def test_prior_auth_boolean_ungrounded_when_facts_silent():
    r = fact_check("Prior authorization required.", ["MRI is covered"], ["boolean"])
    assert r.grounded is False


def test_prior_auth_boolean_grounded_when_facts_support():
    r = fact_check(
        "Prior authorization required.",
        ["MRI is covered", "prior authorization required"],
        ["boolean"],
    )
    assert r.grounded is True

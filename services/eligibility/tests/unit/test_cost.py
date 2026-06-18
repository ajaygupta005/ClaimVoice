"""Unit tests for cost-estimate logic (pure, no DB)."""

from __future__ import annotations

import uuid

from eligibility.services.cost_estimator import build_cost_estimate


def _result(benefit=None, ded_ytd=45000, oop_ytd=120000, plan_ded=150000, plan_oop=500000):
    return {
        "member": {
            "member_id": "CVX-0042-MT",
            "plan_id": uuid.uuid4(),
            "deductible_ytd_cents": ded_ytd,
            "oop_ytd_cents": oop_ytd,
        },
        "plan_deductible_cents": plan_ded,
        "plan_oop_cents": plan_oop,
        "benefit": benefit,
    }


def test_deductible():
    r = build_cost_estimate(_result(), "deductible", None)
    assert r.deductibleTotalCents == 150000
    assert r.deductibleSpentCents == 45000
    assert r.deductibleRemainingCents == 105000
    assert any("$1,500" in f for f in r.facts)


def test_oop():
    r = build_cost_estimate(_result(), "oop", None)
    assert r.oopMaxCents == 500000
    assert r.oopSpentCents == 120000
    assert r.oopRemainingCents == 380000


def test_copay_service_dollar_fact():
    benefit = {
        "benefit_name": "Urgent Care",
        "service_category": "Urgent Care",
        "copay_amount_cents": 7500,
        "coinsurance_percentage": None,
        "requires_prior_auth": False,
    }
    r = build_cost_estimate(_result(benefit), "copay", "urgent care")
    assert r.copayAmountCents == 7500
    assert r.estimateLowCents == 7500 and r.estimateHighCents == 7500
    assert any("$75" in f for f in r.facts)


def test_coinsurance_service_estimate_range():
    benefit = {
        "benefit_name": "MRI / Diagnostic Imaging",
        "service_category": "Diagnostic Imaging",
        "copay_amount_cents": None,
        "coinsurance_percentage": 20.0,
        "requires_prior_auth": True,
    }
    r = build_cost_estimate(_result(benefit), "service", "MRI")
    assert r.coinsurancePercentage == 20.0
    assert r.estimateHighCents == 105000  # up to remaining deductible

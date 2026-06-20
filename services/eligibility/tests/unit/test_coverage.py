"""Unit tests for coverage logic (pure, no DB)."""

from __future__ import annotations

import uuid

from eligibility.services.coverage import build_coverage_response


def _result(benefit, ded_ytd=45000, oop_ytd=120000, plan_ded=150000, plan_oop=500000):
    return {
        "member": {
            "member_id": "CVX-0042-MT",
            "plan_id": uuid.uuid4(),
            "deductible_ytd_cents": ded_ytd,
            "oop_ytd_cents": oop_ytd,
        },
        "benefit": benefit,
        "plan_deductible_cents": plan_ded,
        "plan_oop_cents": plan_oop,
    }


def test_mri_prior_auth_coinsurance():
    benefit = {
        "benefit_name": "MRI / Diagnostic Imaging",
        "service_category": "Diagnostic Imaging",
        "network_type": "In Network",
        "copay_amount_cents": None,
        "coinsurance_percentage": 20.0,
        "individual_deductible_cents": 150000,
        "out_of_pocket_max_cents": 500000,
        "requires_prior_auth": True,
    }
    resp = build_coverage_response(_result(benefit), "MRI", "In Network")
    assert resp.covered is True
    assert resp.requiresPriorAuth is True
    assert resp.coinsurancePercentage == 20.0
    assert resp.deductibleRemainingCents == 105000  # 150000 - 45000
    assert resp.oopRemainingCents == 380000  # 500000 - 120000
    assert any("prior authorization required" in f for f in resp.facts)
    assert any("20% coinsurance" in f for f in resp.facts)


def test_copay_benefit_formats_dollars():
    benefit = {
        "benefit_name": "Primary Care Visit",
        "service_category": "Professional Services",
        "network_type": "In Network",
        "copay_amount_cents": 3000,
        "coinsurance_percentage": None,
        "individual_deductible_cents": 150000,
        "out_of_pocket_max_cents": 500000,
        "requires_prior_auth": False,
    }
    resp = build_coverage_response(_result(benefit), "primary care", "In Network")
    assert resp.copayAmountCents == 3000
    assert resp.requiresPriorAuth is False
    assert any("$30" in f for f in resp.facts)


def test_no_match_not_covered_but_deductible_still_computed():
    resp = build_coverage_response(_result(None), "spaceflight", "In Network")
    assert resp.covered is False
    assert resp.matchedBenefit is None
    assert resp.deductibleRemainingCents == 105000
    assert any("no In Network benefit" in f for f in resp.facts)

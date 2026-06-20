"""Unit tests for formulary-lookup logic (pure, no DB)."""

from __future__ import annotations

import uuid

from eligibility.services.formulary import build_formulary_lookup


def _result(match, alts=None):
    return {"plan_id": uuid.uuid4(), "match": match, "alternatives": alts or []}


def _drug(name, tier, pa=False, st=False):
    return {
        "id": uuid.uuid4(),
        "drug_name": name,
        "ndc_code": "00000000000",
        "formulary_tier": tier,
        "prior_auth_required": pa,
        "step_therapy_required": st,
        "quantity_limit": "30 per 30 days",
    }


def test_lisinopril_tier1_no_pa():
    r = build_formulary_lookup("CVX-0042-MT", _result(_drug("Lisinopril", 1)), "lisinopril")
    assert r.onFormulary is True
    assert r.match.formularyTier == 1
    assert r.match.priorAuthRequired is False
    assert any("Tier 1" in f for f in r.facts)


def test_humira_tier4_pa_with_alternatives():
    match = _drug("Humira", 4, pa=True, st=True)
    alt = _drug("Lisinopril", 1)
    r = build_formulary_lookup("CVX-0042-MT", _result(match, [alt]), "humira")
    assert r.match.priorAuthRequired is True
    assert any("prior authorization required" in f for f in r.facts)
    assert len(r.alternatives) == 1
    assert r.alternatives[0].drugName == "Lisinopril"


def test_not_on_formulary():
    r = build_formulary_lookup("CVX-0042-MT", _result(None), "unobtainium")
    assert r.onFormulary is False
    assert r.match is None
    assert any("not on the plan formulary" in f for f in r.facts)

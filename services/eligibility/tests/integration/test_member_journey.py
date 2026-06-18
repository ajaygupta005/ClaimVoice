"""End-to-end WS-4 journey for the demo member, exercising all endpoints together.

Uses the shared ``client`` fixture (conftest) and is auto-skipped without a live DB.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_demo_member_full_journey(client):
    # 1. Member summary resolves the demo member + plan.
    r = client.get("/api/v1/members/CVX-0042-MT/summary")
    assert r.status_code == 200
    assert r.json()["member"]["memberId"] == "CVX-0042-MT"

    # 2. Coverage for an MRI: covered, 20% coinsurance, prior auth required.
    r = client.get("/api/v1/coverage", params={"memberId": "CVX-0042-MT", "service": "MRI"})
    cov = r.json()
    assert cov["covered"] is True
    assert cov["requiresPriorAuth"] is True
    assert cov["deductibleRemainingCents"] == 105000

    # 3. Cost: deductible status.
    r = client.post(
        "/api/v1/cost/estimate", json={"memberId": "CVX-0042-MT", "costType": "deductible"}
    )
    assert r.json()["deductibleRemainingCents"] == 105000

    # 4. Formulary: Humira is Tier 4 with prior auth.
    r = client.get("/api/v1/formulary/lookup", params={"memberId": "CVX-0042-MT", "drug": "humira"})
    assert r.json()["match"]["formularyTier"] == 4

    # 5. Fact-check a narration built from the coverage facts -> grounded.
    answer = "An MRI needs prior authorization; you have $1,050 left on your deductible."
    r = client.post("/api/v1/fact_check", json={"answer": answer, "facts": cov["facts"]})
    fc = r.json()
    assert fc["grounded"] is True, fc

    # 6. A hallucinated dollar amount is caught.
    bad = "Your MRI will cost exactly $42."
    r = client.post("/api/v1/fact_check", json={"answer": bad, "facts": cov["facts"]})
    assert r.json()["grounded"] is False

"""Unit tests for eligibility schema mapping and API 404 behaviour."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from eligibility.main import app
from eligibility.schemas.member import MemberOut, MemberSummaryResponse, PlanOut
from eligibility.schemas.benefit import BenefitOut, BenefitsResponse
from eligibility.schemas.formulary import FormularyDrugOut, FormularySearchResponse


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── MemberOut ─────────────────────────────────────────────────────────────────

def test_member_out_full() -> None:
    m = MemberOut(
        memberId="CVX-0001",
        name="Alex Rivera",
        eligibilityStatus="active",
        deductibleYtdCents=12000,
        oopYtdCents=24000,
    )
    assert m.memberId == "CVX-0001"
    assert m.eligibilityStatus == "active"


def test_member_out_zero_ytd() -> None:
    m = MemberOut(
        memberId="CVX-0002",
        name="Sam Lee",
        eligibilityStatus="inactive",
        deductibleYtdCents=0,
        oopYtdCents=0,
    )
    assert m.deductibleYtdCents == 0
    assert m.oopYtdCents == 0


# ── PlanOut ───────────────────────────────────────────────────────────────────

def test_plan_out_optional_nulls() -> None:
    plan_id = uuid.uuid4()
    p = PlanOut(
        id=plan_id,
        name="Bronze HMO 6000",
        issuer=None,
        year=None,
        type=None,
        metalLevel=None,
        hsaEligible=None,
        state=None,
    )
    assert p.issuer is None
    assert p.year is None


# ── BenefitOut ────────────────────────────────────────────────────────────────

def test_benefit_out_prior_auth_default() -> None:
    b = BenefitOut(
        id=uuid.uuid4(),
        benefitName="Primary Care Visit",
        serviceCategory="Outpatient",
        networkType="In-Network",
        individualDeductibleCents=None,
        familyDeductibleCents=None,
        copayAmountCents=3000,
        coinsurancePercentage=None,
        outOfPocketMaxCents=None,
        requiresPriorAuth=False,
    )
    assert b.requiresPriorAuth is False
    assert b.copayAmountCents == 3000


def test_benefit_out_coinsurance() -> None:
    b = BenefitOut(
        id=uuid.uuid4(),
        benefitName="Specialist",
        serviceCategory="Outpatient",
        networkType="In-Network",
        individualDeductibleCents=None,
        familyDeductibleCents=None,
        copayAmountCents=None,
        coinsurancePercentage=20.0,
        outOfPocketMaxCents=500000,
        requiresPriorAuth=False,
    )
    assert b.coinsurancePercentage == 20.0


# ── FormularyDrugOut ──────────────────────────────────────────────────────────

def test_formulary_drug_out() -> None:
    d = FormularyDrugOut(
        id=uuid.uuid4(),
        drugName="metformin",
        ndcCode="00378-2560-93",
        formularyTier=1,
        priorAuthRequired=False,
        stepTherapyRequired=False,
        quantityLimit=None,
    )
    assert d.formularyTier == 1
    assert d.priorAuthRequired is False


# ── API 404 behaviour (mock DB) ───────────────────────────────────────────────

def test_member_summary_404(client: TestClient) -> None:
    with patch(
        "eligibility.api.v1.members.get_member_with_plan",
        return_value=None,
    ):
        with patch("eligibility.api.v1.members.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get("/api/v1/members/UNKNOWN-999/summary")

    assert resp.status_code == 404
    assert "UNKNOWN-999" in resp.json()["detail"]


def test_plan_benefits_empty(client: TestClient) -> None:
    plan_id = uuid.uuid4()
    with patch(
        "eligibility.api.v1.plans.get_plan_benefits",
        return_value=[],
    ):
        with patch("eligibility.api.v1.plans.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get(f"/api/v1/plans/{plan_id}/benefits")

    assert resp.status_code == 200
    data = resp.json()
    assert data["benefits"] == []
    assert data["planId"] == str(plan_id)


def test_formulary_search_empty(client: TestClient) -> None:
    plan_id = uuid.uuid4()
    with patch(
        "eligibility.api.v1.formulary.search_formulary",
        return_value=[],
    ):
        with patch("eligibility.api.v1.formulary.db_session") as mock_ctx:
            mock_session = MagicMock()
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.get(f"/api/v1/formulary/search?planId={plan_id}&q=atorvastatin")

    assert resp.status_code == 200
    data = resp.json()
    assert data["drugs"] == []
    assert data["query"] == "atorvastatin"

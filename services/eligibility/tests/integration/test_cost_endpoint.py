"""Integration tests for POST /api/v1/cost/estimate against the seeded dev DB."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def _db_reachable() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    try:
        import psycopg

        with psycopg.connect(
            url.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3
        ):
            return True
    except Exception:
        return False


if not _db_reachable():
    pytest.skip("live database not reachable (set DATABASE_URL)", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from eligibility.main import app  # noqa: E402

client = TestClient(app)


def test_deductible_status():
    r = client.post("/api/v1/cost/estimate", json={"memberId": "CVX-0042-MT", "costType": "deductible"})
    assert r.status_code == 200
    b = r.json()
    assert b["deductibleTotalCents"] == 150000
    assert b["deductibleSpentCents"] == 45000
    assert b["deductibleRemainingCents"] == 105000
    assert any("$1,500" in f for f in b["facts"])


def test_oop_status():
    r = client.post("/api/v1/cost/estimate", json={"memberId": "CVX-0042-MT", "costType": "oop"})
    b = r.json()
    assert b["oopMaxCents"] == 500000
    assert b["oopRemainingCents"] == 380000


def test_urgent_care_copay():
    r = client.post(
        "/api/v1/cost/estimate",
        json={"memberId": "CVX-0042-MT", "costType": "copay", "service": "urgent care"},
    )
    b = r.json()
    assert b["copayAmountCents"] == 7500
    assert any("$75" in f for f in b["facts"])


def test_primary_care_copay():
    r = client.post(
        "/api/v1/cost/estimate",
        json={"memberId": "CVX-0042-MT", "costType": "service", "service": "primary care"},
    )
    assert r.json()["copayAmountCents"] == 3000


def test_unknown_member_404():
    r = client.post("/api/v1/cost/estimate", json={"memberId": "NOPE-999", "costType": "oop"})
    assert r.status_code == 404

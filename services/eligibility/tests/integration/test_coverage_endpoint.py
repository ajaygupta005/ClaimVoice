"""Integration tests for GET /api/v1/coverage against the seeded dev DB.

Requires DATABASE_URL pointing at a database seeded with the demo member
(data/ingest/seed_demo_member.py). Auto-skips when the DB is unreachable.
"""

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


def test_coverage_mri_prior_auth():
    r = client.get("/api/v1/coverage", params={"memberId": "CVX-0042-MT", "service": "MRI"})
    assert r.status_code == 200
    b = r.json()
    assert b["covered"] is True
    assert b["requiresPriorAuth"] is True
    assert b["coinsurancePercentage"] == 20.0
    assert b["deductibleRemainingCents"] == 105000
    assert b["oopRemainingCents"] == 380000


def test_coverage_primary_care_copay():
    r = client.get(
        "/api/v1/coverage", params={"memberId": "CVX-0042-MT", "service": "primary care"}
    )
    assert r.status_code == 200
    assert r.json()["copayAmountCents"] == 3000


def test_coverage_unknown_member_404():
    r = client.get("/api/v1/coverage", params={"memberId": "NOPE-999", "service": "MRI"})
    assert r.status_code == 404

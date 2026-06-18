"""Integration tests for GET /api/v1/formulary/lookup against the seeded dev DB."""

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


def test_lisinopril_tier1():
    r = client.get(
        "/api/v1/formulary/lookup", params={"memberId": "CVX-0042-MT", "drug": "lisinopril"}
    )
    assert r.status_code == 200
    b = r.json()
    assert b["onFormulary"] is True
    assert b["match"]["formularyTier"] == 1
    assert b["match"]["priorAuthRequired"] is False


def test_humira_tier4_pa_with_alternatives():
    r = client.get("/api/v1/formulary/lookup", params={"memberId": "CVX-0042-MT", "drug": "humira"})
    b = r.json()
    assert b["match"]["formularyTier"] == 4
    assert b["match"]["priorAuthRequired"] is True
    assert any(a["drugName"] == "Lisinopril" for a in b["alternatives"])


def test_unknown_member_404():
    r = client.get(
        "/api/v1/formulary/lookup", params={"memberId": "NOPE-999", "drug": "lisinopril"}
    )
    assert r.status_code == 404

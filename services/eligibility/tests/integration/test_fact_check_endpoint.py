"""Integration test for POST /api/v1/fact_check (endpoint wiring).

The endpoint itself needs no DB, but TestClient(app) runs the startup event, so this
is grouped with the integration suite (auto-skips when the DB is unreachable).
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


def test_fact_check_grounded():
    r = client.post(
        "/api/v1/fact_check",
        json={"answer": "Your urgent care copay is $75.", "facts": ["urgent care copay $75"]},
    )
    assert r.status_code == 200
    b = r.json()
    assert b["grounded"] is True
    assert b["mode"] == "mock"


def test_fact_check_ungrounded():
    r = client.post(
        "/api/v1/fact_check",
        json={"answer": "Your copay is $500.", "facts": ["urgent care copay $75"]},
    )
    b = r.json()
    assert b["grounded"] is False
    assert "$500" in b["ungroundedClaims"]

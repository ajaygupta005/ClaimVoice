"""Integration tests for POST /api/v1/providers/bulk against the seeded DB."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def _some_npis(n: int = 3) -> list[str]:
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as c, c.cursor() as cur:
        cur.execute("SELECT npi FROM providers ORDER BY npi LIMIT %s", (n,))
        return [r[0] for r in cur.fetchall()]


def test_bulk_returns_requested_and_omits_missing(client):
    npis = _some_npis(3)
    assert len(npis) == 3
    r = client.post("/api/v1/providers/bulk", json={"npis": npis + ["0000000000"]})
    assert r.status_code == 200
    returned = {p["npi"] for p in r.json()["providers"]}
    assert set(npis) <= returned
    assert "0000000000" not in returned


def test_bulk_shape_matches_detail(client):
    npi = _some_npis(1)[0]
    bulk = client.post("/api/v1/providers/bulk", json={"npis": [npi]}).json()["providers"][0]
    detail = client.get(f"/api/v1/providers/{npi}").json()
    assert bulk["npi"] == detail["npi"]
    assert bulk["qualityRating"] == detail["qualityRating"]


def test_bulk_rejects_empty_list(client):
    r = client.post("/api/v1/providers/bulk", json={"npis": []})
    assert r.status_code == 422  # min_length=1

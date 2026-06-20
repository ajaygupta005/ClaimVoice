"""Integration tests for GET /api/v1/providers/near against the seeded + enriched DB."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

_MIDTOWN = {"lat": 40.7580, "lng": -73.9855}


def _conn():
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def _demo_plan_id() -> str | None:
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT id::text FROM plans WHERE plan_marketing_name = 'ClaimVoice Demo PPO'")
        row = cur.fetchone()
        return row[0] if row else None


def _in_network_specialty(plan_id: str) -> str | None:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """
            SELECT p.taxonomy_description
            FROM providers p JOIN in_network i ON i.provider_npi = p.npi
            WHERE i.plan_id = CAST(%s AS uuid) AND p.taxonomy_description IS NOT NULL
            LIMIT 1
            """,
            (plan_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def test_near_returns_ranked_matches(client):
    r = client.get(
        "/api/v1/providers/near",
        params={"specialty": "Internal Medicine", "radiusKm": 25, **_MIDTOWN},
    )
    assert r.status_code == 200
    b = r.json()
    assert b["total"] >= 1
    provs = b["providers"]
    dists = [p["distanceKm"] for p in provs]
    assert dists == sorted(dists)  # distance ascending
    assert all(p["distanceKm"] <= 25 for p in provs)
    assert all("internal medicine" in (p["specialty"] or "").lower() for p in provs)


def test_near_in_network_only(client):
    pid = _demo_plan_id()
    assert pid, "demo plan must be seeded"
    spec = _in_network_specialty(pid)
    assert spec, "demo plan must have at least one enriched in-network provider"
    r = client.get(
        "/api/v1/providers/near",
        params={
            "specialty": spec,
            "radiusKm": 100,
            "inNetworkOnly": "true",
            "planId": pid,
            **_MIDTOWN,
        },
    )
    b = r.json()
    assert b["total"] >= 1
    assert all(p["inNetwork"] is True for p in b["providers"])


def test_near_in_network_requires_plan(client):
    r = client.get(
        "/api/v1/providers/near",
        params={"specialty": "x", "inNetworkOnly": "true", **_MIDTOWN},
    )
    assert r.status_code == 400

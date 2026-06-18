"""Unit tests for geo filtering/ranking (mirrors the pinned provider_lookup eval)."""

from __future__ import annotations

from providers.services.geo_search import haversine_km, parse_wkt_point, rank_near


def _cand(npi, specialty, lat, lng, quality=3.0, in_network=False, accepting=True):
    return {
        "npi": npi,
        "taxonomy_description": specialty,
        "specialty_codes": [specialty],
        "location": f"POINT({lng} {lat})",
        "quality_rating": quality,
        "accepting_new_patients": accepting,
        "in_network": in_network,
    }


def test_parse_wkt_point():
    assert parse_wkt_point("POINT(-73.9855 40.758)") == (40.758, -73.9855)
    assert parse_wkt_point(None) is None
    assert parse_wkt_point("garbage") is None


def test_haversine_zero_and_positive():
    assert haversine_km(40.0, -73.0, 40.0, -73.0) == 0.0
    assert haversine_km(40.0, -73.0, 41.0, -73.0) > 100  # ~111 km/degree lat


def test_specialty_substring_filter():
    q = {"specialty": "cardio", "lat": 40.0, "lng": -73.0, "radius_km": 50}
    cands = [_cand("A", "Cardiology", 40.0, -73.0), _cand("B", "Dermatology", 40.0, -73.0)]
    assert [c["npi"] for c, _ in rank_near(q, cands)] == ["A"]


def test_radius_filter():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 1}
    cands = [_cand("near", "x", 40.0, -73.0), _cand("far", "x", 41.0, -73.0)]
    assert [c["npi"] for c, _ in rank_near(q, cands)] == ["near"]


def test_in_network_filter():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 50, "in_network_only": True}
    cands = [
        _cand("in", "x", 40.0, -73.0, in_network=True),
        _cand("out", "x", 40.0, -73.0, in_network=False),
    ]
    assert [c["npi"] for c, _ in rank_near(q, cands)] == ["in"]


def test_accepting_new_filter():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 50, "accepting_new_only": True}
    cands = [
        _cand("yes", "x", 40.0, -73.0, accepting=True),
        _cand("no", "x", 40.0, -73.0, accepting=False),
    ]
    assert [c["npi"] for c, _ in rank_near(q, cands)] == ["yes"]


def test_sort_distance_then_quality():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 50}
    cands = [
        _cand("low", "x", 40.0, -73.0, quality=3.0),
        _cand("high", "x", 40.0, -73.0, quality=5.0),
    ]
    # same distance -> higher quality first
    assert [c["npi"] for c, _ in rank_near(q, cands)] == ["high", "low"]

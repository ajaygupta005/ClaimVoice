"""Tests for the provider lookup eval (Component 17)."""
import sys
from pathlib import Path

# Make eval/tasks importable without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tasks"))

import provider_lookup_eval as m  # noqa: E402


def test_dataset_loads_and_has_cases():
    cases = m.load_cases()
    assert isinstance(cases, list)
    assert len(cases) >= 5


def test_every_case_matches_reference_ranking():
    """The golden expected_npis must match what rank_providers produces."""
    for case in m.load_cases():
        sr = m.score_case(case)
        assert sr.passed, f"{case['id']} failed: {sr.failures}"


def test_specialty_filter_excludes_other_specialties():
    q = {"specialty": "cardiology", "lat": 40.0, "lng": -73.0, "radius_km": 50}
    cands = [
        {"npi": "A", "specialty": "Cardiology", "lat": 40.0, "lng": -73.0, "quality_rating": 3},
        {"npi": "B", "specialty": "Dermatology", "lat": 40.0, "lng": -73.0, "quality_rating": 5},
    ]
    out = m.rank_providers(q, cands)
    assert [p["npi"] for p in out] == ["A"]


def test_radius_filter():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 1}
    cands = [
        {"npi": "near", "specialty": "x", "lat": 40.0, "lng": -73.0, "quality_rating": 1},
        {"npi": "far", "specialty": "x", "lat": 41.0, "lng": -73.0, "quality_rating": 5},
    ]
    out = m.rank_providers(q, cands)
    assert [p["npi"] for p in out] == ["near"]


def test_in_network_filter():
    q = {"specialty": "x", "lat": 40.0, "lng": -73.0, "radius_km": 50, "in_network_only": True}
    cands = [
        {"npi": "in", "specialty": "x", "lat": 40.0, "lng": -73.0, "in_network": True, "quality_rating": 1},
        {"npi": "out", "specialty": "x", "lat": 40.0, "lng": -73.0, "in_network": False, "quality_rating": 5},
    ]
    out = m.rank_providers(q, cands)
    assert [p["npi"] for p in out] == ["in"]

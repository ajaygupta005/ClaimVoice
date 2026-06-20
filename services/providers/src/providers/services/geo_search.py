"""Geo filtering + ranking for /providers/near.

Distance is computed app-side with the Haversine formula copied verbatim from
``eval/tasks/provider_lookup_eval.py`` so the live endpoint matches the pinned eval
exactly (no PostGIS needed on the dev DB). ``ST_DWithin`` is a future prod optimization.
"""

from __future__ import annotations

import math
from typing import Any


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km (verbatim from provider_lookup_eval._haversine_km)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_wkt_point(wkt: str | None) -> tuple[float, float] | None:
    """'POINT(lng lat)' -> (lat, lng); None if unparseable."""
    try:
        inner = wkt[wkt.index("(") + 1 : wkt.index(")")]  # type: ignore[index]
        lng_s, lat_s = inner.split()
        return float(lat_s), float(lng_s)
    except (ValueError, AttributeError, TypeError):
        return None


def rank_near(
    query: dict[str, Any], candidates: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], float]]:
    """Filter + rank DB candidate rows; returns (row, distance_km) in ranked order.

    Mirrors ``rank_providers`` from the eval: specialty case-insensitive substring
    (over taxonomy_description or specialty_codes), distance within radius_km, optional
    in-network / accepting-new filters, sorted by (distance asc, quality desc).
    """
    spec = query["specialty"].lower()
    lat, lng = query["lat"], query["lng"]
    radius = query.get("radius_km", 25)
    in_network_only = query.get("in_network_only", False)
    accepting_new_only = query.get("accepting_new_only", False)

    matched: list[tuple[dict[str, Any], float]] = []
    for c in candidates:
        specialty_text = (c.get("taxonomy_description") or "").lower()
        codes_text = " ".join(c.get("specialty_codes") or []).lower()
        if spec not in specialty_text and spec not in codes_text:
            continue
        pt = parse_wkt_point(c.get("location"))
        if pt is None:
            continue
        dist = haversine_km(lat, lng, pt[0], pt[1])
        if dist > radius:
            continue
        if in_network_only and not c.get("in_network", False):
            continue
        if accepting_new_only and not c.get("accepting_new_patients", False):
            continue
        matched.append((c, round(dist, 2)))

    matched.sort(key=lambda t: (t[1], -float(t[0].get("quality_rating") or 0)))
    return matched

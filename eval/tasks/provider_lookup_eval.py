"""
Provider-lookup evaluation.

Scores the provider ranking/filter logic deterministically against a golden
dataset. Each case gives a member query (specialty, ZIP, radius, in-network
requirement, accepting-new requirement) plus a list of candidate providers
with their attributes, and the expected ordered result (by NPI).

The reference ranking function `rank_providers` lives here so the eval runs
in CI with no database and no API key. In production this same contract is
served by the providers service (`/providers/near`); this eval pins the
expected behavior so a real implementation can be checked against it.

Run:
    inspect eval eval/tasks/provider_lookup_eval.py

Importable for unit tests:
    from eval.tasks.provider_lookup_eval import rank_providers, load_cases, score_case
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATASET_PATH = Path(__file__).parent.parent / "datasets" / "provider_queries.json"


# ── geo helper ────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── reference ranking ─────────────────────────────────────────────────────────

def rank_providers(query: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter + rank candidate providers for a query.

    Filters:
      - specialty must match (case-insensitive substring)
      - distance within radius_km of the query point
      - if query.in_network_only: provider.in_network must be true
      - if query.accepting_new_only: provider.accepting_new must be true

    Ranking (ascending priority):
      1. distance (closer first)
      2. quality_rating (higher first) as a tiebreak
    """
    spec = query["specialty"].lower()
    lat, lng = query["lat"], query["lng"]
    radius = query.get("radius_km", 25)
    in_network_only = query.get("in_network_only", False)
    accepting_new_only = query.get("accepting_new_only", False)

    matched: list[dict[str, Any]] = []
    for c in candidates:
        if spec not in c["specialty"].lower():
            continue
        dist = _haversine_km(lat, lng, c["lat"], c["lng"])
        if dist > radius:
            continue
        if in_network_only and not c.get("in_network", False):
            continue
        if accepting_new_only and not c.get("accepting_new", False):
            continue
        matched.append({**c, "distance_km": round(dist, 2)})

    matched.sort(key=lambda c: (c["distance_km"], -c.get("quality_rating", 0)))
    return matched


# ── scoring ───────────────────────────────────────────────────────────────────

@dataclass
class ProviderScore:
    passed: bool
    case_id: str = ""
    failures: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)
    actual: list[str] = field(default_factory=list)


def score_case(case: dict[str, Any]) -> ProviderScore:
    """Run rank_providers and compare the resulting NPI order to expected."""
    result = rank_providers(case["query"], case["candidates"])
    actual_npis = [p["npi"] for p in result]
    expected_npis = case["expected_npis"]

    failures: list[str] = []
    if actual_npis != expected_npis:
        failures.append(f"order: expected={expected_npis} actual={actual_npis}")

    top_k = case.get("expected_top_k")
    if top_k is not None and actual_npis[: len(top_k)] != top_k:
        failures.append(f"top-k: expected={top_k} actual={actual_npis[:len(top_k)]}")

    return ProviderScore(
        passed=not failures,
        case_id=case.get("id", ""),
        failures=failures,
        expected=expected_npis,
        actual=actual_npis,
    )


def load_cases() -> list[dict[str, Any]]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


# ── Inspect AI task (lazy import so unit tests work without inspect-ai) ─────────

def _build_inspect_task():
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import Score, Scorer, scorer, accuracy
    from inspect_ai.solver import Solver, TaskState, Generate, solver
    from inspect_ai.model import ChatMessageAssistant

    cases = load_cases()
    samples = [
        Sample(input=c["query"]["specialty"], target=",".join(c["expected_npis"]), metadata=c)
        for c in cases
    ]

    @solver
    def ranking_solver() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            sr = score_case(state.metadata)
            state.metadata["_score"] = sr.__dict__
            state.messages.append(ChatMessageAssistant(content=",".join(sr.actual)))
            return state
        return solve

    @scorer(metrics=[accuracy()])
    def ranking_scorer() -> Scorer:
        async def score(state: TaskState, target) -> Score:
            raw = state.metadata.get("_score", {})
            passed = bool(raw.get("passed"))
            return Score(
                value=1.0 if passed else 0.0,
                answer=",".join(raw.get("actual", [])),
                explanation="ok" if passed else "; ".join(raw.get("failures", [])),
                metadata={"case_id": raw.get("case_id", "")},
            )
        return score

    return Task(dataset=samples, solver=[ranking_solver()], scorer=[ranking_scorer()])


try:
    from inspect_ai import task as _task

    @_task
    def provider_lookup_eval():
        return _build_inspect_task()

except ImportError:  # inspect-ai not installed (e.g. plain unit-test run)
    pass

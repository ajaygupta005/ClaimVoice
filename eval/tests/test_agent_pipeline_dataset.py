"""
Component 34 — Dataset shape and contract tests.

Validates every record in agent_pipeline_cases.json before any pipeline run.
No API key or service connection needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET = ROOT / "eval" / "datasets" / "agent_pipeline_cases.json"

REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_intent",
    "expected_tool",
    "required_phrases",
    "forbidden_phrases",
    "expected_grounded",
    "expected_escalate",
}

VALID_INTENTS = {"coverage", "cost", "provider", "formulary", "escalate"}

VALID_TOOLS = {
    "check_coverage",
    "estimate_cost",
    "find_provider",
    "check_formulary",
    "escalate_to_human",
}


@pytest.fixture(scope="module")
def cases():
    assert DATASET.exists(), f"Dataset not found: {DATASET}"
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_dataset_is_list(cases):
    assert isinstance(cases, list)


def test_dataset_has_minimum_cases(cases):
    assert len(cases) >= 9, f"Expected at least 9 cases, got {len(cases)}"


def test_all_ids_are_unique(cases):
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "Duplicate case IDs found"


def test_all_required_fields_present(cases):
    for c in cases:
        missing = REQUIRED_FIELDS - c.keys()
        assert not missing, f"Case {c.get('id', '?')} missing fields: {missing}"


def test_all_questions_are_non_empty(cases):
    for c in cases:
        assert isinstance(c["question"], str) and c["question"].strip(), (
            f"Case {c['id']} has empty question"
        )


def test_all_intents_are_valid(cases):
    for c in cases:
        assert c["expected_intent"] in VALID_INTENTS, (
            f"Case {c['id']} has unknown intent: {c['expected_intent']!r}"
        )


def test_all_tools_are_valid(cases):
    for c in cases:
        assert c["expected_tool"] in VALID_TOOLS, (
            f"Case {c['id']} has unknown tool: {c['expected_tool']!r}"
        )


def test_intent_tool_pairs_are_consistent(cases):
    """Each intent maps to exactly one expected tool — enforce the contract."""
    expected_pairs = {
        "coverage": "check_coverage",
        "cost": "estimate_cost",
        "provider": "find_provider",
        "formulary": "check_formulary",
        "escalate": "escalate_to_human",
    }
    for c in cases:
        intent = c["expected_intent"]
        tool = c["expected_tool"]
        assert tool == expected_pairs[intent], (
            f"Case {c['id']}: intent={intent!r} paired with tool={tool!r}; "
            f"expected {expected_pairs[intent]!r}"
        )


def test_grounded_flag_is_bool(cases):
    for c in cases:
        assert isinstance(c["expected_grounded"], bool), (
            f"Case {c['id']} expected_grounded is not bool"
        )


def test_escalate_flag_is_bool(cases):
    for c in cases:
        assert isinstance(c["expected_escalate"], bool), (
            f"Case {c['id']} expected_escalate is not bool"
        )


def test_escalation_cases_not_grounded(cases):
    """Escalation answers must never be marked grounded — they invent no facts."""
    for c in cases:
        if c["expected_escalate"]:
            assert c["expected_grounded"] is False, (
                f"Case {c['id']} is escalate=True but grounded=True — impossible"
            )


def test_required_phrases_are_lists_of_strings(cases):
    for c in cases:
        assert isinstance(c["required_phrases"], list), (
            f"Case {c['id']} required_phrases is not a list"
        )
        for p in c["required_phrases"]:
            assert isinstance(p, str), f"Case {c['id']} required phrase not str: {p!r}"


def test_forbidden_phrases_are_lists_of_strings(cases):
    for c in cases:
        assert isinstance(c["forbidden_phrases"], list), (
            f"Case {c['id']} forbidden_phrases is not a list"
        )
        for p in c["forbidden_phrases"]:
            assert isinstance(p, str), f"Case {c['id']} forbidden phrase not str: {p!r}"


def test_escalation_cases_present(cases):
    escalations = [c for c in cases if c["expected_escalate"]]
    assert len(escalations) >= 2, "Need at least 2 escalation cases"


def test_each_intent_represented(cases):
    covered = {c["expected_intent"] for c in cases}
    assert covered == VALID_INTENTS, f"Missing intents: {VALID_INTENTS - covered}"

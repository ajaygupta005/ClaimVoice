"""
Component 34 — Deterministic scorer and pipeline adapter unit tests.

Imports run_case() and score_case() directly — no inspect-ai, no API key,
no database.  Exercises every scoring dimension in isolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
_VA_SRC = _ROOT / "services" / "voice-agent" / "src"
_EVAL_TASKS = _ROOT / "eval" / "tasks"

for _p in (_VA_SRC, _EVAL_TASKS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from agent_pipeline_eval import (  # noqa: E402
    PipelineResult,
    ScoreResult,
    load_cases,
    run_case,
    score_case,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _perfect(case: dict) -> PipelineResult:
    """Build a PipelineResult that satisfies every assertion in the case."""
    req_phrases = case.get("required_phrases", [])
    answer = " ".join(req_phrases) + " answer text"
    return PipelineResult(
        answer=answer,
        intent=case["expected_intent"],
        tool=case["expected_tool"],
        grounded=case["expected_grounded"],
        escalate=case["expected_escalate"],
    )


def _flawed(case: dict, **overrides) -> PipelineResult:
    base = _perfect(case)
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


# ── load_cases ────────────────────────────────────────────────────────────────

def test_load_cases_returns_list():
    cases = load_cases()
    assert isinstance(cases, list) and len(cases) >= 9


def test_load_cases_each_has_id():
    for c in load_cases():
        assert c.get("id")


# ── run_case — pipeline adapter ───────────────────────────────────────────────

def test_run_case_returns_pipeline_result():
    result = run_case("Is an MRI covered?")
    assert isinstance(result, PipelineResult)


def test_run_case_answer_non_empty():
    result = run_case("Is an MRI covered?")
    assert result.answer.strip()


def test_run_case_intent_non_empty():
    result = run_case("What is my urgent care copay?")
    assert result.intent


def test_run_case_tool_non_empty():
    result = run_case("Is lisinopril on my formulary?")
    assert result.tool


def test_run_case_grounded_is_bool():
    result = run_case("Find a cardiologist near me.")
    assert isinstance(result.grounded, bool)


def test_run_case_escalate_is_bool():
    result = run_case("My claim was denied.")
    assert isinstance(result.escalate, bool)


def test_run_case_tool_trace_is_list():
    result = run_case("Is an MRI covered?")
    assert isinstance(result.tool_trace, list)


def test_run_case_mri_coverage():
    result = run_case("Is an MRI of the brain covered under my plan?")
    assert result.intent == "coverage"
    assert result.tool == "check_coverage"
    assert result.grounded is True


def test_run_case_urgent_care_copay():
    result = run_case("What is my urgent care copay?")
    assert result.intent == "cost"
    assert result.tool == "estimate_cost"
    assert "$75" in result.answer


def test_run_case_lisinopril():
    result = run_case("Is lisinopril on my formulary?")
    assert result.intent == "formulary"
    assert result.tool == "check_formulary"
    assert "lisinopril" in result.answer.lower()


def test_run_case_provider_search():
    result = run_case("Find a cardiologist near me who is in network.")
    assert result.intent == "provider"
    assert result.tool == "find_provider"
    assert "cardiolog" in result.answer.lower()


def test_run_case_escalation():
    result = run_case("My claim was denied — what can I do?")
    assert result.intent == "escalate"
    assert result.tool == "escalate_to_human"
    assert result.escalate is True
    assert result.grounded is False


def test_run_case_unclear_question():
    result = run_case("I have a question about something.")
    assert result.escalate is True


# ── score_case — all checks pass ─────────────────────────────────────────────

def test_score_passes_for_perfect_result():
    cases = load_cases()
    for c in cases:
        result = _perfect(c)
        sr = score_case(c, result)
        assert sr.passed, f"Case {c['id']} failed with perfect result: {sr.failures}"


# ── score_case — intent failure ───────────────────────────────────────────────

def test_score_fails_on_wrong_intent():
    case = next(c for c in load_cases() if c["id"] == "mri-coverage")
    result = _flawed(case, intent="cost")
    sr = score_case(case, result)
    assert not sr.passed
    assert any("intent" in f for f in sr.failures)


# ── score_case — tool failure ─────────────────────────────────────────────────

def test_score_fails_on_wrong_tool():
    case = next(c for c in load_cases() if c["id"] == "urgent-care-copay")
    result = _flawed(case, tool="check_coverage")
    sr = score_case(case, result)
    assert not sr.passed
    assert any("tool" in f for f in sr.failures)


# ── score_case — required phrase missing ─────────────────────────────────────

def test_score_fails_when_required_phrase_missing():
    case = next(c for c in load_cases() if c["id"] == "lisinopril-formulary")
    result = _flawed(case, answer="Your medication is covered.")
    sr = score_case(case, result)
    assert not sr.passed
    assert any("required phrase" in f for f in sr.failures)


# ── score_case — forbidden phrase present ────────────────────────────────────

def test_score_fails_when_forbidden_phrase_present():
    case = next(c for c in load_cases() if c["id"] == "mri-coverage")
    result = _flawed(case, answer="MRI is not covered and was denied.")
    sr = score_case(case, result)
    assert not sr.passed
    assert any("forbidden phrase" in f for f in sr.failures)


# ── score_case — grounded mismatch ───────────────────────────────────────────

def test_score_fails_on_wrong_grounded_flag():
    case = next(c for c in load_cases() if c["id"] == "mri-coverage")
    result = _flawed(case, grounded=False)
    sr = score_case(case, result)
    assert not sr.passed
    assert any("grounded" in f for f in sr.failures)


# ── score_case — escalation mismatch ─────────────────────────────────────────

def test_score_fails_on_wrong_escalate_flag():
    case = next(c for c in load_cases() if c["id"] == "claim-denial")
    result = _flawed(case, escalate=False)
    sr = score_case(case, result)
    assert not sr.passed
    assert any("escalate" in f for f in sr.failures)


# ── score_case — multiple failures reported ───────────────────────────────────

def test_score_reports_multiple_failures():
    case = next(c for c in load_cases() if c["id"] == "urgent-care-copay")
    result = PipelineResult(
        answer="Your medication is fine.",  # wrong answer
        intent="formulary",                 # wrong intent
        tool="check_formulary",             # wrong tool
        grounded=False,                     # wrong grounded
        escalate=True,                      # wrong escalate
    )
    sr = score_case(case, result)
    assert not sr.passed
    assert len(sr.failures) >= 3


# ── score_case — metadata fields ─────────────────────────────────────────────

def test_score_result_has_case_id():
    case = load_cases()[0]
    sr = score_case(case, _perfect(case))
    assert sr.case_id == case["id"]


def test_score_result_has_question():
    case = load_cases()[0]
    sr = score_case(case, _perfect(case))
    assert sr.question == case["question"]


def test_score_result_records_actual_intent():
    case = load_cases()[0]
    result = _flawed(case, intent="formulary")
    sr = score_case(case, result)
    assert sr.actual_intent == "formulary"


def test_score_result_records_actual_tool():
    case = load_cases()[0]
    result = _flawed(case, tool="check_formulary")
    sr = score_case(case, result)
    assert sr.actual_tool == "check_formulary"


# ── full end-to-end: all cases pass through the pipeline and score ────────────

def test_all_cases_end_to_end():
    """Run every golden case through the real agent pipeline and score it."""
    cases = load_cases()
    failures_summary: list[str] = []
    for c in cases:
        result = run_case(c["question"])
        sr = score_case(c, result)
        if not sr.passed:
            failures_summary.append(
                f"\n  [{c['id']}] {c['question']!r}\n"
                + "\n".join(f"    • {f}" for f in sr.failures)
            )
    assert not failures_summary, (
        "Agent pipeline failed deterministic eval for these cases:" + "".join(failures_summary)
    )

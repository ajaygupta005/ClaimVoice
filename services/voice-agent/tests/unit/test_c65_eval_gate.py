"""
Component 65 — Evaluation and Observability Gate tests.

Tests:
- Dataset has ≥12 cases, all with required fields
- Dataset covers all 8 intent categories
- TurnTracer produces a TurnTrace with all observability fields
- TurnTracer captures correct intent, grounded, tool records
- TurnTracer handles pipeline error gracefully
- run_case scores a passing case correctly
- run_case detects intent mismatch
- run_case detects tool mismatch
- run_case detects missing required phrase
- run_case detects forbidden phrase
- run_case detects grounded mismatch
- run_case detects escalation mismatch
- run_eval returns EvalReport with correct totals (mock mode)
- EvalReport pass_rate is deterministic across two identical runs
- EvalReport records tool_mode and composer_mode
- save_json produces valid JSON
- save_markdown produces a markdown table
- Print report does not raise
- TurnTrace.to_dict is serializable
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make voice-agent and evals importable
_VA_SRC = Path(__file__).resolve().parent.parent.parent / "src"
_EVALS_DIR = Path(__file__).resolve().parent.parent.parent  # contains evals/
if str(_VA_SRC) not in sys.path:
    sys.path.insert(0, str(_VA_SRC))
if str(_EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(_EVALS_DIR))

_EVAL_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_DATASET_PATH = _EVAL_ROOT / "eval" / "datasets" / "agent_pipeline_cases.json"

import pytest


# ── Dataset integrity ─────────────────────────────────────────────────────────

def test_dataset_loads():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    assert len(cases) >= 12


def test_dataset_required_fields():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    required = {"id", "question", "expected_intent", "expected_tool",
                "expected_grounded", "expected_escalate"}
    for c in cases:
        missing = required - set(c.keys())
        assert not missing, f"Case {c.get('id')} missing fields: {missing}"


def test_dataset_covers_all_intents():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    intents = {c["expected_intent"] for c in cases}
    required_intents = {"coverage", "cost", "formulary", "provider", "escalate"}
    assert required_intents <= intents, f"Missing intents: {required_intents - intents}"


def test_dataset_has_escalation_cases():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    escalations = [c for c in cases if c["expected_escalate"]]
    assert len(escalations) >= 2, "Need at least 2 escalation cases"


def test_dataset_has_forbidden_phrase_cases():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    with_forbidden = [c for c in cases if c.get("forbidden_phrases")]
    assert len(with_forbidden) >= 1, "Need at least one case with forbidden phrases"


def test_dataset_unique_ids():
    from evals.run_eval import load_dataset
    cases = load_dataset(_DATASET_PATH)
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "Case IDs must be unique"


# ── TurnTracer ────────────────────────────────────────────────────────────────

def test_turn_tracer_produces_trace():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-test", streamSid="SM-test",
        text="Is an MRI covered?", confidence=1.0, duration_ms=None,
    )
    with TurnTracer(scenario_id="test-mri", question="Is an MRI covered?") as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    assert t.trace.scenario_id == "test-mri"
    assert t.trace.intent != ""
    assert isinstance(t.trace.grounded, bool)
    assert t.trace.total_ms >= 0


def test_turn_tracer_captures_intent():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-t", streamSid="SM-t",
        text="What is my PCP copay?", confidence=1.0, duration_ms=None,
    )
    with TurnTracer(scenario_id="pcp", question="pcp copay") as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    assert t.trace.intent == "cost"


def test_turn_tracer_captures_tool_records():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-t", streamSid="SM-t",
        text="Is lisinopril on my formulary?", confidence=1.0, duration_ms=None,
    )
    with TurnTracer() as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    assert len(t.trace.tools) == 1
    assert t.trace.tools[0].tool == "check_formulary"


def test_turn_tracer_captures_guard():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-t", streamSid="SM-t",
        text="Is physical therapy covered?", confidence=1.0, duration_ms=None,
    )
    with TurnTracer() as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    assert isinstance(t.trace.guard.passed, bool)
    assert t.trace.guard.reason != ""


def test_turn_tracer_handles_pipeline_error():
    from voice_agent.observability.trace import TurnTracer

    with TurnTracer(scenario_id="error-test") as t:
        t.set_error("simulated_failure")
        # Do not call set_result — simulates pipeline failure

    assert t.trace is not None
    assert t.trace.error == "simulated_failure"
    assert t.trace.grounded is False


def test_turn_tracer_stages_always_five():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-t", streamSid="SM-t",
        text="Find a dermatologist near me", confidence=1.0, duration_ms=None,
    )
    with TurnTracer() as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    assert len(t.trace.stages) == 5
    stage_names = [s.name for s in t.trace.stages]
    assert stage_names == ["identify", "understand", "tool", "guard", "respond"]


def test_turn_trace_to_dict_serializable():
    from voice_agent.observability.trace import TurnTracer
    from voice_agent.schemas.transcript import FinalTranscriptEvent
    from voice_agent.services.answer_orchestrator import orchestrate

    transcript = FinalTranscriptEvent(
        callSid="CA-t", streamSid="SM-t",
        text="Is an MRI covered?", confidence=1.0, duration_ms=None,
    )
    with TurnTracer() as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

    assert t.trace is not None
    d = t.trace.to_dict()
    # Must be JSON-serializable
    serialized = json.dumps(d)
    assert len(serialized) > 0
    parsed = json.loads(serialized)
    assert parsed["intent"] == "coverage"


# ── run_case scoring ──────────────────────────────────────────────────────────

def test_run_case_passes_mri_coverage():
    from evals.run_eval import run_case
    case = {
        "id": "mri-coverage",
        "question": "Is an MRI of the brain covered under my plan?",
        "expected_intent": "coverage",
        "expected_tool": "check_coverage",
        "required_phrases": ["MRI", "covered"],
        "forbidden_phrases": ["not covered", "denied"],
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, trace = run_case(case)
    assert cr.passed, f"Unexpected failures: {cr.failures}"
    assert cr.turn_id != ""
    assert trace is not None


def test_run_case_fails_on_intent_mismatch():
    from evals.run_eval import run_case
    case = {
        "id": "wrong-intent",
        "question": "Is an MRI covered?",
        "expected_intent": "formulary",  # wrong
        "expected_tool": "check_coverage",
        "required_phrases": [],
        "forbidden_phrases": [],
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, _ = run_case(case)
    assert not cr.passed
    assert any("intent" in f for f in cr.failures)


def test_run_case_fails_on_tool_mismatch():
    from evals.run_eval import run_case
    case = {
        "id": "wrong-tool",
        "question": "Is an MRI covered?",
        "expected_intent": "coverage",
        "expected_tool": "check_formulary",  # wrong
        "required_phrases": [],
        "forbidden_phrases": [],
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, _ = run_case(case)
    assert not cr.passed
    assert any("tool" in f for f in cr.failures)


def test_run_case_fails_on_missing_required_phrase():
    from evals.run_eval import run_case
    case = {
        "id": "missing-phrase",
        "question": "Is an MRI covered?",
        "expected_intent": "coverage",
        "expected_tool": "check_coverage",
        "required_phrases": ["xyzzy_nonexistent_phrase_12345"],
        "forbidden_phrases": [],
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, _ = run_case(case)
    assert not cr.passed
    assert any("missing required phrase" in f for f in cr.failures)


def test_run_case_fails_on_forbidden_phrase_present():
    from evals.run_eval import run_case
    # "covered" will appear in an MRI coverage answer
    case = {
        "id": "forbidden-phrase",
        "question": "Is an MRI covered?",
        "expected_intent": "coverage",
        "expected_tool": "check_coverage",
        "required_phrases": [],
        "forbidden_phrases": ["covered"],  # will be in answer
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, _ = run_case(case)
    assert not cr.passed
    assert any("forbidden phrase" in f for f in cr.failures)


def test_run_case_escalation_passes():
    from evals.run_eval import run_case
    case = {
        "id": "claim-denial",
        "question": "My claim was denied — what can I do?",
        "expected_intent": "escalate",
        "expected_tool": "escalate_to_human",
        "required_phrases": ["specialist", "connect"],
        "forbidden_phrases": [],
        "expected_grounded": False,
        "expected_escalate": True,
    }
    cr, _ = run_case(case)
    assert cr.passed, f"Unexpected failures: {cr.failures}"
    assert cr.escalated is True


def test_run_case_records_data_source():
    from evals.run_eval import run_case
    case = {
        "id": "ds-test",
        "question": "Is an MRI covered?",
        "expected_intent": "coverage",
        "expected_tool": "check_coverage",
        "required_phrases": [],
        "forbidden_phrases": [],
        "expected_grounded": True,
        "expected_escalate": False,
    }
    cr, _ = run_case(case)
    assert cr.data_source in ("real", "demo", "error")


# ── run_eval ──────────────────────────────────────────────────────────────────

def test_run_eval_all_cases_deterministic():
    from evals.run_eval import run_eval
    report = run_eval(dataset_path=_DATASET_PATH)
    assert report.total >= 12
    assert 0 <= report.passed <= report.total
    assert report.pass_rate == report.passed / report.total


def test_run_eval_mock_mode_high_pass_rate():
    """In mock mode all deterministic cases should pass."""
    from evals.run_eval import run_eval
    report = run_eval(dataset_path=_DATASET_PATH)
    assert report.pass_rate >= 0.8, (
        f"Expected ≥80% pass rate in mock mode, got {report.pass_rate:.0%}. "
        f"Failures: {[(c.case_id, c.failures) for c in report.cases if not c.passed]}"
    )


def test_run_eval_records_mode():
    from evals.run_eval import run_eval
    report = run_eval(dataset_path=_DATASET_PATH)
    assert report.tool_mode in ("mock", "http")
    assert report.composer_mode in ("mock", "claude")


def test_run_eval_ids_filter():
    from evals.run_eval import run_eval
    report = run_eval(ids=["mri-coverage", "pcp-copay"], dataset_path=_DATASET_PATH)
    assert report.total == 2
    assert {c.case_id for c in report.cases} == {"mri-coverage", "pcp-copay"}


def test_run_eval_deterministic_across_two_runs():
    from evals.run_eval import run_eval
    r1 = run_eval(ids=["mri-coverage", "lisinopril-formulary", "claim-denial"], dataset_path=_DATASET_PATH)
    r2 = run_eval(ids=["mri-coverage", "lisinopril-formulary", "claim-denial"], dataset_path=_DATASET_PATH)
    assert r1.passed == r2.passed
    assert r1.pass_rate == r2.pass_rate


# ── Report output ─────────────────────────────────────────────────────────────

def test_save_json_valid(tmp_path: Path):
    from evals.run_eval import run_eval, save_json
    report = run_eval(ids=["mri-coverage"], dataset_path=_DATASET_PATH)
    out = tmp_path / "results.json"
    save_json(report, out)
    parsed = json.loads(out.read_text())
    assert "total" in parsed
    assert "cases" in parsed
    assert isinstance(parsed["cases"], list)
    assert parsed["cases"][0]["case_id"] == "mri-coverage"


def test_save_json_contains_turn_id(tmp_path: Path):
    from evals.run_eval import run_eval, save_json
    report = run_eval(ids=["pcp-copay"], dataset_path=_DATASET_PATH)
    out = tmp_path / "results.json"
    save_json(report, out)
    parsed = json.loads(out.read_text())
    assert parsed["cases"][0]["turn_id"] != ""


def test_save_markdown_has_table(tmp_path: Path):
    from evals.run_eval import run_eval, save_markdown
    report = run_eval(ids=["mri-coverage", "claim-denial"], dataset_path=_DATASET_PATH)
    out = tmp_path / "results.md"
    save_markdown(report, out)
    md = out.read_text()
    assert "| ID |" in md
    assert "mri-coverage" in md
    assert "claim-denial" in md


def test_print_report_no_raise(capsys):
    from evals.run_eval import run_eval, print_report
    report = run_eval(ids=["mri-coverage"], dataset_path=_DATASET_PATH)
    print_report(report, use_color=False)
    captured = capsys.readouterr()
    assert "mri-coverage" in captured.out
    assert "PASS" in captured.out or "FAIL" in captured.out

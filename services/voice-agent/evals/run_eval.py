"""
Component 65 — WS-7 Evaluation and Observability Gate

Single-command eval runner for the ClaimVoice voice agent.

Usage:
    # mock mode (deterministic, no API keys needed)
    PYTHONPATH=src python evals/run_eval.py

    # real Claude answer mode
    VOICE_AGENT_ANSWER_MODE=claude ANTHROPIC_API_KEY=sk-... \\
        PYTHONPATH=src python evals/run_eval.py

    # with Langfuse traces
    LANGFUSE_SECRET_KEY=... LANGFUSE_PUBLIC_KEY=... \\
        PYTHONPATH=src python evals/run_eval.py

    # run only specific scenario IDs
    PYTHONPATH=src python evals/run_eval.py --ids mri-coverage,pcp-copay

    # save results
    PYTHONPATH=src python evals/run_eval.py --out results.json

Exit code: 0 if all required checks pass, 1 if any fail.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ── path setup: make voice-agent importable without install ──────────────────
_VA_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_VA_SRC) not in sys.path:
    sys.path.insert(0, str(_VA_SRC))

_EVAL_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DATASET_PATH = _EVAL_ROOT / "eval" / "datasets" / "agent_pipeline_cases.json"

from voice_agent.observability.trace import TurnTracer  # noqa: E402
from voice_agent.schemas.transcript import FinalTranscriptEvent  # noqa: E402
from voice_agent.services.answer_orchestrator import orchestrate  # noqa: E402


# ── Score types ───────────────────────────────────────────────────────────────

@dataclass
class ScoreDetail:
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    case_id: str
    question: str
    passed: bool
    failures: list[str]
    expected_intent: str
    actual_intent: str
    expected_tool: str
    actual_tool: str
    grounded: bool
    escalated: bool
    answer_snippet: str
    turn_id: str
    total_ms: int
    data_source: str  # "real" | "demo" | "error" from first tool call
    error: str = ""


@dataclass
class EvalReport:
    total: int
    passed: int
    failed: int
    pass_rate: float
    cases: list[CaseResult] = field(default_factory=list)
    tool_mode: str = "mock"
    composer_mode: str = "mock"
    run_ms: int = 0


# ── Dataset loader ────────────────────────────────────────────────────────────

def load_dataset(path: Path = _DATASET_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_case(case: dict[str, Any]) -> tuple[CaseResult, Any]:
    """
    Run one scenario through orchestrate() with tracing.
    Returns (CaseResult, TurnTrace).
    """
    from voice_agent.core.config import settings

    transcript = FinalTranscriptEvent(
        callSid=f"CA-eval-{case['id']}",
        streamSid=f"SM-eval-{case['id']}",
        text=case["question"],
        confidence=1.0,
        duration_ms=None,
    )

    with TurnTracer(
        scenario_id=case["id"],
        question=case["question"],
        tool_mode=settings.tool_mode,
        composer_mode=settings.voice_agent_answer_mode,
    ) as tracer:
        try:
            ev = orchestrate(transcript)
            tracer.set_result(ev)
        except Exception as exc:
            tracer.set_error(str(exc))
            ev = None

    trace = tracer.trace
    assert trace is not None

    if ev is None:
        result = CaseResult(
            case_id=case["id"],
            question=case["question"],
            passed=False,
            failures=[f"pipeline_error: {trace.error}"],
            expected_intent=case.get("expected_intent", ""),
            actual_intent="",
            expected_tool=case.get("expected_tool", ""),
            actual_tool="",
            grounded=False,
            escalated=False,
            answer_snippet="",
            turn_id=trace.turn_id,
            total_ms=trace.total_ms,
            data_source="error",
            error=trace.error,
        )
        return result, trace

    # Deterministic scoring
    failures: list[str] = []
    actual_intent = ev.intent
    actual_tool = ev.tool_trace[0].tool if ev.tool_trace else ""
    answer_lower = ev.text.lower()
    escalated = actual_tool == "escalate_to_human"
    data_source = ev.tool_trace[0].data_source if ev.tool_trace else "demo"

    if actual_intent != case["expected_intent"]:
        failures.append(
            f"intent: expected={case['expected_intent']!r} actual={actual_intent!r}"
        )

    if actual_tool != case["expected_tool"]:
        failures.append(
            f"tool: expected={case['expected_tool']!r} actual={actual_tool!r}"
        )

    for phrase in case.get("required_phrases", []):
        if phrase.lower() not in answer_lower:
            failures.append(f"missing required phrase: {phrase!r}")

    for phrase in case.get("forbidden_phrases", []):
        if phrase.lower() in answer_lower:
            failures.append(f"forbidden phrase present: {phrase!r}")

    if ev.grounded != case["expected_grounded"]:
        failures.append(
            f"grounded: expected={case['expected_grounded']} actual={ev.grounded}"
        )

    if escalated != case["expected_escalate"]:
        failures.append(
            f"escalate: expected={case['expected_escalate']} actual={escalated}"
        )

    result = CaseResult(
        case_id=case["id"],
        question=case["question"],
        passed=len(failures) == 0,
        failures=failures,
        expected_intent=case.get("expected_intent", ""),
        actual_intent=actual_intent,
        expected_tool=case.get("expected_tool", ""),
        actual_tool=actual_tool,
        grounded=ev.grounded,
        escalated=escalated,
        answer_snippet=ev.text[:200],
        turn_id=trace.turn_id,
        total_ms=trace.total_ms,
        data_source=data_source if isinstance(data_source, str) else "demo",
        error="",
    )
    return result, trace


# ── Reporter ──────────────────────────────────────────────────────────────────

_GREEN = "\033[32m"
_RED   = "\033[31m"
_YELLOW= "\033[33m"
_BOLD  = "\033[1m"
_RESET = "\033[0m"


def _c(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{_RESET}" if use_color else text


def print_report(report: EvalReport, *, use_color: bool = True) -> None:
    print()
    print(_c("=" * 60, _BOLD, use_color))
    print(_c("ClaimVoice WS-7 Eval Gate — Component 65", _BOLD, use_color))
    print(f"  tool_mode={report.tool_mode}  composer_mode={report.composer_mode}")
    print(_c("=" * 60, _BOLD, use_color))
    print()

    for cr in report.cases:
        icon = _c("PASS", _GREEN, use_color) if cr.passed else _c("FAIL", _RED, use_color)
        src  = f"[{cr.data_source}]" if cr.data_source else ""
        print(f"  {icon}  {cr.case_id:<30} {src}  ({cr.total_ms} ms)")
        if not cr.passed:
            for f in cr.failures:
                print(f"       • {f}")

    print()
    rate_color = _GREEN if report.pass_rate == 1.0 else (_YELLOW if report.pass_rate >= 0.8 else _RED)
    print(_c(f"  {report.passed}/{report.total} passed  ({report.pass_rate:.0%})", rate_color, use_color))
    print(f"  Total run time: {report.run_ms} ms")
    print()


def save_json(report: EvalReport, path: Path) -> None:
    out = {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": report.pass_rate,
        "tool_mode": report.tool_mode,
        "composer_mode": report.composer_mode,
        "run_ms": report.run_ms,
        "cases": [asdict(c) for c in report.cases],
    }
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def save_markdown(report: EvalReport, path: Path) -> None:
    lines = [
        "# WS-7 Eval Gate Results — Component 65",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total  | {report.total} |",
        f"| Passed | {report.passed} |",
        f"| Failed | {report.failed} |",
        f"| Pass rate | {report.pass_rate:.0%} |",
        f"| Tool mode | {report.tool_mode} |",
        f"| Composer | {report.composer_mode} |",
        f"| Run time | {report.run_ms} ms |",
        "",
        "## Case Results",
        "",
        "| ID | Status | Intent | Tool | Grounded | ms | Failures |",
        "|----|--------|--------|------|----------|-----|---------|",
    ]
    for cr in report.cases:
        status = "✅" if cr.passed else "❌"
        failures = "; ".join(cr.failures) if cr.failures else ""
        lines.append(
            f"| {cr.case_id} | {status} | {cr.actual_intent} | {cr.actual_tool} | "
            f"{'✅' if cr.grounded else '❌'} | {cr.total_ms} | {failures} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main entry point ─────────────────────────────────────────────────────────

def run_eval(
    *,
    ids: list[str] | None = None,
    dataset_path: Path = _DATASET_PATH,
) -> EvalReport:
    """
    Run the full eval suite and return an EvalReport.
    Used by both the CLI entry point and the unit tests.
    """
    from voice_agent.core.config import settings

    cases = load_dataset(dataset_path)
    if ids:
        cases = [c for c in cases if c["id"] in ids]

    t0 = time.monotonic()
    results: list[CaseResult] = []
    for case in cases:
        cr, _ = run_case(case)
        results.append(cr)

    run_ms = int((time.monotonic() - t0) * 1000)
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    return EvalReport(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=passed / total if total else 0.0,
        cases=results,
        tool_mode=settings.tool_mode,
        composer_mode=settings.voice_agent_answer_mode,
        run_ms=run_ms,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ClaimVoice WS-7 eval suite.")
    parser.add_argument(
        "--ids", default="",
        help="Comma-separated list of scenario IDs to run (default: all).",
    )
    parser.add_argument(
        "--out", default="",
        help="Path for the JSON results file (optional).",
    )
    parser.add_argument(
        "--md", default="",
        help="Path for the Markdown results file (optional).",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color output.",
    )
    parser.add_argument(
        "--dataset", default=str(_DATASET_PATH),
        help="Path to the JSON scenario dataset.",
    )
    args = parser.parse_args()

    id_filter = [s.strip() for s in args.ids.split(",") if s.strip()] or None
    report = run_eval(ids=id_filter, dataset_path=Path(args.dataset))

    print_report(report, use_color=not args.no_color)

    if args.out:
        save_json(report, Path(args.out))
        print(f"  JSON results saved → {args.out}")

    if args.md:
        save_markdown(report, Path(args.md))
        print(f"  Markdown results saved → {args.md}")

    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()

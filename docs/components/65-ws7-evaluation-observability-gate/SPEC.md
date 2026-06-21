# Component 65 - WS-7 Evaluation and Observability Gate

## Purpose

Turn WS-7 agent behavior into something measurable. The voice agent should pass a repeatable evaluation suite before demos and expose useful traces for debugging.

## Current State

Specs and tests exist across earlier components, but agent quality should become a single repeatable gate covering tool use, answer grounding, guard behavior, and escalation.

## Scope

Add or consolidate:

- scenario dataset
- expected tool use
- expected answer facts
- hallucination guard checks
- escalation cases
- provider/cost/formulary/coverage cases
- out-of-scope questions
- result reporting
- optional Langfuse traces

## Required Behavior

- A single command can run the eval suite.
- Each scenario reports pass/fail and reasons.
- Tool choice is checked.
- Required facts are checked.
- Unsupported claims fail.
- Escalation behavior is checked.
- Results can be saved for demo readiness.

## Non-Goals

- No new model training.
- No subjective LLM-only grading as the only signal.
- No UI changes required.

## Acceptance Criteria

- Eval suite covers core insurance intents.
- Results are deterministic enough for local development.
- Failures identify the pipeline stage responsible.
- Observability fields can be connected to Langfuse when configured.


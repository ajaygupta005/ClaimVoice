# Component 65 - WS-7 Evaluation and Observability Gate Plan

## Implementation Steps

1. Define scenario set.
   - Coverage.
   - Cost.
   - Formulary.
   - Provider search.
   - Prior authorization.
   - Denial/claim help.
   - Out-of-scope.
   - Escalation required.

2. Define expected outputs.
   - Expected intent.
   - Expected tool.
   - Required facts.
   - Forbidden claims.
   - Expected guard outcome.

3. Build eval runner.
   - Run each scenario through `/api/v1/agent/respond` or internal graph.
   - Capture pipeline response.
   - Score deterministic checks.

4. Add report output.
   - Terminal summary.
   - JSON results file.
   - Optional markdown report.

5. Add observability hooks.
   - Turn ID.
   - scenario ID.
   - stage timings.
   - tool traces.
   - guard result.
   - final score.

6. Add CI/dev command.
   - Keep networked model calls optional.
   - Allow mock mode for deterministic CI.
   - Allow Claude mode for demo-readiness checks.

## Suggested Files

- `services/voice-agent/evals/*`
- `services/voice-agent/tests/eval/*`
- `services/voice-agent/src/voice_agent/observability/*`
- `docs/components/65-ws7-evaluation-observability-gate/RESULTS.md` after execution

## Validation

- Eval runner exits non-zero on failing required checks.
- Mock mode is deterministic.
- Claude mode can be run locally when keys are present.

## Risks

- LLM answer wording can vary.
- Overly strict checks can create false failures.
- Too much observability can expose sensitive data if not redacted.

## Done When

- Agent readiness can be assessed with one repeatable command.
- Failures are actionable.
- Demo confidence is based on evidence, not manual clicking only.


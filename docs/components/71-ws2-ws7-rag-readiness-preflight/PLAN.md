# Component 71 - WS-2/WS-7 RAG Readiness Preflight Plan

## Implementation Steps

1. Inspect current startup preflight.
   - Review `scripts/start.py`.
   - Review voice-agent runtime status.
   - Review eligibility health endpoints.

2. Add eligibility RAG readiness.
   - Check `VOYAGE_API_KEY`.
   - Query pgvector availability.
   - Query `sbc_chunks` existence and row count.
   - Query plan-linked chunk count.

3. Expose status to WS-7.
   - Include RAG readiness in voice-agent runtime/status if WS-7 depends on it.
   - Keep status compact and non-secret.

4. Surface status in WS-2.
   - Add a simple "SBC RAG" readiness indicator.
   - Prefer honest unavailable labels over silent demo fallback.

5. Add tests.
   - Missing key.
   - Missing table.
   - Empty table.
   - Healthy table.
   - Startup output formatting.

## Suggested Files

- `scripts/start.py`
- `services/eligibility/src/eligibility/api/v1/*`
- `services/voice-agent/src/voice_agent/api/v1/runtime_status.py`
- `apps/web/src/components/*`

## Validation

- `python scripts/start.py`
- `curl http://localhost:8002/health`
- `curl http://localhost:8004/api/v1/runtime/status`
- Web typecheck

## Risks

- Making RAG readiness a hard startup failure can block unrelated demos.
- Counting rows without checking plan linkage can produce false readiness.
- Status payloads can become noisy if they include too much database detail.

## Done When

- Startup tells the operator whether RAG is usable.
- Runtime status tells the UI whether evidence/citations can be expected.
- Missing or empty RAG state is explicit.

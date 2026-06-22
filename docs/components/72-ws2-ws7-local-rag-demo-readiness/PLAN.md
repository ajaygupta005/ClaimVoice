# Component 72 - WS-2/WS-7 Local RAG Demo Readiness Plan

## Implementation Steps

1. Inspect current seed and ingest scripts.
   - Confirm `scripts/seed_dev.sh` behavior.
   - Confirm `data/ingest/sbc_embed_ingest.py` inputs.
   - Confirm required raw SBC file location.

2. Document local setup.
   - `.env` requirements.
   - Docker/Postgres requirements.
   - Migration requirement.
   - Seed requirement.
   - Ingest requirement.

3. Add a smoke-test sequence.
   - Start services.
   - Seed database.
   - Run ingest.
   - Verify chunks exist.
   - Query `/api/v1/sbc/retrieve`.
   - Ask browser voice question.

4. Add troubleshooting.
   - Missing key.
   - Empty raw SBC directory.
   - Missing plan ID.
   - Empty chunks.
   - Postgres image without pgvector.

5. Add optional demo checklist.
   - Questions to ask.
   - Expected evidence.
   - Logs to inspect.

## Suggested Files

- `docs/components/72-ws2-ws7-local-rag-demo-readiness/*`
- Optional future repo docs if needed after this component is implemented.

## Validation

- Follow the documented commands on a clean local DB.
- Confirm RAG retrieve returns chunks.
- Confirm UI/voice path uses or displays evidence after Components 68-70.

## Risks

- Seeded plan UUID may change between environments.
- Voyage API limits can make ingest flaky without batching/rate-limit guidance.
- Existing Docker volumes may hide migration or image changes.

## Done When

- The local RAG demo has a repeatable checklist.
- A failed demo can be diagnosed from the checklist.
- The browser and API smoke tests agree that RAG is ready.

# Component 71 - WS-2/WS-7 RAG Readiness Preflight

## Purpose

Make startup and runtime status report whether SBC RAG is actually usable.

The system should not say RAG is configured merely because the endpoint exists. It must verify the key, migration/table, and indexed data.

## Required Behavior

Readiness must check:

- `VOYAGE_API_KEY` is configured when RAG is enabled.
- Postgres has pgvector available.
- `sbc_chunks` table exists.
- `sbc_chunks` contains at least one row.
- At least one chunk is linked to an existing plan.

Readiness should expose:

- `ragStatus`
- `ragReason`
- `sbcChunksCount`
- `voyageConfigured`
- `pgvectorAvailable`

## Startup Behavior

`scripts/start.py` should surface RAG status in the same style as voice runtime preflight.

RAG unavailable should be a warning for local demo mode, not a hard failure, unless real RAG mode is explicitly required.

## UI Behavior

WS-2 status panels should show:

- RAG ready
- RAG unavailable
- RAG empty
- RAG key missing

## Acceptance Criteria

- Missing `VOYAGE_API_KEY` is visible in startup and runtime status.
- Missing `sbc_chunks` table is visible.
- Empty `sbc_chunks` table is visible.
- Healthy indexed state is visible.
- UI does not claim citations/RAG are ready unless readiness says ready.

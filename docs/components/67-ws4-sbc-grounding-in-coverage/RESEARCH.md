# Component 67 - WS-4 SBC Grounding in /coverage - Research

## Why enrich at the endpoint, not in the builder
`build_coverage_response` is a pure function unit-tested offline over hand-built result
dicts. Doing SBC retrieval (Azure embed + pgvector) inside it would make those unit tests
hit the network and DB. So enrichment lives in the `/coverage` route handler (which already
opens a DB session); the builder stays pure and its tests stay offline and deterministic.

## Why best-effort + bounded
SBC passages are a bonus on top of the structured facts (which already include
"prior authorization required"), so coverage must still answer if embeddings are
unavailable. `sbc_facts_for` returns `[]` on any failure, and the Azure client is created
with `timeout=4s, max_retries=0`. The OpenAI SDK default is ~600s with retries, which had
hung the whole `/coverage` request and tripped the voice tool's timeout into a mock
fallback -- bounding it caps `/coverage` latency.

## Why trim passages
The synthetic SBCs chunk to ~90 words; trimming each retrieved passage to ~400 chars keeps
`facts[]` compact for the guard and the composer while preserving the relevant sentence
(e.g. the MRI prior-auth clause).

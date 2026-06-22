# Component 67 - WS-4 SBC Grounding in /coverage - Plan

1. `services/coverage.py`: add `sbc_facts_for(plan_id, service)` -- gated on
   `settings.sbc_rag_in_coverage` and an embed key being present; calls
   `sbc_rag.retrieve_chunks` (top_k=2), trims each chunk to ~400 chars, prefixes
   "From the plan's Summary of Benefits (<section>):"; returns `[]` on any error. Leave
   `build_coverage_response` pure.
2. `api/v1/coverage.py`: after `build_coverage_response`, do
   `resp.facts.extend(sbc_facts_for(resp.planId, service))` -- I/O at the endpoint, not in
   the pure builder.
3. `core/config.py`: add `sbc_rag_in_coverage=True` and `sbc_rag_top_k=2`.
4. `lib/embeddings.py`: construct the Azure client with `timeout=4.0, max_retries=0`.

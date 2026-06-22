# Component 67 - WS-4 SBC Grounding in /coverage - Results

## Checklist
- [x] `sbc_facts_for()` in `services/coverage.py`; called from `api/v1/coverage.py`.
- [x] Pure `build_coverage_response` unchanged (offline unit tests intact).
- [x] `sbc_rag_in_coverage` / `sbc_rag_top_k` settings added.
- [x] Azure client bounded (`timeout=4.0, max_retries=0`).

## Verification
- `GET /coverage?memberId=CVX-0042-MT&service=MRI` returns the structured facts **plus two
  SBC passages** (imaging prior-auth, Rx tiers).
- `/coverage` latency ~3.5s (was hanging >30s before the client was bounded).
- Eligibility unit suite green (**35 passed**); eval gate **51 passed**.

## Commit
```
01b11f9 feat(ws4): SBC RAG on Azure text-embedding-3-large, wired into coverage grounding
f27e62c fix(ws4,ws5): bound Azure embed client + emit WKT for provider geo under PostGIS
```

## Notes
- The voice agent's `check_coverage` tool already forwards the `/coverage` `facts`, so SBC
  passages reach `tool_facts` -> the hallucination guard + the Claude composer with no
  change needed on the voice-agent side.

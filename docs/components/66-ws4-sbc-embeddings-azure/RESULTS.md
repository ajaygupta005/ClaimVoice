# Component 66 - WS-4 SBC Embeddings on Azure OpenAI - Results

## Checklist
- [x] Azure embed config + `openai` dep; `SBC_EMBED_PROVIDER=azure` default.
- [x] `lib/embeddings.py` shared by `sbc_rag.py` (query) and the ingest `_Embedder` (docs).
- [x] `gen_synthetic_sbcs.py` -> 8 valid SBC PDFs; manifest mapped to seeded plans + demo.
- [x] Ingest -> **40 `sbc_chunks`** (5 per plan, incl. the demo plan), 1024-dim.
- [x] `sbc_rag_repo` uses `CAST(:query_vec AS vector)`.

## Verification
- Standalone Azure embed returns **1024 dims** (~2-4s).
- `retrieve_chunks(demo_plan, "MRI prior authorization")` returns the imaging-section chunk.
- Eligibility unit suite green (**35 passed**) after the embedding swap.

## Commit
```
bc4c105 feat(ws4): snapshot SBC RAG pipeline (squashed from ws4-sbc-pipeline)
01b11f9 feat(ws4): SBC RAG on Azure text-embedding-3-large, wired into coverage grounding
f27e62c fix(ws4,ws5): bound Azure embed client ...
```

## Notes
- Embeddings are independent of Claude -- Azure for vectors, Anthropic for narration.
- A bounded Azure client (Component 67) prevents a slow embed from hanging requests.
- Synthetic SBCs are dev data; swap real PDFs by editing `sbc_manifest.yaml` + re-ingest.

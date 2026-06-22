# Component 66 - WS-4 SBC Embeddings on Azure OpenAI - Plan

1. `eligibility/core/config.py`: add `sbc_embed_provider` (azure|voyage, default azure),
   `embedding_dimensions=1024`, `azure_openai_endpoint/_api_key/_api_version`, and
   `foundry_deployment_embedding`. Add `openai` to `services/eligibility/pyproject.toml`.
2. New `eligibility/lib/embeddings.py` (`embed_query` / `embed_texts`): Azure `AzureOpenAI`
   (`embeddings.create(input, model=<deployment>, dimensions=1024)`), or Voyage by setting.
3. `services/sbc_rag.py`: replace the inline Voyage call with `embed_query`.
4. `data/ingest/sbc_embed_ingest.py`: replace the Voyage client with an `_Embedder` that
   dispatches the same way (reads provider / azure config from Hydra + env); drop
   Voyage's `input_type`. `data/ingest/configs/sbc_embed_ingest.yaml`: add provider +
   azure settings + `embed_dimensions`.
5. `scripts/gen_synthetic_sbcs.py`: generate one SBC PDF per manifest plan (fpdf2) into
   `data/raw/sbcs/` (+ JSON sidecars), since the payor URLs 404.
6. `data/ingest/configs/sbc_manifest.yaml`: align the 8 `plan_name`s to seeded plans and
   map one to "ClaimVoice Demo PPO".
7. Run: generate -> `sbc_embed_ingest.py embed.chunk_size=90 embed.overlap=20 ...` -> 40
   chunks in `sbc_chunks`.
8. Fix `repositories/sbc_rag_repo.py`: `CAST(:query_vec AS vector)` (SQLAlchemy `text()`
   mis-parses `:vec::vector`).

# Live Product — Results (feat/live-product)

**Date:** 2026-06-22 · **Branch:** `feat/live-product` (off updated `main`)

End-to-end bring-up of the grounded voice product, with the SBC RAG pipeline snapshotted in
and switched to Azure embeddings. Everything below was executed and verified locally.

## What was delivered & verified

| Area | Result |
|---|---|
| **Dedicated DB** | PostGIS+pgvector Postgres built from `infra/postgres/Dockerfile`, on host **:5433** (Sentinel on 5432 untouched). `alembic upgrade head` → `001` + `002_sbc_chunks`. |
| **Seed** | 500 providers, 17 plans, 31 members incl. demo `CVX-0042-MT` (plan `ClaimVoice Demo PPO`, id `4bdc799f…`). |
| **Embeddings** | Swapped Voyage → **Azure `text-embedding-3-large` @ 1024 dims** (ingest + query). Validated: returns 1024-dim. |
| **SBC corpus** | Payor SBC URLs 404'd → generated 8 deterministic synthetic SBCs (`scripts/gen_synthetic_sbcs.py`), ingested → **40 `sbc_chunks`** (5/plan incl. demo plan). |
| **SBC grounding** | `GET /api/v1/coverage?memberId=CVX-0042-MT&service=MRI` returns structured facts **+ SBC passages** (MRI prior-auth, Rx tiers). Fixed a real `sbc_rag_repo` SQL bug (`CAST(:vec AS vector)`). |
| **Voice chain** | In-process agent graph (TOOL_MODE=http) → grounded answers for coverage/cost/provider; `grounded=True`; tool_facts carry SBC. |
| **Eval gate** | `eval/tests -m "not integration"` → **51 passed**, 1 skipped (pre-existing stub). |
| **Eligibility unit tests** | **35 passed.** |
| **Dashboard** | Next proxies `api/{eligibility,providers}/[...slug]`; Plan + Providers tabs fetch live (mock fallback). Web **typecheck passes**; live proxy returns demo member's real summary. |
| **API keys** | Azure embeddings ✅ · Deepgram ✅ (200) · Cartesia ✅ (200) · **Anthropic ✅ (updated key — live Claude verified)**. |
| **Live Claude E2E** | All 3 intents grounded with real Claude: coverage *"…20% coinsurance after your deductible, but prior authorization is required before the scan is performed…"* (SBC-cited); cost *"$1,050 remaining of your $1,500…"*; provider *"…John Gonzalez 1.56 km, Lisa Davis 2.16 km…"*. |

## ✅ Resolved: live Claude path working

The Anthropic key was updated to a valid one; `.env` is now `VOICE_AGENT_ANSWER_MODE=claude` +
`FACT_CHECK_MODE=claude`. Verified end-to-end (see "Live Claude E2E" above): Claude narrates from
`tool_facts` incl. SBC passages, and the `/fact_check` guard runs in claude mode.

Two live-run fixes applied during verification (committed):
- **Embed hang** — bounded the AzureOpenAI client (`timeout=4s, max_retries=0`); the SDK default
  (~600s) had let a slow embed hang `/coverage` (+ check_coverage tool timeout 5s→20s).
- **Provider geo under PostGIS** — `near_candidates` now emits `ST_AsText(location::geometry)`; the
  geography column returned EWKB hex the WKT parser couldn't read, so `/providers/near` returned 0.

## How to run

```powershell
# 1. DB (dedicated, :5433)
docker compose up -d postgres
powershell -File scripts\seed_dev.ps1 -DatabaseUrl "postgresql://claimvoice:changeme@localhost:5433/claimvoice"
# 2. SBC corpus (Azure embeddings; loads .env)
python scripts\gen_synthetic_sbcs.py
python data\ingest\sbc_embed_ingest.py embed.chunk_size=90 embed.overlap=20 embed.min_chunk_words=10
# 3. Services (ephemeral uv) — eligibility :8002, providers :8003, voice-agent :8004
#    (load .env into the shell first; PYTHONPATH=services/<svc>/src; uvicorn <pkg>.main:app)
# 4. Web
corepack pnpm install && corepack pnpm --filter web dev    # :3000
```
Run-mode env (in `.env`): `TOOL_MODE=http`, `SBC_EMBED_PROVIDER=azure`, answer/fact-check =
`mock` until a valid Anthropic key is in place; `STT_MODE=deepgram`, `TTS_MODE=cartesia`.

## Known limitations / follow-ups
- **No cardiologists in the synthetic provider seed** → "find a cardiologist" correctly returns
  "none found". Provider queries that return results: internal/family medicine, pediatrics,
  psychiatry, emergency medicine. (Seed cardiology providers for a richer demo.)
- **Demo plan in-network** links are sparse → Providers tab in-network default is off; geo uses Haversine.
- **Docker Desktop must be running** (Postgres :5433). If it stops, DB-backed calls hang — restart Docker + `docker compose up -d postgres` (the `pg_data` volume persists).
- Browser **STT** is the free Web Speech API; Deepgram/Cartesia validated (keys ok) and used server-side.
- SBC corpus is **synthetic** (payor URLs 404) — swap in real SBC PDFs by updating `sbc_manifest.yaml`.

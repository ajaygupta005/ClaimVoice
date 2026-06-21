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
| **API keys** | Azure embeddings ✅ · Deepgram ✅ (200) · Cartesia ✅ (200) · **Anthropic ❌ 401 invalid x-api-key**. |

## ⚠️ Blocker: Anthropic key invalid (401)

The supplied `ANTHROPIC_API_KEY` returns **401 invalid x-api-key**. Consequence: the Claude
answer composer and `claude` fact-check fall back. To keep the product working now,
`.env` is set to `VOICE_AGENT_ANSWER_MODE=mock` and `FACT_CHECK_MODE=mock` (deterministic; the
MockComposer's hardcoded figures match the demo plan, so demo answers are correct — except the
provider answer uses a placeholder name).

**To enable the real Claude path:** put a valid key in `.env` and flip both back to `claude`.
The composer already grounds on `tool_facts` (incl. SBC passages), so Claude answers will cite
the Summary-of-Benefits text.

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
- **Anthropic key invalid** — real Claude answers + claude fact-check blocked (see above).
- **Provider answer** in mock-compose uses a placeholder name; real provider narration needs Claude.
- **Demo plan in-network** links are sparse → Providers tab in-network default is off; geo uses Haversine.
- Browser **STT** is the free Web Speech API; Deepgram/Cartesia validated (keys ok) and used server-side.
- SBC corpus is **synthetic** (payor URLs 404) — swap in real SBC PDFs by updating `sbc_manifest.yaml`.

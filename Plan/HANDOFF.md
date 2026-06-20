# ClaimVoice WS-4 / WS-5 / WS-6 — Session Hand-off

> **New session: read this first**, then `Plan/ROADMAP.md` and the per-feature component docs in
> `docs/components/40-49/` (SPEC/RESEARCH/PLAN/RESULTS each).
> This captures the non-obvious context (dev DB, run modes, test commands) that is NOT
> derivable from the code alone.

## TL;DR

- **Branch:** `feat/ws456-grounded-agent` — 18 commits ahead of `origin/main`, **not pushed**.
- **Delivered:** WS-4 Eligibility + WS-5 Providers built end-to-end; WS-6 Voice Agent wired
  to them (real tool clients, fact-check guard, Deepgram/Cartesia/VAD adapters, conversation
  memory + member threading). Milestones **M0–M14 complete**, one commit each, all with tests.
- **Tests green:** WS-4 = 40, WS-5 = 20, WS-6 = 236, eval gate = 51 (deterministic).
- **Live e2e proven:** with services up + `TOOL_MODE=http`, the agent returns grounded
  answers sourced from the real DB (not mock fallback).

## Dev environment — the non-obvious bits

- The dev DB is **reused from another running app ("Sentinel")** because Docker Hub pulls of
  the project's own `postgis` image fail in this environment. Sentinel runs
  `postgres:16-alpine` as container **`sentinel-postgres`** on **`localhost:5432`**. We added an
  **isolated `claimvoice` role + database** there (creds `claimvoice` / `changeme`). Sentinel's
  own `sentinel` database is untouched.
- `DATABASE_URL=postgresql://claimvoice:changeme@localhost:5432/claimvoice`
- It is **plain Postgres → no PostGIS, no pgvector.** Consequences:
  - Geo is computed **app-side (Haversine)** — matches `provider_lookup_eval`. `providers.location`
    is stored as text WKT, not `geography`.
  - **SBC RAG is deferred** — WS-4 grounds on structured data only.
- **Seed (idempotent):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\seed_dev.ps1 -ExistingDb -SentinelContainer sentinel-postgres
  ```
  (bash equivalent: `bash scripts/seed_dev.sh`). Seeds ~500 enriched providers, 16 plans +
  benefits + formulary + in_network + ICD/HCPCS, 30 members, **demo member `CVX-0042-MT`**
  (golden values), and 30 X12 271 stubs.
- ⚠️ **Do NOT run the project's own `docker compose up postgres` / `just up`** while reusing
  Sentinel — it collides on port 5432. (`just` may not be installed; the `.ps1` needs neither
  `just` nor bash.) To remove our footprint later: `DROP DATABASE claimvoice; DROP ROLE claimvoice;`
  inside `sentinel-postgres`.

## Running tests — avoid a full `uv sync`

A full `uv sync` pulls the heavy `document-ai` ML deps (torch, etc.). Use **per-service ephemeral
uv envs** with `PYTHONPATH` instead. Integration tests auto-skip when the DB is unreachable.

```powershell
$env:DATABASE_URL="postgresql://claimvoice:changeme@localhost:5432/claimvoice"

# WS-4 eligibility (40 tests)
$env:PYTHONPATH="services/eligibility/src"
uv run --no-project --python 3.12 --with fastapi --with pydantic --with pydantic-settings `
  --with sqlalchemy --with "psycopg[binary]" --with httpx --with loguru --with prometheus-client `
  --with pytest python -m pytest services/eligibility/tests -q

# WS-5 providers (20 tests) — same deps, PYTHONPATH=services/providers/src

# WS-6 voice-agent (236 tests)
$env:PYTHONPATH="services/voice-agent/src"
uv run --no-project --python 3.12 --with langgraph --with anthropic --with fastapi --with httpx `
  --with pydantic --with pydantic-settings --with typing-extensions --with loguru `
  --with prometheus-client --with pytest python -m pytest services/voice-agent/tests -q

# eval gate (51 tests) — voice-agent dep set, from repo root:
uv run --no-project --python 3.12 <voice-agent deps> python -m pytest eval/tests -m "not integration" -q
```

## Run modes (env toggles — all default `"mock"` ⇒ fully offline)

| Var | Effect | Needs |
|---|---|---|
| `TOOL_MODE=http` | voice-agent tools call WS-4/WS-5 over httpx (else mock strings) | services up |
| `VOICE_AGENT_ANSWER_MODE=claude` | ClaudeComposer narrates strictly from facts (**recommended in http mode** — see limitation #2) | `ANTHROPIC_API_KEY` |
| `FACT_CHECK_MODE=claude` | eligibility `/fact_check` uses LLM entailment | `ANTHROPIC_API_KEY` |
| `STT_MODE=deepgram` / `TTS_MODE=cartesia` | real streaming adapters | `DEEPGRAM_API_KEY` / `CARTESIA_API_KEY` |
| `ELIGIBILITY_BASE_URL` / `PROVIDERS_BASE_URL` | http tool targets | default `localhost:8002/8003` |

### Live end-to-end (the capstone check)
Start `eligibility` (:8002) and `providers` (:8003) via uvicorn against the seeded DB, then run
the graph with `TOOL_MODE=http` + base URLs for member `CVX-0042-MT`. Verified: real DB-sourced,
grounded answers; guard calls live `/fact_check`.

## Where things live

- **WS-4** `services/eligibility/src/eligibility/`: `api/v1/{coverage,cost,formulary_lookup,fact_check}.py`,
  `services/{coverage,cost_estimator,formulary,fact_check}.py`, `repositories/member_repo.py`, `lib/money.py`.
- **WS-5** `services/providers/src/providers/`: `services/{geo_search,quality_enrichment}.py`,
  `api/v1/{providers_near,providers_bulk}.py`, `repositories/provider_repo.py`; backfill at `data/ingest/enrich_providers.py`.
- **WS-6** `services/voice-agent/src/voice_agent/`: `tools/*`, `guards/hallucination.py`,
  `graph/nodes/{call_tool,hallucination_guard,identify_member}.py`, `streaming/{deepgram_stt,cartesia_tts,vad,factory}.py`,
  `services/session_memory.py`.
- **Seed/data:** `data/ingest/{seed_dev,seed_demo_member,enrich_providers}.py`, `scripts/seed_dev.{ps1,sh}`.
- **Evals:** `eval/tasks/{agent_pipeline_eval,e2e_voice_eval,provider_lookup_eval,coverage_qa_eval,hallucination_eval}.py`.
- **Specs:** per-feature in `docs/components/40-49/`; program view + component map in `Plan/ROADMAP.md`.

## Known limitations / next steps (prioritized)

1. **Real Claude / Deepgram / Cartesia adapters are implemented + key-gated but NOT live-verified**
   (no API keys here). `uv` resolved newer majors (`cartesia` 3.x, `deepgram-sdk` 7.x) — verify the
   lazy SDK call signatures when keys are available.
2. **http-mode + MockComposer flags cost answers ungrounded**: the mock composer hard-codes
   `$30/$75/$50`, which the guard correctly rejects against the narrower http facts. Fix by setting
   `VOICE_AGENT_ANSWER_MODE=claude`, or refactor the MockComposer cost branch to narrate strictly
   from `tool_result`/`tool_facts`.
3. **SBC RAG deferred** — needs a pgvector-capable Postgres + Voyage key, then a `002_sbc_embeddings`
   migration + retrieval wired as a `facts` source in `/coverage` and `/fact_check`.
4. **Production geo** — migrate `providers.location` to PostGIS `geography(POINT,4326)` + `ST_DWithin`
   (the `/providers/near` contract stays the same).
5. **Out of scope by decision:** api-gateway routing (WS-8); wiring WS-2 Plan/Providers tabs off mock data.
6. **Push the branch + open a PR** when ready (currently local only).

## Provenance

Milestone-by-milestone: `git log --oneline origin/main..HEAD`. The approved plan lives at
`~/.claude/plans/no-first-i-would-enumerated-turing.md` (local, not in the repo).

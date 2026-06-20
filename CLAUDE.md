# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaimVoice is a multi-modal AI agent for US health-insurance members. Members photograph their insurance card and have a voice conversation with an AI agent that answers coverage, cost, and provider questions — grounded entirely in structured data with a hallucination guard that fact-checks every claim before it's spoken.

## Commands

### Setup
```bash
just install        # pnpm install + uv sync  (pre-commit hooks are NOT auto-installed; run `pre-commit install` separately)
just up             # docker compose up -d (Postgres, Redis, MinIO, MLflow, Langfuse, Prometheus, Grafana)
just data.ingest    # dvc repro of the CMS ingest stages, in dependency order
dvc pull            # fetch ML model checkpoints from MinIO remote
just dev            # turbo dev — all services with hot reload

# Or one-shot, cross-platform (no `just` needed): python scripts/start.py  (see Startup Script below)
```

### Development
```bash
just dev            # all services (web :3000, api-gateway :8080, plus Python services)
pnpm dev            # turbo dev
pnpm build          # production build (Turbo-orchestrated)
pnpm lint           # ESLint across all TS workspaces (turbo lint)
# Root scripts are build/dev/lint/test only (see package.json + turbo.json — no root `typecheck` task).
# pnpm workspaces cover only apps/*, services/api-gateway, services/telephony, packages/* — the FastAPI services are a uv workspace.
```

### Testing
```bash
just test                                   # full suite: pnpm test + uv run pytest -q
uv run pytest -q                            # Python tests only (root pytest.ini: tests/, services/telephony/tests/, eval/tests/)
uv run pytest services/voice-agent          # single service's tests
uv run pytest -m "not integration and not e2e"   # skip tests that need running services / external APIs
pnpm test --filter=web                      # single JS workspace
just eval                                   # full Inspect AI suite → `inspect eval eval/tasks/`
inspect eval eval/tasks/card_ocr_eval.py    # one eval task (there is NO `just eval.<name>` recipe)
```

### Code Quality
```bash
uv run ruff check .                 # Python lint (root pyproject: select E/F/W, ignore E501, line-length 100)
uv run ruff format .                # Python format
pnpm lint                           # ESLint (via `turbo lint`)
pnpm --filter=<package> typecheck   # per-package TS check
```

### ML Training
```bash
just train.card_ocr         # fine-tune LayoutLMv3 for card OCR
just train.payor            # fine-tune ResNet-50 payor classifier
just train.sbc              # fine-tune LayoutLMv3 for SBC parsing
just train.all              # all three in sequence
```

### API Client Generation
```bash
just gen.clients    # regenerate TypeScript types from OpenAPI specs (output: packages/shared-types/)
```

## Architecture

### Monorepo Layout

```
apps/web                 # Next.js 15 frontend
services/
  api-gateway            # Fastify (Node 20) — JWT auth, rate limiting, routing
  document-ai            # FastAPI — card OCR, payor classifier, SBC parsing
  eligibility            # FastAPI — plan knowledge graph, SBC RAG, cost estimation
  providers              # FastAPI — NPI registry, PostGIS geo-search, in-network filtering
  voice-agent            # FastAPI + LangGraph — Claude orchestration, STT/TTS streaming
  telephony              # Fastify (Node 20) — Twilio Media Streams, μ-law transcoding
packages/
  shared-prompts         # Versioned Claude prompts
  shared-logging         # Structured JSON logging (pino for Node, loguru for Python)
  shared-observability   # Langfuse + OpenTelemetry clients
  shared-config          # Environment schema + constants
  shared-types           # Auto-generated TypeScript from OpenAPI
data/
  ingest/                # ETL scripts + Hydra configs for CMS public datasets (DVC-tracked)
  CLAUDE.md              # data-directory-specific Claude guidance
  PLAN.md                # WS-1 task tracker (C1–C10, per-commit status)
  SPEC.md                # data schema DDL and source catalog
eval/
  tasks/                 # Inspect AI eval tasks: agent_pipeline, card_ocr, coverage_qa, e2e_voice, hallucination, provider_lookup
  datasets/              # Golden datasets (hallucination_golden.json, etc.)
docs/
  PROJECT_SPEC.md        # full product/tech spec (model + provider choices, workstreams WS-1..)
  ARCHITECTURE.md / architecture.md  # mermaid system diagram + port table + production gaps
  adr/                   # architecture decision records (e.g. 0002-claude-over-gpt)
  components/            # Per-component RESEARCH / SPEC / PLAN / RESULTS docs
  runbook.md             # Operational runbook (stack startup, Twilio setup, demo flows)
infra/                   # per-service config (postgres/init.sql, redis/, prometheus/, grafana/, langfuse/, minio/, mlflow/)
scripts/                 # One-off utilities (NPPES sample download/generation, WS-1 setup)
```
Note: `docker-compose.yml` lives at the **repo root** (not under `infra/`); `infra/` holds the per-service config files those containers mount.

### Service Ports

| Service | Port | Stack | Service | Port | Stack |
| --- | --- | --- | --- | --- | --- |
| web | 3000 | Next.js 15 | api-gateway | 8080 | Fastify |
| document-ai | 8001 | FastAPI | eligibility | 8002 | FastAPI |
| providers | 8003 | FastAPI | voice-agent | 8004 | FastAPI + LangGraph |
| telephony | 8005 | Fastify | — | — | — |

Infra (docker compose): Postgres 5432 · Redis 6379 · MinIO 9000 / console 9001 · Langfuse 3001 · MLflow 5000 · Prometheus 9090 · Grafana 3002.

### Request Flow

```
Browser/Phone
    ↓
Next.js (3000)  ←→  Fastify API Gateway (8080)  [Clerk JWT + rate limit]
                            ↓
              ┌─────────────┼─────────────┐
         Document AI    Eligibility    Providers
         (card OCR,     (plan graph,   (NPI, geo,
          SBC parse)     SBC RAG,       MRF rates)
                         cost est.)
              └─────────────┼─────────────┘
                       Voice Agent
                    (LangGraph + Claude)
                            ↓ tools call ↑
                  Eligibility + Providers services
```

For voice calls: Twilio Media Streams → Telephony service (:8005, μ-law↔PCM16 transcoding) → Voice Agent WebSocket. The Telephony service also handles state-based consent announcements and AES-256-GCM encrypted recording storage.

### Voice Agent (LangGraph State Machine)

Streaming voice stack: **Deepgram Nova-2** (STT) → Claude (tool-use + response) → **Cartesia Sonic** (TTS), with barge-in via VAD.

States: `greet → identify → answer → confirm → close`

Tools available to Claude:
- `check_coverage(service, condition)` → Eligibility service
- `estimate_cost(service, in_network)` → Eligibility service
- `find_provider(specialty, geo)` → Providers service
- `check_formulary(drug)` → Eligibility service
- `verify_identity(dob, zip)` → internal
- `schedule_callback(reason)`, `escalate_to_human()`

**Hallucination guard** (`services/voice-agent/src/voice_agent/guards/hallucination.py`): before any claim is spoken, it's verified against the plan knowledge graph (Postgres), SBC RAG (pgvector), and the Eligibility service. Claude narrates only if grounded.

### Document AI Pipeline

Card upload → LayoutLMv3 (field extraction) + ResNet-50 (payor classification) + Claude via Instructor (structured output validation) → plan lookup in Eligibility service.

ML models are trained with Hydra configs (`services/document-ai/ml/configs/`), tracked in MLflow, artifacts stored in MinIO and versioned with DVC.

### Data Ingestion Pipeline (`data/ingest/`)

Scripts must run in dependency order (enforced by `dvc repro` and `just data.ingest`):

```
1. npi_ingest.py        → providers table          (PostGIS GEOGRAPHY point)
2. plan_puf_ingest.py   → plans + plan_benefits     (monetary values in integer cents)
3. formulary_ingest.py  → formulary_drug table      (needs plans)
4. mrf_parser.py        → in_network table          (stream-parse — files are 100+ GB)
5. care_compare_sync.py → updates providers.quality_rating
6. icd_hcpcs_ingest.py  → icd10_codes, hcpcs_codes
7. synthetic_cards.py   → data/processed/synthetic_cards/
```

Each script is idempotent (`ON CONFLICT DO NOTHING`), uses **Hydra** for config (`ingest/configs/<script>.yaml`), writes to `audit_log`, and reads `DATABASE_URL` from the environment. All monetary amounts are stored as **integer cents (BIGINT)** — never floats. The MRF parser must stream line-by-line due to file size. Schema migrations live in `services/eligibility/alembic/versions/` and must run before any ingestion.

Per-script Hydra overrides:
```bash
python data/ingest/npi_ingest.py npi.geo_filter.states=[NY,PA]
python data/ingest/plan_puf_ingest.py plan_puf.database.batch_size=1000
```

More detail in `data/CLAUDE.md`, task status in `data/PLAN.md`.

### Data Layer

- **PostgreSQL 16** (primary): plan knowledge graph, pgvector embeddings (SBC RAG, Voyage AI `voyage-3-large`), PostGIS provider geo-search, immutable audit logs
- **Redis 7**: session cache, rate limit counters, query result cache
- **MinIO**: card images, audio recordings, DVC ML artifacts

### Telephony — Consent Recording

`services/telephony/src/recording/` contains three modules that must stay in sync:
- `state_lookup.ts` — maps NANPA area codes → US states; identifies the 12 two-party-consent states (CA, CT, DE, FL, IL, MD, MA, MT, NH, OR, PA, WA)
- `consent.ts` — returns a TwiML `<Say>` snippet when the caller's state requires it; empty string otherwise
- `crypto.ts` — AES-256-GCM encryption with per-call random key wrapped under a per-tenant master key; plaintext is never persisted

The call flow is: inbound Twilio webhook → `voice.ts` → consent check → Media Streams WebSocket → Voice Agent.

For local testing, expose telephony (`:8005`) via ngrok and configure the Twilio Console Voice URL + Status Callback URL. See `docs/runbook.md` for step-by-step instructions.

### Hallucination Eval (`eval/tasks/hallucination_eval.py`)

Uses **Inspect AI** + `model_graded_qa`. Claude Opus acts as the judge and grades answers `C` (grounded) or `I` (hallucinated). Golden dataset is at `eval/datasets/hallucination_golden.json`. The system prompt instructs ClaimVoice to answer using **only** facts in the provided plan context — any coverage or cost claim not in the context is scored as a hallucination.

### Observability

All services emit to:
- **Langfuse** — LLM traces, token cost, latency (`:3001`)
- **Prometheus + Grafana** — OTel metrics/dashboards (`:3002`)

### LLM Usage

Claude Sonnet (the configured model id in code/tests is **`claude-sonnet-4-6`**, read from `anthropic_model` settings) handles all product-path generation:
1. Voice Agent (LangGraph orchestration, tool selection, response generation)
2. Document AI (Instructor-structured extraction after OCR)
3. Hallucination guard verification

Claude **Opus** is additionally used as the LLM judge in the eval suite (`model_graded_qa`), so Sonnet is not the only model in the repo. When changing the model, edit the settings/`anthropic_model` value — don't hardcode it. Prompts are versioned in `packages/shared-prompts/` (subdirs: `card_extraction/`, `coverage_qa/`, `tool_use/`, `voice/`).

## Key Conventions

### Python Services
- Python 3.12, FastAPI, Pydantic v2, `uv` for package management
- Each service: `src/<service_name>/` with `main.py`, `api/v1/`, `core/`, `services/`, `repositories/`, `schemas/`, `lib/`
- ruff is the configured linter/formatter (line-length 100, 4-space indent). No `[tool.mypy]` exists in any `pyproject.toml` yet — don't assume type-checking is wired into CI.
- Tests at `tests/{unit,integration,fixtures}/`

### TypeScript Services/Apps
- Node 20 (Fastify gateway + telephony), React 19 / Next.js 15 (web)
- `pnpm` workspaces; Turbo for build orchestration; 2-space indent
- Shared types auto-generated — edit OpenAPI specs, run `just gen.clients`, never hand-edit `packages/shared-types/`

### Branch / Commit Format
- Branch: `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/` prefix
- Commits: Conventional Commits — e.g. `feat(voice): add check_coverage tool`
- PRs: squash-merge to main; 1+ approval; all CI green

### Security / Privacy
- Pre-commit `detect-secrets` blocks credential commits
- PII is redacted before logging; audio recordings are encrypted
- Consent state is tracked per-call in the Telephony service


## Active development: WS-4/5/6 "grounded agent" (branch `feat/ws456-grounded-agent`)

**A new session continuing this work should read `Plan/HANDOFF.md` first** (full context,
run modes, test commands), plus `Plan/ROADMAP.md` and the per-feature component docs under
`docs/components/40-49/`.

Status: WS-4 Eligibility (`/coverage`, `/cost/estimate`, `/formulary/lookup`, `/fact_check`),
WS-5 Providers (`/providers/near`, `/providers/bulk` + enrichment), and WS-6 Voice Agent
(real tool clients → WS-4/5, `/fact_check` hallucination guard, key-gated Deepgram/Cartesia/VAD,
conversation memory + member threading) are **implemented and tested** (milestones M0–M14).

Critical, non-obvious dev facts:
- **Dev DB is reused from another app's Postgres** (`sentinel-postgres`, plain `postgres:16-alpine`
  on `localhost:5432`) — an isolated `claimvoice` db/role was added there. **No PostGIS, no pgvector**
  (geo is app-side Haversine; SBC RAG deferred). Do **not** run the project's own
  `docker compose up postgres` / `just up` (port 5432 collision).
- Seed (idempotent): `powershell -ExecutionPolicy Bypass -File scripts/seed_dev.ps1 -ExistingDb -SentinelContainer sentinel-postgres` (or `bash scripts/seed_dev.sh`). Demo member is `CVX-0042-MT`.
- **Run tests via per-service ephemeral uv envs + `PYTHONPATH`** (a full `uv sync` pulls heavy
  document-ai ML deps) — exact commands in `Plan/HANDOFF.md`.
- Everything defaults to deterministic **mock mode** (offline). Real paths are env-gated:
  `TOOL_MODE=http`, `VOICE_AGENT_ANSWER_MODE=claude`, `FACT_CHECK_MODE=claude`, `STT_MODE=deepgram`,
  `TTS_MODE=cartesia` (need the matching API keys).

### Startup Script (`scripts/start.py`)
# Done
Cross-platform (macOS, Linux, Windows) — requires only Python 3.12, which is already a project prerequisite.

```bash
python scripts/start.py           # full startup: checks prereqs, loads .env, installs deps, starts infra + all services
python scripts/start.py --check   # prerequisite check only (docker, pnpm, uv, just, dvc)
python scripts/start.py --stop    # gracefully stop all background services + docker infra
```

What it does in order:
1. Checks that `docker`, `pnpm`, `uv`, `just`, `dvc` are on `PATH` and Docker daemon is running
2. Copies `.env.example` → `.env` if `.env` is missing, then loads all vars into the environment
3. Runs `pnpm install` then `uv sync` (idempotent — safe to re-run)
4. `docker compose up -d` and waits for Postgres to be ready
5. Spawns each service as a background process; logs go to `.logs/<service>.log`

PIDs are saved to `.claimvoice.pids` so `--stop` can terminate them cleanly. Re-running start while services are already up: run `--stop` first, then start again. On Windows, `taskkill /F` is used instead of SIGTERM.


### WS-2 Enhancements: Done
1. `docs/components/17-ws2-dashboard-shell`

### Enhancements: To-Do
- `docs/components/20-ws2-browser-voice-ui`
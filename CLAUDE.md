# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaimVoice is a multi-modal AI agent for US health-insurance members. Members photograph their insurance card and have a voice conversation with an AI agent that answers coverage, cost, and provider questions — grounded entirely in structured data with a hallucination guard that fact-checks every claim before it's spoken.

## Commands

### Setup
```bash
just install        # pnpm install + uv sync + pre-commit hooks
just up             # docker-compose (Postgres, Redis, MinIO, MLflow, Langfuse, Prometheus, Grafana)
just data.ingest    # download + load all CMS public datasets
dvc pull            # fetch ML model checkpoints from MinIO remote
just dev            # start all services with hot reload
```

### Development
```bash
just dev            # all services (web :3000, api-gateway :8080, plus Python services)
pnpm dev            # frontend only
pnpm build          # production build (Turbo-orchestrated)
pnpm lint           # ESLint across all TS workspaces
pnpm typecheck      # tsc --noEmit across all TS workspaces
```

### Testing
```bash
just test                           # full suite: pnpm test + uv run pytest
uv run pytest -q                    # Python tests only
uv run pytest services/voice-agent  # single service tests
pnpm test --filter=web              # single JS workspace
just eval                           # Inspect AI evaluation suite (nightly tasks)
just eval.card_ocr                  # card OCR eval only
```

### Code Quality
```bash
uv run ruff check .                 # Python lint
uv run ruff format .                # Python format
uv run mypy .                       # strict type check (configured in pyproject.toml)
pnpm lint                           # ESLint
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
data/ingest              # 8 ETL scripts for CMS public datasets (DVC-tracked)
eval/tasks               # Inspect AI eval tasks (e2e, coverage QA, hallucination, OCR)
infra/                   # docker-compose.yml
```

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

For voice calls, Twilio Media Streams → Telephony service (μ-law transcoding) → Voice Agent WebSocket.

### Voice Agent (LangGraph State Machine)

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

### Data Layer

- **PostgreSQL 16** (primary): plan knowledge graph, pgvector embeddings (SBC RAG, Voyage AI `voyage-3-large`), PostGIS provider geo-search, immutable audit logs
- **Redis 7**: session cache, rate limit counters, query result cache
- **MinIO**: card images, audio recordings, DVC ML artifacts

### Observability

All services emit to:
- **Langfuse** — LLM traces, token cost, latency (`:3001`)
- **Prometheus + Grafana** — OTel metrics/dashboards (`:3002`)

### LLM Usage

Claude 3.5 Sonnet is the only LLM — used in:
1. Voice Agent (LangGraph orchestration, tool selection, response generation)
2. Document AI (Instructor-structured extraction after OCR)
3. Hallucination guard verification

Prompts are versioned in `packages/shared-prompts/` (subdirs: `card_extraction/`, `coverage_qa/`, `tool_use/`, `voice/`).

## Key Conventions

### Python Services
- Python 3.12, FastAPI, Pydantic v2, `uv` for package management
- Each service: `src/<service_name>/` with `main.py`, `api/v1/`, `core/`, `services/`, `repositories/`, `schemas/`, `lib/`
- Strict mypy; ruff line-length 100; 4-space indent
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

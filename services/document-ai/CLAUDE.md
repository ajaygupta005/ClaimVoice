# CLAUDE.md

This file is for Claude Code when contributing to the Document AI service in ClaimVoice.

## What this service owns

`services/document-ai/` is WS-3: Document AI.
It owns the pipeline that extracts structured insurance-card fields and SBC information from images and PDFs.

Primary responsibilities:
- Card OCR using LayoutLMv3
- Payor logo classification using ResNet-50
- SBC PDF parsing using a document-aware model and structured extraction
- Claude-assisted field disambiguation for low-confidence regions
- PaddleOCR fallback for noisy or hard-to-read fields
- Training and inference pipelines under `services/document-ai/ml/`
- DVC-tracked model artifacts in `services/document-ai/artifacts/`

## Key folders

- `src/document_ai/` — FastAPI service code and inference runner skeletons
- `ml/` — model training code, configs, and training scripts
- `artifacts/` — DVC-tracked checkpoints and model outputs
- `services/document-ai/pyproject.toml` — Python package config
- `services/document-ai/Dockerfile` — runtime container
- `services/document-ai/Dockerfile.train` — GPU training container

## Why this matters for WS-3

WS-3 is the standalone Document AI workstream. The goal in the first 3 days is to build a complete WS-3 component that can:
1. be installed and run independently
2. train on synthetic insurance-card data
3. expose inference behavior for card OCR and payor classification
4. document the component clearly for future WS-4/WS-8 integration

## Local development commands

From repo root:

```bash
cp .env.example .env
pnpm install
uv sync
pre-commit install
just up
```

Then run the Document AI service locally:

```bash
cd services/document-ai
uv run uvicorn document_ai.main:app --reload --host 0.0.0.0 --port 8001
```

If `uv` is not available in the shell, use the root `uv` workspace from the repo root:

```bash
cd ClaimVoice
uv run python -m document_ai.main
```

## What to change with Claude Code

When using Claude Code, focus on:
- adding or improving `services/document-ai/src/document_ai` routes and inference logic
- creating training scripts and data loaders in `services/document-ai/ml/`
- writing docs in this folder: `CLAUDE.md`, `SPEC.md`, `RESEARCH.md`, `README.md`
- leaving unrelated workstreams untouched unless explicitly required for WS-3 handoff

## How to Contribute Safely

**File scope rule: only modify files under `services/document-ai/`.** The one permitted exception is `data/processed/synthetic_cards/` and `data/raw/sbcs/` when synthetic training data or SBC PDFs need to be added. Every other path in the repo is off-limits unless a WS-3 handoff task explicitly calls for a cross-service change — and that must be noted in the commit message.

### What We Own

Files and directories that are safe to create, edit, or delete freely:

- `services/document-ai/src/document_ai/` — FastAPI routes, inference runners, schemas
- `services/document-ai/ml/` — training scripts, configs, data loaders, evaluation scripts
- `services/document-ai/artifacts/` — DVC-tracked model checkpoints and outputs
- `services/document-ai/Dockerfile` and `Dockerfile.train`
- `services/document-ai/pyproject.toml` — Python dependencies for this service only
- `services/document-ai/*.md` — this file, SPEC.md, RESEARCH.md, README.md
- `data/processed/synthetic_cards/` — generated labeled card images
- `data/raw/sbcs/` — raw SBC PDF inputs

**Safe change example:** modifying `src/document_ai/inference/card_ocr_runner.py` to update the LayoutLMv3 post-processing logic or adding a new field extractor under `src/document_ai/inference/`.

### What We Don’t Touch

These paths are owned by other workstreams. Do not edit them during WS-3 development:

- `services/eligibility/` — plan graph and eligibility checks (WS-2)
- `services/voice-agent/` — voice conversation orchestration (WS-5)
- `services/providers/` — provider network lookups (WS-6)
- `apps/web/` — frontend UI (WS-8)
- `docker-compose.yml` — shared infrastructure; changes here affect all services
- `package.json` and `pnpm-lock.yaml` at the repo root — JS workspace config
- `Justfile` — shared task runner; add WS-3 targets only if needed and document them
- Any `pyproject.toml` outside `services/document-ai/`

**Unsafe change example:** editing `services/eligibility/src/eligibility/plan_graph.py` or adding a dependency to the root `package.json` while working on a card OCR feature. Both changes would silently affect other workstreams and make the PR scope ambiguous.

### Testing Before Commit

Before committing any change:

1. **Type-check:** `uv run mypy src/document_ai/` — fix all errors, do not ignore them with `# type: ignore` without a comment explaining why.
2. **Lint:** `uv run ruff check src/document_ai/ ml/` and `uv run ruff format --check src/document_ai/ ml/`.
3. **Unit tests:** `uv run pytest tests/` from `services/document-ai/`. If no test exists for a new function, add one.
4. **Service smoke-test:** start the service with `uv run uvicorn document_ai.main:app --reload --port 8001` and confirm `/health` returns `200`.
5. **Scope check:** run `git diff --name-only` and verify every changed file is under an owned path listed in "What We Own" above. If any file outside that list appears, either revert it or justify it in the commit message with a `WS-3/WS-X:` prefix.

## Notes for reviewers

If a change touches integration boundaries, explain it in the commit message and link it to WS-4 or WS-8.
For example:
- `WS-3: implement card OCR inference endpoint` — internal service work
- `WS-3/WS-4: add JSON output for plan extraction` — integration boundary
- `WS-3/WS-8: add service README and local dev docs`

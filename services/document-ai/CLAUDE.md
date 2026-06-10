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

## How to contribute safely

- Keep changes isolated to `services/document-ai/` and `data/processed/synthetic_cards/` or `data/raw/sbcs/` where necessary.
- Do not modify frontend code in `apps/web/` or voice orchestration in `services/voice-agent/` during initial WS-3 development.
- When adding a new dependency, prefer Python-first packages already compatible with `pyproject.toml`.
- Use the root `Justfile` and `README.md` as the project’s canonical commands.

## Notes for reviewers

If a change touches integration boundaries, explain it in the commit message and link it to WS-4 or WS-8.
For example:
- `WS-3: implement card OCR inference endpoint` — internal service work
- `WS-3/WS-4: add JSON output for plan extraction` — integration boundary
- `WS-3/WS-8: add service README and local dev docs`

# Document AI — WS-3

ClaimVoice WS-3 is the Document AI service.
It provides card OCR, payor classification, and SBC parsing for the health insurance agent.

## What is included

- `src/document_ai/` — FastAPI service and inference runners
- `ml/` — model training, configs, and evaluation
- `artifacts/` — DVC-tracked model checkpoints
- `Dockerfile` — runtime container
- `Dockerfile.train` — GPU training container

## Important docs

- `CLAUDE.md` — contribution guidance for Claude Code
- `SPEC.md` — WS-3 service specification
- `RESEARCH.md` — research notes and design decisions

## Local development

From the repo root:

```bash
cp .env.example .env
pnpm install
uv sync
pre-commit install
just up
```

Then run the service locally:

```bash
cd services/document-ai
uv run uvicorn document_ai.main:app --reload --host 0.0.0.0 --port 8001
```

## Training

Use the root `Justfile` training commands:

```bash
just train.card_ocr
just train.payor
just train.sbc
```

## Evaluation

Run model evaluation from the root:

```bash
just eval.card_ocr
```

## Service goals

WS-3 is intended to be a separate component with a clean handoff to:
- `services/eligibility` for plan/member data
- `services/voice-agent` for conversational playback
- `data/` for synthetic card images and SBC PDFs

## Notes

The service is currently a scaffold. The first deliverable is a runnable prototype with 
end-to-end card OCR and payor classification on synthetic data.

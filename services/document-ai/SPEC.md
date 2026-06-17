# WS-3 · Document AI Specification

## Purpose

WS-3 is the Document AI workstream for ClaimVoice.
It transforms member insurance cards and SBC documents into structured fields that can be consumed by Eligibility, Providers, and the Voice Agent.

## Scope

### In scope for the first 3-day WS-3 build
- Card OCR pipeline for synthetic insurance cards
- Payor logo classification for 8 payor classes
- SBC PDF parser prototype
- Local service startup and verification
- Documentation and research notes for the service
- DVC-compatible training and artifact storage

### Out of scope for the first 3-day WS-3 build
- Full UI integration with `apps/web`
- End-to-end voice conversation orchestration
- Final production-grade RAG embedding pipeline
- Complete HIPAA/compliance certification

## Deliverables

### D1: Service scaffolding and docs
- `services/document-ai/README.md`
- `services/document-ai/CLAUDE.md`
- `services/document-ai/SPEC.md`
- `services/document-ai/RESEARCH.md`
- Local startup story in `Justfile` / root docs if needed

#### Data paths and config locations

All paths are relative to `services/document-ai/` unless otherwise noted.

**Training configs** (Hydra YAML, consumed by `uv run python -m ml/models/*/train.py`):

| Config file | Model |
|---|---|
| `ml/configs/train_card_ocr.yaml` | LayoutLMv3 card OCR |
| `ml/configs/train_payor_classifier.yaml` | ResNet-50 payor classifier |
| `ml/configs/train_sbc.yaml` | LayoutLMv3 SBC parser |

**Model artifact directories** (DVC-tracked; each `latest/` symlink points to the most recently promoted checkpoint):

| Artifact path | Runner that reads it |
|---|---|
| `artifacts/card_ocr/latest/` | `src/document_ai/inference/card_ocr_runner.py` |
| `artifacts/payor_classifier/latest/` | `src/document_ai/inference/payor_classifier_runner.py` |
| `artifacts/sbc_parser/latest/` | `src/document_ai/inference/sbc_parser_runner.py` |

Each `latest/` directory must contain at minimum:
- `model.safetensors` — model weights
- `config.json` — Hugging Face model config (for LayoutLMv3 runners)
- tokenizer files (`tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`) for LayoutLMv3 runners

The payor classifier `latest/` directory needs only `model.safetensors` (weights are loaded into a torchvision `resnet50` head via the `safetensors` library).

### D2: Card OCR
- Training script stub for LayoutLMv3 (`ml/models/card_ocr_layoutlm/train.py`)
- Config `ml/configs/train_card_ocr.yaml`
- Inference runner skeleton `src/document_ai/inference/card_ocr_runner.py`
- Evaluation command `just eval.card_ocr`
- Field schema defined for: `member_id`, `name`, `dob`, `group_number`, `plan_name`, `effective_date`, `rx_bin`, `rx_pcn`, `rx_group`, `phone`, `carrier`, `plan_type`

#### D2 JSON output contract

`card_ocr_runner` returns a list of field objects. Each object has exactly four keys:

| Key | Type | Description |
|---|---|---|
| `field_name` | `string` | Canonical field name from the schema (e.g. `"member_id"`) |
| `value` | `string` | Extracted text value; empty string `""` if field not found |
| `confidence` | `float` | Model confidence score in range `[0.0, 1.0]` |
| `bbox` | `[x0, y0, x1, y1]` | Bounding box in absolute pixels on the source image; `null` if unavailable |

**Response envelope:**

```json
{
  "card_id": "abc123",
  "fields": [
    {
      "field_name": "member_id",
      "value": "XYZ987654321",
      "confidence": 0.97,
      "bbox": [124, 310, 420, 340]
    },
    {
      "field_name": "name",
      "value": "Jane Doe",
      "confidence": 0.93,
      "bbox": [124, 260, 390, 290]
    },
    {
      "field_name": "dob",
      "value": "1985-04-12",
      "confidence": 0.88,
      "bbox": [124, 350, 310, 378]
    },
    {
      "field_name": "group_number",
      "value": "GRP00123",
      "confidence": 0.91,
      "bbox": [124, 390, 330, 418]
    },
    {
      "field_name": "plan_name",
      "value": "BlueShield PPO Gold",
      "confidence": 0.85,
      "bbox": [124, 200, 500, 230]
    },
    {
      "field_name": "effective_date",
      "value": "2025-01-01",
      "confidence": 0.79,
      "bbox": [124, 430, 320, 458]
    },
    {
      "field_name": "rx_bin",
      "value": "610011",
      "confidence": 0.96,
      "bbox": [450, 310, 620, 340]
    },
    {
      "field_name": "rx_pcn",
      "value": "MEDDPPO",
      "confidence": 0.94,
      "bbox": [450, 350, 640, 378]
    },
    {
      "field_name": "rx_group",
      "value": "RX001",
      "confidence": 0.90,
      "bbox": [450, 390, 600, 418]
    },
    {
      "field_name": "phone",
      "value": "1-800-555-0100",
      "confidence": 0.82,
      "bbox": [124, 470, 390, 498]
    },
    {
      "field_name": "carrier",
      "value": "BlueCross BlueShield",
      "confidence": 0.99,
      "bbox": [124, 50, 560, 100]
    },
    {
      "field_name": "plan_type",
      "value": "PPO",
      "confidence": 0.87,
      "bbox": [124, 160, 240, 190]
    }
  ],
  "low_confidence_fields": ["effective_date", "phone"],
  "model_version": "card_ocr_layoutlm_v0.1"
}
```

Fields with `confidence < 0.80` are also listed in `low_confidence_fields` for downstream Claude-assisted disambiguation. The `bbox` coordinates follow the `[x0, y0, x1, y1]` convention (top-left to bottom-right) in the pixel space of the image passed to the runner.

### D3: Payor classification
- Training script stub for ResNet-50 payor classifier (`ml/models/payor_classifier_resnet/train.py`)
- Inference runner skeleton `src/document_ai/inference/payor_classifier_runner.py`
- `ml/configs/train_payor_classifier.yaml`
- Model card stub `ml/models/payor_classifier_resnet/MODEL_CARD.md`

### D4: SBC parser baseline
- Training script stub for SBC parser (`ml/models/sbc_parser_layoutlm/train.py`)
- Config placeholder or note if missing
- Inference runner stub `src/document_ai/inference/sbc_parser_runner.py`
- Model card stub `ml/models/sbc_parser_layoutlm/MODEL_CARD.md`

### D5: Data and integration points
- Synthetic card data path: `data/processed/synthetic_cards/`
- SBC PDF input path: `data/raw/sbcs/`
- JSONL labels for card fields
- Output payload contract for downstream services:
  - `card_ocr` -> `{field_name: value, confidence, bbox}`
  - `payor_classifier` -> `{payor_label, confidence}`
  - `sbc_parser` -> `{plan_name, section_name, benefit_rows, raw_text}`
- Downstream integration targets:
  - `services/eligibility` consumes card-extracted plan/member details
  - `services/voice-agent` consumes payor and OCR output for member verification
  - `services/providers` uses payor classification to choose provider networks

## Success criteria

- Document AI service starts locally and exposes `/health`
- Basic inference runners exist for card OCR, payor classifier, and SBC parser
- Training config files are present and usable with `uv run`
- Synthetic card data is referenced clearly and available for prototype training
- Service has docs for contributors and reviewers

## Metrics

- WS-3 deliverables: 5 docs + 3 model workflows + 3 inference runners
- Commit target for first 3 days: 10–12 commits
- Minimal prototype deliverable: one end-to-end card OCR pass on synthetic data

## Integration notes

- WS-3 is a separate service in `services/document-ai/`.
- After the 3-day prototyping phase, the next integration phase is:
  1. expose inference outputs as JSON API
  2. connect to `services/eligibility` plan graph
  3. wire `services/voice-agent` to call Document AI for card upload results
  4. support `data/raw/sbcs/` ingestion by `services/eligibility` for SBC RAG

## Risks and assumptions

- Assumes the root repo already has Docker / `uv` installed and `just up` works.
- Assumes synthetic card generation in `data/ingest/synthetic_cards.py` produces usable labeled images.
- Assumes payor logo classes are distinct enough for ResNet-50 on synthetic data.
- Assumes SBC parsing can be prototyped with a small number of PDFs.

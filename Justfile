# ── Setup ──────────────────────────────────────────
install:
    pnpm install
    uv sync
    pre-commit install

# ── Docker ─────────────────────────────────────────
up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

# ── Data ───────────────────────────────────────────
data.ingest:
    python data/ingest/npi_ingest.py
    python data/ingest/plan_puf_ingest.py
    python data/ingest/sbc_download.py
    python data/ingest/mrf_parser.py
    python data/ingest/formulary_ingest.py
    python data/ingest/care_compare_sync.py
    python data/ingest/icd_hcpcs_ingest.py
    python data/ingest/synthetic_cards.py
    dvc add data/processed && dvc push

data.synthetic:
    python data/ingest/synthetic_cards.py --count 100

# ── Training ───────────────────────────────────────
train.card_ocr:
    cd services/document-ai/ml && bash scripts/train_card_ocr.sh

train.payor:
    cd services/document-ai/ml && bash scripts/train_payor_classifier.sh

train.sbc:
    cd services/document-ai/ml && bash scripts/train_sbc_parser.sh

train.all:
    just train.payor
    just train.card_ocr
    just train.sbc

# ── Evaluation ─────────────────────────────────────
eval:
    inspect eval eval/tasks/

eval.card_ocr:
    cd services/document-ai/ml && python -m models.card_ocr_layoutlm.evaluate

# ── Dev ────────────────────────────────────────────
dev:
    turbo dev

# ── Tests ──────────────────────────────────────────
test:
    pnpm test
    uv run pytest

# ── API client gen ─────────────────────────────────
gen.clients:
    bash scripts/generate_api_clients.sh

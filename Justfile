install:
    pnpm install
    uv sync

up:
    docker compose up -d

down:
    docker compose down

dev:
    turbo dev

test:
    pnpm test
    uv run pytest -q

lint:
    pnpm lint
    uv run ruff check .

eval:
    inspect eval eval/tasks/

# ── Data / WS-1 ──────────────────────────────────────────────────────────────

data.ingest:
    dvc repro ingest_npi ingest_plan_puf ingest_icd_hcpcs download_sbcs \
        ingest_formulary parse_mrf sync_care_compare seed_members

data.synthetic:
    python data/ingest/synthetic_cards.py

data.quality:
    uv run pytest data/tests/test_ingest_counts.py -v

train.card_ocr:
    dvc repro train_card_ocr

train.payor:
    cd services/document-ai/ml && uv run python -m models.payor_classifier.train

train.sbc:
    cd services/document-ai/ml && uv run python -m models.sbc_layoutlm.train

train.all:
    just train.card_ocr
    just train.payor
    just train.sbc

gen.clients:
    cd packages/shared-types && pnpm run generate

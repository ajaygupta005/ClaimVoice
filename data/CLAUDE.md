# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

`data/` is the ETL backbone of ClaimVoice. It owns all ingestion scripts that pull US public CMS datasets into PostgreSQL, plus synthetic training data generation. It is **not** a standalone service — it feeds the microservices that live under `services/`.

## Development commands

All commands are defined in the root `Justfile` and aliased in `Makefile`. Run from the repo root:

```bash
just install          # pnpm install + uv sync + pre-commit install
just up               # Start postgres, redis, minio, mlflow, langfuse, grafana (docker-compose)
just down             # Stop all containers

just data.ingest      # Run full ingestion pipeline in dependency order
just data.synthetic   # Generate 100 synthetic insurance card images only

just test             # pnpm test + uv run pytest
```

Run a single ingestion script:
```bash
# From the repo root — scripts use relative paths (data/raw/...)
python data/ingest/npi_ingest.py                       # default config
python data/ingest/npi_ingest.py npi.geo_filter.states=[NY,PA]  # Hydra override
```

Reproduce the full pipeline deterministically:
```bash
dvc repro             # Re-runs all stages in dvc.yaml order
dvc pull              # Fetch cached processed outputs + model checkpoints
```

## Architecture & data flow

### Ingestion dependency order

Scripts **must** run in this order (plans must exist before benefits/formulary/rates):

```
1. npi_ingest.py        → providers table
2. plan_puf_ingest.py   → plans + plan_benefits tables
3. formulary_ingest.py  → formulary_drug table  (needs plans)
4. mrf_parser.py        → in_network table       (needs plans)
5. care_compare_sync.py → updates providers.quality_rating
6. icd_hcpcs_ingest.py  → icd10_codes, hcpcs_codes
7. synthetic_cards.py   → data/processed/synthetic_cards/ (training images)
```

`dvc repro` and `just data.ingest` enforce this order automatically.

### Script pattern (all scripts follow this)

Every ingestion script is idempotent and uses:
- **Hydra** for config (`ingest/configs/<script>.yaml`); CLI overrides via `key=value`
- **psycopg** (v3) for PostgreSQL; bulk batch inserts (`ON CONFLICT DO NOTHING`)
- **audit_log** table: every inserted row gets a SHA256 hash + source URL entry
- **Structured logging** to `data/ingest.log` via `logging`
- `DATABASE_URL` env var (falls back to `postgresql://localhost/claimvoice`)

### Database (PostgreSQL 16 + PostGIS + pgvector)

Key tables and their ownership:
| Table | Populated by | Notes |
|---|---|---|
| `providers` | `npi_ingest.py` + `care_compare_sync.py` | PostGIS `GEOGRAPHY(POINT)` column; spatial index on `location` |
| `plans` | `plan_puf_ingest.py` | Keyed by `plan_marketing_name` |
| `plan_benefits` | `plan_puf_ingest.py` / SBC parsing | Amounts stored in **cents** (BIGINT) |
| `in_network` | `mrf_parser.py` | BIGSERIAL PK; 100+ GB source files — stream-parse |
| `formulary_drug` | `formulary_ingest.py` | Tier 1–4; Part D CY2026 |
| `icd10_codes` / `hcpcs_codes` | `icd_hcpcs_ingest.py` | Static lookup tables |
| `audit_log` | All scripts | Append-only; never update |
| `members` | `seed_test_members.py` | Test data; production = X12 270/271 |

Schema migrations live in `services/eligibility/alembic/versions/` — run Alembic before any ingestion.

### MRF parser specifics

MRF files (Transparency-in-Coverage) can be **100+ GB compressed**. `mrf_parser.py` must stream-parse line-by-line. CMS Schema 2.0 — monitor for quarterly drift. Cache results with 15-min TTL.

### Synthetic data

`synthetic_cards.py` generates PNG insurance card images using Flux + Faker. Output goes to `data/processed/synthetic_cards/` and is tracked by DVC. These images train the LayoutLMv3 OCR model in `services/document-ai/ml/`.

## Configuration

Each script reads from `ingest/configs/<script>.yaml`. The `npi_ingest.yaml` is the reference implementation. Config values can be overridden on the CLI via Hydra syntax:

```bash
python data/ingest/npi_ingest.py npi.database.batch_size=1000
```

`DATABASE_URL` is resolved via `${oc.env:DATABASE_URL,<default>}` — set it in the environment before running.

## Known constraints

- **NPI data**: Takes first practice location when multiple exist; deactivated NPIs filtered unless `include_deactivated: true`
- **MRF data**: Schema drift risk; stale after 30 days; heavily sparse — only index `(plan_id, provider_npi, procedure_code)`
- **Plan PUF**: Employer plan customizations not captured — SBC parsing required for benefit detail
- **Part D formulary**: Changes quarterly; always use the latest CY year config
- **All monetary amounts**: Stored as cents (BIGINT), never floats

#!/usr/bin/env bash
# Tier-1+ DEV seed: schema + synthetic data, NO external downloads.
# Populates every structured table well enough to develop WS-4 / WS-5 / WS-6.
# For full public-data volume (the demo / acceptance bar) use `just data.ingest`.
set -euo pipefail

: "${DATABASE_URL:=postgresql://claimvoice:changeme@localhost:5433/claimvoice}"
export DATABASE_URL
echo "→ DATABASE_URL=$DATABASE_URL"

echo "→ [1/7] applying schema (alembic upgrade head)"
( cd services/eligibility && uv run alembic upgrade head )

echo "→ [2/7] generating synthetic NPPES sample (data/raw/nppes_sample.csv)"
uv run python scripts/generate_nppes_sample.py

echo "→ [3/7] loading providers from the sample (download bypassed)"
uv run python data/ingest/npi_ingest.py npi.source_csv=data/raw/nppes_sample.csv

echo "→ [4/7] enriching providers (specialty + quality + accepting-new from taxonomy)"
uv run python data/ingest/enrich_providers.py

echo "→ [5/7] seeding plans, benefits, formulary, in-network, ICD-10/HCPCS codes"
uv run python data/ingest/seed_dev.py

echo "→ [6/7] seeding 30 test members + X12 271 stubs"
uv run python data/ingest/seed_test_members.py

echo "→ [7/7] seeding canonical demo member + plan (golden values for agent eval)"
uv run python data/ingest/seed_demo_member.py

echo "✅ dev seed complete — WS-4/WS-5/WS-6 now have data to develop against."

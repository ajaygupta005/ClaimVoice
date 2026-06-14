# WS-1 · Data Engineering & Acquisition — Execution Plan

**Branch convention**: `feat/ws1-<short-name>` (e.g. `feat/ws1-plan-puf-ingest`)
**10 commit budget** across Phases 1 and 2 (Days 1–14)
**Depends on**: Alembic migrations in `services/eligibility/alembic/` must run before any ingestion

---

## Status Legend

| Symbol | Meaning |
|---|---|
| ✅ | Done / merged |
| 🔄 | In progress |
| ⬜ | Not started |
| 🔴 | Blocked |

---

## Task Breakdown

### C1 · Monorepo scaffold + data directory skeleton
**Phase 1 · Day 1 · `chore`**
**Status**: ✅ Done
**What was built**:
- `data/` directory tree: `ingest/`, `ingest/configs/`, `raw/`, `processed/`, `stubs/eligibility_271/`, `samples/cards/`, `samples/sbcs/`, `schemas/`, `seeds/`
- `.gitkeep` in empty directories
- `data/README.md` — data source catalog with schema DDL

---

### C2 · NPI ingestion (NPPES V2 → PostGIS)
**Phase 1 · Day 2 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-npi-ingest`
**What was built**:
- `ingest/npi_ingest.py` — full implementation: download, stream-parse, geo-filter, batch insert
- `ingest/configs/npi_ingest.yaml` — Hydra config with NY metro bounds
- `data/raw/nppes_sample.csv` — 100-row sample for unit testing

**Acceptance check**:
```bash
python data/ingest/npi_ingest.py  # requires live DB + downloaded ZIP
python data/ingest/npi_ingest.py npi.geo_filter.states=[NY]  # NY only override
```

**Known gap**: `taxonomy_code` vs `taxonomy_description` column mapping should be verified against the live NPPES CSV header before the first full run.

---

### C3 · Exchange Plan PUFs ingest (plans + benefits)
**Phase 1 · Day 3–4 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-plan-puf-ingest`

**Files created**:
- `ingest/plan_puf_ingest.py`
- `ingest/configs/plan_puf_ingest.yaml`

**Implementation notes**:
1. Download `56.4 MB ZIP` from CMS Marketplace PUFs 2026 page
2. Unzip; parse `Plan_Attributes_PUF_2026.csv` → `plans` table
3. Parse `Benefits_Cost_Sharing_PUF_2026.csv` → `plan_benefits` table
4. Key column mappings from PUF to schema:
   - `PlanId` → used for dedup key; `PlanMarketingName` → `plan_marketing_name`
   - `IssuerId`, `IssuerMarketCoverage` → `issuer_name`
   - `NetworkId` → `plan_type`; `MetalLevel` → `metal_level`
   - `BenefitName` → `benefit_name`; `CopayInnTier1` → `copay_amount_cents` (× 100)
   - `CoinsInnTier1` → `coinsurance_percentage`; `IndvDeduct` → `individual_deductible_cents`
5. All dollar amounts: strip `$` and commas, multiply by 100, cast to BIGINT
6. `ON CONFLICT (plan_marketing_name) DO NOTHING` for plans
7. Audit log every inserted plan + benefit row

**Acceptance**:
- `SELECT COUNT(*) FROM plans` ≥ 500
- `SELECT COUNT(*) FROM plan_benefits` ≥ 5,000
- No float columns in `plan_benefits` for money

---

### C4 · Part D Formulary ingest (CY2026)
**Phase 2 · Day 6 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-formulary-ingest`

**Files to create**:
- `ingest/formulary_ingest.py`
- `ingest/configs/formulary_ingest.yaml`

**Implementation notes**:
1. Download CMS Part D Formulary Reference File CY2026 ZIP
2. Parse pipe-delimited `formulary_file.txt` inside the archive
3. Fields: `CONTRACT_ID`, `FORMULARY_ID`, `NDC`, `TIER_LEVEL_VALUE`, `QUANTITY_LIMIT_APPLY_IND`, `PRIOR_AUTHORIZATION_YN`, `STEP_THERAPY_YN`
4. Resolve `FORMULARY_ID` → `plan_id` via `SELECT id FROM plans WHERE formulary_id = %s`
5. Unresolved formulary IDs: log at WARNING, insert with `plan_id = NULL` for reference
6. Normalize NDC to 11-digit format before insert
7. Batch size 5,000; `ON CONFLICT (plan_id, ndc_code) DO NOTHING`

**Acceptance**:
- `SELECT COUNT(*) FROM formulary_drug` ≥ 10,000
- Tier distribution: 4 distinct values (1–4)

---

### C5 · MRF stream-parser (Transparency-in-Coverage Schema 2.0)
**Phase 2 · Day 7–8 · `feat`**
**Status**: ⬜ Not started
**Branch**: `feat/ws1-mrf-parser`
**Blocked by**: C3 (needs `plans` populated for `plan_id` resolution)

**Files to create**:
- `ingest/mrf_parser.py`
- `ingest/configs/mrf_ingest.yaml`

**Implementation notes**:
1. Use `ijson` for streaming JSON parse — never buffer the full file
2. CMS Schema 2.0 top-level structure:
   ```json
   { "reporting_entity_name": "...", "in_network": [ { "billing_code": "...", "negotiated_rates": [...] } ] }
   ```
3. Filter: HCPCS codes only (skip CPT)
4. For each negotiated rate: cross-reference `provider_references` or `provider_groups` against `providers.npi`; skip if NPI not in NY metro `providers` table
5. Insert: `(plan_id, provider_npi, procedure_code, negotiated_rate_cents, effective_date)`
6. Batch 10,000 rows; `ON CONFLICT DO NOTHING`
7. `mrf_ingest.yaml` must accept `source_url` at CLI: `python mrf_parser.py mrf.source_url=<url>`

**Acceptance**:
- `SELECT COUNT(*) FROM in_network` ≥ 50,000 for the demo payor subset
- Zero rows with NULL `provider_npi` or NULL `procedure_code`

---

### C6 · Care Compare sync (provider quality ratings)
**Phase 2 · Day 9 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-care-compare-sync`

**Files to create**:
- `ingest/care_compare_sync.py`
- `ingest/configs/care_compare_sync.yaml`

**Implementation notes**:
1. Paginated GET to CMS Care Compare datastore API (dataset `xubh-q36u`)
2. Cache each page in Redis with 24-hour TTL (`care_compare:<page>`)
3. Match response rows to `providers` by NPI first; fallback: organization name + ZIP
4. `UPDATE providers SET quality_rating = %s, accepting_new_patients = %s, hospital_name = %s WHERE npi = %s`
5. Log match rate at INFO level; log unmatched providers at DEBUG

**Acceptance**:
- `SELECT COUNT(*) FROM providers WHERE quality_rating IS NOT NULL` ≥ 1,000

---

### C7 · ICD-10 / HCPCS code tables
**Phase 2 · Day 10 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-icd-hcpcs-ingest`

**Files created**:
- `ingest/icd_hcpcs_ingest.py`
- `ingest/configs/icd_hcpcs_ingest.yaml`

**Implementation notes**:
1. ICD-10-CM FY2026: parse `icd10cm_codes_2026.txt` (fixed-width 7 + description)
2. HCPCS Level II: parse annual update CSV/Excel; columns vary by year — inspect headers
3. `ON CONFLICT (code) DO NOTHING` — static tables, load once
4. No Hydra config needed (no tunable parameters); hardcode URLs as module-level constants

**Acceptance**:
- `SELECT COUNT(*) FROM icd10_codes` ≥ 70,000
- `SELECT COUNT(*) FROM hcpcs_codes` ≥ 5,000

---

### C8 · SBC PDF download + synthetic card generation
**Phase 1 · Day 4 · `feat`**
**Status**: ✅ Done
**Branch**: `feat/ws1-synthetic-data`

**Files to create**:
- `ingest/sbc_download.py`
- `ingest/configs/sbc_manifest.yaml`
- `ingest/synthetic_cards.py`

**sbc_download.py notes**:
1. Read PDF URLs from `sbc_manifest.yaml`
2. HTTP GET with 3× exponential backoff
3. Write to `data/raw/sbcs/<payor>_<plan_name_slug>.pdf`
4. Write sidecar JSON next to each PDF
5. Skip if file already exists

**synthetic_cards.py notes**:
1. 4 payor templates × 25 cards = 100 total
2. Render with Pillow on a fixed canvas (1012×638 px, CR80 card ratio)
3. Template fields: logo placement, font, field positions vary per payor
4. All member data via `Faker(locale='en_US')` with fixed seed per payor for reproducibility
5. Output: `data/processed/synthetic_cards/card_NNNN.png` + `labels.jsonl`
6. `labels.jsonl` format: `{"file": "card_0001.png", "payor": "aetna", "fields": {"member_id": {"text": "...", "bbox": [x1,y1,x2,y2]}, ...}}`
7. DVC-track the `data/processed/synthetic_cards/` directory

**Acceptance**:
- `ls data/raw/sbcs/*.pdf | wc -l` ≥ 5
- `ls data/processed/synthetic_cards/*.png | wc -l` = 100
- `wc -l data/processed/synthetic_cards/labels.jsonl` = 100
- Each `labels.jsonl` entry has all 10 required field keys

---

### C9 · X12 271 stubs + seed test members
**Phase 1 · Day 5 · `chore`**
**Status**: ⬜ Not started
**Branch**: `feat/ws1-stubs-and-seeds`
**Blocked by**: C3 (needs plan IDs to exist)

**Files to create**:
- `stubs/eligibility_271/M<id>.json` × 30 files
- `ingest/seed_test_members.py`

**stub JSON structure**: see `SPEC.md §4.10`

**seed_test_members.py notes**:
1. Fixed seed (`random.seed(42)`)
2. Load 30 plan IDs from `SELECT id, plan_marketing_name FROM plans LIMIT 30`
3. Generate 30 Faker members; assign eligibility states: 24 active / 4 inactive / 2 suspended
4. Write matching stub JSON to `stubs/eligibility_271/<member_id>.json`
5. Insert into `members` table

**Acceptance**:
- `SELECT COUNT(*) FROM members` = 30
- `ls stubs/eligibility_271/*.json | wc -l` = 30
- Eligibility state distribution matches 24/4/2

---

### C10 · DVC pipeline + CI data-quality gate
**Phase 2 · Day 11 · `chore`**
**Status**: ⬜ Not started
**Branch**: `feat/ws1-dvc-pipeline`

**Files to create**:
- `dvc.yaml` — all 9 ingestion stages wired in dependency order
- `tests/test_ingest_counts.py` — row-count assertions for CI

**dvc.yaml stage template**:
```yaml
stages:
  ingest_npi:
    cmd: python data/ingest/npi_ingest.py
    deps:
      - data/ingest/npi_ingest.py
      - data/ingest/configs/npi_ingest.yaml
    outs:
      - data/raw/nppes_v2_may2026/:
          cache: false
      - data/ingest.log:
          cache: false
  # ... other stages with correct `deps` order
```

**test_ingest_counts.py**: pytest fixtures that connect to the test DB and assert row count thresholds from `SPEC.md §6`.

**Acceptance**:
- `dvc repro` completes from a clean DB without error
- `pytest tests/test_ingest_counts.py` passes all assertions

---

## Dependency Graph

```
C2 (npi_ingest)  ──────────────────────────────→ C6 (care_compare)
                                                        │
C3 (plan_puf)  ─→ C4 (formulary) ─────────────→ C9 (stubs + seeds)
              └──→ C5 (mrf_parser)──────────────→ C9
C1 (scaffold)
C7 (icd_hcpcs)  (independent)
C8 (sbc + cards)  (independent)
C10 (dvc pipeline)  ──── depends on all above
```

---

## Phase Mapping

| Commit | Phase | Day | Status |
|---|---|---|---|
| C1 — scaffold | Phase 1 | Day 1 | ✅ |
| C2 — NPI ingest | Phase 1 | Day 2 | ✅ |
| C3 — Plan PUF | Phase 1 | Day 3–4 | ✅ |
| C8 — SBC + cards | Phase 1 | Day 4 | ✅ |
| C9 — stubs + seeds | Phase 1 | Day 5 | ⬜ |
| C4 — formulary | Phase 2 | Day 6 | ✅ |
| C5 — MRF parser | Phase 2 | Day 7–8 | ⬜ |
| C6 — Care Compare | Phase 2 | Day 9 | ✅ |
| C7 — ICD/HCPCS | Phase 2 | Day 10 | ✅ |
| C10 — DVC + CI | Phase 2 | Day 11 | ⬜ |

---

## Running Order for a Fresh Environment

```bash
# 1. Start the stack
just up

# 2. Run Alembic migrations (owned by WS-4)
cd services/eligibility && alembic upgrade head && cd -

# 3. Ingest (or reproduce via DVC)
dvc repro

# 4. Verify counts
pytest tests/test_ingest_counts.py -v
```

Individual scripts:
```bash
# NPI (already implemented)
python data/ingest/npi_ingest.py

# Override geo filter
python data/ingest/npi_ingest.py npi.geo_filter.states=[NY]

# MRF with a specific URL
python data/ingest/mrf_parser.py mrf.source_url=https://...

# Synthetic cards only
python data/ingest/synthetic_cards.py
```

---

## Open Questions

| # | Question | Owner | Priority |
|---|---|---|---|
| Q1 | Confirm exact NPPES V2 CSV column headers for taxonomy fields — current mapping uses switch-field | WS-1 | High |
| Q2 | Which Aetna or BCBS NYC MRF URL to use for the demo subset? | WS-1 | High |
| Q3 | Exact CMS PUF 2026 download URL for `plan_puf_ingest.yaml` (CMS page lists several ZIP variants) | WS-1 | Medium |
| Q4 | Does the Flux-based card generator require GPU? If so, document Modal/RunPod usage or swap to pure Pillow | WS-1 / WS-3 | Medium |
| Q5 | Redis available before `care_compare_sync.py` runs? (depends on `just up` having been called) | WS-8 | Low |

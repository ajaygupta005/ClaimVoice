# WS-1 · Data Engineering & Acquisition — Specification

**Workstream owner**: distributed (every contributor touches this)
**Feeds**: WS-3 Document AI, WS-4 Eligibility, WS-5 Providers, WS-6 Voice Agent
**Commit budget**: 10 commits across the 30-day plan

---

## 1 · Scope

WS-1 is responsible for **every public and synthetic dataset** the system depends on. It produces:
- Populated PostgreSQL tables consumed by all other services
- Raw files on disk versioned via DVC
- Synthetic training images for the Document AI pipeline
- Hand-crafted stub responses for the eligibility service

WS-1 does **not** own the schema migrations (those live in `services/eligibility/alembic/`) or the RAG embedding pipeline (WS-4).

---

## 2 · Deliverables

| # | Deliverable | Status |
|---|---|---|
| D1 | `ingest/npi_ingest.py` — NPPES V2 → `providers` (PostGIS) | Done |
| D2 | `ingest/configs/npi_ingest.yaml` — Hydra config for NPI | Done |
| D3 | `ingest/plan_puf_ingest.py` — Exchange PUFs → `plans`, `plan_benefits` | Stub |
| D4 | `ingest/configs/plan_puf_ingest.yaml` | Missing |
| D5 | `ingest/formulary_ingest.py` — Part D CY2026 → `formulary_drug` | Stub |
| D6 | `ingest/configs/formulary_ingest.yaml` | Missing |
| D7 | `ingest/mrf_parser.py` — Transparency-in-Coverage Schema 2.0 → `in_network` | Stub |
| D8 | `ingest/configs/mrf_ingest.yaml` | Missing |
| D9 | `ingest/care_compare_sync.py` — Care Compare API → `providers.quality_rating` | Stub |
| D10 | `ingest/icd_hcpcs_ingest.py` — CMS code tables → `icd10_codes`, `hcpcs_codes` | Stub |
| D11 | `ingest/sbc_download.py` — download 5–10 SBC PDFs to `data/raw/sbcs/` | Stub |
| D12 | `ingest/synthetic_cards.py` — 100 PNG cards to `data/processed/synthetic_cards/` | Stub |
| D13 | `stubs/eligibility_271/` — 30 hand-crafted X12 271 JSON responses | Missing |
| D14 | `ingest/seed_test_members.py` — populate `members` table | Missing |
| D15 | `dvc.yaml` — all stages wired in dependency order | Missing |
| D16 | `ingest/configs/*.yaml` — Hydra configs for all scripts | Partial |

---

## 3 · Script Contract

Every ingestion script **must** satisfy all six properties:

### 3.1 Idempotent
Re-running a script against an already-populated table must produce identical state. All INSERT statements use `ON CONFLICT DO NOTHING` or equivalent upsert logic. Never truncate-and-reload without an explicit `--reset` flag.

### 3.2 Streaming
Scripts that handle large files (NPI CSV ~1 GB, MRF ~100 GB+) must stream row-by-row. Never load an entire file into memory.

### 3.3 Hydra-configured
Every tunable parameter (source URL, geo bounds, batch size, DB connection) lives in `ingest/configs/<script>.yaml`. The `DATABASE_URL` is resolved via `${oc.env:DATABASE_URL,postgresql://localhost/claimvoice}`. CLI overrides use Hydra syntax: `python script.py key=value`.

### 3.4 Auditable
Every inserted row gets an entry in `audit_log` with: `table_name`, `record_id`, `source`, `data_hash` (SHA256 of the row dict), `source_url`.

### 3.5 Structured logging
Use the standard `logging` module. Emit: `rows_parsed`, `rows_loaded`, `rows_skipped`, `duration_seconds` at INFO level at the end of each run. Log file: `data/ingest.log`.

### 3.6 Schema-guarded
Check that the target table exists (via `information_schema.tables`) before attempting inserts. Raise a clear error if Alembic migrations have not been run.

---

## 4 · Per-Script Specification

### 4.1 `npi_ingest.py` — COMPLETE

**Source**: CMS NPPES V2 Bulk Download — monthly CSV in ZIP (~1.08 GB)
**Target table**: `providers`
**Filter**: NY metro states (NY, NJ, CT), lat/lon bounds, active NPIs only, entity types 1+2
**Key logic**:
- Stream CSV via `csv.DictReader`
- Filter rows without lat/lon coordinates
- Batch insert (default 5,000 rows) with `ON CONFLICT (npi) DO NOTHING`
- Store `GEOGRAPHY(POINT, 4326)` from lat/lon fields
- `specialty_codes` populated from primary taxonomy code; Care Compare sync enriches later

**Known issues**:
- Takes first practice location when multiple exist
- `taxonomy_code` / `taxonomy_description` column mapping uses switch-field, not code-field — verify against actual CSV header

---

### 4.2 `plan_puf_ingest.py`

**Source**: CMS Health Insurance Exchange Plan PUFs 2026 — `56.4 MB ZIP` from CMS Marketplace public-use files page
**Target tables**: `plans`, `plan_benefits`
**Filter**: plan year 2026; marketplace plans only
**Key logic**:
- Download and unzip; four relevant CSVs: `Plan_Attributes`, `Benefits_Cost_Sharing`, `Rate`, `ServiceArea`
- `Plan_Attributes` → `plans` table (one row per plan)
- `Benefits_Cost_Sharing` → `plan_benefits` (one row per benefit per network type)
- Monetary amounts (copay, deductible, OOP max) converted to **cents** (BIGINT); never store floats
- `ON CONFLICT (plan_marketing_name) DO NOTHING` for plans; `ON CONFLICT DO NOTHING` for benefits

**Config keys** (`plan_puf_ingest.yaml`):
```yaml
plan_puf:
  download_url: "https://www.cms.gov/marketplace/resources/data/public-use-files"  # actual file URL
  extract_dir: "data/raw/exchange_puf_2026"
  plan_year: 2026
  database:
    connection_string: "${oc.env:DATABASE_URL,postgresql://localhost/claimvoice}"
    batch_size: 2000
```

---

### 4.3 `formulary_ingest.py`

**Source**: CMS Part D Formulary Reference File CY 2026 — quarterly ZIP (April + December files)
**Target tables**: `formulary_drug`
**Key logic**:
- Parse `formulary_file.txt` (pipe-delimited) inside the ZIP
- Each row: `CONTRACT_ID`, `FORMULARY_ID`, `NDC`, `TIER_LEVEL_VALUE`, `QUANTITY_LIMIT_APPLY_IND`, `PRIOR_AUTHORIZATION_YN`, `STEP_THERAPY_YN`
- Join `FORMULARY_ID` to `plans.formulary_id` to resolve `plan_id`; log unmatched formulary IDs at WARNING
- `tier`: 1=generic, 2=preferred brand, 3=non-preferred, 4=specialty
- `ON CONFLICT (plan_id, ndc_code) DO NOTHING`

**Config keys** (`formulary_ingest.yaml`):
```yaml
formulary:
  download_url: "https://www.cms.gov/medicare/coverage/prescription-drug-coverage/formulary-guidance"
  extract_dir: "data/raw/formulary_cy2026"
  plan_year: 2026
  database:
    connection_string: "${oc.env:DATABASE_URL,postgresql://localhost/claimvoice}"
    batch_size: 5000
```

---

### 4.4 `mrf_parser.py`

**Source**: Payer Transparency-in-Coverage MRFs — Schema 2.0 (mandatory Feb 2026)
**Target table**: `in_network`
**Demo scope**: one payor's NYC subset only (Aetna or BCBS)

**Key logic**:
- Stream-parse JSON line-by-line using `ijson` (never buffer the full file — files can be 100+ GB)
- Outer structure: `reporting_entity_name`, `reporting_entity_type`, `in_network[]`
- Per `in_network` item: `billing_code`, `billing_code_type`, `negotiated_rates[]`
- Per `negotiated_rates`: `provider_references[]` or `provider_groups[]`, `negotiated_price[]`
- Filter: keep only HCPCS codes (skip CPT — AMA paywall)
- Filter: keep only NYC metro NPIs (cross-reference against `providers` table)
- `ON CONFLICT DO NOTHING`; sparse index `(plan_id, provider_npi, procedure_code)`

**Constraints**:
- Schema drift is a real risk — monitor CMS Schema 2.0 changelog quarterly
- Stale after 30 days; cache with 15-min TTL at query time
- The `in_network` table may hold tens of millions of rows for a single payor — batch inserts mandatory

**Config keys** (`mrf_ingest.yaml`):
```yaml
mrf:
  source_url: ""  # Set to Aetna/BCBS NYC MRF URL at runtime
  extract_dir: "data/raw/mrf"
  payor: "aetna"  # label for audit_source
  database:
    connection_string: "${oc.env:DATABASE_URL,postgresql://localhost/claimvoice}"
    batch_size: 10000
```

---

### 4.5 `care_compare_sync.py`

**Source**: CMS Care Compare API — `https://data.cms.gov/provider-data/` — JSON, no auth
**Target**: `providers.quality_rating`, `providers.accepting_new_patients`, `providers.hospital_name`
**Key logic**:
- Paginated GET to `https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0` (hospital general info)
- Match on NPI where available; fallback match on provider name + zip
- `UPDATE providers SET quality_rating = %s, hospital_name = %s WHERE npi = %s`
- Cache responses in Redis with 24-hour TTL to avoid hammering the API

**Config keys** (`care_compare_sync.yaml`):
```yaml
care_compare:
  api_base: "https://data.cms.gov/provider-data/api/1/datastore/query"
  dataset_id: "xubh-q36u"  # Hospital General Information
  page_size: 500
  redis_ttl_seconds: 86400
  database:
    connection_string: "${oc.env:DATABASE_URL,postgresql://localhost/claimvoice}"
```

---

### 4.6 `icd_hcpcs_ingest.py`

**Source**: CMS ICD-10-CM FY2026 and HCPCS Level II Annual Update files
**Target tables**: `icd10_codes`, `hcpcs_codes`
**Key logic**:
- ICD-10: parse `icd10cm_codes_2026.txt` (fixed-width: 7-char code, description)
- HCPCS: parse `HCPCSA*.xlsx` or equivalent flat CSV
- Both are static reference tables — load once, rarely updated
- `ON CONFLICT (code) DO NOTHING`

---

### 4.7 `sbc_download.py`

**Source**: HealthCare.gov plan-listing pages (public, no auth)
**Target**: `data/raw/sbcs/*.pdf`
**Scope**: 5–10 SBC PDFs covering ≥3 payors (Aetna, UHC, BCBS minimum)
**Key logic**:
- Hardcode a manifest of known-good PDF URLs in `configs/sbc_manifest.yaml`
- HTTP GET with retry (3× exponential backoff)
- Skip if file already exists (idempotent)
- Write metadata sidecar `*.json` next to each PDF: `{url, downloaded_at, payor, plan_name, plan_year, file_size_bytes}`
- These PDFs are consumed by WS-3 (SBC parser) and WS-4 (RAG embedding)

**Config keys** (`sbc_manifest.yaml`):
```yaml
sbcs:
  output_dir: "data/raw/sbcs"
  plans:
    - url: "..."
      payor: "aetna"
      plan_name: "Aetna Bronze 6850"
      plan_year: 2026
    # ... additional entries
```

---

### 4.8 `synthetic_cards.py`

**Source**: Faker (member data) + Pillow (card rendering); Flux optional for background textures
**Target**: `data/processed/synthetic_cards/` — 100 PNG files + `labels.jsonl`
**Purpose**: training corpus for WS-3 LayoutLMv3 card OCR model
**Key logic**:
- Generate for 4 payor templates: Aetna, UHC, BCBS, Cigna (25 cards each)
- Each card has: member_id, first_name, last_name, dob, group_number, plan_name, rx_bin, rx_pcn, effective_date, phone
- `labels.jsonl`: one JSON object per card with field-level bounding boxes in `[x1, y1, x2, y2]` normalized coordinates
- Apply augmentations: rotation (±5°), brightness jitter, JPEG compression artifacts, optional glare simulation
- No real PII; all names and IDs are Faker-generated

---

### 4.9 `seed_test_members.py`

**Source**: Faker + fixture data
**Target**: `members` table
**Scope**: 30 test members, each linked to a plan loaded by `plan_puf_ingest.py`
**Key logic**:
- Fixed seed (`random.seed(42)`) for reproducibility
- Cover all eligibility states: `active` (24), `inactive` (4), `suspended` (2)
- Vary `deductible_ytd_cents` across 0 / partial / met scenarios
- Each member gets a synthetic insurance card image pointer in `data/processed/synthetic_cards/`

---

### 4.10 X12 271 Stubs (`stubs/eligibility_271/`)

**Target**: 30 JSON files, one per test member
**Purpose**: the eligibility service loads these at startup to simulate real X12 270/271 round-trips

Each file named `<member_id>.json`:
```json
{
  "member_id": "M123456789",
  "eligibility_status": "active",
  "plan_name": "Aetna Bronze 6850",
  "deductible_individual_cents": 685000,
  "deductible_ytd_cents": 142000,
  "oop_max_individual_cents": 850000,
  "oop_ytd_cents": 142000,
  "effective_date": "2026-01-01",
  "termination_date": null,
  "copays": {
    "primary_care_cents": 3000,
    "specialist_cents": 6000,
    "emergency_cents": 35000
  }
}
```

Cover: deductible-not-met, deductible-partially-met, deductible-met, OOP-max-met, inactive member, suspended member.

---

## 5 · DVC Pipeline (`dvc.yaml`)

All stages must be wired in dependency order. The canonical order is:

```
npi_ingest → (no deps)
plan_puf_ingest → (no deps)
formulary_ingest → depends on plan_puf_ingest
mrf_parser → depends on plan_puf_ingest
care_compare_sync → depends on npi_ingest
icd_hcpcs_ingest → (no deps)
seed_test_members → depends on plan_puf_ingest, formulary_ingest
sbc_download → (no deps)
synthetic_cards → (no deps)
```

Each stage must declare:
- `cmd`: the Python invocation
- `deps`: the script file + its config YAML
- `outs`: produced files (with `cache: false` for DB-backed outputs)

---

## 6 · Acceptance Criteria

| Check | Threshold |
|---|---|
| `providers` row count after NPI ingest (NY metro) | ≥ 40,000 rows |
| `plans` row count after PUF ingest | ≥ 500 plans |
| `plan_benefits` row count | ≥ 5,000 benefit rows |
| `formulary_drug` row count | ≥ 10,000 drug entries |
| `icd10_codes` row count | ≥ 70,000 codes |
| `hcpcs_codes` row count | ≥ 5,000 codes |
| SBC PDFs downloaded | ≥ 5 files, ≥ 3 distinct payors |
| Synthetic card images | exactly 100 PNGs + 100 matching `labels.jsonl` entries |
| X12 stub files | exactly 30 JSON files in `stubs/eligibility_271/` |
| Test members | exactly 30 rows in `members` table |
| `audit_log` entries | ≥ 1 entry per loaded row |
| All scripts idempotent | Second run produces no new `audit_log` entries and no errors |
| `dvc repro` | Completes without error from a clean state |

---

## 7 · Monetary Amounts

All monetary values are stored as **cents** (BIGINT). Never use NUMERIC or FLOAT for money.

```python
# Correct
copay_cents = int(round(float(raw_copay_dollars) * 100))

# Wrong — loses precision, causes rounding bugs
copay_float = float(raw_copay_dollars)
```

---

## 8 · Data Quality Rules

- **NPI**: must be exactly 10 digits. Reject records where `len(npi) != 10`.
- **State codes**: must be 2-char uppercase. Normalize with `.upper()[:2]`.
- **ZIP codes**: store 5-digit only — `zip[:5]`.
- **Dates**: store as `DATE` in Postgres. Parse with `datetime.strptime(s, "%Y%m%d").date()` for CMS files; fall back to `dateutil.parser.parse`.
- **NDC codes**: normalize to 11-digit format (convert 10-digit with dash to 11 digits).
- **Taxonomy codes**: store as-is (e.g., `207Q00000X`); no normalization.

---

## 9 · Not In Scope

- Real-time X12 270/271 eligibility (production = Availity/Change Healthcare/Stedi; WS-1 only provides stubs)
- SBC PDF parsing (WS-3 owns the LayoutLMv3 SBC parser)
- Voyage AI embedding of SBC chunks (WS-4)
- Employer-level plan customizations (captured via SBC parsing in WS-4, not PUF)
- Medicaid data (deferred to v2)
- CPT codes (AMA paywall — use HCPCS only)

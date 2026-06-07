# Data Sources & Ingestion Pipeline

ClaimVoice's data backbone. All datasets are **free**, **US-public**, and **verified live as of May 2026**.

Every ingestion script is:
- ✅ **Idempotent** — run twice, same output
- ✅ **Logged** — structured logging to `data/ingest.log`
- ✅ **Parameterized** — Hydra config for each (geo filter, date range, sample size)
- ✅ **Observable** — Prometheus metrics: `ingest_rows_loaded`, `ingest_duration_seconds`
- ✅ **Auditable** — immutable audit trail with SHA256 hash + source URL

---

## 1. Public Data Sources

| Data | Source | Cadence | Script | Destination |
|---|---|---|---|---|
| **NPI provider registry** | [CMS NPPES V2 Bulk](https://download.cms.gov/nppes/NPI_Files.html) | Monthly | `ingest/npi_ingest.py` | `providers` table (PostGIS) |
| **2026 Exchange Plan PUFs** | [CMS Marketplace PUFs](https://www.cms.gov/marketplace/resources/data/public-use-files) | Annually | `ingest/plan_puf_ingest.py` | `plans`, `plan_benefits`, `plan_rates` |
| **SBC PDFs (raw)** | [HealthCare.gov plan listings](https://healthcare.gov) | Annual | `ingest/sbc_download.py` | `data/raw/sbcs/*.pdf` |
| **MRF in-network rates (Schema 2.0)** | Payer Transparency-in-Coverage MRFs | Monthly | `ingest/mrf_parser.py` | `in_network` table |
| **Part D Drug Formulary (CY 2026)** | [CMS Part D Formulary](https://www.cms.gov/medicare/coverage/prescription-drug-coverage/formulary-guidance) | Quarterly | `ingest/formulary_ingest.py` | `formulary_drug`, `formulary_tier` |
| **Hospital Quality (Care Compare)** | [CMS Care Compare API](https://data.cms.gov/provider-data/topics/hospitals/) | Daily | `ingest/care_compare_sync.py` | `providers.quality_rating` |
| **ICD-10 / HCPCS codes** | [CMS Code Downloads](https://www.cms.gov/medicare/coding-billing/icd-10-codes) | Annually | `ingest/icd_hcpcs_ingest.py` | `icd10_codes`, `hcpcs_codes` |

---

## 2. Synthetic Data (Privacy-First)

| Data | Generator | Purpose | Destination |
|---|---|---|---|
| **Insurance cards (100)** | `ingest/synthetic_cards.py` (Flux + Faker) | Train LayoutLMv3 card OCR | `data/synthetic/cards/` |
| **X12 271 eligibility** | Hand-crafted in JSON | Test eligibility flows | `stubs/eligibility_271/` |
| **Test members** | `ingest/seed_test_members.py` | Populate `members` table | `members` table |

---

## 3. Postgres Schema

All tables live in the ClaimVoice PostgreSQL instance. The canonical schema is version-controlled in [`services/eligibility/alembic/versions/`](../services/eligibility/alembic/versions/).

### 3.1 Core Tables

#### `members`
Test members + eligibility state. In production, populated by X12 270 round-trips to a clearinghouse.

```sql
CREATE TABLE members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id VARCHAR UNIQUE NOT NULL,        -- "M123456789"
  first_name VARCHAR,
  last_name VARCHAR,
  dob DATE,
  gender CHAR(1),
  plan_id UUID NOT NULL REFERENCES plans(id),
  enrollment_date DATE,
  eligibility_status VARCHAR,                -- 'active', 'inactive', 'suspended'
  deductible_ytd_cents BIGINT DEFAULT 0,    -- cents
  oop_ytd_cents BIGINT DEFAULT 0,
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR,                      -- 'seed', 'x12_sync', etc.
  CONSTRAINT valid_status CHECK (eligibility_status IN ('active', 'inactive', 'suspended'))
);

CREATE INDEX idx_members_plan_id ON members(plan_id);
CREATE INDEX idx_members_member_id ON members(member_id);
```

#### `providers`
NPI registry + quality ratings. Spatial indexing for geo queries.

```sql
CREATE TABLE providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  npi VARCHAR(10) UNIQUE NOT NULL,
  first_name VARCHAR,
  last_name VARCHAR,
  organization_name VARCHAR,
  credential_text VARCHAR,                   -- 'MD', 'DO', 'NP', etc.
  taxonomy_code VARCHAR,
  taxonomy_description VARCHAR,
  practice_location_address_line_1 VARCHAR,
  practice_location_city VARCHAR,
  practice_location_state CHAR(2),
  practice_location_zip VARCHAR(5),
  practice_location_phone VARCHAR,
  location GEOGRAPHY(POINT, 4326),          -- PostGIS
  accepting_new_patients BOOLEAN,
  quality_rating NUMERIC(3,1),              -- 1–5 stars
  hospital_name VARCHAR,                     -- if applicable
  specialty_codes TEXT[],                    -- ARRAY of taxonomy codes
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR,                      -- 'nppes_v2_may2026', 'care_compare_sync'
  CONSTRAINT valid_stars CHECK (quality_rating >= 1 AND quality_rating <= 5)
);

-- Spatial index for ST_DWithin queries
CREATE INDEX idx_providers_location ON providers USING GIST(location);
CREATE INDEX idx_providers_npi ON providers(npi);
CREATE INDEX idx_providers_taxonomy ON providers USING GIN(specialty_codes);
```

#### `plans`
Health plans (Exchange, MA, etc.).

```sql
CREATE TABLE plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id_type VARCHAR,                      -- 'HMO', 'PPO', 'POS', 'EPOS'
  plan_marketing_name VARCHAR UNIQUE NOT NULL,
  issuer_name VARCHAR,                       -- 'Aetna', 'UHC', 'Cigna', etc.
  plan_year SMALLINT,                        -- 2026, 2027, ...
  plan_type VARCHAR,
  metal_level VARCHAR,                       -- 'Platinum', 'Gold', 'Silver', 'Bronze'
  hsa_eligible BOOLEAN,
  formulary_id VARCHAR,
  service_area_state CHAR(2),
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR                       -- 'plan_puf_2026'
);

CREATE INDEX idx_plans_issuer_year ON plans(issuer_name, plan_year);
```

#### `plan_benefits`
Coverage rules: deductible, copay, coinsurance, OOP max per service.

```sql
CREATE TABLE plan_benefits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  benefit_name VARCHAR,                      -- 'Office Visit - Specialist', 'MRI - In Network', etc.
  service_category VARCHAR,                  -- 'Professional Services', 'Diagnostic Imaging', etc.
  network_type VARCHAR,                      -- 'In Network', 'Out of Network'
  individual_deductible_cents BIGINT,       -- cents
  family_deductible_cents BIGINT,
  copay_amount_cents BIGINT,
  coinsurance_percentage NUMERIC(3,1),      -- 0.0–100.0
  out_of_pocket_max_cents BIGINT,
  benefit_description TEXT,
  requires_prior_auth BOOLEAN DEFAULT FALSE,
  excluded_reason TEXT,                      -- if not covered
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR,                      -- 'sbc_parse_<payor>', 'plan_puf'
  CONSTRAINT valid_coinsurance CHECK (coinsurance_percentage >= 0 AND coinsurance_percentage <= 100)
);

CREATE INDEX idx_plan_benefits_plan_id ON plan_benefits(plan_id);
CREATE INDEX idx_plan_benefits_category ON plan_benefits(service_category);
```

#### `in_network`
MRF-derived in-network provider + rate mappings (sparse; huge table; heavily indexed).

```sql
CREATE TABLE in_network (
  id BIGSERIAL PRIMARY KEY,
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  provider_npi VARCHAR(10) NOT NULL,
  procedure_code VARCHAR,                    -- HCPCS/CPT (text, not numeric)
  negotiated_rate_cents BIGINT,
  effective_date DATE,
  expiry_date DATE,
  bundled_codes TEXT[],                      -- array of bundled procedures
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR                       -- 'mrf_parser_<payor>_<month>'
);

-- Sparse indexing: most queries are (plan_id, provider_npi, procedure_code)
CREATE INDEX idx_in_network_plan_npi_code ON in_network(plan_id, provider_npi, procedure_code);
CREATE INDEX idx_in_network_effective ON in_network(effective_date, expiry_date);
```

#### `formulary_drug`
Drug coverage (Part D + commercial formulary).

```sql
CREATE TABLE formulary_drug (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  drug_name VARCHAR NOT NULL,
  ndc_code VARCHAR,                          -- National Drug Code
  formulary_tier SMALLINT,                   -- 1 (generic), 2 (preferred), 3 (non-preferred), 4 (specialty)
  prior_auth_required BOOLEAN DEFAULT FALSE,
  step_therapy_required BOOLEAN DEFAULT FALSE,
  quantity_limit VARCHAR,                    -- "30 per 30 days"
  audit_created_at TIMESTAMP DEFAULT now(),
  audit_source VARCHAR                       -- 'part_d_cy2026', 'plan_formulary'
);

CREATE INDEX idx_formulary_plan_drug ON formulary_drug(plan_id, drug_name);
CREATE INDEX idx_formulary_tier ON formulary_drug(formulary_tier);
```

#### `audit_log`
Immutable fact-check trail. Every coverage statement + eligibility lookup.

```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name VARCHAR NOT NULL,              -- 'plan_benefits', 'in_network', 'formulary_drug'
  record_id VARCHAR,
  source VARCHAR NOT NULL,                   -- 'npi_ingest', 'mrf_parser', 'x12_sync', 'fact_check'
  ingest_timestamp TIMESTAMP DEFAULT now(),
  data_hash VARCHAR,                         -- SHA256 of the row
  source_url VARCHAR,                        -- URL of the raw file (if applicable)
  notes TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_audit_source ON audit_log(source, ingest_timestamp);
CREATE INDEX idx_audit_table ON audit_log(table_name);
```

#### `icd10_codes` & `hcpcs_codes`
Diagnosis and procedure code lookups.

```sql
CREATE TABLE icd10_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(7) UNIQUE NOT NULL,
  long_description TEXT,
  short_description TEXT,
  audit_source VARCHAR DEFAULT 'cms_icd10_2026'
);

CREATE TABLE hcpcs_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(5) UNIQUE NOT NULL,
  long_description TEXT,
  short_description TEXT,
  audit_source VARCHAR DEFAULT 'cms_hcpcs_2026'
);

CREATE INDEX idx_icd10_code ON icd10_codes(code);
CREATE INDEX idx_hcpcs_code ON hcpcs_codes(code);
```

---

## 4. Data Ingestion Order

**Must follow this dependency order:**

```mermaid
graph TD
  A["1. npi_ingest.py<br/>(providers table)"]
  B["2. plan_puf_ingest.py<br/>(plans + benefits)"]
  C["3. formulary_ingest.py<br/>(formulary_drug)"]
  D["4. mrf_parser.py<br/>(in_network)"]
  E["5. care_compare_sync.py<br/>(update providers.quality_rating)"]
  F["6. icd_hcpcs_ingest.py<br/>(code lookups)"]
  G["7. seed_test_members.py<br/>(populate members)"]
  H["8. sbc_download.py<br/>(raw PDFs for WS-3)"]
  I["9. synthetic_cards.py<br/>(PNGs for WS-3 training)"]

  A --> E
  B --> C
  B --> D
  B --> G
  C --> G
  F --> G
  G --> H
```

---

## 5. Configuration

All ingestion scripts use Hydra configs in `ingest/configs/`. Example:

```yaml
# ingest/configs/npi_ingest.yaml
npi:
  download_url: "https://download.cms.gov/nppes/npi_data.zip"
  extract_dir: "data/raw/nppes_v2_may2026"
  
  # Filtering
  geo_filter:
    states: ["NY", "NJ", "CT"]  # NY metro + surround
    min_latitude: 40.6
    max_latitude: 41.2
    min_longitude: -74.3
    max_longitude: -73.7
  
  taxonomy_filter:
    include_specialties:
      - "Allopathic & Osteopathic Physicians"
      - "Nurse Practitioners"
  
  database:
    connection_string: "${oc.env:DATABASE_URL}"
    batch_size: 5000
    
logging:
  level: "INFO"
  file: "data/ingest.log"
```

---

## 6. Reproducibility & DVC

All ingestion is tracked in `dvc.yaml`:

```yaml
stages:
  ingest_npi:
    cmd: python data/ingest/npi_ingest.py
    deps:
      - data/ingest/npi_ingest.py
      - data/ingest/configs/npi_ingest.yaml
    params:
      - npi_ingest.geo_filter
    outs:
      - data/raw/nppes_v2_may2026.csv:
          cache: false  # DB is the source of truth
      - data/ingest.log:
          cache: false
  
  ingest_plans:
    cmd: python data/ingest/plan_puf_ingest.py
    deps:
      - data/ingest/plan_puf_ingest.py
      - data/ingest/configs/plan_puf_ingest.yaml
    outs:
      - data/raw/exchange_puf_2026.csv:
          cache: false

  # ... all other stages
```

Run reproducibly:
```bash
dvc repro  # Re-runs all ingestion from scratch
```

---

## 7. Edge Cases & Known Limitations

### NPI Data
- **Deactivated NPIs**: Filtered out by `npi_ingest.py` unless `include_deactivated: true`
- **Address ambiguity**: Some NPIs list multiple practice locations; we take the first
- **Specialty mismatch**: NPI's primary taxonomy != actual practice; document in `specialty_codes[]`

### Plan PUF Data
- **Employer variations**: Each employer customizes benefits; PUF only captures plan-level; SBC parsing required for details
- **Plan year transitions**: Some plans effective mid-year; see `effective_date`, `expiry_date`

### MRF Data
- **File size**: Each payor's MRF can be 100+ GB compressed; stream-parse line-by-line
- **Schema drift**: Monitor CMS Schema 2.0 changes quarterly
- **Stale data**: MRFs updated monthly; cache aggressively with 15-min TTL

### Drug Formulary
- **Tier changes**: Part D formularies change quarterly; always use latest CY year
- **Unlisted drugs**: OTC drugs not in formulary; document separately

---

## 8. Audit Trail

Every row ingested creates an immutable audit log entry:

```sql
INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
VALUES (
  'providers',
  'npi_1234567890',
  'nppes_v2_may2026',
  'sha256_hash_of_row',
  'https://download.cms.gov/nppes/NPI_Files.html'
);
```

Query lineage anytime:
```sql
SELECT * FROM audit_log 
WHERE table_name = 'providers' 
  AND record_id = 'npi_1234567890'
ORDER BY ingest_timestamp DESC;
```

---

## 9. Running Ingestion Locally

### Prerequisites
```bash
# Install Python + dependencies
python -m pip install -r requirements.txt

# Start Postgres + Redis (docker-compose)
docker-compose up postgres redis

# Set environment
export DATABASE_URL="postgresql://user:pass@localhost/claimvoice"
```

### Run all ingestion
```bash
# Run in dependency order
dvc repro
```

### Run a single ingestion
```bash
python data/ingest/npi_ingest.py
```

### Verify schema
```bash
# List all tables
psql $DATABASE_URL -c "\dt"

# Row counts
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';" | \
  while read t; do echo "$t: $(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM $t")"; done
```

---

## 10. Next Steps

1. **Alembic migrations**: Define schema in `services/eligibility/alembic/versions/001_init_schema.py`
2. **Hydra configs**: Create `ingest/configs/*.yaml` for each ingestion script
3. **Unit tests**: `tests/test_npi_ingest.py`, etc.
4. **Integration tests**: DVC pipeline run + row count assertions

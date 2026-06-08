# WS-1 Quick Start Guide — Database Setup & Testing

## 5-Minute Quick Start

### Option 1: Docker (Recommended)

```bash
# Start Postgres + Redis
cd d:\IISC\DeepLearning\ClaimVoice
docker-compose up -d postgres redis

# Wait 5 seconds for Postgres to be ready
sleep 5

# Run migrations
cd services/eligibility
alembic upgrade head

# Test load synthetic data
cd ../..
python data/ingest/npi_ingest.py npi.extract_dir=data/raw

# Verify
psql postgresql://postgres@localhost/claimvoice -c "SELECT COUNT(*) as providers FROM providers;"
```

### Option 2: Local Postgres

```bash
# Create database (Windows: use pgAdmin or psql)
createdb claimvoice

# Set environment
set DATABASE_URL=postgresql://user:pass@localhost/claimvoice

# Run migrations
cd services/eligibility
alembic upgrade head

# Test load
cd ../..
python data/ingest/npi_ingest.py npi.extract_dir=data/raw

# Verify
psql %DATABASE_URL% -c "SELECT COUNT(*) FROM providers;"
```

---

## Step-by-Step: Running NPI Ingestion

### 1. Verify Prerequisites

```bash
python --version          # Should be 3.10+
pip list | grep -E "sqlalchemy|hydra|psycopg"  # Check packages installed
```

### 2. Check Database Connection

```bash
python -c "import psycopg; print('✅ psycopg installed')"

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### 3. Run Migrations (if not done)

```bash
cd services/eligibility
alembic current        # Show current revision
alembic upgrade head   # Migrate to latest
alembic current        # Verify
```

### 4. Load Synthetic Data

```bash
cd d:\IISC\DeepLearning\ClaimVoice

# Standard run (uses data/raw/nppes_sample.csv)
python data/ingest/npi_ingest.py

# With debug logging
python data/ingest/npi_ingest.py logging.level=DEBUG

# Override config
python data/ingest/npi_ingest.py npi.database.batch_size=1000 npi.extract_dir=data/raw
```

### 5. Verify Data Loaded

```bash
psql $DATABASE_URL

# Basic counts
SELECT COUNT(*) as providers FROM providers;
SELECT COUNT(*) as audit_entries FROM audit_log;
SELECT COUNT(*) as plans FROM plans;

# Sample data
SELECT npi, first_name, last_name, practice_location_city FROM providers LIMIT 5;

# Spatial query (within 10 km of Times Square: 40.758, -73.985)
SELECT npi, first_name, last_name, 
       ST_Distance(location, ST_Point(-73.985, 40.758)::geography) / 1000 as distance_km
FROM providers
WHERE location IS NOT NULL
ORDER BY distance_km
LIMIT 5;

# Audit trail
SELECT table_name, source, COUNT(*) as entries FROM audit_log GROUP BY table_name, source;
```

---

## Troubleshooting

### "Connection refused"
**Problem**: Postgres not running  
**Solution**:
```bash
docker-compose up postgres  # If using Docker
# Or start Postgres service locally
```

### "Table 'providers' does not exist"
**Problem**: Alembic migrations not run  
**Solution**:
```bash
cd services/eligibility
alembic upgrade head
```

### "ModuleNotFoundError: No module named 'psycopg'"
**Problem**: Python packages not installed  
**Solution**:
```bash
pip install psycopg[binary] hydra-core sqlalchemy alembic
```

### "HTTP Error 403" when downloading real NPPES
**Problem**: CMS server blocking direct downloads  
**Solution**:
1. Visit: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NPI/
2. Manually download ZIP
3. Extract to `data/raw/nppes_v2_may2026/`
4. Run `python data/ingest/npi_ingest.py`

### No data loaded from synthetic CSV
**Problem**: Wrong extract_dir path  
**Solution**:
```bash
# Make sure nppes_sample.csv exists
ls -la data/raw/nppes_sample.csv

# Or regenerate it
python scripts/generate_nppes_sample.py

# Then run ingestion
python data/ingest/npi_ingest.py npi.extract_dir=data/raw
```

---

## What Each File Does

| File | Purpose | Time |
|------|---------|------|
| `001_init_schema.py` | Creates all 16 tables + indexes + constraints | 1 min |
| `npi_ingest.py` | Parses CSV + loads providers + spatial index | 2 min (synthetic) / 10 min (real) |
| `audit_log` | Immutable trail of every ingested record | Automatic |
| `providers` (table) | NPI registry with PostGIS spatial indexing | Queried by WS-5 |

---

## Verify Everything Works

```bash
# 1. Schema created
psql $DATABASE_URL -c "\dt"

# 2. Providers loaded (should show ~500 for synthetic)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM providers;"

# 3. Spatial index working
psql $DATABASE_URL -c "
  SELECT ST_Distance(
    location, 
    ST_Point(-73.97, 40.77)::geography
  ) as distance_km 
  FROM providers 
  WHERE location IS NOT NULL 
  LIMIT 1;"

# 4. Audit trail populated
psql $DATABASE_URL -c "SELECT * FROM audit_log LIMIT 3;"

# 5. Prometheus metrics (if enabled)
curl http://localhost:8000/metrics | grep ingest_
```

---

## Files Used in This Process

- **Input**: `data/raw/nppes_sample.csv` (synthetic) or real NPPES ZIP
- **Config**: `data/ingest/configs/npi_ingest.yaml`
- **Schema**: `services/eligibility/alembic/versions/001_init_schema.py`
- **Script**: `data/ingest/npi_ingest.py`
- **Output**: PostgreSQL tables (providers, audit_log, etc.)

---

## Next: Load Real Data (When Available)

```bash
# Download real NPPES V2 (~1.5 GB)
# URL: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NPI/

# Extract to data/raw/nppes_v2_may2026/

# Load (takes 5–10 minutes)
python data/ingest/npi_ingest.py \
  npi.extract_dir=data/raw/nppes_v2_may2026 \
  npi.geo_filter.states=[NY,NJ,CT]

# Verify: expect 150K–200K providers in NY metro
psql $DATABASE_URL -c "SELECT COUNT(*) FROM providers;"
```

---

**Status**: Ready for database setup!  
**Questions?** See `data/README.md` for more details.

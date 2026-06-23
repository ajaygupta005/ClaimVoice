# Tier-1+ DEV seed for Windows / PowerShell (no `just`, no bash needed).
# Schema + synthetic data, NO external downloads -- enough to develop WS-4/5/6.
#
# Two modes:
#   1) Own Postgres (default): pulls postgis image + `docker compose up -d postgres`.
#        .\scripts\seed_dev.ps1
#   2) Reuse an already-running Postgres (e.g. another app's), avoiding Docker Hub:
#        .\scripts\seed_dev.ps1 -ExistingDb -SentinelContainer sentinel-postgres
#      This provisions an ISOLATED `claimvoice` role + database inside that server;
#      the host app's own database is never touched. NOTE: a plain (non-PostGIS)
#      server means geo-distance search is unavailable until recreated on PostGIS.
#
# Uses isolated ephemeral uv envs (`uv run --no-project --with ...`) so it does
# NOT require a full `uv sync` of the workspace.

param(
    [switch]$ExistingDb,                          # reuse a running Postgres; skip image pull + compose up
    [string]$SentinelContainer = "",              # with -ExistingDb: docker container to create the claimvoice role+db in
    [string]$DatabaseUrl = ""                     # override DATABASE_URL
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:PYTHONUTF8 = "1"

if ($DatabaseUrl) { $env:DATABASE_URL = $DatabaseUrl }
elseif (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://claimvoice:changeme@localhost:5433/claimvoice" }
Write-Host "DATABASE_URL=$($env:DATABASE_URL)"

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env from .env.example" }

# ---- [1] Provision / start the database --------------------------------------
if ($ExistingDb) {
    Write-Host "`n[1/8] reusing an existing Postgres (skipping image pull + compose up)"
    if ($SentinelContainer) {
        Write-Host "  ensuring isolated 'claimvoice' role + database exist in '$SentinelContainer'"
        Write-Host "  (the host app's own database is NOT touched)"
        if (-not (docker exec $SentinelContainer psql -U sentinel -tAc "SELECT 1 FROM pg_roles WHERE rolname='claimvoice'")) {
            docker exec $SentinelContainer psql -U sentinel -c "CREATE ROLE claimvoice LOGIN PASSWORD 'changeme'" | Out-Null
        }
        if (-not (docker exec $SentinelContainer psql -U sentinel -tAc "SELECT 1 FROM pg_database WHERE datname='claimvoice'")) {
            docker exec $SentinelContainer psql -U sentinel -c "CREATE DATABASE claimvoice OWNER claimvoice" | Out-Null
        }
    }
} else {
    # Docker Hub's CDN can drop blob downloads mid-transfer; `docker pull` is resumable.
    Write-Host "`n[1/8] ensuring postgis image is present (retrying flaky Docker Hub pulls)"
    $haveImage = $false
    foreach ($i in 1..20) {
        docker image inspect postgis/postgis:16-3.4 *> $null
        if ($LASTEXITCODE -eq 0) { $haveImage = $true; break }
        Write-Host "  pull attempt $i ..."
        docker pull postgis/postgis:16-3.4
        if ($LASTEXITCODE -eq 0) { $haveImage = $true; break }
        Start-Sleep -Seconds 3
    }
    if (-not $haveImage) { throw "Could not pull postgis/postgis:16-3.4. Use -ExistingDb to reuse another Postgres, or try a different network/VPN." }

    Write-Host "starting Postgres (docker compose up -d postgres)"
    docker compose up -d postgres
    Write-Host "waiting for Postgres..."
    $ready = $false
    foreach ($i in 1..40) {
        docker compose exec -T postgres pg_isready -U claimvoice -d claimvoice *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; Write-Host "  ready (${i}s)"; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "Postgres did not become ready in 40s" }
}

# ---- [2..8] Migrate + seed (common to both modes) ----------------------------
Write-Host "`n[2/8] applying schema (alembic upgrade head)"
Push-Location (Join-Path $root "services\eligibility")
uv run --no-project --python 3.12 --with alembic --with sqlalchemy --with "psycopg[binary]" alembic upgrade head
Pop-Location

Write-Host "`n[3/8] generating NPPES sample"
uv run --no-project --python 3.12 python scripts/generate_nppes_sample.py
Write-Host "[4/8] loading providers from the sample (download bypassed)"
uv run --no-project --python 3.12 --with hydra-core --with omegaconf --with "psycopg[binary]" `
    python data/ingest/npi_ingest.py npi.source_csv=data/raw/nppes_sample.csv

Write-Host "[5/8] enriching providers (specialty + quality + accepting-new from taxonomy)"
uv run --no-project --python 3.12 --with "psycopg[binary]" python data/ingest/enrich_providers.py

Write-Host "`n[6/8] seeding plans, benefits, formulary, in-network, ICD-10/HCPCS"
uv run --no-project --python 3.12 --with "psycopg[binary]" python data/ingest/seed_dev.py

Write-Host "[7/8] seeding 30 test members + X12 271 stubs"
uv run --no-project --python 3.12 --with faker --with "psycopg[binary]" python data/ingest/seed_test_members.py

Write-Host "[8/8] seeding canonical demo member + plan (golden values for agent eval)"
uv run --no-project --python 3.12 --with "psycopg[binary]" python data/ingest/seed_demo_member.py

# ---- Report row counts (via DATABASE_URL, works in both modes) ----------------
Write-Host "`n=== ROW COUNTS ==="
$py = @'
import os, psycopg
tabs = ["providers","plans","plan_benefits","formulary_drug","in_network","members","icd10_codes","hcpcs_codes","audit_log"]
u = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(u) as c, c.cursor() as cur:
    for t in tabs:
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"{t:<16}{cur.fetchone()[0]}")
'@
$py | uv run --no-project --python 3.12 --with "psycopg[binary]" python -

Write-Host "`nDone. WS-4/WS-5/WS-6 now have data to develop against." -ForegroundColor Green

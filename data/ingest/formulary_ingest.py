#!/usr/bin/env python3
"""
Part D Formulary Ingest: Load CMS Part D Formulary Reference File CY2026 into PostgreSQL.

Source: CMS Part D Formulary Reference File CY2026 (quarterly, pipe-delimited .txt inside ZIP)
Target: formulary_drug table

Join key: formulary_file.FORMULARY_ID → plans.formulary_id (populated by plan_puf_ingest.py)

Idempotency: plan-level — skips any plan_id that already has rows under this audit_source.
Missing formulary IDs (no matching plan) are logged at WARNING and skipped;
plan_id is NOT NULL in the schema so NULL inserts are not possible.

Usage:
    python data/ingest/formulary_ingest.py
    python data/ingest/formulary_ingest.py formulary.batch_size=5000
    python data/ingest/formulary_ingest.py formulary.download_url=https://...
"""

import csv
import hashlib
import logging
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator, Optional

import psycopg
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

AUDIT_SOURCE = "cms_formulary_cy2026"

# CMS Part D Formulary Reference File column names (pipe-delimited)
_COL_CONTRACT_ID = "CONTRACT_ID"
_COL_FORMULARY_ID = "FORMULARY_ID"
_COL_NDC = "NDC"
_COL_TIER = "TIER_LEVEL_VALUE"
_COL_QTY_LIMIT = "QUANTITY_LIMIT_APPLY_IND"
_COL_PRIOR_AUTH = "PRIOR_AUTHORIZATION_YN"
_COL_STEP_THERAPY = "STEP_THERAPY_YN"


# ---------------------------------------------------------------------------
# NDC normalization
# ---------------------------------------------------------------------------

def _normalize_ndc(ndc: str) -> Optional[str]:
    """
    Normalize NDC to 11-digit format.

    CMS uses 11-digit NDC. Some sources ship 10-digit with dashes
    (e.g., 1234-5678-90). Strip dashes and zero-pad labeler segment to 11 digits.
    """
    if not ndc:
        return None
    cleaned = ndc.replace("-", "").strip()
    if not cleaned.isdigit():
        return None
    if len(cleaned) == 11:
        return cleaned
    if len(cleaned) == 10:
        return cleaned.zfill(11)
    if len(cleaned) < 10:
        return None
    return cleaned


def _parse_yn(value: str) -> bool:
    return value.strip().upper() in ("Y", "1", "YES", "TRUE")


# ---------------------------------------------------------------------------
# Download / extract
# ---------------------------------------------------------------------------

def download_formulary_zip(url: str, extract_dir: str) -> Path:
    """Download and extract the formulary ZIP; returns the extract directory."""
    out_dir = Path(extract_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = list(out_dir.glob("*.txt")) + list(out_dir.glob("*.csv"))
    if existing:
        logger.info("Formulary data already extracted at %s, skipping download", out_dir)
        return out_dir

    logger.info("Downloading formulary ZIP from %s", url)
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        raise

    logger.info("Extracting to %s", out_dir)
    with zipfile.ZipFile(tmp.name, "r") as zf:
        zf.extractall(out_dir)
    return out_dir


def _find_formulary_file(extract_dir: Path) -> Path:
    """Locate the pipe-delimited formulary file in the extracted directory."""
    for pattern in ("*formulary*file*.txt", "*formulary*.txt", "*.txt", "*.csv"):
        matches = list(extract_dir.rglob(pattern))
        if matches:
            return matches[0]
    contents = [str(p) for p in extract_dir.rglob("*")]
    raise FileNotFoundError(
        f"No formulary text/CSV file found in {extract_dir}. Contents: {contents}"
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def iter_formulary_rows(formulary_file: Path) -> Iterator[dict]:
    """Stream rows from the pipe-delimited CMS formulary file."""
    with open(formulary_file, encoding="utf-8", errors="replace") as fh:
        first_line = fh.readline()
        fh.seek(0)
        delimiter = "|" if "|" in first_line else ","
        reader = csv.DictReader(fh, delimiter=delimiter)
        yield from reader


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _build_formulary_to_plan_map(cursor) -> dict[str, str]:
    """
    Return {formulary_id_str: plan_uuid_str} for all plans with a non-null formulary_id.
    This is the join key between the CMS formulary file and our plans table.
    """
    cursor.execute(
        "SELECT formulary_id, id::text FROM plans WHERE formulary_id IS NOT NULL"
    )
    mapping = {row[0]: row[1] for row in cursor.fetchall()}
    logger.info("Loaded %d formulary_id → plan_id mappings", len(mapping))
    return mapping


def _fetch_loaded_plan_ids(cursor) -> set[str]:
    """Return plan_id UUIDs (as text) that already have rows under this audit_source."""
    cursor.execute(
        "SELECT DISTINCT plan_id::text FROM formulary_drug WHERE audit_source = %s",
        (AUDIT_SOURCE,),
    )
    return {row[0] for row in cursor.fetchall()}


def _assert_table_exists(cursor, table_name: str) -> None:
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
        (table_name,),
    )
    if not cursor.fetchone()[0]:
        raise RuntimeError(
            f"Table '{table_name}' not found. Run Alembic migrations first."
        )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_formulary(conn, extract_dir: Path, cfg) -> None:
    """
    Stream the formulary file and batch-insert into formulary_drug.

    Skips any plan already loaded (plan-level idempotency, same pattern as plan_benefits).
    Skips rows whose FORMULARY_ID has no matching plan (logs warning at end).
    """
    cursor = conn.cursor()
    _assert_table_exists(cursor, "formulary_drug")
    _assert_table_exists(cursor, "plans")

    formulary_to_plan = _build_formulary_to_plan_map(cursor)
    if not formulary_to_plan:
        logger.warning(
            "No formulary_id values found in plans table — run plan_puf_ingest.py first"
        )
        return

    already_loaded = _fetch_loaded_plan_ids(cursor)
    logger.info("%d plans already have formulary data, will skip", len(already_loaded))

    formulary_file = _find_formulary_file(extract_dir)
    logger.info("Parsing formulary file: %s", formulary_file)

    batch_size = cfg.formulary.database.batch_size
    source_url = str(cfg.formulary.download_url)

    batch: list[dict] = []
    rows_parsed = rows_loaded = rows_skipped = 0
    unresolved_ids: set[str] = set()
    start = time.monotonic()

    for raw in iter_formulary_rows(formulary_file):
        rows_parsed += 1
        formulary_id = raw.get(_COL_FORMULARY_ID, "").strip()
        plan_uuid = formulary_to_plan.get(formulary_id)

        if plan_uuid is None:
            unresolved_ids.add(formulary_id)
            rows_skipped += 1
            continue

        if plan_uuid in already_loaded:
            rows_skipped += 1
            continue

        ndc_raw = raw.get(_COL_NDC, "").strip()
        ndc = _normalize_ndc(ndc_raw)

        tier_raw = raw.get(_COL_TIER, "").strip()
        tier: Optional[int] = int(tier_raw) if tier_raw.isdigit() else None

        batch.append({
            "plan_id": plan_uuid,
            "drug_name": ndc or f"NDC:{ndc_raw}",  # NOT NULL in schema; NDC is the identifier
            "ndc_code": ndc,
            "formulary_tier": tier,
            "prior_auth_required": _parse_yn(raw.get(_COL_PRIOR_AUTH, "N")),
            "step_therapy_required": _parse_yn(raw.get(_COL_STEP_THERAPY, "N")),
            "quantity_limit": raw.get(_COL_QTY_LIMIT, "").strip() or None,
            "audit_source": AUDIT_SOURCE,
        })

        if len(batch) >= batch_size:
            rows_loaded += _insert_formulary_batch(cursor, batch, source_url)
            batch = []

    if batch:
        rows_loaded += _insert_formulary_batch(cursor, batch, source_url)

    duration = time.monotonic() - start

    if unresolved_ids:
        sample = sorted(unresolved_ids)[:10]
        logger.warning(
            "%d FORMULARY_IDs had no matching plan (first 10: %s)",
            len(unresolved_ids),
            sample,
        )

    logger.info(
        "formulary_ingest complete: rows_parsed=%d rows_loaded=%d rows_skipped=%d duration_seconds=%.1f",
        rows_parsed,
        rows_loaded,
        rows_skipped,
        duration,
    )


def _insert_formulary_batch(cursor, batch: list[dict], source_url: str) -> int:
    if not batch:
        return 0

    placeholders = ", ".join(["(%s, %s, %s, %s, %s, %s, %s, %s)"] * len(batch))
    values: list = []
    for r in batch:
        values.extend([
            r["plan_id"],
            r["drug_name"],
            r["ndc_code"],
            r["formulary_tier"],
            r["prior_auth_required"],
            r["step_therapy_required"],
            r["quantity_limit"],
            r["audit_source"],
        ])

    cursor.execute(
        f"""INSERT INTO formulary_drug
               (plan_id, drug_name, ndc_code, formulary_tier,
                prior_auth_required, step_therapy_required, quantity_limit, audit_source)
            VALUES {placeholders}""",
        values,
    )
    inserted = cursor.rowcount

    for r in batch:
        cursor.execute(
            """INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                "formulary_drug",
                r["ndc_code"] or r["drug_name"],
                AUDIT_SOURCE,
                hashlib.sha256(f"{r['plan_id']}:{r['ndc_code']}".encode()).hexdigest(),
                source_url,
            ),
        )
    return inserted


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="formulary_ingest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    extract_dir = download_formulary_zip(
        cfg.formulary.download_url,
        cfg.formulary.extract_dir,
    )

    logger.info("Connecting to database")
    with psycopg.connect(cfg.formulary.database.connection_string, autocommit=True) as conn:
        load_formulary(conn, extract_dir, cfg)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ICD-10 / HCPCS Code Ingestion: Load CMS diagnosis and procedure code tables into PostgreSQL.

Sources:
  ICD-10-CM FY2026  — flat file with 7-char codes + descriptions
  HCPCS Level II 2026 — annual update file with 5-char codes + descriptions

Note: CPT codes are AMA-paywalled. We use HCPCS Level II only.

Usage:
    python data/ingest/icd_hcpcs_ingest.py
    python data/ingest/icd_hcpcs_ingest.py icd.batch_size=5000
"""

import csv
import hashlib
import io
import logging
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

import psycopg
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CMS source URLs (FY/CY 2026)
# Verify at: https://www.cms.gov/medicare/coding-billing/icd-10-codes
#            https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system
# ---------------------------------------------------------------------------
ICD10_ZIP_URL = (
    "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order-updated.zip"
)
HCPCS_ZIP_URL = (
    "https://www.cms.gov/files/zip/2026-alpha-numeric-hcpcs-file.zip"
)

ICD10_AUDIT_SOURCE = "cms_icd10_2026"
HCPCS_AUDIT_SOURCE = "cms_hcpcs_2026"


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _download_and_open_zip(url: str, label: str) -> zipfile.ZipFile:
    """Download a ZIP from `url` into a temp file and return an open ZipFile handle."""
    logger.info("Downloading %s from %s", label, url)
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)
    except Exception as exc:
        logger.error("Download failed for %s: %s", label, exc)
        raise
    return zipfile.ZipFile(tmp.name, "r")


def _find_zip_member(zf: zipfile.ZipFile, keyword: str) -> str:
    """Return the first member whose name contains `keyword` (case-insensitive)."""
    kw = keyword.lower()
    matches = [n for n in zf.namelist() if kw in n.lower()]
    if not matches:
        raise FileNotFoundError(
            f"No ZIP member matching '{keyword}'. Members: {zf.namelist()}"
        )
    return matches[0]


# ---------------------------------------------------------------------------
# ICD-10-CM parser
# ---------------------------------------------------------------------------

def iter_icd10_codes(zf: zipfile.ZipFile) -> Iterator[dict]:
    """
    Yield {code, long_description, short_description} from ICD-10-CM flat file.

    CMS flat file format: fixed-width OR tab-separated.
    Primary format: one line = 7-char code + TAB/space + description.
    Fallback: try tab-separated with columns (code, description).
    """
    member = _find_zip_member(zf, "code")
    with zf.open(member) as raw:
        content = raw.read().decode("utf-8", errors="replace")

    for line in content.splitlines():
        line = line.rstrip()
        if not line:
            continue

        # Tab-separated: code<TAB>description
        if "\t" in line:
            parts = line.split("\t", 1)
            code = parts[0].strip().upper()
            description = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Fixed-width: first 7 chars = code, rest = description
            if len(line) < 8:
                continue
            code = line[:7].strip().upper()
            description = line[7:].strip()

        # ICD-10 codes are 3-7 chars; skip malformed lines
        if not (3 <= len(code) <= 7) or not code[0].isalpha():
            continue

        yield {
            "code": code,
            "long_description": description or None,
            "short_description": (description[:60] if description else None),
            "audit_source": ICD10_AUDIT_SOURCE,
        }


# ---------------------------------------------------------------------------
# HCPCS Level II parser
# ---------------------------------------------------------------------------

def iter_hcpcs_codes(zf: zipfile.ZipFile) -> Iterator[dict]:
    """
    Yield {code, long_description, short_description} from HCPCS annual update file.

    CMS HCPCS Level II flat file: fixed-width or CSV.
    Code field: 5 chars (alpha-numeric, e.g. A0021, G0008).
    """
    # The HCPCS zip may contain an Excel or a flat text file
    # Try text/csv first; fall back to first .txt member
    txt_members = [n for n in zf.namelist()
                   if n.lower().endswith((".txt", ".csv")) and not n.lower().endswith("readme")]
    if not txt_members:
        raise FileNotFoundError(f"No text/CSV member found. Members: {zf.namelist()}")

    member = txt_members[0]
    with zf.open(member) as raw:
        content = raw.read().decode("utf-8", errors="replace")

    lines = content.splitlines()
    # Detect CSV vs fixed-width: if first non-blank line has commas treat as CSV
    first_data = next((l for l in lines if l.strip()), "")
    is_csv = "," in first_data

    if is_csv:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            # Try common column names used by CMS HCPCS files
            code = (
                row.get("HCPCS_CD") or row.get("CODE") or row.get("hcpc") or ""
            ).strip().upper()
            description = (
                row.get("LONG_DESCRIPTION") or row.get("BETOS_DESC")
                or row.get("DESCRIPTION") or row.get("long_description") or ""
            ).strip()
            short_desc = (
                row.get("SHORT_DESCRIPTION") or row.get("short_description") or ""
            ).strip()
            if not code or len(code) != 5:
                continue
            yield {
                "code": code,
                "long_description": description or None,
                "short_description": (short_desc or description[:60]) or None,
                "audit_source": HCPCS_AUDIT_SOURCE,
            }
    else:
        # Fixed-width: code occupies first 5 characters
        for line in lines:
            if len(line) < 6:
                continue
            code = line[:5].strip().upper()
            description = line[5:].strip()
            if not code or len(code) != 5:
                continue
            yield {
                "code": code,
                "long_description": description or None,
                "short_description": (description[:60] if description else None),
                "audit_source": HCPCS_AUDIT_SOURCE,
            }


# ---------------------------------------------------------------------------
# Database loaders
# ---------------------------------------------------------------------------

def load_icd10(conn, batch_size: int) -> None:
    cursor = conn.cursor()
    _assert_table_exists(cursor, "icd10_codes")

    # Check if already loaded
    cursor.execute("SELECT COUNT(*) FROM icd10_codes")
    if cursor.fetchone()[0] > 0:
        logger.info("icd10_codes already populated, skipping")
        return

    zf = _download_and_open_zip(ICD10_ZIP_URL, "ICD-10-CM FY2026")
    try:
        total = _load_codes(cursor, iter_icd10_codes(zf), "icd10_codes", ICD10_ZIP_URL, batch_size)
    finally:
        zf.close()
    logger.info("ICD-10: %d codes loaded", total)


def load_hcpcs(conn, batch_size: int) -> None:
    cursor = conn.cursor()
    _assert_table_exists(cursor, "hcpcs_codes")

    cursor.execute("SELECT COUNT(*) FROM hcpcs_codes")
    if cursor.fetchone()[0] > 0:
        logger.info("hcpcs_codes already populated, skipping")
        return

    zf = _download_and_open_zip(HCPCS_ZIP_URL, "HCPCS Level II 2026")
    try:
        total = _load_codes(cursor, iter_hcpcs_codes(zf), "hcpcs_codes", HCPCS_ZIP_URL, batch_size)
    finally:
        zf.close()
    logger.info("HCPCS: %d codes loaded", total)


def _load_codes(
    cursor,
    code_iter: Iterator[dict],
    table: str,
    source_url: str,
    batch_size: int,
) -> int:
    batch: list[dict] = []
    total = 0
    for record in code_iter:
        batch.append(record)
        if len(batch) >= batch_size:
            total += _insert_codes_batch(cursor, batch, table, source_url)
            batch = []
    if batch:
        total += _insert_codes_batch(cursor, batch, table, source_url)
    return total


def _insert_codes_batch(cursor, batch: list, table: str, source_url: str) -> int:
    if not batch:
        return 0
    placeholders = ", ".join(["(%s, %s, %s, %s)"] * len(batch))
    values: list = []
    for r in batch:
        values.extend([r["code"], r["long_description"], r["short_description"], r["audit_source"]])

    cursor.execute(
        f"""INSERT INTO {table} (code, long_description, short_description, audit_source)
            VALUES {placeholders}
            ON CONFLICT (code) DO NOTHING""",
        values,
    )
    inserted = cursor.rowcount

    for r in batch:
        cursor.execute(
            """INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                table,
                r["code"],
                r["audit_source"],
                hashlib.sha256(str(r).encode()).hexdigest(),
                source_url,
            ),
        )
    return inserted


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
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="icd_hcpcs_ingest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    conn_string = cfg.icd.database.connection_string
    batch_size = cfg.icd.batch_size

    logger.info("Connecting to database")
    with psycopg.connect(conn_string, autocommit=True) as conn:
        load_icd10(conn, batch_size)
        load_hcpcs(conn, batch_size)

    logger.info("icd_hcpcs_ingest complete")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Exchange Plan PUF Ingestion: Download CMS Marketplace Plan PUFs 2026, load into PostgreSQL.

Downloads the Plan Attributes and Benefits Cost-Sharing PUFs from the CMS Marketplace
public-use files page. Loads into `plans` and `plan_benefits` tables.

Usage:
    python data/ingest/plan_puf_ingest.py
    python data/ingest/plan_puf_ingest.py plan_puf.plan_year=2026
    python data/ingest/plan_puf_ingest.py plan_puf.database.batch_size=1000
"""

import csv
import hashlib
import logging
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import psycopg
from hydra import compose, initialize_config_dir
from omegaconf import DictConfig, OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# CMS PUF column names — Plan Attributes file
_PLAN_COLS = {
    "plan_id": "PlanId",
    "state_code": "StateCode",
    "issuer_id": "IssuerId",
    "plan_marketing_name": "PlanMarketingName",
    "plan_type": "PlanType",
    "metal_level": "MetalLevel",
    "formulary_id": "FormularyId",
    "hsa_eligible": "HSAEligible",
    "market_coverage": "MarketCoverage",
}

# CMS PUF column names — Benefits Cost-Sharing file
_BENEFIT_COLS = {
    "plan_id": "PlanId",
    "benefit_name": "BenefitName",
    "copay_inn": "CopayInnTier1",
    "copay_oon": "CopayOutofNet",
    "coins_inn": "CoinsInnTier1",
    "coins_oon": "CoinsOutofNet",
    "is_covered": "IsCovered",
    "is_subj_ded": "IsSubjToDed",
    "indv_ded_inn": "IndvDeductibleInnTier1",
    "fam_ded_inn": "FamDeductibleInnTier1",
    "indv_ded_oon": "IndvDeductibleOutofNet",
    "fam_ded_oon": "FamDeductibleOutofNet",
    "indv_moop_inn": "IndvMOOPInnTier1",
}

# Benefit name → service category (keyword matching, first match wins)
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Diagnostic Imaging",   ["mri", "ct scan", "x-ray", "imaging", "diagnostic test", "lab"]),
    ("Emergency Services",   ["emergency", "urgent care"]),
    ("Inpatient Services",   ["inpatient", "hospital stay", "surgery"]),
    ("Outpatient Services",  ["outpatient", "ambulatory"]),
    ("Pharmacy",             ["drug", "prescription", "generic", "brand", "specialty drug"]),
    ("Rehabilitation",       ["rehab", "physical therapy", "occupational therapy",
                               "speech therapy", "skilled nursing"]),
    ("Professional Services", ["primary care", "specialist", "physician", "office visit",
                                "preventive", "mental health", "behavioral"]),
]


# ---------------------------------------------------------------------------
# Value parsers
# ---------------------------------------------------------------------------

def _parse_money_cents(value: str) -> Optional[int]:
    """Parse a CMS PUF dollar string to cents.

    "$30" → 3000, "No Charge" → 0, "Not Applicable" → None
    """
    if not value:
        return None
    v = value.strip()
    if v in ("", "Not Applicable", "N/A", "---", "Not Covered"):
        return None
    if v in ("No Charge", "$0", "0"):
        return 0
    try:
        return int(round(float(v.replace("$", "").replace(",", "")) * 100))
    except ValueError:
        return None


def _parse_coinsurance(value: str) -> Optional[float]:
    """Parse a coinsurance string: "20%" → 20.0."""
    if not value:
        return None
    v = value.strip()
    if v in ("", "Not Applicable", "N/A", "No Charge", "Not Covered"):
        return None
    try:
        return float(v.replace("%", "").strip())
    except ValueError:
        return None


def _parse_bool(value: str) -> Optional[bool]:
    v = (value or "").strip().lower()
    if v in ("yes", "true", "1", "y"):
        return True
    if v in ("no", "false", "0", "n"):
        return False
    return None


def _derive_service_category(benefit_name: str) -> str:
    lower = benefit_name.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return category
    return "Other"


def _audit_source(plan_year: int) -> str:
    return f"plan_puf_{plan_year}"


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_puf_zip(url: str, extract_dir: str) -> Path:
    """Download and unzip the PUF archive. Returns extract directory path."""
    extract_path = Path(extract_dir)
    extract_path.mkdir(parents=True, exist_ok=True)

    if list(extract_path.glob("*.csv")):
        logger.info("PUF CSVs already present at %s, skipping download", extract_path)
        return extract_path

    logger.info("Downloading PUF ZIP from %s", url)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "puf.zip"
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as exc:
            logger.error("Download failed: %s", exc)
            raise
        logger.info("Extracting to %s", extract_path)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_path)

    return extract_path


def _find_csv(extract_dir: Path, keyword: str) -> Path:
    """Find a CSV whose filename contains keyword (case-insensitive)."""
    candidates = list(extract_dir.rglob("*.csv"))
    kw = keyword.lower()
    matches = [p for p in candidates if kw in p.name.lower()]
    if not matches:
        available = [p.name for p in candidates]
        raise FileNotFoundError(
            f"No CSV matching '{keyword}' in {extract_dir}. Available: {available}"
        )
    return matches[0]


# ---------------------------------------------------------------------------
# Plans table
# ---------------------------------------------------------------------------

def load_plans(conn, extract_dir: Path, config: DictConfig) -> dict:
    """Load Plan_Attributes CSV → `plans` table. Returns {puf_plan_id: db_uuid}."""
    csv_path = _find_csv(extract_dir, "plan_attr")
    plan_year = config.plan_puf.plan_year
    batch_size = config.plan_puf.database.batch_size

    logger.info("Loading plans from %s", csv_path.name)
    cursor = conn.cursor()
    _assert_table_exists(cursor, "plans")

    batch: list[dict] = []
    total_parsed = total_loaded = 0

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = _parse_plan_row(row, plan_year)
            if record is None:
                continue
            batch.append(record)
            total_parsed += 1
            if len(batch) >= batch_size:
                total_loaded += _insert_plans_batch(cursor, batch)
                batch = []

    if batch:
        total_loaded += _insert_plans_batch(cursor, batch)

    logger.info("Plans: %d parsed, %d newly inserted", total_parsed, total_loaded)
    return _build_puf_to_db_map(cursor, plan_year)


def _parse_plan_row(row: dict, plan_year: int) -> Optional[dict]:
    name = row.get(_PLAN_COLS["plan_marketing_name"], "").strip()
    if not name:
        return None
    return {
        "plan_id_type": "marketplace",
        "plan_marketing_name": name,
        "issuer_name": row.get(_PLAN_COLS["issuer_id"], "").strip() or None,
        "plan_year": plan_year,
        "plan_type": row.get(_PLAN_COLS["plan_type"], "").strip() or None,
        "metal_level": row.get(_PLAN_COLS["metal_level"], "").strip() or None,
        "hsa_eligible": _parse_bool(row.get(_PLAN_COLS["hsa_eligible"], "")),
        "formulary_id": row.get(_PLAN_COLS["formulary_id"], "").strip() or None,
        "service_area_state": (row.get(_PLAN_COLS["state_code"], "").strip().upper()[:2] or None),
        "puf_plan_id": row.get(_PLAN_COLS["plan_id"], "").strip(),
        "audit_source": _audit_source(plan_year),
    }


def _insert_plans_batch(cursor, batch: list) -> int:
    if not batch:
        return 0
    placeholders = ", ".join(
        ["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"] * len(batch)
    )
    values: list = []
    for p in batch:
        values.extend([
            p["plan_id_type"],
            p["plan_marketing_name"],
            p["issuer_name"],
            p["plan_year"],
            p["plan_type"],
            p["metal_level"],
            p["hsa_eligible"],
            p["formulary_id"],
            p["service_area_state"],
            p["audit_source"],
        ])

    cursor.execute(
        f"""INSERT INTO plans
               (plan_id_type, plan_marketing_name, issuer_name, plan_year,
                plan_type, metal_level, hsa_eligible, formulary_id,
                service_area_state, audit_source)
            VALUES {placeholders}
            ON CONFLICT (plan_marketing_name) DO NOTHING""",
        values,
    )
    inserted = cursor.rowcount

    for p in batch:
        cursor.execute(
            """INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                "plans",
                p["puf_plan_id"],
                p["audit_source"],
                hashlib.sha256(str(p).encode()).hexdigest(),
                "https://www.cms.gov/marketplace/resources/data/public-use-files",
            ),
        )
    return inserted


def _build_puf_to_db_map(cursor, plan_year: int) -> dict:
    """Return {puf_plan_id: db_uuid} using audit_log.record_id as the PUF key."""
    cursor.execute(
        """SELECT al.record_id, p.id::text
           FROM audit_log al
           JOIN plans p
             ON p.audit_source = al.source
            AND al.table_name  = 'plans'
           WHERE p.plan_year = %s""",
        (plan_year,),
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# Plan benefits table
# ---------------------------------------------------------------------------

def load_plan_benefits(conn, extract_dir: Path, puf_to_db: dict, config: DictConfig) -> None:
    """Load Benefits_Cost_Sharing CSV → `plan_benefits` table."""
    csv_path = _find_csv(extract_dir, "benefit")
    plan_year = config.plan_puf.plan_year
    batch_size = config.plan_puf.database.batch_size

    logger.info("Loading plan benefits from %s", csv_path.name)
    cursor = conn.cursor()
    _assert_table_exists(cursor, "plan_benefits")

    # Skip plan_ids already loaded for this source (idempotency)
    already_loaded = _fetch_loaded_plan_ids(cursor, _audit_source(plan_year))

    # Group rows by PUF plan_id for atomic per-plan insertion
    grouped: dict[str, list] = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get(_BENEFIT_COLS["plan_id"], "").strip()
            grouped.setdefault(pid, []).append(row)

    unmatched: set = set()
    batch: list[dict] = []
    total_loaded = 0

    for puf_pid, rows in grouped.items():
        db_pid = puf_to_db.get(puf_pid)
        if db_pid is None:
            unmatched.add(puf_pid)
            continue
        if db_pid in already_loaded:
            continue

        for row in rows:
            batch.extend(_parse_benefit_row(row, db_pid, plan_year))
            if len(batch) >= batch_size:
                total_loaded += _insert_benefits_batch(cursor, batch)
                batch = []

    if batch:
        total_loaded += _insert_benefits_batch(cursor, batch)

    if unmatched:
        logger.warning(
            "%d PUF plan IDs unmatched in DB (first 5: %s)",
            len(unmatched), list(unmatched)[:5],
        )
    logger.info("Plan benefits: %d rows inserted", total_loaded)


def _fetch_loaded_plan_ids(cursor, audit_source: str) -> set:
    cursor.execute(
        "SELECT DISTINCT plan_id::text FROM plan_benefits WHERE audit_source = %s",
        (audit_source,),
    )
    return {row[0] for row in cursor.fetchall()}


def _parse_benefit_row(row: dict, db_plan_id: str, plan_year: int) -> list[dict]:
    benefit_name = row.get(_BENEFIT_COLS["benefit_name"], "").strip()
    if not benefit_name:
        return []

    is_covered_raw = row.get(_BENEFIT_COLS["is_covered"], "Covered").strip()
    excluded_reason = None if is_covered_raw.lower() == "covered" else is_covered_raw
    service_category = _derive_service_category(benefit_name)
    audit_src = _audit_source(plan_year)
    requires_prior_auth = _parse_bool(row.get(_BENEFIT_COLS["is_subj_ded"], "")) or False

    indv_ded_inn = _parse_money_cents(row.get(_BENEFIT_COLS["indv_ded_inn"], ""))
    fam_ded_inn  = _parse_money_cents(row.get(_BENEFIT_COLS["fam_ded_inn"], ""))
    indv_ded_oon = _parse_money_cents(row.get(_BENEFIT_COLS["indv_ded_oon"], ""))
    fam_ded_oon  = _parse_money_cents(row.get(_BENEFIT_COLS["fam_ded_oon"], ""))
    indv_moop    = _parse_money_cents(row.get(_BENEFIT_COLS["indv_moop_inn"], ""))

    records = [
        {
            "plan_id": db_plan_id,
            "benefit_name": benefit_name,
            "service_category": service_category,
            "network_type": "In Network",
            "individual_deductible_cents": indv_ded_inn,
            "family_deductible_cents": fam_ded_inn,
            "copay_amount_cents": _parse_money_cents(row.get(_BENEFIT_COLS["copay_inn"], "")),
            "coinsurance_percentage": _parse_coinsurance(row.get(_BENEFIT_COLS["coins_inn"], "")),
            "out_of_pocket_max_cents": indv_moop,
            "benefit_description": None,
            "requires_prior_auth": requires_prior_auth,
            "excluded_reason": excluded_reason,
            "audit_source": audit_src,
        }
    ]

    # Only emit an OON record when at least one OON cost-sharing value is present
    copay_oon = _parse_money_cents(row.get(_BENEFIT_COLS["copay_oon"], ""))
    coins_oon = _parse_coinsurance(row.get(_BENEFIT_COLS["coins_oon"], ""))
    if copay_oon is not None or coins_oon is not None:
        records.append({
            "plan_id": db_plan_id,
            "benefit_name": benefit_name,
            "service_category": service_category,
            "network_type": "Out of Network",
            "individual_deductible_cents": indv_ded_oon,
            "family_deductible_cents": fam_ded_oon,
            "copay_amount_cents": copay_oon,
            "coinsurance_percentage": coins_oon,
            "out_of_pocket_max_cents": None,
            "benefit_description": None,
            "requires_prior_auth": requires_prior_auth,
            "excluded_reason": excluded_reason,
            "audit_source": audit_src,
        })

    return records


def _insert_benefits_batch(cursor, batch: list) -> int:
    if not batch:
        return 0
    placeholders = ", ".join(
        ["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"] * len(batch)
    )
    values: list = []
    for b in batch:
        values.extend([
            b["plan_id"],
            b["benefit_name"],
            b["service_category"],
            b["network_type"],
            b["individual_deductible_cents"],
            b["family_deductible_cents"],
            b["copay_amount_cents"],
            b["coinsurance_percentage"],
            b["out_of_pocket_max_cents"],
            b["benefit_description"],
            b["requires_prior_auth"],
            b["excluded_reason"],
            b["audit_source"],
        ])

    cursor.execute(
        f"""INSERT INTO plan_benefits
               (plan_id, benefit_name, service_category, network_type,
                individual_deductible_cents, family_deductible_cents,
                copay_amount_cents, coinsurance_percentage, out_of_pocket_max_cents,
                benefit_description, requires_prior_auth, excluded_reason,
                audit_source)
            VALUES {placeholders}""",
        values,
    )
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Shared guard
# ---------------------------------------------------------------------------

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
        cfg = compose(config_name="plan_puf_ingest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    extract_dir = download_puf_zip(cfg.plan_puf.download_url, cfg.plan_puf.extract_dir)

    logger.info("Connecting to database")
    with psycopg.connect(cfg.plan_puf.database.connection_string, autocommit=True) as conn:
        puf_to_db = load_plans(conn, extract_dir, cfg)
        load_plan_benefits(conn, extract_dir, puf_to_db, cfg)

    logger.info("plan_puf_ingest complete")


if __name__ == "__main__":
    main()

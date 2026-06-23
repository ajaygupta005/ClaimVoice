#!/usr/bin/env python3
"""Synthetic DEV seed for the structured tables WS-1's public-data ingesters own.

This fills the tables that otherwise only get populated by the heavy Tier-2 CMS
downloads (plans, plan_benefits, formulary_drug, in_network, icd10_codes,
hcpcs_codes) with a small, believable, FK-correct synthetic dataset — enough to
develop and test WS-4 (eligibility), WS-5 (providers in-network), and WS-6 (the
voice agent's grounded tools) with NO external downloads.

It is deliberately the dev counterpart to the real ingesters, not a replacement:
real volume/fidelity still comes from `just data.ingest` (Tier-2).

Plan names and per-metal amounts are imported from ``seed_test_members`` so the
plan rows created here resolve exactly when that script seeds members + X12 stubs.

Run order (Tier-1+):
    alembic upgrade head                              # schema (services/eligibility)
    python data/ingest/npi_ingest.py npi.source_csv=data/raw/nppes_sample.csv
    python data/ingest/seed_dev.py                    # <-- this script (needs providers for in_network)
    python data/ingest/seed_test_members.py           # members + X12 stubs (needs plans from here)

Idempotent: safe to re-run. Each section is gated on its own audit_source rows
(plans/benefits/formulary/in_network) or a UNIQUE(code) conflict (icd10/hcpcs).

Usage:
    python data/ingest/seed_dev.py
    DATABASE_URL=postgresql://user:pass@localhost:5433/claimvoice python data/ingest/seed_dev.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

# Canonical plan definitions (shared with the member seeder so names match exactly).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plan_fixtures import _METALS, _PAYORS, _PLAN_DATA, _PLAN_NAMES  # noqa: E402

# Repo-root-relative log path so importing/running this from any cwd is safe.
_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "ingest.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_PATH, encoding="utf-8"),
    ],
)
_LOG = logging.getLogger(__name__)

_AUDIT_SOURCE = "seed_dev"
_SOURCE_URL = "data/ingest/seed_dev.py"

_ISSUER_NAMES = {
    "aetna": "Aetna",
    "uhc": "UnitedHealthcare",
    "bcbs": "Blue Cross Blue Shield",
    "cigna": "Cigna",
}
# A stable plan_type per payor so the data isn't all identical.
_PLAN_TYPES = {"aetna": "PPO", "uhc": "HMO", "bcbs": "EPO", "cigna": "POS"}

# A few common drugs spanning tiers + utilization-management flags.
_DRUGS: list[dict[str, Any]] = [
    {"drug_name": "Lisinopril", "ndc": "00071022223", "tier": 1, "pa": False, "st": False, "ql": "30 per 30 days"},
    {"drug_name": "Atorvastatin", "ndc": "00071015523", "tier": 1, "pa": False, "st": False, "ql": "30 per 30 days"},
    {"drug_name": "Amoxicillin", "ndc": "00093415578", "tier": 1, "pa": False, "st": False, "ql": None},
    {"drug_name": "Ozempic", "ndc": "00169413212", "tier": 3, "pa": True, "st": True, "ql": "1 per 28 days"},
    {"drug_name": "Humira", "ndc": "00074379902", "tier": 4, "pa": True, "st": True, "ql": "2 per 28 days"},
]

# Diagnosis + procedure reference codes (UNIQUE(code) → naturally idempotent).
_ICD10: list[tuple[str, str, str]] = [
    ("I10", "Essential (primary) hypertension", "Hypertension"),
    ("E11.9", "Type 2 diabetes mellitus without complications", "T2DM"),
    ("J45.909", "Unspecified asthma, uncomplicated", "Asthma"),
    ("M54.5", "Low back pain", "Low back pain"),
    ("M25.561", "Pain in right knee", "Right knee pain"),
]
_HCPCS: list[tuple[str, str, str]] = [
    ("70551", "Magnetic resonance imaging, brain; without contrast", "MRI brain"),
    ("99213", "Office/outpatient visit, established patient", "Office visit"),
    ("G0463", "Hospital outpatient clinic visit", "Outpatient clinic visit"),
    ("J1745", "Injection, infliximab, 10 mg", "Infliximab injection"),
    ("J3490", "Unclassified drugs", "Unclassified drug"),
]
# Procedure codes used to populate in_network rates.
_PROCEDURES = ["70551", "99213", "G0463"]


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://localhost/claimvoice")
    # psycopg.connect wants a libpq URL, not the SQLAlchemy "+psycopg" form.
    return url.replace("postgresql+psycopg://", "postgresql://")


def _data_hash(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def _audit(cur: psycopg.Cursor, table: str, record_id: str, row: dict, note: str = "") -> None:
    cur.execute(
        """
        INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (table, record_id, _AUDIT_SOURCE, _data_hash(row), _SOURCE_URL, note),
    )


def _has_seeded(cur: psycopg.Cursor, table: str) -> bool:
    cur.execute(f"SELECT 1 FROM {table} WHERE audit_source = %s LIMIT 1", (_AUDIT_SOURCE,))
    return cur.fetchone() is not None


def seed_plans(cur: psycopg.Cursor) -> dict[str, str]:
    """Insert the 16 synthetic plans. Returns {plan_marketing_name: plan_uuid}."""
    inserted = 0
    for payor in _PAYORS:
        for metal in _METALS:
            name = _PLAN_NAMES[payor][metal]
            row = {
                "plan_id_type": _PLAN_TYPES[payor],
                "plan_marketing_name": name,
                "issuer_name": _ISSUER_NAMES[payor],
                "plan_year": 2026,
                "plan_type": _PLAN_TYPES[payor],
                "metal_level": metal.capitalize(),
                "hsa_eligible": metal in ("bronze", "silver"),
                "formulary_id": f"FORM-{payor.upper()}-{metal.upper()}",
                "service_area_state": "NY",
                "audit_source": _AUDIT_SOURCE,
            }
            cur.execute(
                """
                INSERT INTO plans
                    (plan_id_type, plan_marketing_name, issuer_name, plan_year, plan_type,
                     metal_level, hsa_eligible, formulary_id, service_area_state, audit_source)
                VALUES
                    (%(plan_id_type)s, %(plan_marketing_name)s, %(issuer_name)s, %(plan_year)s,
                     %(plan_type)s, %(metal_level)s, %(hsa_eligible)s, %(formulary_id)s,
                     %(service_area_state)s, %(audit_source)s)
                ON CONFLICT (plan_marketing_name) DO NOTHING
                """,
                row,
            )
            if cur.rowcount > 0:
                _audit(cur, "plans", name, row)
                inserted += 1

    cur.execute("SELECT plan_marketing_name, id::text FROM plans")
    name_to_id = {n: i for n, i in cur.fetchall()}
    _LOG.info("plans: %d inserted (%d total in table)", inserted, len(name_to_id))
    return name_to_id


def seed_benefits(cur: psycopg.Cursor, name_to_id: dict[str, str]) -> None:
    if _has_seeded(cur, "plan_benefits"):
        _LOG.info("plan_benefits: already seeded (audit_source=%s) — skipping", _AUDIT_SOURCE)
        return
    inserted = 0
    for payor in _PAYORS:
        for metal in _METALS:
            name = _PLAN_NAMES[payor][metal]
            plan_id = name_to_id.get(name)
            if not plan_id:
                continue
            d = _PLAN_DATA[metal]
            ded = d["deductible_individual_cents"]
            oop = d["oop_max_individual_cents"]
            cp = d["copays"]
            benefits = [
                ("Primary Care Visit", "Professional Services", "In Network", cp["primary_care_cents"], 0.0, False),
                ("Specialist Visit", "Professional Services", "In Network", cp["specialist_cents"], 0.0, False),
                ("Emergency Room", "Emergency Services", "In Network", cp["emergency_cents"], 0.0, False),
                ("MRI / Diagnostic Imaging", "Diagnostic Imaging", "In Network", None, 20.0, True),
                ("MRI / Diagnostic Imaging", "Diagnostic Imaging", "Out of Network", None, 40.0, True),
                ("Generic Drugs", "Prescription Drugs", "In Network", 1500, 0.0, False),
            ]
            for bname, cat, net, copay, coins, pa in benefits:
                is_out = net == "Out of Network"
                row = {
                    "plan_id": plan_id,
                    "benefit_name": bname,
                    "service_category": cat,
                    "network_type": net,
                    "individual_deductible_cents": ded * (2 if is_out else 1),
                    "family_deductible_cents": ded * (4 if is_out else 2),
                    "copay_amount_cents": copay,
                    "coinsurance_percentage": coins,
                    "out_of_pocket_max_cents": oop * (2 if is_out else 1),
                    "benefit_description": f"{bname} — {net} ({metal} plan)",
                    "requires_prior_auth": pa,
                    "audit_source": _AUDIT_SOURCE,
                }
                cur.execute(
                    """
                    INSERT INTO plan_benefits
                        (plan_id, benefit_name, service_category, network_type,
                         individual_deductible_cents, family_deductible_cents, copay_amount_cents,
                         coinsurance_percentage, out_of_pocket_max_cents, benefit_description,
                         requires_prior_auth, audit_source)
                    VALUES
                        (%(plan_id)s::uuid, %(benefit_name)s, %(service_category)s, %(network_type)s,
                         %(individual_deductible_cents)s, %(family_deductible_cents)s, %(copay_amount_cents)s,
                         %(coinsurance_percentage)s, %(out_of_pocket_max_cents)s, %(benefit_description)s,
                         %(requires_prior_auth)s, %(audit_source)s)
                    """,
                    row,
                )
                _audit(cur, "plan_benefits", f"{name}:{bname}:{net}", row)
                inserted += 1
    _LOG.info("plan_benefits: %d inserted", inserted)


def seed_formulary(cur: psycopg.Cursor, name_to_id: dict[str, str]) -> None:
    if _has_seeded(cur, "formulary_drug"):
        _LOG.info("formulary_drug: already seeded — skipping")
        return
    inserted = 0
    for plan_name, plan_id in name_to_id.items():
        for drug in _DRUGS:
            row = {
                "plan_id": plan_id,
                "drug_name": drug["drug_name"],
                "ndc_code": drug["ndc"],
                "formulary_tier": drug["tier"],
                "prior_auth_required": drug["pa"],
                "step_therapy_required": drug["st"],
                "quantity_limit": drug["ql"],
                "audit_source": _AUDIT_SOURCE,
            }
            cur.execute(
                """
                INSERT INTO formulary_drug
                    (plan_id, drug_name, ndc_code, formulary_tier, prior_auth_required,
                     step_therapy_required, quantity_limit, audit_source)
                VALUES
                    (%(plan_id)s::uuid, %(drug_name)s, %(ndc_code)s, %(formulary_tier)s,
                     %(prior_auth_required)s, %(step_therapy_required)s, %(quantity_limit)s,
                     %(audit_source)s)
                """,
                row,
            )
            _audit(cur, "formulary_drug", f"{plan_name}:{drug['drug_name']}", row)
            inserted += 1
    _LOG.info("formulary_drug: %d inserted", inserted)


def seed_codes(cur: psycopg.Cursor) -> None:
    icd = 0
    for code, long_desc, short_desc in _ICD10:
        cur.execute(
            """
            INSERT INTO icd10_codes (code, long_description, short_description, audit_source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, long_desc, short_desc, _AUDIT_SOURCE),
        )
        if cur.rowcount > 0:
            _audit(cur, "icd10_codes", code, {"code": code, "d": long_desc})
            icd += 1
    hc = 0
    for code, long_desc, short_desc in _HCPCS:
        cur.execute(
            """
            INSERT INTO hcpcs_codes (code, long_description, short_description, audit_source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, long_desc, short_desc, _AUDIT_SOURCE),
        )
        if cur.rowcount > 0:
            _audit(cur, "hcpcs_codes", code, {"code": code, "d": long_desc})
            hc += 1
    _LOG.info("icd10_codes: %d inserted · hcpcs_codes: %d inserted", icd, hc)


def seed_in_network(cur: psycopg.Cursor, name_to_id: dict[str, str]) -> None:
    """Link a sample of providers to each plan with negotiated rates.

    Requires providers to exist (load them first via npi_ingest). If the
    providers table is empty this is skipped with a warning so it can be re-run.
    """
    if _has_seeded(cur, "in_network"):
        _LOG.info("in_network: already seeded — skipping")
        return
    cur.execute("SELECT npi FROM providers ORDER BY npi LIMIT 25")
    npis = [r[0] for r in cur.fetchall()]
    if not npis:
        _LOG.warning(
            "in_network: providers table is empty — skipping. Load providers first "
            "(python data/ingest/npi_ingest.py npi.source_csv=data/raw/nppes_sample.csv), then re-run."
        )
        return
    inserted = 0
    eff, exp = date(2026, 1, 1), date(2026, 12, 31)
    for plan_name, plan_id in name_to_id.items():
        # Make ~10 providers in-network per plan, each with a few procedure rates.
        for npi in npis[:10]:
            for i, proc in enumerate(_PROCEDURES):
                row = {
                    "plan_id": plan_id,
                    "provider_npi": npi,
                    "procedure_code": proc,
                    "negotiated_rate_cents": 80000 + i * 40000,  # $800 / $1200 / $1600
                    "effective_date": eff,
                    "expiry_date": exp,
                    "audit_source": _AUDIT_SOURCE,
                }
                cur.execute(
                    """
                    INSERT INTO in_network
                        (plan_id, provider_npi, procedure_code, negotiated_rate_cents,
                         effective_date, expiry_date, audit_source)
                    VALUES
                        (%(plan_id)s::uuid, %(provider_npi)s, %(procedure_code)s,
                         %(negotiated_rate_cents)s, %(effective_date)s, %(expiry_date)s, %(audit_source)s)
                    """,
                    row,
                )
                _audit(cur, "in_network", f"{plan_name}:{npi}:{proc}", row)
                inserted += 1
    _LOG.info("in_network: %d inserted", inserted)


def _check_schema(cur: psycopg.Cursor) -> None:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'plans' AND table_schema = 'public'"
    )
    if not cur.fetchone():
        raise RuntimeError("plans table not found — run Alembic migrations first (alembic upgrade head)")


def main() -> None:
    url = _database_url()
    _LOG.info("seed_dev: connecting to %s", url)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            _check_schema(cur)
            name_to_id = seed_plans(cur)
            seed_benefits(cur, name_to_id)
            seed_formulary(cur, name_to_id)
            seed_codes(cur)
            seed_in_network(cur, name_to_id)
        conn.commit()
    _LOG.info("seed_dev: done")


if __name__ == "__main__":
    main()

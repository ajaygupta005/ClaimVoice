#!/usr/bin/env python3
"""Seed the canonical demo member + plan used by the agent-pipeline golden cases.

The voice agent defaults to member ``CVX-0042-MT`` (services/voice-agent .../schemas/
agent_respond.py), and eval/datasets/agent_pipeline_cases.json hardcodes $30 PCP copay,
$75 urgent-care copay, $1,500 deductible, lisinopril Tier 1, Humira prior-auth. The
generic dev seed does not match those, so DB-backed WS-4 tools would break the eval.
This script seeds a demo plan whose In-Network benefits reproduce the golden values and
a demo member on that plan, plus in-network links to the providers nearest Midtown
Manhattan (so /providers/near?inNetworkOnly returns real results).

Idempotent (audit_source='seed_demo'); safe to re-run. Requires the schema to exist and
providers to be loaded first (run after `seed_dev.py` / `npi_ingest.py`).

Usage:
    python data/ingest/seed_demo_member.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from datetime import date
from pathlib import Path
from typing import Any

import psycopg

_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "ingest.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_LOG_PATH, encoding="utf-8")],
)
_LOG = logging.getLogger(__name__)

_AUDIT = "seed_demo"
_SOURCE_URL = "data/ingest/seed_demo_member.py"
_PLAN_NAME = "ClaimVoice Demo PPO"
_MEMBER_ID = "CVX-0042-MT"

# Plan-level amounts (integer cents) — match the agent-pipeline golden values.
_DED = 150000   # $1,500 individual deductible
_OOP = 500000   # $5,000 out-of-pocket max

# In-Network benefits: (benefit_name, service_category, copay_cents, coinsurance%, prior_auth)
_BENEFITS: list[tuple[str, str, int | None, float | None, bool]] = [
    ("Primary Care Visit", "Professional Services", 3000, None, False),   # $30
    ("Urgent Care", "Urgent Care", 7500, None, False),                    # $75
    ("Specialist Visit", "Professional Services", 5000, None, False),      # $50
    ("Emergency Room", "Emergency Services", 25000, None, False),          # $250
    ("MRI / Diagnostic Imaging", "Diagnostic Imaging", None, 20.0, True),  # 20% + PA
]

# Formulary: (drug_name, ndc, tier, prior_auth, step_therapy)
_DRUGS: list[tuple[str, str, int, bool, bool]] = [
    ("Lisinopril", "00071022223", 1, False, False),
    ("Humira", "00074379902", 4, True, True),
]

_TARGET_LAT, _TARGET_LNG = 40.7580, -73.9855  # Midtown Manhattan
_PROCEDURES = ["99213", "70551", "G0463"]      # office visit, MRI brain, outpatient
_IN_NETWORK_PROVIDERS = 20                      # link the N nearest providers


def _db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://localhost/claimvoice").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def _hash(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def _audit(cur: psycopg.Cursor, table: str, rec: str, row: dict) -> None:
    cur.execute(
        "INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (table, rec, _AUDIT, _hash(row), _SOURCE_URL, ""),
    )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_wkt_point(wkt: str) -> tuple[float, float] | None:
    """'POINT(lng lat)' -> (lat, lng); None if unparseable."""
    try:
        inner = wkt[wkt.index("(") + 1 : wkt.index(")")]
        lng_s, lat_s = inner.split()
        return float(lat_s), float(lng_s)
    except (ValueError, AttributeError):
        return None


def _has_rows(cur: psycopg.Cursor, table: str, plan_id: str) -> bool:
    cur.execute(
        f"SELECT 1 FROM {table} WHERE plan_id = %s::uuid AND audit_source = %s LIMIT 1",
        (plan_id, _AUDIT),
    )
    return cur.fetchone() is not None


def seed(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'plans'")
        if not cur.fetchone():
            raise RuntimeError("plans table not found — run `alembic upgrade head` first")

        # Plan (idempotent on unique plan_marketing_name)
        plan_row: dict[str, Any] = {"name": _PLAN_NAME}
        cur.execute(
            """
            INSERT INTO plans (plan_id_type, plan_marketing_name, issuer_name, plan_year,
                               plan_type, metal_level, hsa_eligible, formulary_id,
                               service_area_state, audit_source)
            VALUES ('PPO', %s, 'ClaimVoice', 2026, 'PPO', 'Gold', false, 'FORM-DEMO', 'NY', %s)
            ON CONFLICT (plan_marketing_name) DO NOTHING
            """,
            (_PLAN_NAME, _AUDIT),
        )
        if cur.rowcount > 0:
            _audit(cur, "plans", _PLAN_NAME, plan_row)
        cur.execute("SELECT id::text FROM plans WHERE plan_marketing_name = %s", (_PLAN_NAME,))
        plan_id = cur.fetchone()[0]

        # Benefits
        if not _has_rows(cur, "plan_benefits", plan_id):
            for name, cat, copay, coins, pa in _BENEFITS:
                cur.execute(
                    """
                    INSERT INTO plan_benefits
                        (plan_id, benefit_name, service_category, network_type,
                         individual_deductible_cents, family_deductible_cents, copay_amount_cents,
                         coinsurance_percentage, out_of_pocket_max_cents, benefit_description,
                         requires_prior_auth, audit_source)
                    VALUES (%s::uuid, %s, %s, 'In Network', %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (plan_id, name, cat, _DED, _DED * 2, copay, coins, _OOP,
                     f"{name} — In Network (demo plan)", pa, _AUDIT),
                )
                _audit(cur, "plan_benefits", f"{_PLAN_NAME}:{name}", {"benefit": name})
            _LOG.info("demo benefits inserted: %d", len(_BENEFITS))
        else:
            _LOG.info("demo benefits already present — skipping")

        # Formulary
        if not _has_rows(cur, "formulary_drug", plan_id):
            for name, ndc, tier, pa, st in _DRUGS:
                cur.execute(
                    """
                    INSERT INTO formulary_drug
                        (plan_id, drug_name, ndc_code, formulary_tier, prior_auth_required,
                         step_therapy_required, quantity_limit, audit_source)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (plan_id, name, ndc, tier, pa, st, "30 per 30 days", _AUDIT),
                )
                _audit(cur, "formulary_drug", f"{_PLAN_NAME}:{name}", {"drug": name})
            _LOG.info("demo formulary inserted: %d", len(_DRUGS))
        else:
            _LOG.info("demo formulary already present — skipping")

        # Member (idempotent on unique member_id)
        cur.execute(
            """
            INSERT INTO members (member_id, first_name, last_name, dob, gender, plan_id,
                                 enrollment_date, eligibility_status, deductible_ytd_cents,
                                 oop_ytd_cents, audit_source)
            VALUES (%s, 'Demo', 'Member', '1985-04-02', 'F', %s::uuid, '2026-01-01',
                    'active', 45000, 120000, %s)
            ON CONFLICT (member_id) DO NOTHING
            """,
            (_MEMBER_ID, plan_id, _AUDIT),
        )
        if cur.rowcount > 0:
            _audit(cur, "members", _MEMBER_ID, {"member": _MEMBER_ID})
            _LOG.info("demo member %s inserted", _MEMBER_ID)
        else:
            _LOG.info("demo member %s already present — skipping", _MEMBER_ID)

        # In-network links: the N providers nearest Midtown Manhattan
        if not _has_rows(cur, "in_network", plan_id):
            cur.execute("SELECT npi, location FROM providers WHERE location IS NOT NULL")
            ranked: list[tuple[float, str]] = []
            for npi, loc in cur.fetchall():
                pt = _parse_wkt_point(loc)
                if pt:
                    ranked.append((_haversine_km(_TARGET_LAT, _TARGET_LNG, pt[0], pt[1]), npi))
            ranked.sort(key=lambda t: t[0])
            nearest = [npi for _, npi in ranked[:_IN_NETWORK_PROVIDERS]]
            eff, exp = date(2026, 1, 1), date(2026, 12, 31)
            n = 0
            for npi in nearest:
                for i, proc in enumerate(_PROCEDURES):
                    cur.execute(
                        """
                        INSERT INTO in_network (plan_id, provider_npi, procedure_code,
                                                negotiated_rate_cents, effective_date,
                                                expiry_date, audit_source)
                        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s)
                        """,
                        (plan_id, npi, proc, 80000 + i * 40000, eff, exp, _AUDIT),
                    )
                    n += 1
            _LOG.info("demo in_network links: %d rows across %d providers", n, len(nearest))
        else:
            _LOG.info("demo in_network already present — skipping")

    conn.commit()
    _LOG.info("seed_demo: done plan_id=%s member=%s", plan_id, _MEMBER_ID)


def main() -> None:
    url = _db_url()
    _LOG.info("seed_demo: connecting to %s", url)
    with psycopg.connect(url) as conn:
        seed(conn)


if __name__ == "__main__":
    main()

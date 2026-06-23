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
_DEMO_SBC_SOURCE_FILE = "claimvoice_demo_sbc_seeded.txt"
_CARDIOLOGY_SEED_SQL = Path(__file__).with_name("seed_cardiology.sql")

# Local-demo SBC snippets. These mirror the structured seed rows above so RAG
# evidence, guard facts, and DB-backed tools agree during the demo.
_DEMO_SBC_CHUNKS: list[tuple[str, str]] = [
    (
        "Medical Benefits",
        (
            "ClaimVoice Demo PPO, shown in the demo UI as Silver PPO 4500, covers "
            "MRI and diagnostic imaging when medically necessary. In-network MRI "
            "and diagnostic imaging are subject to 20% coinsurance after applicable "
            "cost sharing, and prior authorization is required before scheduling."
        ),
    ),
    (
        "Office and Urgent Care Visits",
        (
            "ClaimVoice Demo PPO in-network cost sharing: primary care office visits "
            "have a $30 copay, specialist visits have a $50 copay, urgent care has a "
            "$75 copay, and emergency room services have a $250 copay."
        ),
    ),
    (
        "Prescription Drug Coverage",
        (
            "The ClaimVoice Demo PPO formulary includes Lisinopril as a Tier 1 drug "
            "without prior authorization or step therapy. Humira is a Tier 4 drug and "
            "requires both prior authorization and step therapy."
        ),
    ),
]


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


def _sbc_chunks_table_exists(cur: psycopg.Cursor) -> bool:
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'sbc_chunks'")
    return cur.fetchone() is not None


def _seed_demo_sbc_chunks(cur: psycopg.Cursor, plan_id: str) -> None:
    """Seed local-demo RAG chunks for the canonical demo plan.

    The normal SBC ingest path depends on external PDFs. That is appropriate for
    real data, but brittle for a local demo because payer URLs often return HTML,
    login pages, or moved documents. These chunks provide a deterministic demo
    fallback while still using real Voyage embeddings and the same `sbc_chunks`
    retrieval path as production.
    """
    if not _sbc_chunks_table_exists(cur):
        _LOG.warning("sbc_chunks table not found — skipping demo SBC chunk seed")
        return

    cur.execute(
        """
        SELECT count(*)
        FROM sbc_chunks
        WHERE plan_id = %s::uuid AND source_file = %s
        """,
        (plan_id, _DEMO_SBC_SOURCE_FILE),
    )
    existing = int(cur.fetchone()[0])
    if existing >= len(_DEMO_SBC_CHUNKS):
        _LOG.info("demo SBC chunks already present — skipping")
        return

    voyage_api_key = os.environ.get("VOYAGE_API_KEY", "").strip()
    if not voyage_api_key:
        _LOG.warning("VOYAGE_API_KEY is not set — skipping demo SBC chunk seed")
        return

    try:
        import voyageai
    except ImportError:
        _LOG.warning("voyageai package not installed — skipping demo SBC chunk seed")
        return

    texts = [text for _, text in _DEMO_SBC_CHUNKS]
    model = os.environ.get("VOYAGE_MODEL", "voyage-4-large")
    try:
        client = voyageai.Client(api_key=voyage_api_key)
        embeddings = client.embed(texts, model=model, input_type="document").embeddings
    except Exception as exc:
        _LOG.warning("Voyage embedding failed — skipping demo SBC chunk seed: %s", exc)
        return

    cur.executemany(
        """
        INSERT INTO sbc_chunks
            (plan_id, source_file, section_name, chunk_index, chunk_text, embedding, page_number)
        VALUES
            (%s::uuid, %s, %s, %s, %s, %s::vector, %s)
        ON CONFLICT (plan_id, source_file, section_name, chunk_index)
        DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            embedding = EXCLUDED.embedding,
            page_number = EXCLUDED.page_number
        """,
        [
            (
                plan_id,
                _DEMO_SBC_SOURCE_FILE,
                section_name,
                idx,
                text,
                str(embedding),
                idx + 1,
            )
            for idx, ((section_name, text), embedding) in enumerate(
                zip(_DEMO_SBC_CHUNKS, embeddings)
            )
        ],
    )
    _audit(
        cur,
        "sbc_chunks",
        f"{_PLAN_NAME}:{_DEMO_SBC_SOURCE_FILE}",
        {"source_file": _DEMO_SBC_SOURCE_FILE, "chunks": len(_DEMO_SBC_CHUNKS)},
    )
    _LOG.info("demo SBC chunks inserted/updated: %d", len(_DEMO_SBC_CHUNKS))


def _seed_cardiology_providers(cur: psycopg.Cursor) -> None:
    """Ensure the canonical cardiology demo query has NY providers to return."""
    if not _CARDIOLOGY_SEED_SQL.exists():
        _LOG.warning("cardiology seed file missing: %s", _CARDIOLOGY_SEED_SQL)
        return
    cur.execute(_CARDIOLOGY_SEED_SQL.read_text(encoding="utf-8"))
    _LOG.info("cardiology demo providers ensured from %s", _CARDIOLOGY_SEED_SQL.name)


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
            VALUES ('PPO', %s, 'ClaimVoice', 2026, 'PPO', 'Silver', false, 'FORM-DEMO', 'NY', %s)
            ON CONFLICT (plan_marketing_name) DO UPDATE SET
                metal_level = EXCLUDED.metal_level,
                issuer_name = EXCLUDED.issuer_name,
                plan_type = EXCLUDED.plan_type,
                service_area_state = EXCLUDED.service_area_state,
                audit_source = EXCLUDED.audit_source
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

        _seed_demo_sbc_chunks(cur, plan_id)

        # Member (idempotent on unique member_id)
        cur.execute(
            """
            INSERT INTO members (member_id, first_name, last_name, dob, gender, plan_id,
                                 enrollment_date, eligibility_status, deductible_ytd_cents,
                                 oop_ytd_cents, audit_source)
            VALUES (%s, 'Maya', 'Thompson', '1985-04-02', 'F', %s::uuid, '2026-01-01',
                    'active', 45000, 120000, %s)
            ON CONFLICT (member_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                gender = EXCLUDED.gender,
                plan_id = EXCLUDED.plan_id,
                eligibility_status = EXCLUDED.eligibility_status,
                deductible_ytd_cents = EXCLUDED.deductible_ytd_cents,
                oop_ytd_cents = EXCLUDED.oop_ytd_cents,
                audit_source = EXCLUDED.audit_source
            """,
            (_MEMBER_ID, plan_id, _AUDIT),
        )
        if cur.rowcount > 0:
            _audit(cur, "members", _MEMBER_ID, {"member": _MEMBER_ID})
            _LOG.info("demo member %s inserted", _MEMBER_ID)
        else:
            _LOG.info("demo member %s already present — skipping", _MEMBER_ID)

        # In-network links: the N providers nearest Midtown Manhattan
        _seed_cardiology_providers(cur)
        if not _has_rows(cur, "in_network", plan_id):
            cur.execute(
                "SELECT npi, ST_AsText(location::geometry) AS location "
                "FROM providers WHERE location IS NOT NULL"
            )
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

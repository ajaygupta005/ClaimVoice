#!/usr/bin/env python3
"""Seed 30 reproducible test members into the members table.

Writes matching X12 271 JSON stubs to data/stubs/eligibility_271/.
Fixed seed 42 ensures identical output on every run.

Usage:
    python data/ingest/seed_test_members.py
    python data/ingest/seed_test_members.py --stubs-only  # write stubs without touching DB
"""

import argparse
import hashlib
import json
import logging
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from faker import Faker

from _plan_fixtures import _METALS, _PAYORS, _PLAN_DATA, _PLAN_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/ingest.log", encoding="utf-8"),
    ],
)
_LOG = logging.getLogger(__name__)

_AUDIT_SOURCE = "seed_test_members"
_MEMBER_COUNT = 30
_STUBS_DIR = Path("data/stubs/eligibility_271")

# Eligibility state distribution — 24 active / 4 inactive / 2 suspended
_STATUSES = ["active"] * 24 + ["inactive"] * 4 + ["suspended"] * 2

# Plan definitions (_PAYORS, _METALS, _PLAN_DATA, _PLAN_NAMES) are imported from
# _plan_fixtures so the dev seed and member seed share one source of truth.


def _member_id(idx: int) -> str:
    return f"M{100000001 + idx:09d}"


def _ytd_amounts(idx: int, metal: str) -> tuple[int, int]:
    """Return (deductible_ytd_cents, oop_ytd_cents) based on scenario bucket."""
    ded = _PLAN_DATA[metal]["deductible_individual_cents"]
    oop = _PLAN_DATA[metal]["oop_max_individual_cents"]
    status = _STATUSES[idx]

    if status != "active":
        # inactive/suspended: partial deductible progress
        return int(ded * 0.25), int(oop * 0.1)

    bucket = idx % 3  # 0=not-met, 1=partial, 2=met
    if bucket == 0:
        return 0, 0
    elif bucket == 1:
        partial = int(ded * 0.40)
        return partial, partial
    else:
        # Last active member in a "met" group: OOP-max met
        if idx == 23:
            return ded, oop
        return ded, int(oop * 0.65)


def _termination_date(idx: int) -> str | None:
    if _STATUSES[idx] == "inactive":
        # Stagger termination dates across 2025
        month = 3 + (idx - 24) * 3
        return f"2025-{month:02d}-01"
    return None


def _enrollment_date(fake: Faker, idx: int) -> str:
    year = 2024 if idx < 10 else 2025 if idx < 20 else 2026
    return f"{year}-01-01"


def build_stub(idx: int, fake: Faker) -> dict[str, Any]:
    mid = _member_id(idx)
    payor = _PAYORS[idx % 4]
    metal = _METALS[idx % 4]
    plan_data = _PLAN_DATA[metal]
    plan_name = _PLAN_NAMES[payor][metal]
    status = _STATUSES[idx]
    deductible_ytd, oop_ytd = _ytd_amounts(idx, metal)
    term_date = _termination_date(idx)

    return {
        "member_id": mid,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "dob": fake.date_of_birth(minimum_age=22, maximum_age=70).isoformat(),
        "gender": random.choice(["M", "F"]),
        "eligibility_status": status,
        "plan_name": plan_name,
        "payor": payor,
        "metal_level": metal,
        "deductible_individual_cents": plan_data["deductible_individual_cents"],
        "deductible_ytd_cents": deductible_ytd,
        "oop_max_individual_cents": plan_data["oop_max_individual_cents"],
        "oop_ytd_cents": oop_ytd,
        "effective_date": "2026-01-01",
        "termination_date": term_date,
        "copays": plan_data["copays"],
    }


def _x12_stub(stub: dict[str, Any]) -> dict[str, Any]:
    """Extract the subset written to the stub JSON (X12 271 simulation fields)."""
    return {
        "member_id": stub["member_id"],
        "eligibility_status": stub["eligibility_status"],
        "plan_name": stub["plan_name"],
        "deductible_individual_cents": stub["deductible_individual_cents"],
        "deductible_ytd_cents": stub["deductible_ytd_cents"],
        "oop_max_individual_cents": stub["oop_max_individual_cents"],
        "oop_ytd_cents": stub["oop_ytd_cents"],
        "effective_date": stub["effective_date"],
        "termination_date": stub["termination_date"],
        "copays": stub["copays"],
    }


def write_stubs(stubs: list[dict[str, Any]], stubs_dir: Path) -> int:
    stubs_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for stub in stubs:
        dest = stubs_dir / f"{stub['member_id']}.json"
        x12 = _x12_stub(stub)
        dest.write_text(json.dumps(x12, indent=2) + "\n", encoding="utf-8")
        written += 1
    _LOG.info("stubs written", extra={"count": written, "dir": str(stubs_dir)})
    return written


def _resolve_plan_ids(cursor: psycopg.Cursor, stubs: list[dict]) -> dict[str, str]:
    """Return {plan_name: plan_uuid} for the plan names we need."""
    names_needed = list({s["plan_name"] for s in stubs})
    placeholders = ",".join(["%s"] * len(names_needed))
    cursor.execute(
        f"SELECT id::text, plan_marketing_name FROM plans WHERE plan_marketing_name IN ({placeholders})",
        names_needed,
    )
    return {row[1]: row[0] for row in cursor.fetchall()}


def _check_table_exists(cursor: psycopg.Cursor) -> None:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'members' AND table_schema = 'public'"
    )
    if not cursor.fetchone():
        raise RuntimeError("members table not found — run Alembic migrations first")


def _already_seeded(cursor: psycopg.Cursor) -> bool:
    cursor.execute("SELECT COUNT(*) FROM members WHERE audit_source = %s", (_AUDIT_SOURCE,))
    count = cursor.fetchone()[0]
    if count > 0:
        _LOG.info("already seeded: %d members found with audit_source=%s — skipping DB insert", count, _AUDIT_SOURCE)
        return True
    return False


def _data_hash(row: dict) -> str:
    payload = json.dumps(row, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def seed_members(conn: psycopg.Connection, stubs: list[dict], plan_id_map: dict[str, str]) -> int:
    inserted = 0
    unresolved_plans: set[str] = set()

    with conn.cursor() as cur:
        _check_table_exists(cur)

        if _already_seeded(cur):
            return 0

        for stub in stubs:
            plan_uuid = plan_id_map.get(stub["plan_name"])
            if plan_uuid is None:
                unresolved_plans.add(stub["plan_name"])
                continue

            row = {
                "member_id": stub["member_id"],
                "first_name": stub["first_name"],
                "last_name": stub["last_name"],
                "dob": stub["dob"],
                "gender": stub["gender"],
                "plan_id": plan_uuid,
                "enrollment_date": stub["effective_date"],
                "eligibility_status": stub["eligibility_status"],
                "deductible_ytd_cents": stub["deductible_ytd_cents"],
                "oop_ytd_cents": stub["oop_ytd_cents"],
                "audit_source": _AUDIT_SOURCE,
            }
            cur.execute(
                """
                INSERT INTO members
                    (member_id, first_name, last_name, dob, gender, plan_id,
                     enrollment_date, eligibility_status,
                     deductible_ytd_cents, oop_ytd_cents, audit_source)
                VALUES
                    (%(member_id)s, %(first_name)s, %(last_name)s, %(dob)s, %(gender)s,
                     %(plan_id)s::uuid, %(enrollment_date)s, %(eligibility_status)s,
                     %(deductible_ytd_cents)s, %(oop_ytd_cents)s, %(audit_source)s)
                ON CONFLICT (member_id) DO NOTHING
                """,
                row,
            )
            if cur.rowcount > 0:
                cur.execute(
                    """
                    INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "members",
                        stub["member_id"],
                        _AUDIT_SOURCE,
                        _data_hash(row),
                        "seed_test_members.py",
                        f"eligibility_status={stub['eligibility_status']}",
                    ),
                )
                inserted += 1

    if unresolved_plans:
        _LOG.warning(
            "skipped %d members: plan names not found in plans table: %s",
            len(unresolved_plans),
            sorted(unresolved_plans),
        )

    _LOG.info(
        "members seeded: inserted=%d skipped=%d",
        inserted,
        len(stubs) - inserted,
    )
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql://localhost/claimvoice"),
    )
    parser.add_argument(
        "--stubs-dir",
        default=str(_STUBS_DIR),
        help="Directory to write X12 271 stub JSON files",
    )
    parser.add_argument(
        "--stubs-only",
        action="store_true",
        help="Write stub files without connecting to the database",
    )
    args = parser.parse_args()

    random.seed(42)
    fake = Faker("en_US")
    Faker.seed(42)

    stubs = [build_stub(idx, fake) for idx in range(_MEMBER_COUNT)]

    stubs_dir = Path(args.stubs_dir)
    write_stubs(stubs, stubs_dir)

    if args.stubs_only:
        _LOG.info("--stubs-only: skipping DB insert")
        return

    t0 = datetime.now()
    try:
        with psycopg.connect(args.database_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                plan_id_map = _resolve_plan_ids(cur, stubs)

            if not plan_id_map:
                _LOG.warning(
                    "No matching plans found in DB — stub files written but no DB rows inserted. "
                    "Run plan_puf_ingest.py first, then re-run this script."
                )
                sys.exit(0)

            _LOG.info("resolved %d / %d plan names from DB", len(plan_id_map), len({s["plan_name"] for s in stubs}))
            inserted = seed_members(conn, stubs, plan_id_map)
    except psycopg.OperationalError as exc:
        _LOG.error("DB connection failed: %s", exc)
        _LOG.info("Stub files were written. Re-run without --stubs-only once the DB is available.")
        sys.exit(1)

    duration = (datetime.now() - t0).total_seconds()
    status_counts = {}
    for s in stubs:
        status_counts[s["eligibility_status"]] = status_counts.get(s["eligibility_status"], 0) + 1

    _LOG.info(
        "seed complete: rows_loaded=%d duration_seconds=%.2f status_distribution=%s",
        inserted,
        duration,
        status_counts,
    )


if __name__ == "__main__":
    main()

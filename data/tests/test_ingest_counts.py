"""Row-count assertions for the WS-1 CI data-quality gate.

Run after a full `dvc repro` against a populated database:

    DATABASE_URL=postgresql://localhost/claimvoice pytest data/tests/test_ingest_counts.py -v

All DB-backed tests are skipped automatically when DATABASE_URL is not set,
so offline CI (unit-test only) passes without a live Postgres instance.
File-based tests (synthetic cards, stubs) always run.
"""

import os
from pathlib import Path

import psycopg
import pytest

_DB_URL = os.environ.get("DATABASE_URL")
_NEEDS_DB = pytest.mark.skipif(not _DB_URL, reason="DATABASE_URL not set — skipping DB count checks")

_REPO_ROOT = Path(__file__).parent.parent.parent
_DATA_DIR = _REPO_ROOT / "data"


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    """Open a read-only connection to the test database."""
    with psycopg.connect(_DB_URL, autocommit=True) as conn:
        yield conn


def _count(conn: psycopg.Connection, table: str, where: str = "") -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} {where}")  # noqa: S608
        return cur.fetchone()[0]


# ── DB-backed row count tests ────────────────────────────────────────────────

@_NEEDS_DB
def test_providers_row_count(db):
    """NPI ingest: NY-metro providers loaded into PostGIS."""
    count = _count(db, "providers")
    assert count >= 40_000, f"providers: expected >= 40,000, got {count:,}"


@_NEEDS_DB
def test_plans_row_count(db):
    """Plan PUF ingest: Exchange plans loaded."""
    count = _count(db, "plans")
    assert count >= 500, f"plans: expected >= 500, got {count:,}"


@_NEEDS_DB
def test_plan_benefits_row_count(db):
    """Plan PUF ingest: benefit rows loaded."""
    count = _count(db, "plan_benefits")
    assert count >= 5_000, f"plan_benefits: expected >= 5,000, got {count:,}"


@_NEEDS_DB
def test_plan_benefits_no_float_money(db):
    """All monetary columns in plan_benefits are integer cents (BIGINT), not float."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'plan_benefits'
              AND column_name IN (
                  'individual_deductible_cents', 'family_deductible_cents',
                  'copay_amount_cents', 'out_of_pocket_max_cents'
              )
            """
        )
        rows = cur.fetchall()
    for col, dtype in rows:
        assert dtype == "bigint", f"{col} must be bigint, got {dtype}"


@_NEEDS_DB
def test_formulary_drug_row_count(db):
    """Formulary ingest: Part D CY2026 drug entries loaded."""
    count = _count(db, "formulary_drug")
    assert count >= 10_000, f"formulary_drug: expected >= 10,000, got {count:,}"


@_NEEDS_DB
def test_formulary_tier_distribution(db):
    """Formulary should have all 4 tier levels (generic → specialty)."""
    with db.cursor() as cur:
        cur.execute("SELECT DISTINCT formulary_tier FROM formulary_drug WHERE formulary_tier IS NOT NULL")
        tiers = {row[0] for row in cur.fetchall()}
    assert len(tiers) >= 4, f"formulary_drug: expected 4 distinct tiers, got {sorted(tiers)}"


@_NEEDS_DB
def test_icd10_codes_row_count(db):
    """ICD-10-CM FY2026 code table loaded."""
    count = _count(db, "icd10_codes")
    assert count >= 70_000, f"icd10_codes: expected >= 70,000, got {count:,}"


@_NEEDS_DB
def test_hcpcs_codes_row_count(db):
    """HCPCS Level II code table loaded."""
    count = _count(db, "hcpcs_codes")
    assert count >= 5_000, f"hcpcs_codes: expected >= 5,000, got {count:,}"


@_NEEDS_DB
def test_members_row_count(db):
    """Seed: exactly 30 test members in the members table."""
    count = _count(db, "members", "WHERE audit_source = 'seed_test_members'")
    assert count == 30, f"members: expected 30, got {count}"


@_NEEDS_DB
def test_members_eligibility_distribution(db):
    """Seed: 24 active / 4 inactive / 2 suspended."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT eligibility_status, COUNT(*)
            FROM members
            WHERE audit_source = 'seed_test_members'
            GROUP BY eligibility_status
            """
        )
        dist = {row[0]: row[1] for row in cur.fetchall()}

    assert dist.get("active", 0) == 24, f"active members: expected 24, got {dist.get('active', 0)}"
    assert dist.get("inactive", 0) == 4, f"inactive members: expected 4, got {dist.get('inactive', 0)}"
    assert dist.get("suspended", 0) == 2, f"suspended members: expected 2, got {dist.get('suspended', 0)}"


@_NEEDS_DB
def test_providers_with_quality_rating(db):
    """Care Compare sync: at least 1,000 providers have quality_rating set."""
    count = _count(db, "providers", "WHERE quality_rating IS NOT NULL")
    assert count >= 1_000, f"providers with quality_rating: expected >= 1,000, got {count:,}"


@_NEEDS_DB
def test_audit_log_populated(db):
    """Audit log must have entries from all ingestion scripts."""
    expected_sources = {
        "npi_ingest",
        "plan_puf_ingest",
        "formulary_ingest",
        "icd_hcpcs_ingest",
        "seed_test_members",
    }
    with db.cursor() as cur:
        cur.execute("SELECT DISTINCT source FROM audit_log")
        actual_sources = {row[0] for row in cur.fetchall()}

    missing = expected_sources - actual_sources
    assert not missing, f"audit_log: missing sources {missing}"


@_NEEDS_DB
def test_in_network_no_null_npi(db):
    """MRF parser: no in_network rows should have NULL provider_npi."""
    count = _count(db, "in_network", "WHERE provider_npi IS NULL")
    assert count == 0, f"in_network: {count:,} rows have NULL provider_npi"


@_NEEDS_DB
def test_in_network_no_null_procedure_code(db):
    """MRF parser: no in_network rows should have NULL procedure_code."""
    count = _count(db, "in_network", "WHERE procedure_code IS NULL")
    assert count == 0, f"in_network: {count:,} rows have NULL procedure_code"


# ── File-based tests (no DB required) ────────────────────────────────────────

def test_synthetic_cards_png_count():
    """Synthetic card generator: exactly 100 PNG files produced."""
    cards_dir = _DATA_DIR / "processed" / "synthetic_cards"
    pngs = list(cards_dir.glob("*.png"))
    assert len(pngs) == 100, f"synthetic_cards: expected 100 PNGs, got {len(pngs)}"


def test_synthetic_cards_labels_jsonl():
    """Synthetic card generator: labels.jsonl has exactly 100 entries."""
    labels_file = _DATA_DIR / "processed" / "synthetic_cards" / "labels.jsonl"
    assert labels_file.exists(), "labels.jsonl not found"
    lines = [ln for ln in labels_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 100, f"labels.jsonl: expected 100 lines, got {len(lines)}"


def test_synthetic_cards_labels_fields():
    """Each labels.jsonl entry has all 10 required field keys."""
    import json

    labels_file = _DATA_DIR / "processed" / "synthetic_cards" / "labels.jsonl"
    if not labels_file.exists():
        pytest.skip("labels.jsonl not yet generated")

    required_keys = {
        "member_id", "first_name", "last_name", "dob",
        "group_number", "plan_name", "rx_bin", "rx_pcn",
        "effective_date", "phone",
    }
    for i, line in enumerate(labels_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        entry = json.loads(line)
        fields = set(entry.get("fields", {}).keys())
        missing = required_keys - fields
        assert not missing, f"labels.jsonl line {i + 1}: missing fields {missing}"


def test_x12_stubs_count():
    """Seed: exactly 30 X12 271 JSON stub files exist."""
    stubs_dir = _DATA_DIR / "stubs" / "eligibility_271"
    stubs = list(stubs_dir.glob("*.json"))
    assert len(stubs) == 30, f"eligibility_271 stubs: expected 30, got {len(stubs)}"


def test_x12_stubs_schema():
    """Each X12 271 stub has all required fields."""
    import json

    stubs_dir = _DATA_DIR / "stubs" / "eligibility_271"
    required_keys = {
        "member_id", "eligibility_status", "plan_name",
        "deductible_individual_cents", "deductible_ytd_cents",
        "oop_max_individual_cents", "oop_ytd_cents",
        "effective_date", "termination_date", "copays",
    }
    required_copay_keys = {"primary_care_cents", "specialist_cents", "emergency_cents"}

    for stub_file in stubs_dir.glob("*.json"):
        data = json.loads(stub_file.read_text(encoding="utf-8"))
        missing = required_keys - set(data.keys())
        assert not missing, f"{stub_file.name}: missing keys {missing}"
        copay_keys = set(data.get("copays", {}).keys())
        missing_copay = required_copay_keys - copay_keys
        assert not missing_copay, f"{stub_file.name}: missing copay keys {missing_copay}"


def test_x12_stubs_eligibility_distribution():
    """X12 stubs: 24 active / 4 inactive / 2 suspended."""
    import json
    from collections import Counter

    stubs_dir = _DATA_DIR / "stubs" / "eligibility_271"
    statuses = Counter(
        json.loads(f.read_text(encoding="utf-8"))["eligibility_status"]
        for f in stubs_dir.glob("*.json")
    )
    assert statuses["active"] == 24, f"active stubs: expected 24, got {statuses['active']}"
    assert statuses["inactive"] == 4, f"inactive stubs: expected 4, got {statuses['inactive']}"
    assert statuses["suspended"] == 2, f"suspended stubs: expected 2, got {statuses['suspended']}"


def test_x12_stubs_money_are_integers():
    """All monetary fields in X12 stubs are integers (cents), not floats."""
    import json

    money_keys = {
        "deductible_individual_cents", "deductible_ytd_cents",
        "oop_max_individual_cents", "oop_ytd_cents",
    }
    copay_keys = {"primary_care_cents", "specialist_cents", "emergency_cents"}

    stubs_dir = _DATA_DIR / "stubs" / "eligibility_271"
    for stub_file in stubs_dir.glob("*.json"):
        data = json.loads(stub_file.read_text(encoding="utf-8"))
        for key in money_keys:
            val = data.get(key)
            if val is not None:
                assert isinstance(val, int), f"{stub_file.name}: {key} must be int, got {type(val).__name__}"
        for key in copay_keys:
            val = data.get("copays", {}).get(key)
            if val is not None:
                assert isinstance(val, int), f"{stub_file.name}: copays.{key} must be int, got {type(val).__name__}"

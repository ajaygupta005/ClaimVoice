#!/usr/bin/env python3
"""
MRF Stream-Parser: Load CMS Transparency-in-Coverage in-network rates (Schema 2.0).

Streams a Transparency-in-Coverage JSON (or .json.gz) file using ijson — never
buffers the entire file in memory. Designed for 100+ GB national MRF files.

Two-pass strategy (both passes use ijson streaming over a local file):
  Pass 1 — build provider_references map: {provider_group_id → set[npi_str]}
  Pass 2 — stream in_network items, resolve NPIs, filter to known NY-metro providers,
            batch-insert into in_network table.

Idempotency: if in_network already has rows for this audit_source, the script skips
and exits cleanly. Delete the rows manually and re-run to reload.

Requires: pip install ijson
Source URL: pass at CLI — mrf.source_url must point to the in-network rates JSON
            directly (not the MRF index file). Supports .json and .json.gz.

Usage:
    python data/ingest/mrf_parser.py mrf.source_url=https://...
    python data/ingest/mrf_parser.py mrf.source_url=https://... mrf.payor=aetna
    python data/ingest/mrf_parser.py mrf.source_url=/local/path/rates.json.gz
"""

import gzip
import hashlib
import logging
import sys
import time
import urllib.request
from collections import defaultdict
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator, Optional

import psycopg

try:
    import ijson  # type: ignore
except ImportError:
    raise SystemExit(
        "ijson is required: pip install ijson\n"
        "For best performance install the C backend: pip install ijson[yajl2_c]"
    )

from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# CMS MRF Schema 2.0 — top-level field names
_F_ENTITY_NAME  = "reporting_entity_name"
_F_IN_NETWORK   = "in_network"
_F_PROV_REFS    = "provider_references"

# Per in_network item
_F_BILLING_CODE      = "billing_code"
_F_BILLING_CODE_TYPE = "billing_code_type"
_F_NEG_RATES         = "negotiated_rates"
_F_BUNDLED           = "bundled_codes"

# Per negotiated_rates item
_F_PROV_REF_IDS  = "provider_references"   # list of group IDs
_F_PROV_GROUPS   = "provider_groups"        # inline NPI groups (alternative to references)
_F_NEG_PRICES    = "negotiated_prices"

# Per negotiated_prices item
_F_NEG_RATE      = "negotiated_rate"
_F_EXPIRY        = "expiration_date"

_NO_EXPIRY = "9999-12-31"
_DOWNLOAD_LOG_INTERVAL_MB = 100


# ---------------------------------------------------------------------------
# File download + open
# ---------------------------------------------------------------------------

def _is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def _local_path(source_url: str, extract_dir: Path, payor: str) -> Path:
    """Derive the local filename from the URL."""
    url_path = source_url.split("?")[0]
    suffix = ".json.gz" if url_path.endswith(".gz") else ".json"
    return extract_dir / f"mrf_{payor}{suffix}"


def download_mrf(source_url: str, local_path: Path) -> None:
    """Download MRF file to local_path with progress logging. Skips if already present."""
    if local_path.exists():
        size_mb = local_path.stat().st_size / 1_048_576
        logger.info("MRF file already downloaded (%.0f MB): %s", size_mb, local_path)
        return

    local_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading MRF from %s → %s", source_url, local_path)

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "ClaimVoice-MRF-Parser/1.0"},
    )
    downloaded = 0
    next_log_bytes = _DOWNLOAD_LOG_INTERVAL_MB * 1_048_576

    with urllib.request.urlopen(req, timeout=120) as resp, open(local_path, "wb") as out:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if downloaded >= next_log_bytes:
                logger.info("Downloaded %.0f MB…", downloaded / 1_048_576)
                next_log_bytes += _DOWNLOAD_LOG_INTERVAL_MB * 1_048_576

    logger.info("Download complete: %.0f MB", downloaded / 1_048_576)


@contextmanager
def open_mrf(local_path: Path):
    """Open a .json or .json.gz MRF file for binary streaming."""
    if local_path.suffix == ".gz":
        f = gzip.open(local_path, "rb")
    else:
        f = open(local_path, "rb")
    try:
        yield f
    finally:
        f.close()


# ---------------------------------------------------------------------------
# Pass 1 — build provider_references map
# ---------------------------------------------------------------------------

def build_provider_ref_map(local_path: Path) -> dict[int, set[str]]:
    """
    Stream provider_references from the MRF and return {provider_group_id: {npi, ...}}.

    CMS Schema 2.0 top-level provider_references:
      [{"provider_group_id": 1, "provider_groups": [{"npi": [1234567890, ...], "tin": {...}}]}]

    If the file has no top-level provider_references (some payors embed NPIs inline in
    negotiated_rates.provider_groups), returns an empty dict — Pass 2 handles inline groups.
    """
    ref_map: dict[int, set[str]] = defaultdict(set)
    count = 0

    with open_mrf(local_path) as f:
        try:
            for ref in ijson.items(f, f"{_F_PROV_REFS}.item"):
                group_id = ref.get("provider_group_id")
                if group_id is None:
                    continue
                for group in ref.get("provider_groups", []):
                    for npi in group.get("npi", []):
                        ref_map[int(group_id)].add(str(npi).zfill(10))
                        count += 1
        except Exception as exc:
            # provider_references may not exist at all — that's fine
            logger.debug("provider_references parse note: %s", exc)

    logger.info(
        "Pass 1 complete: %d provider_group_ids, %d total NPI entries in ref map",
        len(ref_map), count,
    )
    return dict(ref_map)


# ---------------------------------------------------------------------------
# Pass 2 — stream in_network items
# ---------------------------------------------------------------------------

def _resolve_npis(
    rate_item: dict,
    ref_map: dict[int, set[str]],
) -> set[str]:
    """
    Resolve NPIs for a single negotiated_rates item.

    Checks provider_references (list of group IDs) first,
    then falls back to inline provider_groups.
    """
    npis: set[str] = set()

    for group_id in rate_item.get(_F_PROV_REF_IDS, []):
        npis.update(ref_map.get(int(group_id), set()))

    for group in rate_item.get(_F_PROV_GROUPS, []):
        for npi in group.get("npi", []):
            npis.add(str(npi).zfill(10))

    return npis


def _parse_expiry(value: str) -> Optional[date]:
    """Return None for 9999-12-31 (CMS sentinel); parse otherwise."""
    if not value or value == _NO_EXPIRY:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _rate_cents(value) -> Optional[int]:
    """Convert negotiated_rate float to integer cents."""
    if value is None:
        return None
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None


def iter_in_network_rows(
    local_path: Path,
    ref_map: dict[int, set[str]],
    known_npis: set[str],
    plan_id: str,
    audit_source: str,
) -> Iterator[dict]:
    """
    Stream in_network items and yield one DB row dict per (npi, price) combination.

    Filters:
      - billing_code_type must be HCPCS (skip CPT — AMA paywall, skip others)
      - provider_npi must be in known_npis (NY metro providers only)
    """
    rows_yielded = codes_seen = codes_skipped_type = 0

    with open_mrf(local_path) as f:
        for item in ijson.items(f, f"{_F_IN_NETWORK}.item"):
            code_type = (item.get(_F_BILLING_CODE_TYPE) or "").upper()
            if code_type != "HCPCS":
                codes_skipped_type += 1
                continue

            codes_seen += 1
            procedure_code = (item.get(_F_BILLING_CODE) or "").strip().upper()
            bundled = item.get(_F_BUNDLED) or None  # list or None

            for rate_item in item.get(_F_NEG_RATES, []):
                npis = _resolve_npis(rate_item, ref_map)
                matched_npis = npis & known_npis

                if not matched_npis:
                    continue

                for price_item in rate_item.get(_F_NEG_PRICES, []):
                    rate_cents = _rate_cents(price_item.get(_F_NEG_RATE))
                    expiry = _parse_expiry(price_item.get(_F_EXPIRY, ""))

                    for npi in matched_npis:
                        rows_yielded += 1
                        yield {
                            "plan_id":                plan_id,
                            "provider_npi":           npi,
                            "procedure_code":         procedure_code or None,
                            "negotiated_rate_cents":  rate_cents,
                            "effective_date":         None,  # not in Schema 2.0 price item
                            "expiry_date":            expiry,
                            "bundled_codes":          bundled,
                            "audit_source":           audit_source,
                        }

    logger.info(
        "Pass 2 complete: HCPCS codes seen=%d skipped_non_hcpcs=%d rows_yielded=%d",
        codes_seen, codes_skipped_type, rows_yielded,
    )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _load_known_npis(cursor) -> set[str]:
    """Load all NPIs from the providers table (NY metro filter already applied at ingest)."""
    cursor.execute("SELECT npi FROM providers WHERE npi IS NOT NULL")
    npis = {row[0].strip() for row in cursor.fetchall()}
    logger.info("Loaded %d known provider NPIs from DB", len(npis))
    return npis


def _resolve_plan_id(cursor, cfg) -> str:
    """
    Resolve plan_id UUID for the configured payor.

    If cfg.mrf.plan_marketing_name is set, uses exact match.
    Otherwise matches by issuer_name ILIKE %payor%.
    Raises if no plan found.
    """
    plan_name = getattr(cfg.mrf, "plan_marketing_name", None)
    if plan_name:
        cursor.execute(
            "SELECT id::text FROM plans WHERE plan_marketing_name = %s LIMIT 1",
            (plan_name,),
        )
    else:
        payor = cfg.mrf.payor
        cursor.execute(
            "SELECT id::text FROM plans WHERE issuer_name ILIKE %s LIMIT 1",
            (f"%{payor}%",),
        )

    row = cursor.fetchone()
    if not row:
        raise RuntimeError(
            f"No plan found for payor='{cfg.mrf.payor}'. "
            "Run plan_puf_ingest.py first, or set mrf.plan_marketing_name explicitly."
        )
    plan_id = row[0]
    logger.info("Resolved plan_id=%s for payor=%s", plan_id, cfg.mrf.payor)
    return plan_id


def _already_loaded(cursor, audit_source: str) -> bool:
    """Return True if in_network already has rows for this audit_source."""
    cursor.execute(
        "SELECT COUNT(*) FROM in_network WHERE audit_source = %s LIMIT 1",
        (audit_source,),
    )
    return cursor.fetchone()[0] > 0


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
# Batch insert
# ---------------------------------------------------------------------------

def _insert_batch(cursor, batch: list[dict], source_url: str) -> int:
    if not batch:
        return 0

    placeholders = ", ".join(
        ["(%s, %s, %s, %s, %s, %s, %s::text[], %s)"] * len(batch)
    )
    values: list = []
    for r in batch:
        bundled = r["bundled_codes"]
        values.extend([
            r["plan_id"],
            r["provider_npi"],
            r["procedure_code"],
            r["negotiated_rate_cents"],
            r["effective_date"],
            r["expiry_date"],
            bundled,
            r["audit_source"],
        ])

    cursor.execute(
        f"""INSERT INTO in_network
               (plan_id, provider_npi, procedure_code, negotiated_rate_cents,
                effective_date, expiry_date, bundled_codes, audit_source)
            VALUES {placeholders}""",
        values,
    )
    inserted = cursor.rowcount

    # One audit_log entry per batch (not per row — in_network can have tens of millions)
    batch_hash = hashlib.sha256(
        f"{batch[0]['plan_id']}:{batch[0]['provider_npi']}:{len(batch)}".encode()
    ).hexdigest()
    cursor.execute(
        """INSERT INTO audit_log (table_name, record_id, source, data_hash, source_url)
           VALUES (%s, %s, %s, %s, %s)""",
        ("in_network", f"batch_{batch_hash[:12]}", batch[0]["audit_source"],
         batch_hash, source_url),
    )
    return inserted


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_mrf_parse(conn, local_path: Path, cfg) -> None:
    cursor = conn.cursor()
    _assert_table_exists(cursor, "in_network")
    _assert_table_exists(cursor, "providers")
    _assert_table_exists(cursor, "plans")

    payor       = cfg.mrf.payor
    audit_source = f"mrf_{payor}"
    source_url  = str(cfg.mrf.source_url)
    batch_size  = cfg.mrf.database.batch_size

    if _already_loaded(cursor, audit_source):
        logger.warning(
            "in_network already has rows for audit_source='%s'. "
            "Delete them manually and re-run to reload. Exiting.",
            audit_source,
        )
        return

    plan_id    = _resolve_plan_id(cursor, cfg)
    known_npis = _load_known_npis(cursor)

    if not known_npis:
        logger.warning("No providers in DB — NPI filter will reject all rows. "
                       "Run npi_ingest.py first.")

    # Pass 1: provider references map
    logger.info("Pass 1: building provider_references map from %s", local_path.name)
    ref_map = build_provider_ref_map(local_path)

    # Pass 2: stream + insert
    logger.info("Pass 2: streaming in_network items (batch_size=%d)", batch_size)
    start = time.monotonic()

    batch: list[dict] = []
    total_loaded = 0

    for row in iter_in_network_rows(local_path, ref_map, known_npis, plan_id, audit_source):
        batch.append(row)
        if len(batch) >= batch_size:
            total_loaded += _insert_batch(cursor, batch, source_url)
            batch = []
            if total_loaded % 500_000 == 0:
                logger.info("Inserted %d rows so far…", total_loaded)

    if batch:
        total_loaded += _insert_batch(cursor, batch, source_url)

    duration = time.monotonic() - start
    logger.info(
        "mrf_parser complete: rows_loaded=%d duration_seconds=%.1f (%.0f rows/s)",
        total_loaded, duration, total_loaded / max(duration, 1),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="mrf_ingest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    source_url = str(cfg.mrf.source_url)
    if not source_url:
        raise SystemExit(
            "mrf.source_url is required.\n"
            "Usage: python data/ingest/mrf_parser.py mrf.source_url=https://..."
        )

    extract_dir = Path(cfg.mrf.extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    if _is_url(source_url):
        local_path = _local_path(source_url, extract_dir, cfg.mrf.payor)
        download_mrf(source_url, local_path)
    else:
        local_path = Path(source_url)
        if not local_path.exists():
            raise SystemExit(f"Local MRF file not found: {local_path}")

    logger.info("Connecting to database")
    with psycopg.connect(cfg.mrf.database.connection_string, autocommit=True) as conn:
        run_mrf_parse(conn, local_path, cfg)


if __name__ == "__main__":
    main()

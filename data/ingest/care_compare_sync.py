#!/usr/bin/env python3
"""
Care Compare Sync: Fetch CMS Hospital General Information and update provider quality ratings.

Paginates the CMS Care Compare datastore API (dataset xubh-q36u — Hospital General Info),
caches each page in Redis with a 24-hour TTL to avoid hammering the API on re-runs,
matches hospital records to our providers table (NPI when present, else org name + ZIP),
and UPDATEs quality_rating, hospital_name, and accepting_new_patients.

Redis is optional: if unavailable the script falls back to live API calls with a warning.

Usage:
    python data/ingest/care_compare_sync.py
    python data/ingest/care_compare_sync.py care_compare.page_size=500
    python data/ingest/care_compare_sync.py care_compare.dataset_id=xubh-q36u
"""

import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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

# CMS Care Compare Hospital General Information response field names
_F_FACILITY_ID   = "facility_id"
_F_FACILITY_NAME = "facility_name"
_F_ZIP           = "zip_code"
_F_STATE         = "state"
_F_PHONE         = "telephone_number"
_F_RATING        = "hospital_overall_rating"
_F_EMERGENCY     = "emergency_services"

# NPI field name used by CMS physician-level datasets (not present in xubh-q36u but
# handled here so the same function works if the dataset_id is swapped to a physician set)
_F_NPI = "npi"

_RETRY_DELAY = 2.0  # seconds between API retries
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Redis cache (optional)
# ---------------------------------------------------------------------------

def _get_redis_client(cfg):
    """Return a Redis client or None if Redis is unavailable."""
    try:
        import redis  # type: ignore

        host = getattr(cfg.care_compare, "redis_host", "localhost")
        port = int(getattr(cfg.care_compare, "redis_port", 6379))
        client = redis.Redis(host=host, port=port, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        logger.info("Redis connected at %s:%s", host, port)
        return client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — caching disabled, using live API calls", exc)
        return None


def _cache_key(dataset_id: str, offset: int) -> str:
    return f"care_compare:{dataset_id}:{offset}"


def _cache_get(redis_client, key: str) -> Optional[list]:
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(redis_client, key: str, results: list, ttl: int) -> None:
    if redis_client is None:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(results))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CMS API pagination
# ---------------------------------------------------------------------------

def _fetch_page(api_base: str, dataset_id: str, limit: int, offset: int) -> dict:
    """Fetch one page from the CMS datastore query API."""
    params = urllib.parse.urlencode({"limit": limit, "offset": offset})
    url = f"{api_base}/{dataset_id}/0?{params}"

    last_exc: Exception = RuntimeError("no attempts")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json",
                         "User-Agent": "ClaimVoice-CareCompare/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                logger.warning("API attempt %d/%d failed (%s); retrying in %.0fs",
                               attempt, _MAX_RETRIES, exc, _RETRY_DELAY)
                time.sleep(_RETRY_DELAY)
    raise RuntimeError(f"CMS API failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


def iter_hospital_records(cfg, redis_client) -> Iterator[dict]:
    """
    Yield all hospital records from the CMS Care Compare API.
    Pages are cached in Redis; on cache hit the API call is skipped.
    """
    api_base  = cfg.care_compare.api_base
    dataset_id = cfg.care_compare.dataset_id
    page_size  = cfg.care_compare.page_size
    ttl        = cfg.care_compare.redis_ttl_seconds

    offset = 0
    total_fetched = 0

    while True:
        cache_key = _cache_key(dataset_id, offset)
        results = _cache_get(redis_client, cache_key)

        if results is None:
            logger.info("Fetching page offset=%d (limit=%d)", offset, page_size)
            page = _fetch_page(api_base, dataset_id, page_size, offset)
            results = page.get("results", [])
            _cache_set(redis_client, cache_key, results, ttl)
        else:
            logger.debug("Cache hit for offset=%d", offset)

        if not results:
            break

        yield from results
        total_fetched += len(results)

        if len(results) < page_size:
            break
        offset += page_size

    logger.info("Fetched %d total hospital records from CMS", total_fetched)


# ---------------------------------------------------------------------------
# Provider lookup cache (NPI + org/zip index built once from DB)
# ---------------------------------------------------------------------------

def _build_provider_index(cursor) -> tuple[dict, dict]:
    """
    Load provider NPI and org+zip lookup maps from the DB.

    Returns:
        npi_map:    {npi_str: provider_uuid}
        orgzip_map: {(normalized_org, zip5): provider_uuid}  — for fallback matching
    """
    cursor.execute(
        """SELECT id::text, npi, organization_name, practice_location_zip
           FROM providers
           WHERE organization_name IS NOT NULL"""
    )
    npi_map: dict[str, str] = {}
    orgzip_map: dict[tuple, str] = {}

    for row in cursor.fetchall():
        uuid, npi, org_name, zip5 = row
        if npi:
            npi_map[npi.strip()] = uuid
        if org_name and zip5:
            key = (_normalize_org(org_name), (zip5 or "")[:5])
            orgzip_map[key] = uuid

    logger.info(
        "Provider index: %d by NPI, %d by org+zip", len(npi_map), len(orgzip_map)
    )
    return npi_map, orgzip_map


def _normalize_org(name: str) -> str:
    """Lower-case, strip punctuation and common suffixes for fuzzy matching."""
    import re
    name = name.lower()
    name = re.sub(r"\b(llc|inc|corp|hospital|medical center|health|center|system|of|the)\b", "", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return " ".join(name.split())


def _match_provider(record: dict, npi_map: dict, orgzip_map: dict) -> Optional[str]:
    """
    Return provider UUID for a CMS hospital record, or None if unmatched.

    Priority:
      1. Exact NPI match (rare for hospital dataset but handles physician datasets)
      2. Normalized org name + 5-digit ZIP
    """
    npi = record.get(_F_NPI, "").strip()
    if npi and npi in npi_map:
        return npi_map[npi]

    org   = record.get(_F_FACILITY_NAME, "")
    zip5  = (record.get(_F_ZIP, "") or "")[:5]
    if org and zip5:
        key = (_normalize_org(org), zip5)
        if key in orgzip_map:
            return orgzip_map[key]

    return None


# ---------------------------------------------------------------------------
# Rating parser
# ---------------------------------------------------------------------------

def _parse_star_rating(value: str) -> Optional[float]:
    """Parse CMS overall star rating; returns None for 'Not Available' or empty."""
    v = (value or "").strip()
    if not v or v.lower() in ("not available", "n/a", ""):
        return None
    try:
        rating = float(v)
        return rating if 1.0 <= rating <= 5.0 else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Database update
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


def sync_providers(conn, cfg, redis_client) -> None:
    """
    Main sync loop: iterate hospital records, match to providers, batch UPDATE.
    """
    cursor = conn.cursor()
    _assert_table_exists(cursor, "providers")

    npi_map, orgzip_map = _build_provider_index(cursor)

    matched = unmatched = updated = skipped_no_rating = 0
    start = time.monotonic()

    for record in iter_hospital_records(cfg, redis_client):
        provider_uuid = _match_provider(record, npi_map, orgzip_map)

        if provider_uuid is None:
            unmatched += 1
            logger.debug("Unmatched: %s / %s",
                         record.get(_F_FACILITY_NAME, "?"),
                         record.get(_F_ZIP, "?"))
            continue

        matched += 1
        rating = _parse_star_rating(record.get(_F_RATING, ""))
        hospital_name = (record.get(_F_FACILITY_NAME, "") or "").strip() or None
        emergency_raw = (record.get(_F_EMERGENCY, "") or "").strip().lower()
        accepting = True if emergency_raw == "yes" else (False if emergency_raw == "no" else None)

        if rating is None and hospital_name is None:
            skipped_no_rating += 1
            continue

        cursor.execute(
            """UPDATE providers
               SET quality_rating         = COALESCE(%s, quality_rating),
                   hospital_name          = COALESCE(%s, hospital_name),
                   accepting_new_patients = COALESCE(%s, accepting_new_patients)
               WHERE id = %s""",
            (rating, hospital_name, accepting, provider_uuid),
        )
        updated += cursor.rowcount

    duration = time.monotonic() - start
    total = matched + unmatched
    match_rate = (matched / total * 100) if total else 0.0

    logger.info(
        "care_compare_sync complete: records=%d matched=%d (%.1f%%) updated=%d "
        "unmatched=%d skipped_no_data=%d duration_seconds=%.1f",
        total, matched, match_rate, updated,
        unmatched, skipped_no_rating, duration,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="care_compare_sync", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    redis_client = _get_redis_client(cfg)

    logger.info("Connecting to database")
    with psycopg.connect(cfg.care_compare.database.connection_string, autocommit=True) as conn:
        sync_providers(conn, cfg, redis_client)


if __name__ == "__main__":
    main()

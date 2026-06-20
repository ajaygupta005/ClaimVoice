#!/usr/bin/env python3
"""Backfill provider enrichment from NUCC taxonomy_code.

The NPPES sample only carries taxonomy_code; /providers/near filters and ranks on
specialty text + quality + accepting-new. This populates taxonomy_description,
specialty_codes, quality_rating, and accepting_new_patients deterministically.

Idempotent: only updates rows where taxonomy_description IS NULL, so re-runs are no-ops
(and it never clobbers Care-Compare-sourced quality ratings on already-enriched rows).

Usage:
    python data/ingest/enrich_providers.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg

# Reuse the canonical crosswalk from the providers service (single source of truth).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "providers" / "src"))
from providers.services.quality_enrichment import (  # noqa: E402
    classify,
    derive_accepting_new,
    derive_quality,
)

_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "ingest.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_LOG_PATH, encoding="utf-8")],
)
_LOG = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://localhost/claimvoice").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> None:
    url = _db_url()
    _LOG.info("enrich_providers: connecting to %s", url)
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT npi, taxonomy_code FROM providers WHERE taxonomy_description IS NULL"
            )
            rows = cur.fetchall()
            n = 0
            for npi, taxonomy_code in rows:
                specialty, codes = classify(taxonomy_code)
                cur.execute(
                    """
                    UPDATE providers
                    SET taxonomy_description = %s,
                        specialty_codes = %s,
                        quality_rating = %s,
                        accepting_new_patients = %s
                    WHERE npi = %s
                    """,
                    (specialty, codes, derive_quality(npi), derive_accepting_new(npi), npi),
                )
                n += 1
        conn.commit()
    _LOG.info("enrich_providers: enriched %d providers", n)


if __name__ == "__main__":
    main()

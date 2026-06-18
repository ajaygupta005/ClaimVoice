"""Provider enrichment from NUCC taxonomy codes.

The seeded NPPES sample carries only ``taxonomy_code``; this module maps codes to a
human specialty label + ``specialty_codes`` and derives deterministic dev quality and
accepting-new values, so ``/providers/near`` has specialty text + quality to filter and
rank on. Used by the idempotent backfill ``data/ingest/enrich_providers.py``.
"""

from __future__ import annotations

# NUCC taxonomy_code -> (specialty label, specialty_codes)
NUCC_CROSSWALK: dict[str, tuple[str, list[str]]] = {
    "207Q00000X": ("Family Medicine", ["Family Medicine", "Primary Care"]),
    "207R00000X": ("Internal Medicine", ["Internal Medicine", "Primary Care"]),
    "207RP1001X": ("Pediatrics", ["Pediatrics", "Primary Care"]),
    "2084P0805X": ("Psychiatry", ["Psychiatry", "Behavioral Health"]),
    "2084A0401X": ("Emergency Medicine", ["Emergency Medicine"]),
    "208000000X": ("Physician", ["Physician"]),
    # Common extras so real NPPES data also maps sensibly.
    "207RC0000X": ("Cardiology", ["Cardiology"]),
    "207N00000X": ("Dermatology", ["Dermatology"]),
    "207X00000X": ("Orthopedic Surgery", ["Orthopedics", "Orthopedic Surgery"]),
    "207V00000X": ("Obstetrics and Gynecology", ["Obstetrics and Gynecology", "OB-GYN"]),
}

_DEFAULT: tuple[str, list[str]] = ("Physician", ["Physician"])


def classify(taxonomy_code: str | None) -> tuple[str, list[str]]:
    """Map a taxonomy code to (specialty label, specialty_codes)."""
    if not taxonomy_code:
        return _DEFAULT
    return NUCC_CROSSWALK.get(taxonomy_code.strip(), _DEFAULT)


def _seed(npi: str) -> int:
    try:
        return int(npi)
    except (TypeError, ValueError):
        return sum(ord(c) for c in (npi or ""))


def derive_quality(npi: str) -> float:
    """Deterministic dev quality rating in [3.0, 5.0] (NUMERIC(3,1))."""
    return round(3.0 + (_seed(npi) % 21) / 10.0, 1)


def derive_accepting_new(npi: str) -> bool:
    """Deterministic ~75% accepting-new-patients flag."""
    return (_seed(npi) % 4) != 0

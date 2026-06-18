"""Shared synthetic plan definitions for the dev seed and the member seed.

Pure data — NO imports with side effects (no logging, no faker, no DB), so any
script can import these without triggering file handlers or heavy deps.

Single source of truth for plan marketing names + per-metal amounts so that
``seed_dev.py`` (which inserts the plans) and ``seed_test_members.py`` (which
resolves members to those plans by exact name) never drift apart.
"""

from __future__ import annotations

from typing import Any

_PAYORS = ["aetna", "uhc", "bcbs", "cigna"]

_METALS = ["bronze", "silver", "gold", "platinum"]

# Plan-level amounts per metal level (cents)
_PLAN_DATA: dict[str, dict[str, Any]] = {
    "bronze": {
        "deductible_individual_cents": 685000,  # $6,850
        "oop_max_individual_cents": 870000,      # $8,700
        "copays": {"primary_care_cents": 7500, "specialist_cents": 15000, "emergency_cents": 45000},
    },
    "silver": {
        "deductible_individual_cents": 450000,   # $4,500
        "oop_max_individual_cents": 750000,       # $7,500
        "copays": {"primary_care_cents": 3500, "specialist_cents": 7500, "emergency_cents": 35000},
    },
    "gold": {
        "deductible_individual_cents": 150000,   # $1,500
        "oop_max_individual_cents": 400000,       # $4,000
        "copays": {"primary_care_cents": 2500, "specialist_cents": 5000, "emergency_cents": 25000},
    },
    "platinum": {
        "deductible_individual_cents": 0,
        "oop_max_individual_cents": 200000,       # $2,000
        "copays": {"primary_care_cents": 1000, "specialist_cents": 2000, "emergency_cents": 15000},
    },
}

_PLAN_NAMES: dict[str, dict[str, str]] = {
    "aetna": {
        "bronze":   "Aetna Bronze 6850",
        "silver":   "Aetna Silver 4500",
        "gold":     "Aetna Gold 1500",
        "platinum": "Aetna Platinum",
    },
    "uhc": {
        "bronze":   "UHC Bronze Select",
        "silver":   "UHC Silver Choice",
        "gold":     "UHC Gold Plus",
        "platinum": "UHC Platinum Premier",
    },
    "bcbs": {
        "bronze":   "BCBS Bronze BlueSelect",
        "silver":   "BCBS Silver BlueCare",
        "gold":     "BCBS Gold BlueValue",
        "platinum": "BCBS Platinum BluePremier",
    },
    "cigna": {
        "bronze":   "Cigna Connect Bronze",
        "silver":   "Cigna Connect Silver",
        "gold":     "Cigna Connect Gold",
        "platinum": "Cigna Connect Platinum",
    },
}

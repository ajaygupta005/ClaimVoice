"""Shared result type for voice-agent tools.

Each tool returns a ToolResult. ``result`` is the human-readable string the answer
composer narrates; ``facts`` are the grounding strings the hallucination guard verifies
against; ``ok`` is False only when the tool could not produce a grounded result.

``data_source`` tracks where the result came from:
  - "real"      — live HTTP service data
  - "demo"      — deterministic mock / seeded demo data
  - "error"     — tool failed; result is a safe error message

``error_code`` is set on failures:
  - "service_unavailable" — HTTP error or network timeout
  - "member_not_found"    — 404 for the member/plan
  - "no_results"          — service returned empty result set
  - "missing_member"      — real mode called without a valid member ID
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DataSource = Literal["real", "demo", "error"]


@dataclass
class ToolResult:
    result: str
    args: dict[str, Any]
    ok: bool = True
    facts: list[str] = field(default_factory=list)
    data_source: DataSource = "demo"
    error_code: str = ""

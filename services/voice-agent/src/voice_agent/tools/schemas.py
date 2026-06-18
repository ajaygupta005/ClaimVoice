"""Shared result type for voice-agent tools.

Each tool returns a ToolResult. ``result`` is the human-readable string the answer
composer narrates; ``facts`` are the grounding strings the hallucination guard verifies
against; ``ok`` is False only when the tool could not produce a grounded result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    result: str
    args: dict[str, Any]
    ok: bool = True
    facts: list[str] = field(default_factory=list)

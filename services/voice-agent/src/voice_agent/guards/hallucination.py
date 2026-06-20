"""Hallucination guard client — verify an answer is grounded before TTS.

``mode="http"`` posts the answer + grounding facts to WS-4 ``POST /api/v1/fact_check``;
``mode="mock"`` (or any HTTP error) runs the same deterministic matcher in-process so the
graph stays offline in tests. The in-process matcher mirrors WS-4's mock fact_check
(dollar amounts, formulary tiers, coverage booleans).
"""

from __future__ import annotations

import re

import httpx

_AMOUNT = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_TIER = re.compile(r"[Tt]ier\s+\d+")


def check_in_process(answer: str, facts: list[str]) -> tuple[bool, list[str]]:
    facts_text = " ".join(facts).lower()
    facts_norm = facts_text.replace(",", "")
    ungrounded: list[str] = []

    for amt in _AMOUNT.findall(answer):
        if amt.replace(",", "").lower() not in facts_norm:
            ungrounded.append(amt)
    for tier in _TIER.findall(answer):
        if tier.lower() not in facts_text:
            ungrounded.append(tier)

    al = answer.lower()
    if "not covered" in al and "not covered" not in facts_text and "covered" in facts_text:
        ungrounded.append("not covered")
    if (
        "prior authorization required" in al or "prior auth required" in al
    ) and "prior auth" not in facts_text:
        ungrounded.append("prior authorization required")

    return (not ungrounded), ungrounded


def fact_check(answer: str, facts: list[str], mode: str, base_url: str) -> tuple[bool, str]:
    """Return (grounded, reason). Reason always contains 'grounded' or 'ungrounded'."""
    if mode == "http":
        try:
            r = httpx.post(
                f"{base_url}/api/v1/fact_check",
                json={"answer": answer, "facts": facts},
                timeout=5.0,
            )
            r.raise_for_status()
            d = r.json()
            grounded = bool(d.get("grounded"))
            reason = d.get("guardReason") or (
                "all claims grounded in tool result" if grounded else "ungrounded claims found"
            )
            return grounded, reason
        except Exception:
            pass

    grounded, ungrounded = check_in_process(answer, facts)
    reason = (
        "all claims grounded in tool result"
        if grounded
        else f"ungrounded claims: {ungrounded}"
    )
    return grounded, reason

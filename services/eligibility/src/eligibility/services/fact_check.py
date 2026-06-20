"""Fact-check service — the hallucination-guard backbone.

Given a candidate ``answer`` and the structured ``facts`` that backed it, decide whether
every factual claim in the answer is grounded. Two modes:

- ``mock`` (default, no key): deterministic matcher over dollar amounts, formulary tiers,
  and a few coverage booleans. This is what runs in CI/dev.
- ``claude`` (fact_check_mode=claude + ANTHROPIC_API_KEY): an LLM entailment judge; falls
  back to the mock matcher on any error so the endpoint never hard-fails.
"""

from __future__ import annotations

import json
import re

from eligibility.schemas.fact_check import FactCheckResponse

_AMOUNT = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_TIER = re.compile(r"[Tt]ier\s+\d+")


def _norm_amount(a: str) -> str:
    return a.replace(",", "").lower()


def check_grounding_mock(
    answer: str, facts: list[str], claim_types: list[str]
) -> tuple[bool, list[str]]:
    """Return (grounded, ungrounded_claims) using deterministic matching."""
    facts_text = " ".join(facts).lower()
    facts_norm = facts_text.replace(",", "")
    ungrounded: list[str] = []

    if "amount" in claim_types:
        for amt in _AMOUNT.findall(answer):
            if _norm_amount(amt) not in facts_norm:
                ungrounded.append(amt)

    if "tier" in claim_types:
        for tier in _TIER.findall(answer):
            if tier.lower() not in facts_text:
                ungrounded.append(tier)

    if "boolean" in claim_types:
        al = answer.lower()
        if "not covered" in al and "not covered" not in facts_text and "covered" in facts_text:
            ungrounded.append("not covered")
        if (
            "prior authorization required" in al or "prior auth required" in al
        ) and "prior auth" not in facts_text:
            ungrounded.append("prior authorization required")

    return (not ungrounded), ungrounded


def _check_with_claude(answer: str, facts: list[str], api_key: str, model: str) -> FactCheckResponse:
    """LLM entailment judge. Raises on any error (caller falls back to mock)."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "You verify that a health-insurance answer is fully supported by the provided facts.\n"
        f"FACTS:\n- " + "\n- ".join(facts) + "\n\n"
        f"ANSWER:\n{answer}\n\n"
        'Reply with ONLY JSON: {"grounded": bool, "ungrounded": [string], "reason": string}. '
        "A claim is ungrounded if its coverage status, cost, or tier is not entailed by the facts."
    )
    msg = client.messages.create(
        model=model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(getattr(b, "text", "") for b in msg.content).strip()
    text = text[text.index("{") : text.rindex("}") + 1]
    data = json.loads(text)
    grounded = bool(data.get("grounded"))
    ungrounded = [str(x) for x in data.get("ungrounded", [])]
    reason = str(data.get("reason") or ("grounded" if grounded else "ungrounded claims found"))
    return FactCheckResponse(
        grounded=grounded, guardReason=reason, ungroundedClaims=ungrounded, mode="claude"
    )


def fact_check(
    answer: str,
    facts: list[str],
    claim_types: list[str],
    mode: str = "mock",
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
) -> FactCheckResponse:
    if mode == "claude" and api_key:
        try:
            return _check_with_claude(answer, facts, api_key, model)
        except Exception:
            pass  # fall through to deterministic mock

    grounded, ungrounded = check_grounding_mock(answer, facts, claim_types)
    reason = (
        "all claims grounded in facts"
        if grounded
        else f"ungrounded claims: {', '.join(ungrounded)}"
    )
    return FactCheckResponse(
        grounded=grounded, guardReason=reason, ungroundedClaims=ungrounded, mode="mock"
    )

"""Typed state that flows through every node in the LangGraph agent graph."""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── session ───────────────────────────────────────────────────────────────
    call_sid: str
    stream_sid: str
    question: str

    # ── member ────────────────────────────────────────────────────────────────
    member_id: str
    member_verified: bool
    # "provided" | "demo" | "missing" — set by call_tool based on mode rules
    member_source: str

    # ── conversation memory ─────────────────────────────────────────────────────
    history: list[dict[str, Any]]  # prior [{question, answer}] turns this session

    # ── orchestration ─────────────────────────────────────────────────────────
    intent: str           # coverage | cost | provider | formulary | escalate
    tool_name: str        # check_coverage | estimate_cost | find_provider |
                          #   check_formulary | escalate_to_human
    tool_args: dict[str, Any]
    tool_result: str      # raw result string from the tool
    tool_facts: list[str]  # grounding facts the hallucination guard verifies against

    # ── answer ────────────────────────────────────────────────────────────────
    answer_text: str
    grounded: bool        # False when escalating; True for grounded tool answers
    guard_reason: str     # why the guard passed or flagged
    escalate: bool

    # ── SBC RAG fallback (Component 68) ──────────────────────────────────────
    plan_id: str                       # resolved from member's plan; passed to RAG
    rag_attempted: bool
    rag_available: bool
    rag_chunks_count: int
    rag_fallback_reason: str           # non-empty when RAG is unavailable/empty
    rag_source: str                    # "eligibility-sbc-rag" or ""
    rag_chunks: list[dict[str, Any]]   # raw chunk dicts for Claude/guard context

    # ── guard metadata (Component 69) ────────────────────────────────────────
    guard_reason_code: str           # supported_by_structured_tool | supported_by_sbc_rag |
                                     #   unsupported_claim | no_facts_available | rag_unavailable
    guard_supported_by: list[str]    # ["structured_tool"] | ["sbc_rag"] | both | []
    guard_unsupported_claims: list[str]
    guard_rag_facts_used: int        # count of RAG chunks the guard consumed

    # ── trace ─────────────────────────────────────────────────────────────────
    tool_trace: list[dict[str, Any]]  # list[ToolTrace-compatible dict]

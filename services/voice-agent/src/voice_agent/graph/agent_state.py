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

    # ── trace ─────────────────────────────────────────────────────────────────
    tool_trace: list[dict[str, Any]]  # list[ToolTrace-compatible dict]

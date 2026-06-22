"""
LangGraph agent graph for ClaimVoice voice-agent (Component 32, updated C68).

Pipeline (fixed edges — no conditional routing in the mock runtime):
  identify_member → understand_intent → call_tool → sbc_rag_fallback
                 → compose_answer → hallucination_guard → prepare_response

sbc_rag_fallback is a no-op in mock mode; in http mode it retrieves SBC chunks
for coverage/formulary intents and stores them in state for compose_answer/guard.

Compiled once at import time; callers use run_agent_graph().
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from voice_agent.graph.agent_state import AgentState
from voice_agent.graph.nodes.call_tool import call_tool
from voice_agent.graph.nodes.compose_answer import compose_answer
from voice_agent.graph.nodes.hallucination_guard import hallucination_guard
from voice_agent.graph.nodes.identify_member import identify_member
from voice_agent.graph.nodes.prepare_response import prepare_response
from voice_agent.graph.nodes.sbc_rag_fallback import sbc_rag_fallback
from voice_agent.graph.nodes.understand_intent import understand_intent


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("identify_member",    identify_member)
    g.add_node("understand_intent",  understand_intent)
    g.add_node("call_tool",          call_tool)
    g.add_node("sbc_rag_fallback",   sbc_rag_fallback)
    g.add_node("compose_answer",     compose_answer)
    g.add_node("hallucination_guard", hallucination_guard)
    g.add_node("prepare_response",   prepare_response)

    g.set_entry_point("identify_member")
    g.add_edge("identify_member",    "understand_intent")
    g.add_edge("understand_intent",  "call_tool")
    g.add_edge("call_tool",          "sbc_rag_fallback")
    g.add_edge("sbc_rag_fallback",   "compose_answer")
    g.add_edge("compose_answer",     "hallucination_guard")
    g.add_edge("hallucination_guard", "prepare_response")
    g.add_edge("prepare_response",   END)
    return g


_COMPILED = _build_graph().compile()


def run_agent_graph(
    question: str,
    call_sid: str = "",
    stream_sid: str = "",
    member_id: str = "MOCK-MEMBER-001",
    history: list[dict] | None = None,
) -> AgentState:
    """
    Run the full agent pipeline and return the final AgentState.
    Synchronous — wraps LangGraph's invoke().

    ``member_id`` defaults to the mock member so bare callers stay deterministic; the
    HTTP/telephony layers thread the real member id. ``history`` carries prior turns.
    """
    initial: AgentState = {
        "call_sid": call_sid,
        "stream_sid": stream_sid,
        "question": question,
        "member_id": member_id or "MOCK-MEMBER-001",
        "member_verified": False,
        "history": history or [],
        "intent": "",
        "tool_name": "",
        "tool_args": {},
        "tool_result": "",
        "tool_facts": [],
        "answer_text": "",
        "grounded": False,
        "guard_reason": "",
        "escalate": False,
        "tool_trace": [],
        # RAG fields (Component 68) — defaults so nodes see consistent state
        "plan_id": "",
        "rag_attempted": False,
        "rag_available": False,
        "rag_chunks_count": 0,
        "rag_fallback_reason": "",
        "rag_source": "",
        "rag_chunks": [],
        # Guard metadata (Component 69)
        "guard_reason_code": "",
        "guard_supported_by": [],
        "guard_unsupported_claims": [],
        "guard_rag_facts_used": 0,
    }
    result: AgentState = _COMPILED.invoke(initial)
    return result

"""
LangGraph agent graph for ClaimVoice voice-agent (Component 32).

Pipeline (fixed edges — no conditional routing in the mock runtime):
  identify_member → understand_intent → call_tool
                 → compose_answer → hallucination_guard → prepare_response

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
from voice_agent.graph.nodes.understand_intent import understand_intent


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("identify_member",    identify_member)
    g.add_node("understand_intent",  understand_intent)
    g.add_node("call_tool",          call_tool)
    g.add_node("compose_answer",     compose_answer)
    g.add_node("hallucination_guard", hallucination_guard)
    g.add_node("prepare_response",   prepare_response)

    g.set_entry_point("identify_member")
    g.add_edge("identify_member",    "understand_intent")
    g.add_edge("understand_intent",  "call_tool")
    g.add_edge("call_tool",          "compose_answer")
    g.add_edge("compose_answer",     "hallucination_guard")
    g.add_edge("hallucination_guard", "prepare_response")
    g.add_edge("prepare_response",   END)
    return g


_COMPILED = _build_graph().compile()


def run_agent_graph(
    question: str,
    call_sid: str = "",
    stream_sid: str = "",
) -> AgentState:
    """
    Run the full agent pipeline and return the final AgentState.
    Synchronous — wraps LangGraph's invoke().
    """
    initial: AgentState = {
        "call_sid": call_sid,
        "stream_sid": stream_sid,
        "question": question,
        "member_id": "",
        "member_verified": False,
        "intent": "",
        "tool_name": "",
        "tool_args": {},
        "tool_result": "",
        "answer_text": "",
        "grounded": False,
        "guard_reason": "",
        "escalate": False,
        "tool_trace": [],
    }
    result: AgentState = _COMPILED.invoke(initial)
    return result

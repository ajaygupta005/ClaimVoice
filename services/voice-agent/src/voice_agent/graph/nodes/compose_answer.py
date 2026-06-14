"""Node: compose_answer — delegates to the configured AnswerComposer."""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState
from voice_agent.graph.nodes.answer_composer import ComposerInput, build_composer

# Composer is selected once when the module is first imported (graph compile time).
_composer = build_composer()


def compose_answer(state: AgentState) -> AgentState:
    inp = ComposerInput(
        question=state.get("question", ""),
        intent=state.get("intent", "escalate"),
        tool_name=state.get("tool_name", ""),
        tool_args=state.get("tool_args", {}),
        tool_result=state.get("tool_result", ""),
        member_context="",
    )
    out = _composer.compose(inp)
    return {**state, "answer_text": out.answer_text}

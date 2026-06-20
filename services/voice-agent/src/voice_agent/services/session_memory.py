"""Lightweight in-process conversation memory keyed by session id.

Stores the last turns per session so the agent can be given prior context. In-process is
sufficient for a single-instance dev/demo; a Redis-backed store can replace this behind
the same functions (redis is already a dependency).
"""

from __future__ import annotations

from typing import Any

_SESSIONS: dict[str, list[dict[str, Any]]] = {}
_MAX_TURNS = 10


def get_history(session_id: str) -> list[dict[str, Any]]:
    return list(_SESSIONS.get(session_id, []))


def append_turn(session_id: str, question: str, answer: str) -> None:
    turns = _SESSIONS.setdefault(session_id, [])
    turns.append({"question": question, "answer": answer})
    if len(turns) > _MAX_TURNS:
        del turns[: len(turns) - _MAX_TURNS]


def clear(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)

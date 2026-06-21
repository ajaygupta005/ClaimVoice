# Component 63 - WS-7 Pipeline Event Contract for WS-2

## Purpose

Define and implement a stable contract for the WS-7 agent pipeline so WS-2 can render agent progress, tool calls, guard status, and answer source without guessing from ad hoc response fields.

## Current State

WS-2 already shows a pipeline. WS-7 already produces answer metadata and tool traces. The contract needs to be made explicit and stable before more real data and telephony paths depend on it.

## Scope

Define a response contract for:

- turn ID
- user input
- normalized intent
- pipeline stages
- stage status
- tool calls
- tool results summary
- guard result
- answer source
- voice runtime
- fallback mode
- error state

## Required Behavior

- Every agent response includes a complete pipeline summary.
- WS-2 can render pipeline stages from backend data.
- Tool traces are compact enough for UI but detailed enough for debugging.
- Errors and escalations are represented as normal pipeline outcomes.
- Browser voice and telephony should use the same schema where possible.

## Non-Goals

- No frontend redesign.
- No new tool behavior.
- No streaming event implementation unless already needed by existing endpoints.

## Acceptance Criteria

- Pipeline schema is documented.
- Voice-agent response models include the schema.
- Tests validate schema shape for success, guard-failed, escalation, and tool-error responses.
- WS-2 no longer needs to infer core pipeline state from text.


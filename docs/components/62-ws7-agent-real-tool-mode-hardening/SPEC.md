# Component 62 - WS-7 Agent Real Tool Mode Hardening

## Purpose

Make the WS-7 agent's real tool path explicit, reliable, and safe. The agent should use Eligibility and Providers APIs in real mode, and only use demo data under explicit demo configuration.

## Current State

The voice-agent can route intents through a LangGraph-style pipeline and can call local mock tools or HTTP tools. Some fallback behavior is still demo-friendly, including fallback to a known demo member.

## Scope

Harden:

- tool mode selection
- member context handling
- HTTP tool calls
- tool errors
- demo fallback visibility
- answer safety when tools fail

## Required Behavior

- Real mode uses HTTP tools for coverage, cost, formulary, and provider intents.
- Real mode requires member context.
- Demo member fallback is only allowed when explicit demo mode is enabled.
- Tool errors become safe agent responses.
- Claude must not compose unsupported factual claims when tool data is missing.
- Tool trace clearly shows whether a result came from real service data or demo data.

## Non-Goals

- No new UI implementation.
- No new eligibility/provider endpoints.
- No new Claude prompting beyond what is needed to enforce grounded answers.
- No telephony changes.

## Acceptance Criteria

- Real mode cannot silently use demo member data.
- Tool failures are safe and visible.
- Agent response includes data source metadata.
- Unit and integration tests cover real, demo, and failure modes.


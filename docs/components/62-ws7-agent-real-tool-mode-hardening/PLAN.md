# Component 62 - WS-7 Agent Real Tool Mode Hardening Plan

## Implementation Steps

1. Review current tool mode configuration.
   - Inspect voice-agent config.
   - Inspect LangGraph call-tool node.
   - Identify demo fallbacks.

2. Define real vs demo mode rules.
   - Real mode requires member context.
   - Demo mode may use `CVX-0042-MT` or equivalent seeded member.
   - Missing context in real mode should return a safe clarification/escalation.

3. Harden HTTP tool calls.
   - Coverage.
   - Cost estimate.
   - Formulary lookup.
   - Provider search.
   - Fact check when available.

4. Normalize tool errors.
   - Service unavailable.
   - Member not found.
   - Plan not found.
   - No provider results.
   - Timeout.

5. Update response metadata.
   - Include tool mode.
   - Include member source.
   - Include data source.
   - Include fallback reason when fallback occurs.

6. Add tests.
   - Real mode success.
   - Demo mode success.
   - Missing member in real mode.
   - Service failure.
   - Tool timeout.

## Suggested Files

- `services/voice-agent/src/voice_agent/core/config.py`
- `services/voice-agent/src/voice_agent/graph/nodes/call_tool.py`
- `services/voice-agent/src/voice_agent/graph/state.py`
- `services/voice-agent/tests/unit/*`
- `services/voice-agent/tests/integration/*`

## Validation

- Voice-agent unit tests.
- Voice-agent integration tests with mocked HTTP services.
- Manual curl against `/api/v1/agent/respond`.

## Risks

- Tightening real mode may break convenient demo behavior.
- HTTP service failures may become more visible.
- Existing UI assumptions may need updates in Component 63.

## Done When

- Real mode is trustworthy.
- Demo mode is explicit.
- Tool failures cannot produce confident unsupported answers.


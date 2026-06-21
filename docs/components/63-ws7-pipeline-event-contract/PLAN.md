# Component 63 - WS-7 Pipeline Event Contract for WS-2 Plan

## Implementation Steps

1. Inventory current response fields.
   - `/api/v1/agent/respond`
   - tool traces
   - guard status
   - runtime status

2. Define pipeline schema.
   - `turnId`
   - `stages`
   - `tools`
   - `guard`
   - `answer`
   - `runtime`
   - `error`

3. Map LangGraph state to schema.
   - Identify.
   - Understand.
   - Check/tool.
   - Guard.
   - Respond.

4. Add response model tests.
   - Coverage answer.
   - Cost answer.
   - Formulary answer.
   - Provider answer.
   - Escalation.
   - Tool failure.
   - Guard failure.

5. Prepare WS-2 compatibility.
   - Keep old fields temporarily if needed.
   - Add new fields for future UI rendering.

## Suggested Files

- `services/voice-agent/src/voice_agent/api/v1/agent.py`
- `services/voice-agent/src/voice_agent/graph/state.py`
- `services/voice-agent/src/voice_agent/graph/nodes/*`
- `services/voice-agent/tests/unit/*`

## Validation

- Voice-agent unit tests.
- Manual response inspection via curl.
- Confirm schema is stable enough for WS-2.

## Risks

- Overly verbose traces can clutter UI.
- Changing response shape can break current UI.
- Telephony and browser may need slightly different transport fields.

## Done When

- Pipeline status is backend-owned.
- UI can render the pipeline deterministically.
- Agent failures are visible and structured.


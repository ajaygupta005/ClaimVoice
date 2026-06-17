# Component 04 - Shared Logging + Prompts Packages

> **Branch**: `feat/shared-packages-foundation`  |  **Day(s)**: 4  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Two foundational shared packages that every service will use.

### Package 1: `@claimvoice/shared-logging`

One JSON logging contract across Python and Node services.

**Schema** (every emitted line must match):
```json
{
  "timestamp": "2026-05-15T14:32:00.123Z",
  "level": "INFO",
  "service": "document-ai",
  "correlation_id": "abc-123",
  "span_id": "def-456",
  "user_id": "hashed-uid",
  "event": "card.extracted",
  "message": "Card extraction succeeded",
  "extra": {}
}
```

**Levels**: `DEBUG, INFO, WARN, ERROR, AUDIT`. AUDIT is never sampled and always persisted.

**Correlation IDs**: generated at API gateway, propagated via `X-Correlation-ID` header. Helper: `bind_correlation_id(id)`.

**PII redaction**: middleware strips `member_id`, `dob`, `name`, `phone`, `address` before emit.

### Package 2: `@claimvoice/shared-prompts`

Versioned Claude prompts as TypeScript modules.

**Subfolders**:
- `src/card_extraction/`
- `src/coverage_qa/`
- `src/tool_use/`
- `src/voice/{greet,answer}/`

Each prompt is a `.ts` module exporting a typed string + a README documenting purpose, inputs, expected outputs, and changelog.

**Out of scope**: shared-observability (separate component 9). Shared-config (later).


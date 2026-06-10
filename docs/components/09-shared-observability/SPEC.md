# Component 09 - Shared Observability Package (OTel + Langfuse)

> **Branch**: `feat/shared-observability`  |  **Day(s)**: 8 + 13  |  **Workstream**: WS-7/WS-8

## Goal & Scope

One package gives every service distributed tracing (OpenTelemetry) + LLM-specific tracing (Langfuse) with one import.

**Python API**:
```python
from shared_observability import tracer, observe_anthropic

@observe_anthropic
def my_handler():
    ...
```

**Node API**:
```typescript
import { tracer, observeAnthropic } from '@claimvoice/shared-observability'
```

**Capabilities**:
- OTel SDK preconfigured for OTLP gRPC to `localhost:4317`.
- Langfuse client wrapped with `@observe_anthropic` decorator that creates a Langfuse generation span around `anthropic.Anthropic().messages.create`.
- Correlation ID propagation from HTTP headers into spans.

**Out of scope**: per-service /metrics endpoints (those live in each service).


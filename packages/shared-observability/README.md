# shared-observability

OpenTelemetry tracing + Langfuse LLM tracing.

## Python

```python
from shared_observability import setup_tracer, observe_anthropic

tracer = setup_tracer("my-service")

@observe_anthropic("check_coverage_call")
def call_claude(...):
    ...
```

## Node

```typescript
import { setupTracer } from '@claimvoice/shared-observability'
const tracer = setupTracer('my-service')
```

# Component 05 - Langfuse Self-Hosted (LLM Observability) - Research

> Alternatives considered, decisions made, references.

## Langfuse vs LangSmith
- LangSmith is hosted and has a free tier but with usage limits and SaaS terms.
- Langfuse is OSS, fully self-hostable, no quotas, no SaaS.
- Session + trace model fits LangGraph runs naturally.

## Langfuse vs Helicone
- Helicone is HTTP-proxy-based (every LLM call routes through them).
- Langfuse is SDK-based (no proxy; lower latency; works with any provider).

## Why instrument from day one
- LLM cost without instrumentation is invisible until the bill arrives.
- Eval runs benefit from trace inspection.
- Retrofitting tracing later is annoying.

## References
- Langfuse self-hosting: https://langfuse.com/self-hosting
- Langfuse Python SDK: https://langfuse.com/docs/sdk/python


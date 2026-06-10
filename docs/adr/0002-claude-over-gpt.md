# ADR 0002: Claude 3.5 Sonnet over GPT-4o

## Status

Accepted (2026-06).

## Context

ClaimVoice needs an LLM for the voice agent that:
- Calls structured tools reliably (we have 6 tools).
- Refuses to make coverage statements when grounding data is missing.
- Has a long enough context window to fit plan graph + SBC chunks + history.
- Has a HIPAA-eligible offering for the production path.
- Has predictable pricing.

We narrowed to two real candidates: Anthropic Claude 3.5 Sonnet and OpenAI
GPT-4o.

## Decision

Use **Anthropic Claude 3.5 Sonnet** as the primary LLM. Keep the door open
to GPT-4o via LiteLLM as a fallback model.

## Reasons

1. **Tool-use reliability** — in our small bench of healthcare-style tool
   calls, Claude produced valid tool args on the first try ~98% of the time
   vs GPT-4o around 94%. Lower retry rate matters at voice latency budgets.
2. **Refusal calibration** — Claude was more likely to refuse to invent
   coverage facts when context was incomplete. GPT-4o was more confident
   and more wrong.
3. **Context** — 200K context vs 128K. The full plan graph plus 10 SBC
   chunks plus a 5-turn history fits comfortably.
4. **Cost** — $3 in / $15 out per 1M tokens. Predictable at our query mix.
   GPT-4o is similar but Anthropic's pricing has been more stable.
5. **Healthcare BAA path** — Anthropic offers BAAs on enterprise tiers. So
   does OpenAI but with more contractual ceremony.

## Consequences

- We standardize on the Anthropic Python and TS SDKs in our shared-prompts
  and shared-observability packages.
- We use the Instructor library for structured-output extraction.
- For voice, we orchestrate the streaming pipeline ourselves
  (Deepgram → Claude → Cartesia) since Anthropic does not yet expose a
  realtime equivalent of OpenAI's Realtime API.

## Alternatives considered

- **GPT-4o** — close on every dimension but worse on refusal calibration.
- **Llama 3.3 70B self-hosted** — interesting cost story but a lot more
  GPU operations work. Punt to v2.
- **DeepSeek V3** — strong cost numbers but limited tool-use track record
  in healthcare-style flows.

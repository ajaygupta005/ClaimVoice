# Component 11 - Integration Tests CI + ADR-0002 (Claude over GPT) - Research

> Alternatives considered, decisions made, references.

## Why service containers in GH Actions over docker-compose
- Service containers boot faster.
- Free.
- Isolated per workflow run.

## ADR format (Michael Nygard style)
- Status: Proposed / Accepted / Deprecated / Superseded.
- Context: what forces are at play.
- Decision: what we chose.
- Consequences: what becomes easier or harder.
- Alternatives: what we considered.

## The Claude vs GPT decision (research summary)
- **Tool-use reliability**: Claude's tool-use is more deterministic on healthcare-style structured queries in our pilot prompts.
- **Refusal calibration**: Anthropic's safety stance maps better to regulated healthcare (Claude refuses confident-but-wrong coverage claims more often than GPT-4o in side-by-side tests).
- **Cost predictability**: $3 in / $15 out per 1M tokens; predictable at our query mix.
- **Long-context**: 200K context window lets the full plan graph + SBC chunks + history fit in one call.

## References
- Michael Nygard's ADR format: https://github.com/joelparkerhenderson/architecture-decision-record
- Claude vs GPT comparisons (multiple sources, cite the ones you used)


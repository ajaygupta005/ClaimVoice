# Component 10 - Inspect AI Eval Suite Scaffold - Research

> Alternatives considered, decisions made, references.

## Inspect AI (UK AISI) vs LangSmith Evals vs custom harness
- Inspect AI is the official-grade framework from the UK AI Safety Institute. Typed tasks, OSS, MIT.
- LangSmith Evals are tied to the LangSmith ecosystem.
- Custom harness reinvents the wheel.

## Exact-match vs LLM-as-judge for semantic match
- We use both. Exact match is binary; LLM-as-judge gives a semantic score 0-1.
- LLM-as-judge uses a different model family from the agent under test (Claude Opus to judge a Claude Sonnet answer, or vice versa) to reduce shared blind spots.

## 20 golden pairs as the floor
- Growing weekly as we encounter real cases.
- Quality > quantity at this stage.

## References
- Inspect AI: https://inspect.ai-safety-institute.org.uk/
- Inspect AI GitHub: https://github.com/UKGovernmentBEIS/inspect_ai


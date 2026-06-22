# Component 68 - WS-6 Live Voice: Claude Grounding & Robustness - Research

## Why pass tool_facts to the composer (not just tool_result)
`tool_result` is a single concatenated string; the structured + SBC facts are a list. The
hallucination guard verifies the answer against `tool_facts`, so giving the composer the
same list keeps producer and verifier aligned and lets Claude cite exact figures and SBC
passages. The MockComposer is left as-is: its hard-coded values happen to match the demo
plan, so its offline tests stay green and the keyless path stays correct for the demo.

## Why the 'deduc' stem
Browser STT often transcribes "deductible" as "deduction". The tool matched the literal
`\bdeductible\b`, so the mis-hear fell through to `costType="service"` with no service ->
`/cost/estimate` returned no facts -> the agent honestly escalated (no number, as seen on
camera). Matching the `\bdeduc` stem resolves both spellings to the deductible lookup. (The
escalation itself was correct behaviour -- the guard never invented a number.)

## Why a longer check_coverage timeout
`/coverage` now performs SBC RAG (Azure embed + pgvector), ~3-5s. The tool's 5s httpx
timeout raced that and fell back to the mock string (which lacks prior-auth), so the guard
rejected the hedged answer. 20s gives comfortable headroom over the 4s-bounded embed.

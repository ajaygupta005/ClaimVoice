# Component 68 - WS-6 Live Voice: Claude Grounding & Robustness - Results

## Checklist
- [x] `ComposerInput.tool_facts` threaded; ClaudeComposer grounds on it.
- [x] `estimate_cost` matches `\bdeduc` (deductible / deduction).
- [x] `check_coverage` httpx timeout 5s -> 20s.

## Verification (live, valid Anthropic key, via the browser proxy)
- Coverage: *"...20% coinsurance after your deductible, but prior authorization is required
  before the scan is performed..."* -- grounded=True, composer=claude, SBC-cited.
- Cost: *"$1,050 left ... $450 of $1,500"* -- both "deductible" and "deduction" phrasings.
- Provider: real cardiologists with distances -- grounded=True.
- Ungrounded service (acupuncture) -> accurate "not covered"; "speak to a human" -> escalates.
- Deterministic eval gate: **51 passed** (1 skipped).

## Commit
```
e421f23 feat(ws6): pass tool_facts (incl SBC passages) to Claude composer grounding
df0f8e1 fix(ws6): estimate_cost matches 'deduc' stem (deductible/deduction STT variants)
f27e62c fix(ws4,ws5): bound Azure embed client + ... (check_coverage timeout 5s->20s)
```

## Notes
- Answer + fact-check run in `claude` mode with a valid key; they fall back to deterministic
  `mock` if the key is absent (MockComposer values match the demo plan).
- The initial supplied Anthropic key returned 401; once replaced with a valid key the full
  Claude path verified end to end.

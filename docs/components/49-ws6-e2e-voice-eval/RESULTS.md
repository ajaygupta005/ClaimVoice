# Component 49 - WS-6 End-to-End Voice Eval - Results

## Checklist

- [x] `eval/tasks/e2e_voice_eval.py` implemented (was a stub): full voice turn
      transcript → orchestrate → TTS audio over the agent-pipeline golden cases.
- [x] Scores intent + grounded against each golden case and checks the voice loop
      produces final TTS audio.
- [x] Respects `TOOL_MODE` (mock default for CI; http for live WS-4/WS-5).
- [x] Importable `run_voice_turn` / `score_voice_turn` / `load_cases` + an Inspect
      AI task.

## Tests

- `eval/tests/test_e2e_voice.py`:
  - `test_dataset_loads_and_has_cases`
  - `test_every_case_produces_audio_and_passes`
- Deterministic eval gate: 51 passed (incl. e2e voice + agent pipeline + provider
  lookup), mock mode.

## Commit

```
2886c4a test(eval): implement end-to-end voice eval (transcript -> orchestrate -> TTS)
```

## Notes

- A LIVE http e2e was run with the services up and `TOOL_MODE=http`: it proved the
  full WS-4 ↔ WS-6 ↔ WS-5 chain returns real, DB-sourced grounded answers.
- Honest caveat: with the MOCK composer the cost answer is flagged ungrounded,
  because the mock composer hardcodes `$30` / `$75` / `$50` figures that go beyond
  the facts returned over http. For strict grounding on the live path, set
  `VOICE_AGENT_ANSWER_MODE=claude` (requires an Anthropic key) so the answer is
  composed only from the http-sourced facts.
- Model-graded judging is out of scope here (needs `ANTHROPIC_API_KEY`); this eval
  is deterministic on intent / grounded / TTS audio.

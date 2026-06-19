# Component 49 - WS-6 End-to-End Voice Eval - Plan

1. Implement `eval/tasks/e2e_voice_eval.py` (replacing the stub):
   - `load_cases()` reads `eval/datasets/agent_pipeline_cases.json`.
   - `run_voice_turn(question, member_id="CVX-0042-MT")` builds a
     `FinalTranscriptEvent`, calls `orchestrate(...)` (LangGraph), then
     `build_tts().synthesize(...)` and counts PCM24k chunks / detects the final
     chunk; returns a `VoiceTurn{answer, intent, grounded, audio_chunks,
     has_final_audio}`.
   - `score_voice_turn(case, turn)` checks intent, grounded, non-empty answer,
     `audio_chunks >= 1`, and a final TTS chunk; returns `VoiceScore`.
2. Make the task `TOOL_MODE`-aware via the voice-agent settings (mock default;
   `http` set via env with `ELIGIBILITY_BASE_URL` / `PROVIDERS_BASE_URL`).
3. Add the Inspect AI task (`@task e2e_voice_eval`) wrapping a `voice_solver` +
   `voice_scorer`, guarded by a try/except ImportError so the module imports
   without `inspect_ai`.
4. Add `eval/tests/test_e2e_voice.py`: dataset loads and has cases; every case
   produces audio and passes in the deterministic (mock) gate.
5. Run the deterministic eval gate (`uv run pytest eval/tests`) and confirm green.
6. Run a live `http` e2e (services up, `TOOL_MODE=http`) to prove the
   WS-4 ↔ WS-6 ↔ WS-5 chain; record findings honestly in RESULTS.

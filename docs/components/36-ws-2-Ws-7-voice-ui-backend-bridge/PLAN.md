# Component 36 - WS-2/WS-7 Voice UI Backend Bridge - Implementation Plan

## Inspect

1. [ ] Read `apps/web/src/components/VoiceAssistantUI.tsx`.
2. [ ] Read `apps/web/src/lib/mock-pipeline.ts`.
3. [ ] Read `services/voice-agent/src/voice_agent/services/answer_orchestrator.py`.
4. [ ] Read `services/voice-agent/src/voice_agent/api/v1/telephony_ws.py`.
5. [ ] Read `services/voice-agent/src/voice_agent/graph/state_machine.py`.
6. [ ] Read `services/voice-agent/src/voice_agent/schemas/answer.py`.
7. [ ] Read web app API route patterns if any exist.
8. [ ] Read environment config patterns for web and voice-agent.

## Backend Endpoint

9. [ ] Add request/response schemas for text response API.
10. [ ] Add `POST /api/v1/agent/respond` to voice-agent.
11. [ ] Validate non-empty question.
12. [ ] Generate demo `callSid` and `streamSid` for web calls.
13. [ ] Convert request into `FinalTranscriptEvent`.
14. [ ] Call `orchestrate()`.
15. [ ] Return normalized response:
    - question
    - answer
    - intent
    - grounded
    - guard reason if available
    - tool trace
    - composer mode
    - backend status list
16. [ ] Return clear 400 for empty question.
17. [ ] Return clear 500/error response for unexpected failure.

## Web Proxy Route

18. [ ] Add Next.js route `POST /api/voice-agent/respond`.
19. [ ] Read backend base URL from env:
    - `VOICE_AGENT_HTTP_URL`
    - default `http://localhost:8004`
20. [ ] Forward request body to voice-agent endpoint.
21. [ ] Return backend JSON to browser.
22. [ ] Handle backend unavailable with useful error JSON.
23. [ ] Do not expose secrets to browser.

## Frontend Client Adapter

24. [ ] Add a small frontend function:
    - `sendVoiceAgentQuestion(question, source)`
25. [ ] Call `/api/voice-agent/respond`.
26. [ ] Normalize response into UI state shape.
27. [ ] Map backend tool trace to pipeline step details.
28. [ ] Map backend status to LED rail.
29. [ ] Keep browser mock fallback as explicit fallback only.

## VoiceAssistantUI Updates

30. [ ] Replace default `runMockPipeline(question)` path with backend call.
31. [ ] On typed send:
    - add user turn immediately
    - set status to processing
    - call backend
    - append backend answer turn
    - set latest answer
    - set guard state
    - update backend LEDs
32. [ ] On simulated voice:
    - keep current two-click listening UX
    - use next predefined question
    - send that question to backend
33. [ ] Ensure transcript shows the exact question sent to backend.
34. [ ] Show error message if backend fails.
35. [ ] Mark Voice Agent API LED as offline/degraded on failure.
36. [ ] If fallback is used, show that answer is demo fallback.

## Pipeline Display

37. [ ] Use backend response to show:
    - Identify
    - Understand
    - Check
    - Guard
    - Respond
38. [ ] Show selected tool in Check step detail.
39. [ ] Show guard pass/fail.
40. [ ] Show composer mode as mock/Claude in backend rail.

## Claude Mode Visibility

41. [ ] Include composer mode in backend API response.
42. [ ] Display `Claude: mock` or `Claude: connected` in backend rail.
43. [ ] Confirm `VOICE_AGENT_ANSWER_MODE=claude` changes UI result source after service restart.

## Tests

44. [ ] Add backend tests for `/api/v1/agent/respond`.
45. [ ] Test valid question returns answer.
46. [ ] Test empty question returns 400.
47. [ ] Test tool trace included.
48. [ ] Test composer mode included.
49. [ ] Add web proxy route tests if project has API route testing pattern.
50. [ ] Add frontend unit tests for response normalization if existing setup supports it.

## Manual Verify

51. [ ] Start services.
52. [ ] Confirm `curl http://localhost:8004/health`.
53. [ ] Test:

```bash
curl -X POST http://localhost:8004/api/v1/agent/respond \
  -H "Content-Type: application/json" \
  -d '{"question":"Is lisinopril covered on my formulary?","memberId":"CVX-0042-MT","source":"typed"}'
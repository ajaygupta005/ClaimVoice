## Goal

Make the voice assistant feel like a real AI agent instead of a prefilled mock demo.

This component strengthens the existing WS-2 voice UI and WS-7 LangGraph backend by:

- removing prefilled demo conversation state
- showing what the user is saying while recording
- routing more real questions to tools instead of generic escalation
- using existing backend tools before Claude composes the final answer
- making the UI clearly show when Claude, tools, and browser speech are active

## Current Problem

The current voice assistant has several demo-like behaviors:

- Transcript starts with preloaded conversation messages.
- Voice input does not show live/interim speech clearly before submission.
- Some real questions are routed to generic escalation even when they should use tools.
- Claude is only composing from shallow mock tool results.
- The UI says Claude is connected, but the user cannot easily see which tool facts Claude used.
- Browser does not reliably speak the returned answer aloud.

## Required Behavior

### 1. Fresh Conversation State

On `/dashboard/voice`, the transcript must start empty.

Do not initialize UI state from `mockVoiceTranscript`.

Allowed startup UI:

- empty transcript
- short neutral helper text
- collapsed example questions

Not allowed:

- prefilled member/assistant messages
- fake completed conversation history
- automatic answer shown before user asks anything

### 2. Real Voice Input UX

When the user taps the mic:

- start browser speech recognition if available
- show interim speech in the Agent Talk panel as “Listening…”
- do not send to backend until speech recognition ends or the user stops recording
- after final text is available, append it to transcript as the member message
- then call backend `/api/voice-agent/respond`

If browser speech recognition is unavailable:

- keep typed input available
- show a clear browser-limited state
- do not fake a voice transcript unless user explicitly selects a demo example

### 3. Stronger Intent Routing

The backend intent router must handle these question families:

- coverage: MRI, x-ray, therapy, urgent care, ER, dental, vision, imaging
- cost: copay, deductible, out-of-pocket, coinsurance, “how much”
- formulary: drug, medication, prescription, lisinopril, tier
- provider/facility: doctor, PCP, primary care, cardiologist, hospital, clinic, imaging center, “where can I get”
- help/capability: “what can you do”, “how can you help”
- escalation: claim denial, billing dispute, unclear unsafe question

Questions like “where can I get x-ray” should not go directly to escalation. They should use coverage/provider tooling where possible.

### 4. Tool-First Claude Answering

Claude must not invent facts.

Flow:

1. LangGraph identifies intent.
2. LangGraph calls the correct tool.
3. Tool returns structured facts.
4. Claude composes a short member-friendly answer using only those facts.
5. Guard validates the answer.
6. UI displays answer, tool trace, and guard status.

Claude should not choose tools in this component. Tool choice remains deterministic in LangGraph.

### 5. Tool Adapters

Replace shallow mock-only tool responses with adapters that can use existing backend read APIs where available.

Minimum adapters:

- member summary
- plan benefits / coverage
- formulary lookup
- provider search
- escalation

If a real API is unavailable, return a clearly marked demo fallback.

### 6. UI Proof of Real Pipeline

The UI must show:

- current composer mode: `Claude` or `Mock`
- selected intent
- tool called
- short tool result summary
- guard passed/flagged
- backend connection states

Backend connections should remain visually subtle and not dominate the page.

### 7. Browser Speak-Back

After a successful assistant answer:

- use browser `speechSynthesis` to speak the answer
- stop speaking if user taps mic again
- show “Speaking” status while audio is playing
- mark this as browser TTS/demo, not production telephony TTS

This component does not require Google Cloud TTS or external sound packs.

## Acceptance Criteria

- Opening `/dashboard/voice` shows no prefilled transcript.
- Tapping mic shows live/interim speech preview before sending.
- Typed question and voice question both call backend.
- Backend response shows `composer_mode=claude` when configured.
- “Is lisinopril on my formulary?” uses formulary tool.
- “Where can I get x-ray?” does not generic-escalate.
- “Find a primary care doctor” uses provider tool.
- “What can you do?” returns capability/help answer.
- Assistant answer speaks back in browser.
- UI displays tool trace and guard status.

## Out of Scope

- Real Twilio phone call demo
- Real production streaming STT
- Real production streaming TTS
- Letting Claude dynamically choose tools
- Appointment scheduling
- Claims adjudication
## Implementation Plan

### 1. Clean Voice UI Initial State

Update the voice UI so transcript state starts empty.

- Remove `mockVoiceTranscript` as initial state.
- Keep example questions collapsed.
- Add optional empty state text inside transcript panel.
- Add clear transcript/reset action if useful.

Expected result: page no longer looks prefilled.

### 2. Improve Voice Recording Flow

Update browser mic behavior.

- On mic start, begin speech recognition.
- Store interim speech separately from submitted transcript.
- Display interim speech in Agent Talk panel.
- On recognition final/end, submit the final text.
- If recognition is unavailable, leave typed input as the primary path.

States:

- `idle`
- `listening`
- `processing`
- `speaking`
- `error`

### 3. Strengthen Backend Intent Router

Update `understand_intent`.

Add routing coverage for:

- x-ray / imaging center
- dental / vision
- PCP / primary care provider
- “where can I get”
- “nearest doctor”
- “what can you do”

Keep fallback escalation only for genuinely unsupported or unclear questions.

### 4. Strengthen Tool Layer

Update `call_tool`.

Move from one-line mock strings to structured tool results.

Each tool should return:

- `tool_name`
- `args`
- `facts`
- `source`
- `is_demo`
- `summary`

Use real read APIs when available:

- eligibility member summary
- plan benefits
- formulary search
- provider search

If unavailable, return deterministic demo facts with `is_demo=true`.

### 5. Keep Claude as Composer Only

Update Claude composer prompt/input so Claude receives:

- user question
- intent
- tool name
- structured facts
- safety constraints

Claude must answer only from facts.

For escalation/help paths:

- help can be deterministic or Claude-composed from allowed capability facts
- escalation should remain safe and short

### 6. Improve Guard and Tool Trace

Update guard/UI response payload so frontend can show:

- intent
- tool called
- factual source
- guard result
- composer mode
- whether answer used demo fallback

UI should display these without clutter.

### 7. Add Browser Speak-Back

In the frontend:

- call `speechSynthesis.speak()` after assistant answer arrives
- set UI state to `speaking`
- stop speech when user starts a new mic recording
- handle unsupported browser gracefully

No external TTS provider is required in this component.

### 8. Tests

Backend tests:

- formulary question routes to formulary tool
- x-ray question routes to coverage/provider path
- PCP question routes to provider tool
- help question does not escalate incorrectly
- claim denial still escalates
- Claude composer receives structured tool facts

Frontend tests where available:

- initial transcript is empty
- typing submits backend request
- speech recognition final text submits backend request
- backend `composer_mode=claude` displays Claude status
- speak-back is invoked after answer

## Manual Demo Script

1. Open `/dashboard/voice`.
2. Confirm transcript is empty.
3. Ask: “Is lisinopril on my formulary?”
4. Confirm:
   - formulary tool used
   - Claude answer shown
   - guard passed
   - browser speaks answer
5. Ask: “Where can I get an x-ray?”
6. Confirm it does not generic-escalate.
7. Ask: “What can you do?”
8. Confirm assistant explains supported capabilities.
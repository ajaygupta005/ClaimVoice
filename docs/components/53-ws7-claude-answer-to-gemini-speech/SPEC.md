# Component 53 - WS-7 Claude Answer to Gemini Speech

> **Workstream**: WS-7 voice-agent runtime + WS-2 browser voice UI  
> **Depends on**: Component 52 - WS-2 Gemini Live Browser Client

## Goal

Use Gemini Live only to speak the final ClaimVoice answer aloud.

The answer text must still come from the existing ClaimVoice agent flow:

1. user transcript
2. intent routing
3. Eligibility / Providers tools
4. Claude answer composer
5. hallucination guard
6. final answer text
7. Gemini speech output

## Required Behavior

After `/api/v1/agent/respond` returns a final answer:

- send the final answer text to Gemini Live for speech output
- stream or return playable audio to the browser
- play the audio in the UI
- return to `Ready` after playback completes

The UI must label this correctly:

```text
Answer: Claude
Voice: Gemini Live
```

Do not call this:

```text
Claude voice
```

## Interrupt Behavior

If the user taps the mic while Gemini is speaking:

- stop playback
- close or reset the active Gemini output stream
- return to listening state
- do not submit duplicate questions

## Acceptance Criteria

- Claude answer appears in transcript before or as speech starts.
- Gemini audio is audible when available.
- UI enters `Speaking` only after audio starts.
- UI returns to `Ready` on playback end.
- User can interrupt speech and ask another question.
- Browser/system TTS fallback still works if Gemini speech fails.

## Out of Scope

- Gemini deciding the answer.
- Gemini calling tools.
- Changing the hallucination guard.
- Twilio audio return.


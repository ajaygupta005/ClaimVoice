# Component 36 - WS-2/WS-7 Voice UI Backend Bridge

> **Workstream**: WS-2 frontend + WS-7 voice-agent integration  
> **Depends on**: Component 35 - WS-7 Claude Answer Composer

## Goal

Connect the `/dashboard/voice` UI to the real voice-agent backend pipeline.

Today the Voice tab runs a browser-only mock pipeline:

```text
UI button/input -> runMockPipeline() -> mock transcript/answer
# Component 70 - WS-2 SBC Evidence Citations

## Purpose

Show SBC RAG evidence in the WS-2 UI when the voice agent uses retrieved plan-document chunks.

The UI should help the evaluator see why an answer was grounded without pretending evidence exists when RAG is unavailable.

## Required Behavior

- The browser voice UI can render evidence returned by WS-7.
- Evidence uses:
  - `sectionName`
  - `sourceFile`
  - `chunkText`
  - optional `distance`
- Evidence appears only when the response includes real chunks.
- Empty or unavailable RAG state shows a neutral "no source evidence available" state only if useful.
- Demo fallback should never create fake citations.

## UI Behavior

- Keep the main answer readable.
- Show evidence in a compact citation/evidence panel near the answer.
- Long chunk text should be truncated with a way to expand.
- Source file and section name should be visible.
- Evidence rendering must not break mobile or desktop layout.

## Data Contract

The UI should consume normalized WS-7 response metadata rather than calling the RAG endpoint directly from the browser.

Minimum evidence item:

- `text`
- `sectionName`
- `sourceFile`
- `distance`

## Acceptance Criteria

- A RAG-backed answer shows at least one evidence item.
- A structured-only answer does not show fake citations.
- Empty chunks do not render stale evidence from the previous turn.
- Long evidence text does not overflow the transcript panel.
- Typecheck passes for the web app.

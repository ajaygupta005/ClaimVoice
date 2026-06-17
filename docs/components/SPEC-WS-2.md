
# WS-2 SPEC: Frontend and UX

## What I am building

I am building the web frontend for ClaimVoice. The goal is to make the project usable from the browser, so a user can upload an insurance card, see extracted plan information, search providers, talk to the assistant, and review past calls.

This is the main user-facing part of the project. Even if backend services are mocked during development, the frontend should clearly show how the complete product will work.

## Why this is needed

ClaimVoice has many backend services: document AI, eligibility, providers, voice agent, and telephony. Without a clean frontend, the project is difficult to demo and understand.

The frontend connects these pieces into one simple dashboard. A non-technical user should be able to understand the flow:

1. Upload insurance card
2. Confirm extracted details
3. View plan benefits
4. Search nearby in-network providers
5. Ask questions using voice
6. Review call history

## Scope

The frontend will be built using Next.js and TypeScript.

Main screens:

- Card upload
- Plan details
- Provider search
- Voice assistant
- Call history

Main components:

- Dashboard shell with sidebar navigation
- Card upload UI
- Extracted fields review UI
- Provider list / map placeholder
- Browser voice assistant screen
- Conversation transcript panel
- Tool-call / safety-check progress panel
- Call playback screen
- Tutorial / onboarding flow

## User flow

### 1. Card upload

The user uploads an insurance card image.

The UI should show:

- Selected file name
- Upload progress
- Extraction status
- Extracted fields
- Confidence score
- Fields needing review

If OCR/backend is not connected, mock data can be used, but the UI should not reuse wrong demo data for a real uploaded card.

### 2. Plan details

Once card details are available, the plan screen shows member and plan information.

Example fields:

- Member name
- Member ID
- Plan name
- Group number
- Coverage status
- Deductible
- Coinsurance
- Prior authorization requirements

### 3. Provider search

The provider screen shows nearby in-network providers.

For demo, mock provider data is acceptable.

The UI should show:

- Provider name
- Specialty
- Distance
- In-network status
- Accepting patients
- Rating / quality indicator

A map can be shown, but if full map integration is not ready, it should be labelled as demo/mock and not look misleading.

### 4. Voice assistant

The voice screen is the main demo screen.

It should support:

- Push-to-talk
- Typed fallback
- Assistant response
- Text-to-speech playback
- Conversation transcript
- Latest answer card
- Tool-call trace / safety stages

The chat should be easy to read. New messages should be visible without unnecessary scrolling.

### 5. Tutorial

A first-time user may not understand healthcare terms or the workflow. A short tutorial should explain the product in simple terms.

Tutorial steps:

1. Upload your insurance card
2. Review extracted details
3. Ask a question like “Is MRI covered?”
4. See the assistant verify the answer
5. Check providers or call history

The tutorial should use simple language, not provider/admin language.

## Data handling

During development, mock data can be used for:

- Member details
- Plan benefits
- Provider list
- Voice transcript
- Tool-call trace
- Call history

Mock data should be stored separately from UI components so later it can be replaced with real API data.

## Acceptance criteria

- User can navigate between all dashboard tabs.
- Card upload screen shows a complete extraction flow.
- Voice screen has readable chat and visible assistant status.
- Provider screen shows understandable provider results.
- Tutorial explains the workflow clearly.
- UI works on desktop and reasonable laptop screen sizes.
- No raw generated build files are committed.

## Testing plan

Manual testing:

- Open dashboard
- Upload a sample card
- Check extracted field UI
- Go to voice tab
- Ask a typed fallback question
- Confirm assistant answer appears
- Check provider screen
- Check tutorial flow

Technical checks:

- `pnpm install`
- `pnpm dev`
- `pnpm build`
- TypeScript should pass without errors

## Out of scope

This workstream does not train OCR models.
It does not implement the real eligibility engine.
It does not implement the full telephony backend.
It only consumes or mocks those services for the user interface.
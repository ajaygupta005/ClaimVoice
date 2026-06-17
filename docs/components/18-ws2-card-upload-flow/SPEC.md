e# Component 18 - WS-2 Card Upload Flow

> **Branch**: `feat/ws2-card-upload-flow` | **Day(s)**: 18 | **Workstream**: WS-2

## Goal

Replace the Card tab placeholder with a working insurance-card upload flow.

This component is still frontend-focused. Real OCR is not required here. The goal is to show the correct product flow: user uploads a card, the UI shows extraction progress, then extracted fields appear with confidence scores and review status.

## Scope

Build the Card tab UI under:

- `/dashboard/card`

Main pieces:

- Upload area
- File selected state
- Mock extraction progress
- Extracted fields section
- Review queue section
- Reset action

The UI should look like a realistic card intake workflow, not just a plain file input.

## User Flow

1. User opens the Card tab.
2. User uploads or selects a card image.
3. UI shows the selected file name.
4. UI moves through mock states:
   - ready
   - uploading
   - extracting
   - review ready
5. UI shows extracted card fields.
6. Low-confidence fields are highlighted for review.
7. User can reset and try again.

## Mock Data

Use frontend mock data for now.

Example extracted fields:

- Member ID
- Member name
- Group number
- Plan name
- RX BIN
- RX PCN
- Carrier
- Effective date

Each field should include:

- label
- value
- confidence
- source
- status

Example statuses:

- confirmed
- review
- missing

## UI Requirements

The upload panel should show:

- title: Insurance card extraction
- file picker
- drag/drop style visual area
- selected file name
- progress bar
- extraction status badge

The extracted fields section should show:

- field label
- extracted value
- confidence percentage
- status badge

The review queue should show only fields below the confidence threshold.

Use 90% as the mock threshold for review.

## Important Behavior

If a user uploads a new card, the UI should not keep showing old unrelated demo values without indicating it is mock extraction.

For now, mock values are acceptable, but the screen should make it clear that this is a simulated extraction until the Document AI backend is connected.

## Out of Scope

- Real LayoutLMv3 OCR.
- Real PaddleOCR fallback.
- Real Document AI API integration.
- Real image storage.
- Authentication or member lookup.

Those will be handled by other workstreams.

## Acceptance Criteria

- Card tab no longer shows a placeholder.
- User can select an image file.
- Selected file name appears in the UI.
- Mock progress/extraction state is shown.
- Extracted fields render after mock extraction.
- Low-confidence fields appear in a review queue.
- Reset clears the selected file and extraction results.
- UI works with the existing dashboard shell.
- No backend service is required for this component.
# Component 59 - WS-2 Card Upload to Document AI

## Purpose

Wire the WS-2 Card page to real Document AI card OCR and payor classification APIs while preserving a safe demo fallback when model artifacts are unavailable.

## Current State

The card upload UI currently demonstrates upload and extraction, but the extracted fields are mock data. Document AI exposes service routes that can be used:

- `POST /api/v1/card_ocr`
- `POST /api/v1/payor_classify`

These routes may return unavailable if model runners or artifacts are not loaded.

## Scope

Connect the Card Upload flow to:

- card image upload
- base64 conversion
- card OCR request
- payor classification request
- confidence and low-confidence display
- model version display
- unavailable fallback

## Required Behavior

- User uploads an insurance card image.
- UI sends the image to Document AI through the shared WS-2 API client.
- OCR fields appear in the existing review UI.
- Low-confidence fields are visibly marked.
- Payor classification appears alongside extracted card fields.
- If Document AI returns unavailable, UI shows a clear "Document AI unavailable" state.
- Mock extraction remains available only as explicit demo fallback.

## Data Contract

Card OCR response should be normalized into:

- member name
- member ID
- plan name
- group number
- payer name
- BIN/PCN/RxGroup when available
- extracted fields with confidence
- low-confidence field names
- model version

Payor classification response should be normalized into:

- payor label
- confidence
- source model

## Non-Goals

- No model training.
- No OCR model artifact changes.
- No database persistence unless an existing endpoint already supports it.
- No login/member account linking.

## Acceptance Criteria

- Uploading a card image calls Document AI.
- OCR and payor classification results render in the Card UI.
- Low-confidence fields are visible.
- Model-unavailable errors do not break the page.
- Demo fallback is explicitly labeled.
- Typecheck and build pass.


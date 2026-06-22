# Component 59 - WS-2 Card Upload to Document AI Plan

## Implementation Steps

1. Review current Card Upload flow.
   - Identify where mock extraction is produced.
   - Identify existing field review state.

2. Add Document AI client calls.
   - Use the shared API client from Component 58.
   - Call `card_ocr`.
   - Call `payor_classify`.

3. Normalize responses.
   - Map backend field names to UI field names.
   - Preserve confidence values.
   - Preserve model version/source model.

4. Update UI states.
   - Uploading.
   - Extracting.
   - Success.
   - Low-confidence review.
   - Document AI unavailable.
   - Demo fallback.

5. Add error handling.
   - 400 invalid image.
   - 503 model unavailable.
   - network failure.
   - unexpected response shape.

6. Add tests.
   - Successful OCR render.
   - Low-confidence render.
   - Payor classification render.
   - Document AI unavailable fallback.

## Suggested Files

- `apps/web/src/components/CardUploadFlow.tsx`
- `apps/web/src/lib/api/document-ai.ts`
- `apps/web/src/app/api/document-ai/*` if proxy routes are needed
- Card upload tests

## Validation

- `pnpm --filter web typecheck`
- `pnpm --filter web build`
- Playwright or component test for upload flow

## Risks

- Document AI may be healthy but model runners unavailable.
- Large images may need compression before upload.
- OCR field names may not match UI expectations.

## Done When

- Card Upload can use real Document AI output.
- Demo fallback is explicit.
- A user can review extracted data confidently.


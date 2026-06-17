# WS-3 · Document AI Research Notes

## Problem statement

WS-3 must turn insurance cards and SBCs into structured data that is reliable enough for the Eligibility service and voice agent to answer plan questions.

Key research goals:
- Choose the right model architecture for card OCR and SBC parsing
- Create a label schema that matches downstream coverage extraction needs
- Identify low-cost fallback strategies for low-confidence text
- Define evaluation metrics for field-level accuracy and model bias

## Architecture choices

### Card OCR
- Base model: `microsoft/layoutlmv3-base`
- Task: region-aware structured extraction of card fields
- Target fields: `member_id`, `name`, `dob`, `group_number`, `plan_name`, `effective_date`, `rx_bin`, `rx_pcn`, `rx_group`, `phone`, `carrier`, `plan_type`
- Training data: synthetic PNG cards with JSONL labels
- Output: JSON payload with field values + normalized confidence scores

### Payor classification
- Base model: ResNet-50
- Task: classify payor from insurance-card image and logo region
- Classes: Aetna, UHC, Cigna, BCBS, Humana, Kaiser, Anthem, Other
- Use: fallback when textual payer name is ambiguous and as metadata for downstream plan mapping

### SBC parser
- Base model: LayoutLMv3 or a document encoder capable of handling tables and multi-block text
- Task: extract SBC section headings, benefit rows, and network-specific cost-sharing values
- Input: real SBC PDFs from `data/raw/sbcs/`
- Output: structured JSON suitable for downstream SBC RAG or plan knowledge graph

## Fallback strategy

When LayoutLMv3 output is low-confidence or missing critical fields:
- use Claude prompt engineering to disambiguate field values via an instructor-style extraction flow
- use PaddleOCR as a secondary text extractor for noisy image regions
- use a confidence threshold to trigger "ask user to confirm" flow in the voice UX later

## Data strategy

### Synthetic card generation
- Generate 100+ cards using `data/ingest/synthetic_cards.py`
- Use 4 payor templates and Faker-generated member details
- Produce `labels.jsonl` with normalized bounding boxes per field
- Use augmentation: rotation, brightness jitter, blur, glare simulation

### Real SBC documents
- Download 5–10 public SBC PDFs with diverse payors
- Keep metadata sidecars with source URL and payor mapping
- Create a small hand-labeled evaluation set for key sections and table row extraction

## Evaluation metrics

### Card OCR
- Field-level precision / recall / F1 for each target field
- Overall document extraction accuracy
- Confidence-calibrated threshold performance

### Payor classification
- Top-1 accuracy on synthetic + real cards
- Confusion matrix for the 8 payor classes

### SBC parsing
- Section detection accuracy
- Table row extraction F1 on essential benefit rows
- End-to-end JSON completeness for a sample of documents

## Risk areas

- Synthetic cards may not generalize to real-world scan/photo noise.
- Payor logos are visually similar; low confidence should not break downstream matching.
- SBC PDFs vary widely in layout and table structure.
- LayoutLMv3 training is compute-heavy; use small prototype data first.

## Next research tasks

1. Build the card field label schema and verify with downstream eligibility needs.
2. Decide whether to encode card fields as token-level labels or region-level labels.
3. Compare LayoutLMv3 with a Donut-style document model for the SBC parser.
4. Add a model card for each trained model after initial experiments.
5. Design the JSON contract for downstream services clearly in `SPEC.md`.

## References

- LayoutLMv3: document-level visual+text representation
- ResNet-50: image classification backbone
- PaddleOCR: robust OCR fallback for noisy regions
- Anthropic Claude + instructor: semantic field disambiguation
- DVC + MLflow: reproducible model artifact tracking

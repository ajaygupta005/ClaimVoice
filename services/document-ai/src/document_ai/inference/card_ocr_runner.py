from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForTokenClassification, LayoutLMv3Processor

FIELD_NAMES: list[str] = [
    "member_id",
    "name",
    "dob",
    "group_number",
    "plan_name",
    "effective_date",
    "rx_bin",
    "rx_pcn",
    "rx_group",
    "phone",
    "carrier",
    "plan_type",
]

# Path anchored to the service root (3 parents up from this file inside src/document_ai/inference/)
_SERVICE_ROOT = Path(__file__).parents[3]
_DEFAULT_MODEL_DIR = _SERVICE_ROOT / "artifacts" / "card_ocr" / "latest"

_LOW_CONF_THRESHOLD = 0.80
_COORD_MAX = 1000  # LayoutLMv3 normalises bboxes to [0, 1000] before the model sees them


class CardOCRRunner:
    """Runs LayoutLMv3 NER inference on an insurance card image.

    Returns one field object per canonical field in FIELD_NAMES, matching the
    D2 JSON contract defined in SPEC.md.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        checkpoint = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR
        if not checkpoint.exists():
            raise FileNotFoundError(
                f"Card OCR checkpoint not found at '{checkpoint}'. "
                "Run 'just train.card_ocr' to train the model, or place a "
                "pre-trained checkpoint under 'artifacts/card_ocr/latest/' "
                "(must contain config.json, model.safetensors, and tokenizer files)."
            )

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._processor = LayoutLMv3Processor.from_pretrained(
            str(checkpoint), apply_ocr=True
        )
        self._model = AutoModelForTokenClassification.from_pretrained(
            str(checkpoint)
        ).to(self._device)
        self._model.eval()
        self._id2label: dict[int, str] = self._model.config.id2label

    def __call__(
        self,
        image: Union[Image.Image, np.ndarray],
        card_id: str,
    ) -> dict:
        """Run card OCR on *image* and return the D2 JSON payload.

        Args:
            image: A PIL RGB image or a numpy uint8 array (H, W, 3).
            card_id: Opaque identifier for the card; echoed in the response.

        Returns:
            {
                "card_id": str,
                "fields": [{field_name, value, confidence, bbox}, ...],
                "low_confidence_fields": [field_name, ...],
                "model_version": str,
            }
        """
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image).convert("RGB")
        elif image.mode != "RGB":
            image = image.convert("RGB")

        img_w, img_h = image.size  # PIL convention: (width, height)

        # --- Step 1: OCR via LayoutLMv3ImageProcessor ---
        # apply_ocr=True triggers pytesseract internally and returns words + boxes.
        img_enc = self._processor.image_processor([image], return_tensors="pt")
        words: list[str] = img_enc["words"][0]
        raw_boxes = img_enc["boxes"][0]
        # Normalised [0, 1000] bboxes; convert tensor → list for indexing convenience.
        word_boxes: list[list[int]] = (
            raw_boxes.tolist() if hasattr(raw_boxes, "tolist") else raw_boxes
        )

        # --- Step 2: Tokenise OCR words for the model ---
        tok_enc = self._processor.tokenizer(
            words,
            boxes=word_boxes,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            is_split_into_words=True,
            padding="max_length",
        )
        # word_ids maps each token position → its source word index (None for specials).
        word_ids: list[int | None] = tok_enc.word_ids(batch_index=0)

        # --- Step 3: Forward pass ---
        model_input = {
            "pixel_values": img_enc["pixel_values"].to(self._device),
            **{k: v.to(self._device) for k, v in tok_enc.items()},
        }
        with torch.no_grad():
            logits = self._model(**model_input).logits  # (1, seq_len, num_labels)

        probs = torch.softmax(logits[0], dim=-1)  # (seq_len, num_labels)
        pred_ids = probs.argmax(dim=-1).tolist()
        token_confs = probs.max(dim=-1).values.tolist()

        # --- Step 4: Collapse sub-word tokens → word-level predictions ---
        # For multi-token words keep only the first sub-token's prediction.
        word_label: dict[int, str] = {}
        word_conf: dict[int, float] = {}
        for token_idx, w_id in enumerate(word_ids):
            if w_id is None or w_id in word_label:
                continue
            word_label[w_id] = self._id2label.get(pred_ids[token_idx], "O")
            word_conf[w_id] = token_confs[token_idx]

        # --- Step 5: Decode BIO spans → field values ---
        fields = self._build_field_list(
            words, word_boxes, word_label, word_conf, img_w, img_h
        )
        low_conf = [
            f["field_name"]
            for f in fields
            if f["value"] and f["confidence"] < _LOW_CONF_THRESHOLD
        ]

        return {
            "card_id": card_id,
            "fields": fields,
            "low_confidence_fields": low_conf,
            "model_version": self._model.config.name_or_path or "card_ocr_layoutlm_v0.1",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_field_list(
        self,
        words: list[str],
        word_boxes: list[list[int]],
        word_label: dict[int, str],
        word_conf: dict[int, float],
        img_w: int,
        img_h: int,
    ) -> list[dict]:
        """Walk the word sequence, decode BIO tags, and return one dict per field."""
        best_span: dict[str, dict] = {}  # field_name -> highest-confidence span found

        current_field: str | None = None
        span_words: list[str] = []
        span_confs: list[float] = []
        span_boxes: list[list[int]] = []

        def _commit() -> None:
            if not current_field or not span_words:
                return
            mean_conf = float(np.mean(span_confs))
            # Merge all per-word bboxes into a single bounding box.
            merged = [
                min(b[0] for b in span_boxes),
                min(b[1] for b in span_boxes),
                max(b[2] for b in span_boxes),
                max(b[3] for b in span_boxes),
            ]
            # Scale from LayoutLMv3 [0, 1000] space back to pixel coordinates.
            pixel_bbox = [
                int(merged[0] * img_w / _COORD_MAX),
                int(merged[1] * img_h / _COORD_MAX),
                int(merged[2] * img_w / _COORD_MAX),
                int(merged[3] * img_h / _COORD_MAX),
            ]
            candidate = {
                "field_name": current_field,
                "value": " ".join(span_words),
                "confidence": round(mean_conf, 4),
                "bbox": pixel_bbox,
            }
            # Keep whichever span has the higher confidence for this field.
            if (
                current_field not in best_span
                or candidate["confidence"] > best_span[current_field]["confidence"]
            ):
                best_span[current_field] = candidate

        for w_id in range(len(words)):
            label = word_label.get(w_id, "O")
            conf = word_conf.get(w_id, 0.0)

            if label.startswith("B-"):
                _commit()
                current_field = label[2:]
                span_words = [words[w_id]]
                span_confs = [conf]
                span_boxes = [word_boxes[w_id]]
            elif label.startswith("I-") and current_field == label[2:]:
                span_words.append(words[w_id])
                span_confs.append(conf)
                span_boxes.append(word_boxes[w_id])
            else:
                _commit()
                current_field = None
                span_words = []
                span_confs = []
                span_boxes = []

        _commit()  # flush the final span

        # Return one entry per canonical field in declaration order.
        return [
            best_span.get(
                field_name,
                {
                    "field_name": field_name,
                    "value": "",
                    "confidence": 0.0,
                    "bbox": None,
                },
            )
            for field_name in FIELD_NAMES
        ]

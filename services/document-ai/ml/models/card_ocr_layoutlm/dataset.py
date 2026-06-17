from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal

import torch
from PIL import Image
from torch.utils.data import Dataset
from transformers import LayoutLMv3Processor

# ---------------------------------------------------------------------------
# Label scheme
# ---------------------------------------------------------------------------
# Must stay in sync with FIELD_NAMES in src/document_ai/inference/card_ocr_runner.py.
# The runner uses model.config.id2label (written by save_pretrained) so the
# integer ordering here is the source of truth for both training and inference.

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

# "O" first, then B-/I- interleaved so B-<field> and I-<field> are adjacent.
LABEL_LIST: list[str] = ["O"] + [f"{pfx}-{field}" for field in FIELD_NAMES for pfx in ("B", "I")]
# Total: 1 + 2 * 12 = 25

TAG_TO_ID: dict[str, int] = {tag: i for i, tag in enumerate(LABEL_LIST)}
ID_TO_TAG: dict[int, str] = {i: tag for i, tag in enumerate(LABEL_LIST)}

# CrossEntropyLoss ignores positions with this value (special tokens, padding,
# and non-first sub-word tokens produced by the BPE tokeniser).
IGNORED_LABEL: int = -100


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class CardOCRDataset(Dataset):
    """LayoutLMv3 token-classification dataset over synthetic insurance cards.

    Each record in ``labels.jsonl`` is one card.  The dataset splits records
    *stratified by payor class* so every class appears proportionally in
    both train and val splits.

    ``__getitem__`` returns a dict with:
        ``pixel_values``  – (3, 224, 224) float tensor
        ``input_ids``     – (max_length,)  long tensor
        ``attention_mask``– (max_length,)  long tensor
        ``bbox``          – (max_length, 4) long tensor  [0, 1000] normalised
        ``labels``        – (max_length,)  long tensor  −100 for ignored positions

    Args:
        data_dir:     Directory containing ``labels.jsonl`` and the PNG files.
        processor:    ``LayoutLMv3Processor`` initialised with ``apply_ocr=False``.
        split:        ``"train"`` or ``"val"``.
        val_fraction: Fraction of each payor class held out for validation.
        seed:         Shuffle seed for reproducible splits.
        max_length:   Tokeniser truncation / padding length (default 512).
    """

    def __init__(
        self,
        data_dir: str | Path,
        processor: LayoutLMv3Processor,
        split: Literal["train", "val"] = "train",
        val_fraction: float = 0.2,
        seed: int = 42,
        max_length: int = 512,
    ) -> None:
        data_dir = Path(data_dir)
        jsonl_path = data_dir / "labels.jsonl"
        if not jsonl_path.exists():
            raise FileNotFoundError(
                f"labels.jsonl not found at '{jsonl_path}'. "
                "Run `python data/ingest/synthetic_cards.py` first."
            )

        all_records: list[dict] = [
            json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()
        ]

        # Stratified split: group by payor class, shuffle, take first n_val for val.
        by_class: dict[str, list[dict]] = {}
        for rec in all_records:
            by_class.setdefault(rec["payor_class"], []).append(rec)

        rng = random.Random(seed)
        chosen: list[dict] = []
        for recs in by_class.values():
            shuffled = recs.copy()
            rng.shuffle(shuffled)
            n_val = max(1, round(len(shuffled) * val_fraction))
            chosen.extend(shuffled[:n_val] if split == "val" else shuffled[n_val:])

        # Pre-resolve image paths so __getitem__ is fast.
        for rec in chosen:
            rec["_img_path"] = str(data_dir / rec["image_path"])

        self._records = chosen
        self._processor = processor
        self._max_length = max_length

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        rec = self._records[idx]
        image = Image.open(rec["_img_path"]).convert("RGB")
        words: list[str] = rec["words"]
        boxes: list[list[int]] = rec["boxes"]  # already [0, 1000] normalised
        ner_tags: list[str] = rec["ner_tags"]

        # Convert string NER tags → integer label IDs.
        # Unknown tags (should not occur with clean synthetic data) fall back to O (0).
        word_labels: list[int] = [TAG_TO_ID.get(tag, 0) for tag in ner_tags]

        # ── Step 1: image encoding ───────────────────────────────────────
        # image_processor handles resize / normalise; returns (1, 3, 224, 224).
        img_enc = self._processor.image_processor([image], return_tensors="pt")

        # ── Step 2: text + layout encoding with label alignment ──────────
        # is_split_into_words=True: each element of `words` is a pre-split token.
        # word_labels: the tokeniser aligns these to sub-word positions, placing
        #   -100 on special tokens, padding, and non-first sub-word pieces.
        # LayoutLMv3Tokenizer is word-oriented by design (no fast variant exists).
        # It takes `text` as a pre-split word list and `boxes` aligned to those
        # words — `is_split_into_words` is not a valid parameter here.
        tok_enc = self._processor.tokenizer(
            words,
            boxes=boxes,
            word_labels=word_labels,
            truncation=True,
            max_length=self._max_length,
            padding="max_length",
            return_tensors="pt",
        )

        # Merge and drop the leading batch dimension (DataLoader re-adds it).
        return {
            "pixel_values": img_enc["pixel_values"].squeeze(0),
            **{k: v.squeeze(0) for k, v in tok_enc.items()},
        }

    # ------------------------------------------------------------------

    @staticmethod
    def label_list() -> list[str]:
        return LABEL_LIST.copy()

    @staticmethod
    def num_labels() -> int:
        return len(LABEL_LIST)

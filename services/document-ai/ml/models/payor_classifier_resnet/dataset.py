from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

# Must match the order in payor_classifier_runner.py
PAYOR_CLASSES: list[str] = [
    "Aetna",
    "UHC",
    "Cigna",
    "BCBS",
    "Humana",
    "Kaiser",
    "Anthem",
    "Other",
]
CLASS_TO_IDX: dict[str, int] = {cls: i for i, cls in enumerate(PAYOR_CLASSES)}

# ImageNet stats used by the pretrained ResNet-50 backbone
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

# Insurance cards should not be horizontally flipped (text becomes mirrored),
# but mild rotation and colour jitter simulate real-world scan variability.
TRAIN_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.RandomRotation(degrees=4),
        transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ]
)

VAL_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ]
)


class SyntheticCardDataset(Dataset):
    """PyTorch Dataset over the synthetic insurance-card images.

    Reads ``labels.jsonl`` produced by ``data/ingest/synthetic_cards.py`` and
    returns ``(image_tensor, class_index)`` pairs.

    The split is *stratified* — each payor class contributes the same
    ``val_fraction`` to the validation set, so class balance is preserved in
    both splits.

    Args:
        data_dir:     Directory containing ``labels.jsonl`` and the PNG files.
        split:        ``"train"`` or ``"val"``.
        val_fraction: Fraction of each class reserved for validation (default 0.2).
        seed:         Shuffle seed for reproducible splits (default 42).
    """

    def __init__(
        self,
        data_dir: str | Path,
        split: Literal["train", "val"] = "train",
        val_fraction: float = 0.2,
        seed: int = 42,
    ) -> None:
        data_dir = Path(data_dir)
        jsonl_path = data_dir / "labels.jsonl"
        if not jsonl_path.exists():
            raise FileNotFoundError(
                f"labels.jsonl not found at '{jsonl_path}'. "
                "Run `python data/ingest/synthetic_cards.py` first."
            )

        records = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]

        # Group by class, shuffle within each group, then split.
        by_class: dict[str, list[dict]] = {}
        for rec in records:
            by_class.setdefault(rec["payor_class"], []).append(rec)

        rng = random.Random(seed)
        self._samples: list[tuple[Path, int]] = []

        for cls in PAYOR_CLASSES:
            class_recs = by_class.get(cls, []).copy()
            rng.shuffle(class_recs)
            n_val = max(1, round(len(class_recs) * val_fraction))
            chosen = class_recs[:n_val] if split == "val" else class_recs[n_val:]
            for rec in chosen:
                self._samples.append((data_dir / rec["image_path"], CLASS_TO_IDX[cls]))

        self._transform = TRAIN_TRANSFORMS if split == "train" else VAL_TRANSFORMS

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        img_path, label = self._samples[idx]
        image = Image.open(img_path).convert("RGB")
        return self._transform(image), label

    @staticmethod
    def class_names() -> list[str]:
        return PAYOR_CLASSES.copy()

    @staticmethod
    def num_classes() -> int:
        return len(PAYOR_CLASSES)

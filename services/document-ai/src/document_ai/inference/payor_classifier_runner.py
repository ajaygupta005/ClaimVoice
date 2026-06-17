from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet50

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

_SERVICE_ROOT = Path(__file__).parents[3]
_DEFAULT_MODEL_DIR = _SERVICE_ROOT / "artifacts" / "payor_classifier" / "latest"
_WEIGHTS_FILENAME = "model.safetensors"

# Confidence below this threshold causes the prediction to fall back to "Other".
_CONFIDENCE_THRESHOLD = 0.50

# ImageNet normalisation — standard for ResNet-50 fine-tuned from torchvision weights.
_PREPROCESS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)


def _load_weights(model: nn.Module, weights_path: Path) -> None:
    """Load model.safetensors or fall back to a plain torch checkpoint."""
    suffix = weights_path.suffix.lower()
    if suffix == ".safetensors":
        try:
            from safetensors.torch import load_file
        except ImportError as exc:
            raise ImportError(
                "The 'safetensors' package is required to load .safetensors weights. "
                "Install it with: pip install safetensors"
            ) from exc
        state_dict = load_file(str(weights_path), device="cpu")
    else:
        state_dict = torch.load(str(weights_path), map_location="cpu")
        if "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]

    model.load_state_dict(state_dict)


class PayorClassifierRunner:
    """Classifies the payor (insurance carrier) from an insurance card image.

    Uses a ResNet-50 fine-tuned on synthetic card logo crops.  The model head
    has ``len(PAYOR_CLASSES)`` output units.  Predictions whose softmax
    confidence falls below ``_CONFIDENCE_THRESHOLD`` are reported as "Other".
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        checkpoint_dir = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR
        weights_path = checkpoint_dir / _WEIGHTS_FILENAME

        if not checkpoint_dir.exists():
            raise FileNotFoundError(
                f"Payor classifier checkpoint directory not found at '{checkpoint_dir}'. "
                "Train with 'just train.payor_classifier' or place a pre-trained "
                "checkpoint under 'artifacts/payor_classifier/latest/'."
            )
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Weights file '{_WEIGHTS_FILENAME}' not found in '{checkpoint_dir}'. "
                "Expected path: '{weights_path}'."
            )

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Build the same ResNet-50 head used during training.
        model = resnet50(weights=None)
        model.fc = nn.Linear(model.fc.in_features, len(PAYOR_CLASSES))
        _load_weights(model, weights_path)
        model.to(self._device)
        model.eval()
        self._model = model

    def __call__(
        self,
        image: Image.Image | np.ndarray,
    ) -> dict:
        """Classify the payor shown on *image*.

        Args:
            image: A PIL RGB image or a numpy uint8 array (H, W, 3).

        Returns:
            ``{"payor_class": str, "confidence": float}``

            ``payor_class`` is one of ``PAYOR_CLASSES``.  If the model's top-1
            confidence is below ``_CONFIDENCE_THRESHOLD`` the result is forced
            to ``"Other"`` regardless of the argmax class.
        """
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image).convert("RGB")
        elif image.mode != "RGB":
            image = image.convert("RGB")

        tensor = _PREPROCESS(image).unsqueeze(0).to(self._device)  # (1, 3, 224, 224)

        with torch.no_grad():
            logits = self._model(tensor)  # (1, num_classes)

        probs = torch.softmax(logits[0], dim=-1)  # (num_classes,)
        confidence = float(probs.max().item())
        predicted_idx = int(probs.argmax().item())
        predicted_class = PAYOR_CLASSES[predicted_idx]

        if confidence < _CONFIDENCE_THRESHOLD:
            predicted_class = "Other"

        return {
            "payor_label": predicted_class,
            "confidence": round(confidence, 4),
            "source_model": "payor_classifier_resnet_v0.1",
        }

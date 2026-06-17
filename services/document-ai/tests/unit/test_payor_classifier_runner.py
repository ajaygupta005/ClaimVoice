from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from PIL import Image

from document_ai.inference.payor_classifier_runner import (
    PAYOR_CLASSES,
    PayorClassifierRunner,
    _CONFIDENCE_THRESHOLD,
)


def _dummy_image() -> Image.Image:
    return Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8)).convert("RGB")


def _make_runner_with_mock_model(probs: list[float]) -> PayorClassifierRunner:
    """Return a PayorClassifierRunner whose ResNet-50 returns fixed softmax probs."""
    runner = object.__new__(PayorClassifierRunner)
    runner._device = torch.device("cpu")

    mock_model = MagicMock()
    logits = torch.tensor([probs])
    mock_model.return_value = logits
    runner._model = mock_model
    return runner


class TestPayorClassifierContract:
    def test_output_keys_present(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        result = runner(_dummy_image())
        assert set(result.keys()) == {"payor_label", "confidence", "source_model"}

    def test_payor_label_is_string(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        result = runner(_dummy_image())
        assert isinstance(result["payor_label"], str)

    def test_confidence_is_float_in_unit_interval(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        result = runner(_dummy_image())
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_source_model_is_string(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        result = runner(_dummy_image())
        assert isinstance(result["source_model"], str)

    def test_high_confidence_returns_correct_label(self):
        # Pass logits (not probs); softmax([10, -10, ...]) ≈ [1.0, 0.0, ...]
        # so Aetna (index 0) wins well above the 0.5 threshold.
        logits = [10.0] + [-10.0] * 7
        runner = _make_runner_with_mock_model(logits)
        result = runner(_dummy_image())
        assert result["payor_label"] == PAYOR_CLASSES[0]

    def test_low_confidence_falls_back_to_other(self):
        # Spread evenly — max confidence will be ~0.125, below threshold
        probs = [1.0 / len(PAYOR_CLASSES)] * len(PAYOR_CLASSES)
        runner = _make_runner_with_mock_model(probs)
        result = runner(_dummy_image())
        assert result["payor_label"] == "Other"
        assert result["confidence"] < _CONFIDENCE_THRESHOLD

    def test_accepts_numpy_array(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        arr = np.zeros((224, 224, 3), dtype=np.uint8)
        result = runner(arr)
        assert "payor_label" in result

    def test_confidence_rounded_to_4dp(self):
        runner = _make_runner_with_mock_model([0.9] + [0.1 / 7] * 7)
        result = runner(_dummy_image())
        assert result["confidence"] == round(result["confidence"], 4)

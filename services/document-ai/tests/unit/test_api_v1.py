from __future__ import annotations

import base64
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from document_ai.main import app


def _b64_png(w: int = 64, h: int = 64) -> str:
    """Return a base64-encoded minimal PNG image."""
    import io

    img = Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _mock_card_ocr_runner() -> MagicMock:
    runner = MagicMock()
    runner.return_value = {
        "card_id": "test-card",
        "fields": [
            {"field_name": "member_id", "value": "ABC123", "confidence": 0.95, "bbox": [0, 0, 10, 10]},
        ],
        "low_confidence_fields": [],
        "model_version": "test-v0",
    }
    return runner


def _mock_payor_runner() -> MagicMock:
    runner = MagicMock()
    runner.return_value = {
        "payor_label": "Aetna",
        "confidence": 0.92,
        "source_model": "payor_classifier_resnet_v0.1",
    }
    return runner


@pytest.fixture()
def client() -> TestClient:
    app.state.card_ocr_runner = _mock_card_ocr_runner()
    app.state.payor_classifier_runner = _mock_payor_runner()
    return TestClient(app)


@pytest.fixture()
def client_no_runners() -> TestClient:
    app.state.card_ocr_runner = None
    app.state.payor_classifier_runner = None
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self, client: TestClient):
        assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/payor_classify
# ---------------------------------------------------------------------------


class TestPayorClassify:
    def test_happy_path_200(self, client: TestClient):
        r = client.post("/api/v1/payor_classify", json={"image_base64": _b64_png()})
        assert r.status_code == 200

    def test_response_keys(self, client: TestClient):
        r = client.post("/api/v1/payor_classify", json={"image_base64": _b64_png()})
        assert set(r.json().keys()) == {"payor_label", "confidence", "source_model"}

    def test_missing_field_422(self, client: TestClient):
        r = client.post("/api/v1/payor_classify", json={})
        assert r.status_code == 422

    def test_invalid_base64_422(self, client: TestClient):
        r = client.post("/api/v1/payor_classify", json={"image_base64": "not-valid-b64!!!"})
        assert r.status_code == 422

    def test_valid_base64_non_image_422(self, client: TestClient):
        garbage = base64.b64encode(b"this is not an image").decode()
        r = client.post("/api/v1/payor_classify", json={"image_base64": garbage})
        assert r.status_code == 422

    def test_no_runner_503(self, client_no_runners: TestClient):
        r = client_no_runners.post("/api/v1/payor_classify", json={"image_base64": _b64_png()})
        assert r.status_code == 503

    def test_get_method_not_allowed(self, client: TestClient):
        r = client.get("/api/v1/payor_classify")
        assert r.status_code == 405


# ---------------------------------------------------------------------------
# POST /api/v1/card_ocr
# ---------------------------------------------------------------------------


class TestCardOcr:
    def test_happy_path_200(self, client: TestClient):
        r = client.post(
            "/api/v1/card_ocr",
            json={"image_base64": _b64_png(), "card_id": "c-001"},
        )
        assert r.status_code == 200

    def test_response_keys(self, client: TestClient):
        r = client.post(
            "/api/v1/card_ocr",
            json={"image_base64": _b64_png(), "card_id": "c-001"},
        )
        assert set(r.json().keys()) == {"card_id", "fields", "low_confidence_fields", "model_version"}

    def test_missing_card_id_422(self, client: TestClient):
        r = client.post("/api/v1/card_ocr", json={"image_base64": _b64_png()})
        assert r.status_code == 422

    def test_invalid_base64_422(self, client: TestClient):
        r = client.post("/api/v1/card_ocr", json={"image_base64": "!!!", "card_id": "x"})
        assert r.status_code == 422

    def test_no_runner_503(self, client_no_runners: TestClient):
        r = client_no_runners.post(
            "/api/v1/card_ocr",
            json={"image_base64": _b64_png(), "card_id": "x"},
        )
        assert r.status_code == 503

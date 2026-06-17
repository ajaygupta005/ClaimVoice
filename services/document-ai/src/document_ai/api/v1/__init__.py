from __future__ import annotations

import base64
import binascii
import io

from document_ai.inference.card_ocr_runner import CardOCRRunner
from document_ai.inference.payor_classifier_runner import PayorClassifierRunner
from fastapi import APIRouter, HTTPException, Request
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _decode_image(image_base64: str) -> Image.Image:
    """Decode a raw base64 string to a PIL RGB Image, raising 422 on any failure."""
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(
            status_code=422,
            detail=f"image_base64 is not valid base64: {exc}",
        ) from exc
    try:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not decode image bytes. Supply a PNG or JPEG encoded as base64.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Image decoding failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Card OCR — request / response models
# ---------------------------------------------------------------------------


class CardOCRRequest(BaseModel):
    image_base64: str = Field(
        ...,
        description="Base64-encoded PNG or JPEG of the insurance card (no data-URI prefix).",
    )
    card_id: str = Field(
        ...,
        description="Opaque identifier for this card; echoed verbatim in the response.",
    )


class FieldResult(BaseModel):
    field_name: str
    value: str
    confidence: float
    bbox: list[int] | None = Field(
        None,
        description="[x0, y0, x1, y1] bounding box in source-image pixel coordinates, "
        "or null when the field was not located.",
    )


class CardOCRResponse(BaseModel):
    card_id: str
    fields: list[FieldResult]
    low_confidence_fields: list[str] = Field(
        description="field_names whose confidence fell below 0.80; candidates for "
        "Claude-assisted disambiguation."
    )
    model_version: str


# ---------------------------------------------------------------------------
# Payor classifier — request / response models
# ---------------------------------------------------------------------------


class PayorClassifyRequest(BaseModel):
    image_base64: str = Field(
        ...,
        description="Base64-encoded PNG or JPEG of the insurance card (no data-URI prefix).",
    )


class PayorClassifyResponse(BaseModel):
    payor_label: str = Field(
        description="Predicted payor label. One of: Aetna, UHC, Cigna, BCBS, Humana, "
        "Kaiser, Anthem, Other.  Forced to 'Other' when confidence < 0.50.",
    )
    confidence: float = Field(
        description="Softmax probability of the top-1 class before the threshold check."
    )
    source_model: str = Field(description="Model identifier used to produce this prediction.")


# ---------------------------------------------------------------------------
# Dependencies — read pre-loaded runners from app.state
# ---------------------------------------------------------------------------


def _get_card_ocr_runner(request: Request) -> CardOCRRunner:
    runner: CardOCRRunner | None = getattr(request.app.state, "card_ocr_runner", None)
    if runner is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Card OCR model is not loaded. "
                "Train with 'just train.card_ocr' or place a checkpoint under "
                "'artifacts/card_ocr/latest/' and restart the service."
            ),
        )
    return runner


def _get_payor_runner(request: Request) -> PayorClassifierRunner:
    runner: PayorClassifierRunner | None = getattr(
        request.app.state, "payor_classifier_runner", None
    )
    if runner is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Payor classifier model is not loaded. "
                "Train with 'just train.payor_classifier' or place a checkpoint under "
                "'artifacts/payor_classifier/latest/' and restart the service."
            ),
        )
    return runner


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/card_ocr",
    response_model=CardOCRResponse,
    summary="Extract structured fields from an insurance card image",
)
def card_ocr(body: CardOCRRequest, request: Request) -> CardOCRResponse:
    """Run LayoutLMv3 OCR on a base64-encoded card image.

    Returns one field object for each of the 12 canonical fields defined in
    SPEC.md D2, matching the contract ``{field_name, value, confidence, bbox}``.
    Fields that were not detected have ``value=""`` and ``confidence=0.0``.
    """
    image = _decode_image(body.image_base64)
    runner = _get_card_ocr_runner(request)
    try:
        result = runner(image, card_id=body.card_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
    return CardOCRResponse(**result)


@router.post(
    "/payor_classify",
    response_model=PayorClassifyResponse,
    summary="Classify the insurance payor from a card image",
)
def payor_classify(body: PayorClassifyRequest, request: Request) -> PayorClassifyResponse:
    """Run ResNet-50 classification on a base64-encoded card image.

    Returns the predicted payor label and the model's softmax confidence.
    When confidence falls below 0.50 the label is forced to ``"Other"``
    regardless of the argmax class.
    """
    image = _decode_image(body.image_base64)
    runner = _get_payor_runner(request)
    try:
        result = runner(image)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
    return PayorClassifyResponse(**result)

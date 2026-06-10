from __future__ import annotations

import base64
import binascii
import io

from fastapi import APIRouter, HTTPException, Request
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from document_ai.inference.card_ocr_runner import CardOCRRunner

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
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
# Dependency
# ---------------------------------------------------------------------------


def _get_runner(request: Request) -> CardOCRRunner:
    """Return the pre-loaded runner from app.state, or 503 if the model is absent."""
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


# ---------------------------------------------------------------------------
# Endpoint
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
    # --- Decode base64 ---
    try:
        image_bytes = base64.b64decode(body.image_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(
            status_code=422,
            detail=f"image_base64 is not valid base64: {exc}",
        )

    # --- Decode image ---
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=422,
            detail="Could not decode image bytes. Supply a PNG or JPEG encoded as base64.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Image decoding failed: {exc}",
        )

    # --- Run inference ---
    runner = _get_runner(request)
    try:
        result = runner(image, card_id=body.card_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {exc}",
        )

    return CardOCRResponse(**result)

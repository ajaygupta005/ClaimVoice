from fastapi import FastAPI
from .api.v1 import router as v1_router
from .lib.logger import logger

app = FastAPI(title="document-ai")
app.include_router(v1_router, prefix="/api/v1")


@app.on_event("startup")
async def startup() -> None:
    logger.info("document-ai starting")
    # Eagerly load all inference runners so the first request is not slow.
    # Missing checkpoints log a warning rather than crashing the service;
    # the relevant endpoint returns 503 until the checkpoint is deployed.
    try:
        from .inference.card_ocr_runner import CardOCRRunner
        app.state.card_ocr_runner = CardOCRRunner()
        logger.info("card_ocr_runner loaded successfully")
    except FileNotFoundError as exc:
        logger.warning(f"card_ocr_runner not loaded: {exc}")
        app.state.card_ocr_runner = None

    try:
        from .inference.payor_classifier_runner import PayorClassifierRunner
        app.state.payor_classifier_runner = PayorClassifierRunner()
        logger.info("payor_classifier_runner loaded successfully")
    except FileNotFoundError as exc:
        logger.warning(f"payor_classifier_runner not loaded: {exc}")
        app.state.payor_classifier_runner = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

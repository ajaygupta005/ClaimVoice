from fastapi import FastAPI
from .api.v1 import router as v1_router
from .lib.logger import logger

app = FastAPI(title="voice-agent")
app.include_router(v1_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    logger.info("voice-agent starting")

@app.get("/health")
def health(): return {"status": "ok"}

from fastapi import FastAPI
from .api.v1 import router as v1_router
from .lib.logger import logger

app = FastAPI(title="providers")
app.include_router(v1_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    logger.info("providers starting")

@app.get("/health")
def health(): return {"status": "ok"}

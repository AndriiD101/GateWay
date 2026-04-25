import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.db_test import router as db_test_router
from app.database import Base, engine
from app.routers.ai import router as ai_router
from app.routers.auth import router as auth_router
from app.routers.blob import router as blob_router
from app.routers.chat import router as chat_router
from app.routers.trips import router as trips_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Travel AI – Combined Backend",
    version="2.0.0",
    description=(
        "Unified backend combining JWT auth/chat (MySQL) "
        "with Travel AI trips, blob storage, and AWS Bedrock (Azure SQL)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)    # /api/register  /api/login  /api/me  /api/users
app.include_router(chat_router)    # /api/chat/history  /api/chat/message
app.include_router(trips_router)   # /trips
app.include_router(ai_router)      # /ai/process
app.include_router(blob_router)    # /blob/health  /blob/upload-test
app.include_router(db_test_router) # /db/health  /db/test-*


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    for attempt in range(3):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Azure SQL schema initialised.")
            return
        except SQLAlchemyError as exc:
            logger.warning("DB init attempt %s failed: %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(2)
    logger.warning("Azure SQL unavailable at startup; continuing without blocking.")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "status": "ok",
        "service": "gateway-backend",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "version": "2.0.0"}

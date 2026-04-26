import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
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
        "Unified backend for JWT auth/chat and Travel AI trips "
        "with Azure SQL storage, Azure Blob, and AWS Bedrock."
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


def _ensure_auth_columns() -> None:
    """Backfill legacy users table to match current auth model."""
    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'users'")
        ).scalar_one()
        if not table_exists:
            return

        existing_columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users'"
                )
            )
        }

        if "username" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD username NVARCHAR(255) NULL"))
            existing_columns.add("username")

        if "role" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD role NVARCHAR(32) NULL"))
            existing_columns.add("role")

        if "username" in existing_columns:
            conn.execute(text("UPDATE users SET username = email WHERE username IS NULL"))

        if "role" in existing_columns:
            conn.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN role NVARCHAR(32) NOT NULL"))


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    for attempt in range(3):
        try:
            Base.metadata.create_all(bind=engine)
            _ensure_auth_columns()
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

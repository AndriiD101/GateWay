import logging
import time

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.db_test import router as db_test_router
from app.database import Base, engine
from app.routers.ai import router as ai_router
from app.routers.blob import router as blob_router

app = FastAPI(title="Travel AI Backend", version="1.0.0")
app.include_router(db_test_router)
app.include_router(blob_router)
app.include_router(ai_router)
logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup() -> None:
    for attempt in range(3):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialization succeeded.")
            return
        except SQLAlchemyError as exc:
            logger.warning(
                "Database initialization attempt %s failed: %s",
                attempt + 1,
                str(exc),
            )
            if attempt < 2:
                time.sleep(2)

    logger.warning("Database unavailable at startup; continuing without blocking app boot.")


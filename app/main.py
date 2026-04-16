import json
import logging
import time

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.db_test import router as db_test_router
from app.config import settings
from app.database import Base, engine, get_db
from app.routers.ai import router as ai_router
from app.routers.blob import router as blob_router
from app.schemas import ProcessResponse
from app.services import call_nova_lite, process_request, upload_image_to_blob

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


@app.post("/process", response_model=ProcessResponse)
async def process(
    image: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ProcessResponse:
    result = await process_request(image=image, text=text, db=db)
    return ProcessResponse.model_validate(result)


@app.post("/ai/test")
async def ai_test(
    image: UploadFile | None = File(default=None),
    prompt: str | None = Form(default=None),
    payload: str | None = Form(default=None),
):
    payload_data: dict = {}
    payload_text_fallback = ""
    if payload:
        stripped_payload = payload.strip()
        if stripped_payload.startswith("{"):
            try:
                decoded = json.loads(stripped_payload)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="payload must be a valid JSON object string.",
                ) from exc
            if not isinstance(decoded, dict):
                raise HTTPException(
                    status_code=400,
                    detail="payload must be a JSON object.",
                )
            payload_data = decoded
        else:
            payload_text_fallback = stripped_payload

    prompt_used = (prompt or "").strip()
    if not prompt_used and payload_data:
        prompt_used = str(payload_data.get("prompt") or payload_data.get("text") or "").strip()
    if not prompt_used and payload_text_fallback:
        prompt_used = payload_text_fallback

    if image is None and not prompt_used:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one input: prompt text or image.",
        )

    image_payload: dict | None = None
    image_url: str | None = None
    if image is not None:
        image_payload = await upload_image_to_blob(image)
        image_url = str(image_payload.get("image_url"))

    if not prompt_used:
        prompt_used = "Analyze this image and return travel JSON fields."

    model_id = settings.aws_bedrock_model_id
    region = settings.aws_region
    logger.info("AI test invoke model_id=%s region=%s", model_id, region)

    try:
        start = time.perf_counter()
        parsed = call_nova_lite(prompt_used, optional_image=image_payload)
        latency_ms = (time.perf_counter() - start) * 1000.0

        logger.info("AI test success model_id=%s region=%s latency_ms=%.2f", model_id, region, latency_ms)
        return {
            "model_id": model_id,
            "region": region,
            "prompt_used": prompt_used,
            "raw_response": json.dumps(parsed, ensure_ascii=False),
            "parsed": parsed,
            "latency_ms": latency_ms,
            "image_url": image_url,
            "status": "success",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("AI test failed model_id=%s region=%s error=%s", model_id, region, str(exc))
        return JSONResponse(
            status_code=502,
            content={
                "model_id": model_id,
                "region": region,
                "prompt_used": prompt_used,
                "raw_response": str(exc),
                "parsed": None,
                "latency_ms": 0.0,
                "image_url": image_url,
                "status": "failed",
            },
        )


"""
AI (AWS Bedrock Nova Lite) endpoints.

Routes
------
POST /ai/process   – Upload image + optional prompt, get AI trip analysis [JWT]
"""

import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.services import (
    _trip_to_response_payload,
    call_nova_lite,
    save_trip_to_db,
    upload_image_to_blob,
    upload_trip_report_pdf_to_blob,
    _get_or_create_demo_user,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


@router.post("/process")
async def ai_process(
    image: UploadFile | None = File(default=None),
    prompt: str | None = Form(default=None),
    text: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Analyse a travel image (and/or a text prompt) with AWS Bedrock Nova Lite.
    Saves the resulting trip to Azure SQL and generates a PDF report in Azure Blob.
    Requires a valid JWT — the trip is recorded against the authenticated user.
    """
    prompt_used = (prompt or "").strip() or (text or "").strip()

    if image is None and not prompt_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one input: image or prompt/text.",
        )

    uploaded = None
    image_url = None

    if image is not None:
        try:
            uploaded = await upload_image_to_blob(image)
            image_url = uploaded["image_url"]
        except HTTPException:
            logger.warning("AI process: image upload failed")
            raise HTTPException(status_code=502, detail="Image upload failed.")

    if not prompt_used:
        prompt_used = "Analyze this image and return travel JSON fields."

    try:
        start = time.perf_counter()
        ai_output = call_nova_lite(prompt_used, optional_image=uploaded)
        latency_ms = (time.perf_counter() - start) * 1000.0
    except HTTPException:
        logger.warning("AI process: Bedrock inference failed")
        raise HTTPException(status_code=502, detail="AI inference failed.")

    try:
        pdf_url = upload_trip_report_pdf_to_blob(
            city=ai_output.get("city"),
            itinerary=ai_output.get("itinerary", []),
            budget_estimate=ai_output.get("budget_estimate", "0"),
            tips=ai_output.get("tips", []),
        )
    except HTTPException:
        logger.warning("AI process: PDF upload failed")
        raise HTTPException(status_code=502, detail="PDF upload failed.")

    try:
        user = _get_or_create_demo_user(db)
        trip = save_trip_to_db(
            db,
            {
                "user_id": user.id,
                "detected_city": ai_output.get("city") or "unknown",
                "image_url": image_url or "text-only",
                "itinerary": ai_output["itinerary"],
                "budget_estimate": ai_output["budget_estimate"],
            },
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("AI process database operation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Check SQL connectivity/firewall settings.",
        )

    return {
        "status": "success",
        "model_id": settings.aws_bedrock_model_id,
        "region": settings.aws_region,
        "prompt_used": prompt_used,
        "latency_ms": round(latency_ms, 2),
        "image_url": image_url,
        "pdf_url": pdf_url,
        "parsed": ai_output,
        "trip": _trip_to_response_payload(trip),
    }

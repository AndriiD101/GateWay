import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    _get_or_create_demo_user,
    _trip_to_response_payload,
    call_nova_lite,
    save_trip_to_db,
    upload_image_to_blob,
)

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


@router.post("/process")
async def ai_process(
    image: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict:
    text_value = (text or "").strip()
    if image is None and not text_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one input: image or text.",
        )

    uploaded = None
    image_url = None

    if image is not None:
        try:
            uploaded = await upload_image_to_blob(image)
            image_url = uploaded["image_url"]
        except HTTPException:
            logger.warning("AI process image upload failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Image upload failed.",
            )

    prompt = (
        text_value
        if text_value
        else "Analyze this travel image and return city, itinerary, budget estimate, and travel tips as strict JSON."
    )

    try:
        ai_output = call_nova_lite(prompt, optional_image=uploaded)
    except HTTPException:
        logger.warning("AI process Bedrock inference failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI inference failed.",
        )

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

    return _trip_to_response_payload(trip)

import json
import os
import time
import uuid
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from azure.storage.blob import BlobServiceClient
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Trip, User

NOVA_LITE_MODEL_ID = settings.aws_bedrock_model_id or os.getenv(
    "AWS_BEDROCK_MODEL_ID", "amazon.nova-2-lite-v1:0"
)
logger = logging.getLogger(__name__)


def _get_blob_client(blob_name: str):
    if not settings.azure_blob_connection_string:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AZURE_BLOB_CONNECTION_STRING is not configured.",
        )

    blob_service_client = BlobServiceClient.from_connection_string(
        settings.azure_blob_connection_string
    )
    return blob_service_client.get_blob_client(
        container=settings.azure_blob_container_name,
        blob=blob_name,
    )


def _get_bedrock_client():
    missing = []
    if not settings.aws_access_key_id:
        missing.append("AWS_ACCESS_KEY_ID")
    if not settings.aws_secret_access_key:
        missing.append("AWS_SECRET_ACCESS_KEY")
    if not settings.aws_region:
        missing.append("AWS_REGION")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing AWS settings: {', '.join(missing)}",
        )

    logger.info("Initializing Bedrock client for region=%s", settings.aws_region)
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def _is_transient_client_error(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code", "")
    return code in {
        "ThrottlingException",
        "ServiceUnavailableException",
        "InternalServerException",
        "ModelNotReadyException",
        "RequestTimeoutException",
    }


def _get_image_format_from_content_type(content_type: str) -> str:
    normalized = (content_type or "").strip().lower()
    mapping = {
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    image_format = mapping.get(normalized)
    if not image_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed: JPEG, PNG, GIF, WEBP",
        )
    return image_format


def _extract_nova_text_response(response: dict[str, Any]) -> str:
    output = response.get("output")
    if not isinstance(output, dict):
        raise ValueError("Invalid Bedrock response: missing output object")

    message = output.get("message")
    if not isinstance(message, dict):
        raise ValueError("Invalid Bedrock response: missing message object")

    content = message.get("content")
    if not isinstance(content, list):
        raise ValueError("Invalid Bedrock response: missing content list")

    text_chunks = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
    if not text_chunks:
        raise ValueError("Invalid Bedrock response: no text content")

    return "\n".join(text_chunks).strip()


async def upload_image_to_blob(file: UploadFile) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    extension = Path(file.filename).suffix.lower().strip()
    if extension and not extension.startswith("."):
        extension = f".{extension}"

    allowed_extensions = {
        ".jpeg": ".jpg",
        ".jpg": ".jpg",
        ".png": ".png",
        ".gif": ".gif",
        ".webp": ".webp",
    }

    normalized_extension = allowed_extensions.get(extension)
    if not normalized_extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed: JPEG, PNG, GIF, WEBP",
        )

    content_type_by_extension = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    upload_content_type = (
        file.content_type
        if (file.content_type or "").startswith("image/")
        else content_type_by_extension[normalized_extension]
    )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    blob_name = f"uploads/{uuid.uuid4().hex}{normalized_extension}"
    blob_client = _get_blob_client(blob_name)

    try:
        blob_client.upload_blob(
            image_bytes,
            overwrite=False,
            content_type=upload_content_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload image to Azure Blob Storage: {exc}",
        ) from exc

    return {
        "image_url": blob_client.url,
        "image_bytes": image_bytes,
        "content_type": upload_content_type,
    }


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    candidate = raw_text.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")

    return json.loads(candidate[start : end + 1])


def call_nova_lite(prompt: str, optional_image: dict[str, Any] | None = None) -> dict[str, Any]:
    bedrock = _get_bedrock_client()

    if not prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt cannot be empty.",
        )

    content: list[dict[str, Any]] = [{"text": prompt}]
    if optional_image:
        image_bytes = optional_image.get("image_bytes")
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image payload for inference.",
            )

        image_format = _get_image_format_from_content_type(
            str(optional_image.get("content_type", ""))
        )

        content.append(
            {
                "image": {
                    "format": image_format,
                    "source": {"bytes": bytes(image_bytes)},
                }
            }
        )

    system_prompt = (
        "Return strict JSON only. No markdown, no backticks, no explanations, no extra keys. "
        "The JSON object must contain exactly these keys: "
        "city (string or null), itinerary (list of strings), budget_estimate (string number only), "
        "tips (list of strings)."
    )
    model_id = settings.aws_bedrock_model_id
    inference_profile_id = os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ID", "").strip()
    model_target = inference_profile_id or model_id

    if not model_target:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Configure AWS_BEDROCK_MODEL_ID or AWS_BEDROCK_INFERENCE_PROFILE_ID "
                "for Bedrock invocation."
            ),
        )

    logger.info("Invoking Bedrock modelId=%s region=%s", model_target, settings.aws_region)

    for attempt in range(2):
        try:
            response = bedrock.converse(
                modelId=model_target,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": content}],
                inferenceConfig={"maxTokens": 900, "temperature": 0.2},
            )

            response_text = _extract_nova_text_response(response)
            parsed = _extract_json_payload(response_text)

            city = parsed.get("city")
            if city is not None and not isinstance(city, str):
                city = str(city)

            itinerary = parsed.get("itinerary", [])
            if not isinstance(itinerary, list):
                itinerary = [str(itinerary)]
            itinerary = [str(item) for item in itinerary]

            budget_estimate = str(parsed.get("budget_estimate", "0"))
            budget_estimate = "".join(ch for ch in budget_estimate if ch.isdigit() or ch == ".") or "0"

            tips = parsed.get("tips", [])
            if not isinstance(tips, list):
                tips = [str(tips)]
            tips = [str(tip) for tip in tips]

            logger.info("Bedrock inference succeeded modelId=%s region=%s", model_target, settings.aws_region)
            return {
                "city": city,
                "itinerary": itinerary,
                "budget_estimate": budget_estimate,
                "tips": tips,
            }
        except HTTPException:
            raise
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "UnknownError")
            error_message = exc.response.get("Error", {}).get("Message", "")
            if attempt == 0 and _is_transient_client_error(exc):
                logger.warning(
                    "Bedrock transient error modelId=%s region=%s code=%s; retrying once",
                    model_target,
                    settings.aws_region,
                    error_code,
                )
                time.sleep(0.5)
                continue
            logger.error(
                "Bedrock client error modelId=%s region=%s code=%s",
                model_target,
                settings.aws_region,
                error_code,
            )

            if error_code == "ValidationException" and "inference profile" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "Nova Lite requires an inference profile in this region. "
                        "Set AWS_BEDROCK_INFERENCE_PROFILE_ID to the profile ID or ARN."
                    ),
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Nova Lite inference failed ({error_code}): {error_message}",
            ) from exc
        except Exception as exc:
            logger.error("Bedrock inference failure modelId=%s region=%s", model_target, settings.aws_region)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Nova Lite inference failed: {type(exc).__name__}",
            ) from exc


def _get_or_create_demo_user(db: Session) -> User:
    stmt = select(User).where(User.email == "demo@example.com")
    user = db.scalars(stmt).first()
    if user:
        return user

    user = User(email="demo@example.com", password_hash="demo_hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_trip_to_db(db: Session, data: dict[str, Any]) -> Trip:
    itinerary = data.get("itinerary", [])
    if not isinstance(itinerary, list):
        itinerary = [itinerary]

    budget_estimate = data.get("budget_estimate", 0)
    if not isinstance(budget_estimate, Decimal):
        try:
            budget_estimate = Decimal(str(budget_estimate))
        except (InvalidOperation, ValueError, TypeError):
            budget_estimate = Decimal("0")

    trip = Trip(
        user_id=data["user_id"],
        detected_city=data["detected_city"],
        image_url=data["image_url"],
        itinerary=json.dumps(itinerary),
        budget_estimate=budget_estimate,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def get_trip_by_id(db: Session, trip_id: int) -> Trip | None:
    return db.get(Trip, trip_id)


def _trip_to_response_payload(trip: Trip) -> dict[str, Any]:
    try:
        itinerary = json.loads(trip.itinerary) if trip.itinerary else []
    except (json.JSONDecodeError, TypeError):
        itinerary = []

    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "detected_city": trip.detected_city,
        "image_url": trip.image_url,
        "itinerary": itinerary,
        "budget_estimate": str(trip.budget_estimate),
    }


async def process_upload_pipeline(file: UploadFile, db: Session) -> dict[str, Any]:
    uploaded = await upload_image_to_blob(file)
    ai_output = call_nova_lite(
        prompt=(
            "Analyze the travel image, detect the city, and create a 3-day itinerary, "
            "budget estimate, and practical travel tips."
        ),
        optional_image=uploaded,
    )

    user = _get_or_create_demo_user(db)
    trip = save_trip_to_db(
        db,
        {
            "user_id": user.id,
            "detected_city": ai_output.get("city") or "unknown",
            "image_url": uploaded["image_url"],
            "itinerary": ai_output["itinerary"],
            "budget_estimate": "".join(
                ch for ch in ai_output["budget_estimate"] if ch.isdigit() or ch == "."
            )
            or "0",
        },
    )

    return _trip_to_response_payload(trip)


async def process_request(image: UploadFile | None, text: str | None, db: Session) -> dict[str, Any]:
    text_value = (text or "").strip()
    if image is None and not text_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one input: image or text.",
        )

    uploaded: dict[str, Any] | None = None
    image_url: str | None = None
    if image is not None:
        uploaded = await upload_image_to_blob(image)
        image_url = uploaded["image_url"]

    prompt = (
        text_value
        if text_value
        else (
            "Analyze this travel photo and return city, itinerary, budget estimate, and travel tips "
            "as strict JSON."
        )
    )

    ai_output = call_nova_lite(prompt=prompt, optional_image=uploaded)

    user = _get_or_create_demo_user(db)
    trip = save_trip_to_db(
        db,
        {
            "user_id": user.id,
            "detected_city": ai_output.get("city") or "unknown",
            "image_url": image_url or "text-only",
            "itinerary": ai_output["itinerary"],
            "budget_estimate": "".join(
                ch for ch in ai_output["budget_estimate"] if ch.isdigit() or ch == "."
            )
            or "0",
        },
    )

    return _trip_to_response_payload(trip)

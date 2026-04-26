import json
import os
import time
import uuid
import logging
import textwrap
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import bcrypt
import boto3
from botocore.exceptions import ClientError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Trip, User

logger = logging.getLogger(__name__)


# ── Azure Blob ────────────────────────────────────────────────────────────────

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


# ── AWS Bedrock ───────────────────────────────────────────────────────────────

def _get_bedrock_client():
    missing = [
        k for k, v in {
            "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
            "AWS_REGION": settings.aws_region,
        }.items() if not v
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing AWS settings: {', '.join(missing)}",
        )
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
    mapping = {
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    fmt = mapping.get((content_type or "").strip().lower())
    if not fmt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed: JPEG, PNG, GIF, WEBP",
        )
    return fmt


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
    chunks = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
    if not chunks:
        raise ValueError("Invalid Bedrock response: no text content")
    return "\n".join(chunks).strip()


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    candidate = raw_text.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return json.loads(candidate[start: end + 1])


def call_nova_lite(prompt: str, optional_image: dict[str, Any] | None = None) -> dict[str, Any]:
    bedrock = _get_bedrock_client()
    if not prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty.")

    content: list[dict[str, Any]] = [{"text": prompt}]
    if optional_image:
        image_bytes = optional_image.get("image_bytes")
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            raise HTTPException(status_code=400, detail="Invalid image payload for inference.")
        content.append(
            {
                "image": {
                    "format": _get_image_format_from_content_type(
                        str(optional_image.get("content_type", ""))
                    ),
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

    model_target = (
        os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ID", "").strip() or settings.aws_bedrock_model_id
    )
    if not model_target:
        raise HTTPException(
            status_code=500,
            detail="Configure AWS_BEDROCK_MODEL_ID or AWS_BEDROCK_INFERENCE_PROFILE_ID.",
        )

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
            itinerary = [str(i) for i in itinerary]

            budget_estimate = "".join(
                ch for ch in str(parsed.get("budget_estimate", "0")) if ch.isdigit() or ch == "."
            ) or "0"

            tips = parsed.get("tips", [])
            if not isinstance(tips, list):
                tips = [str(tips)]
            tips = [str(t) for t in tips]

            return {"city": city, "itinerary": itinerary, "budget_estimate": budget_estimate, "tips": tips}

        except HTTPException:
            raise
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            msg = exc.response.get("Error", {}).get("Message", "")
            if attempt == 0 and _is_transient_client_error(exc):
                time.sleep(0.5)
                continue
            if code == "ValidationException" and "inference profile" in msg.lower():
                raise HTTPException(
                    status_code=502,
                    detail="Nova Lite requires an inference profile. Set AWS_BEDROCK_INFERENCE_PROFILE_ID.",
                ) from exc
            raise HTTPException(status_code=502, detail=f"Nova Lite inference failed ({code}): {msg}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Nova Lite inference failed: {type(exc).__name__}") from exc


# ── Image upload ──────────────────────────────────────────────────────────────

async def upload_image_to_blob(file: UploadFile) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")

    ext = Path(file.filename).suffix.lower().strip()
    allowed = {".jpeg": ".jpg", ".jpg": ".jpg", ".png": ".png", ".gif": ".gif", ".webp": ".webp"}
    norm_ext = allowed.get(ext)
    if not norm_ext:
        raise HTTPException(status_code=400, detail="Unsupported image format. Allowed: JPEG, PNG, GIF, WEBP")

    ct_map = {".jpg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    content_type = (
        file.content_type if (file.content_type or "").startswith("image/") else ct_map[norm_ext]
    )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    blob_name = f"uploads/{uuid.uuid4().hex}{norm_ext}"
    blob_client = _get_blob_client(blob_name)

    try:
        blob_client.upload_blob(image_bytes, overwrite=False, content_type=content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to upload image: {exc}") from exc

    return {"image_url": blob_client.url, "image_bytes": image_bytes, "content_type": content_type}


# ── PDF generation + upload ───────────────────────────────────────────────────

def _build_trip_report_pdf_bytes(
    *, city: str | None, itinerary: list[str], budget_estimate: str, tips: list[str]
) -> bytes:
    def _esc(v: str) -> str:
        return v.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ").replace("\n", " ")

    lines = ["Travel AI Report", f"City: {city or 'unknown'}", f"Budget Estimate: {budget_estimate}", "", "Itinerary:"]
    for i, item in enumerate(itinerary or ["No itinerary items provided."], 1):
        lines.extend(textwrap.wrap(f"{i}. {item}", width=95) or [""])
    lines.extend(["", "Tips:"])
    for i, tip in enumerate(tips or ["No tips provided."], 1):
        lines.extend(textwrap.wrap(f"{i}. {tip}", width=95) or [""])

    if len(lines) > 42:
        lines = lines[:41] + ["... output truncated ..."]

    ops = ["BT", "/F1 12 Tf"]
    for idx, line in enumerate(lines):
        y = 780 - idx * 17
        if y < 40:
            break
        ops.append(f"1 0 0 1 50 {y} Tm ({_esc(line)}) Tj")
    ops.append("ET")

    stream = "\n".join(ops).encode("latin-1", errors="replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for oid, obj in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{oid} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objs) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode()
    )
    return bytes(pdf)


def _extract_account_key_from_connection_string(conn_str: str) -> str | None:
    """Extract AccountKey from Azure Storage connection string."""
    if not conn_str:
        return None
    for part in conn_str.split(";"):
        if part.startswith("AccountKey="):
            return part.split("=", 1)[1]
    return None


def upload_trip_report_pdf_to_blob(
    *, city: str | None, itinerary: list[str], budget_estimate: str, tips: list[str]
) -> str:
    pdf_bytes = _build_trip_report_pdf_bytes(
        city=city, itinerary=itinerary, budget_estimate=budget_estimate, tips=tips
    )
    blob_client = _get_blob_client(f"reports/{uuid.uuid4().hex}.pdf")
    try:
        blob_client.upload_blob(
            pdf_bytes,
            overwrite=False,
            content_settings=ContentSettings(
                content_type="application/pdf",
                content_disposition='attachment; filename="trip-itinerary.pdf"',
            ),
        )
    except Exception as exc:
        logger.error(f"Blob upload error: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to upload PDF: {exc}") from exc

    # Return a short-lived signed URL so downloads work with private containers.
    try:
        expiry = datetime.now(timezone.utc) + timedelta(hours=2)
        
        # Try to extract account key from connection string
        account_key = _extract_account_key_from_connection_string(
            settings.azure_blob_connection_string
        )

        if account_key:
            try:
                sas = generate_blob_sas(
                    account_name=blob_client.account_name,
                    container_name=blob_client.container_name,
                    blob_name=blob_client.blob_name,
                    account_key=account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry,
                )
                signed_url = f"{blob_client.url}?{sas}"
                logger.info(f"Generated signed PDF URL for blob: {blob_client.blob_name}")
                return signed_url
            except Exception as sas_exc:
                logger.error(f"SAS generation failed: {sas_exc}", exc_info=True)
                logger.warning("Returning unsigned PDF URL as fallback")
                return blob_client.url
        else:
            logger.warning("No account key found in connection string; returning unsigned PDF URL")
            return blob_client.url
            
    except Exception as exc:
        logger.error(f"PDF URL signing error: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to sign PDF URL: {exc}") from exc


# ── Trip DB helpers ───────────────────────────────────────────────────────────

def _get_or_create_demo_user(db: Session) -> User:
    """Get or create a demo user for testing purposes."""
    demo_email = "demo@gateway.local"
    
    # Try to find existing demo user
    user = db.query(User).filter(User.email == demo_email).first()
    if user:
        return user
    
    # Create new demo user
    demo_password = "demo123"
    password_hash = bcrypt.hashpw(demo_password.encode(), bcrypt.gensalt()).decode()
    
    user = User(email=demo_email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_trip_to_db(db: Session, data: dict[str, Any]) -> Trip:
    itinerary = data.get("itinerary", [])
    if not isinstance(itinerary, list):
        itinerary = [itinerary]
    try:
        budget = Decimal(str(data.get("budget_estimate", 0)))
    except (InvalidOperation, ValueError, TypeError):
        budget = Decimal("0")

    trip = Trip(
        user_id=data["user_id"],
        detected_city=data["detected_city"],
        image_url=data["image_url"],
        itinerary=json.dumps(itinerary),
        budget_estimate=budget,
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

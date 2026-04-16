from fastapi import APIRouter, File, HTTPException, UploadFile, status
from azure.storage.blob import BlobServiceClient

from app.config import settings
from app.services import upload_image_to_blob

router = APIRouter(prefix="/blob", tags=["blob"])


@router.get("/health")
def blob_health() -> dict[str, str]:
    try:
        if not settings.azure_blob_connection_string:
            raise ValueError("AZURE_BLOB_CONNECTION_STRING is not configured")

        container_name = (settings.azure_blob_container_name or "").strip()
        if not container_name:
            raise ValueError("AZURE_BLOB_CONTAINER_NAME is not configured")

        client = BlobServiceClient.from_connection_string(
            settings.azure_blob_connection_string
        )
        client.get_container_client(container_name)

        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blob health check failed: {exc}",
        ) from exc


@router.post("/upload-test")
async def blob_upload_test(file: UploadFile = File(...)) -> dict[str, str | int]:
    try:
        result = await upload_image_to_blob(file)
        return {
            "image_url": str(result.get("image_url", "")),
            "content_type": str(result.get("content_type", "application/octet-stream")),
            "size_bytes": len(result.get("image_bytes", b"")),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blob upload test failed: {exc}",
        ) from exc

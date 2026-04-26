import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


def _get_jwt_expire_hours() -> int:
    raw_hours = os.getenv("JWT_EXPIRE_HOURS", "").strip()
    if raw_hours:
        try:
            value = int(raw_hours)
            if value > 0:
                return value
        except ValueError:
            pass

    raw_minutes = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "").strip()
    if raw_minutes:
        try:
            minutes = int(raw_minutes)
            if minutes > 0:
                return max(1, (minutes + 59) // 60)
        except ValueError:
            pass

    return 1


@dataclass(frozen=True)
class Settings:
    # ── Azure SQL (Travel AI trips/users) ─────────────────────────────────────
    azure_sql_connection_string: str = os.getenv("AZURE_SQL_CONNECTION_STRING", "").strip()

    # ── Azure Blob Storage ────────────────────────────────────────────────────
    azure_blob_connection_string: str = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container_name: str = os.getenv("AZURE_BLOB_CONTAINER_NAME", "travel-images")

    # ── AWS Bedrock (AI) ──────────────────────────────────────────────────────
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "eu-west-3")
    aws_bedrock_model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID", "eu.amazon.nova-2-lite-v1:0")

    # ── JWT ───────────────────────────────────────────────────────────────────
    secret_key: str = (
        os.getenv("SECRET_KEY", "").strip()
        or os.getenv("JWT_SECRET_KEY", "").strip()
        or "change-this-in-production!"
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = _get_jwt_expire_hours()


settings = Settings()

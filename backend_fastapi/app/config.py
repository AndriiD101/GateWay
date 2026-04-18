import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


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

    # ── MySQL (auth / chat history) ───────────────────────────────────────────
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "gateway_db")

    # ── JWT ───────────────────────────────────────────────────────────────────
    secret_key: str = os.getenv("SECRET_KEY", "change-this-in-production!")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "1"))


settings = Settings()

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    azure_sql_connection_string: str = os.getenv("AZURE_SQL_CONNECTION_STRING", "").strip()
    azure_blob_connection_string: str = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container_name: str = os.getenv("AZURE_BLOB_CONTAINER_NAME", "travel-images")

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"
    access_token_expire_minutes: int = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "eu-west-3")
    aws_bedrock_model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID", "eu.amazon.nova-2-lite-v1:0")


settings = Settings()

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    azure_sql_connection_string: str = os.getenv("AZURE_SQL_CONNECTION_STRING", "").strip()
    azure_blob_connection_string: str = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container_name: str = os.getenv("AZURE_BLOB_CONTAINER_NAME", "travel-images")

    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_bedrock_model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID", "amazon.nova-2-lite-v1:0")


settings = Settings()

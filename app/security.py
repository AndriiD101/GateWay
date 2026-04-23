from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_password_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=390000,
)


def hash_password(password: str) -> str:
    return _password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_context.verify(plain_password, hashed_password)


def _ensure_jwt_settings() -> None:
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY is not configured.",
        )


def create_access_token(*, subject: str, expires_minutes: int | None = None) -> tuple[str, int]:
    _ensure_jwt_settings()

    now = datetime.now(UTC)
    ttl_minutes = expires_minutes or settings.access_token_expire_minutes
    expires_at = now + timedelta(minutes=ttl_minutes)

    payload = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    expires_in = int((expires_at - now).total_seconds())
    return token, expires_in

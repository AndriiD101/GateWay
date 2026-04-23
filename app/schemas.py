from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TripCreate(BaseModel):
    user_id: int = Field(default=1)
    detected_city: str
    image_url: str
    itinerary: list[Any] = Field(default_factory=list)
    budget_estimate: Decimal


class TripResponse(BaseModel):
    id: int
    user_id: int
    detected_city: str
    image_url: str
    itinerary: list[Any]
    budget_estimate: Decimal

    model_config = ConfigDict(from_attributes=True)


class ProcessRequest(BaseModel):
    text: str | None = None


class ProcessResponse(BaseModel):
    city: str | None = None
    itinerary: list[Any] = Field(default_factory=list)
    budget_estimate: str
    tips: list[str] = Field(default_factory=list)


class UserPublic(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must include at least one letter.")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must include at least one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic

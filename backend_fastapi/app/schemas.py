from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, max_length=128)


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    role: str  # "user" | "assistant"
    message: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    message: str
    created_at: Any  # datetime or str depending on driver


# ── Trips (Azure SQL) ─────────────────────────────────────────────────────────

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


# ── AI ────────────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    text: str | None = None


class ProcessResponse(BaseModel):
    city: str | None = None
    itinerary: list[Any] = Field(default_factory=list)
    budget_estimate: str
    tips: list[str] = Field(default_factory=list)

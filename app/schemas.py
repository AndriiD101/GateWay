from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

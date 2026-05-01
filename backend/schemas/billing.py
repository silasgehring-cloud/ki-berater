from typing import Literal

from pydantic import BaseModel, Field


class CheckoutCreate(BaseModel):
    plan: Literal["starter", "growth", "pro"] = Field(default="starter")


class CheckoutSessionRead(BaseModel):
    url: str


class PortalSessionRead(BaseModel):
    url: str


class QuotaStatus(BaseModel):
    plan: str
    monthly_eur: int
    monthly_conversations: int | None
    used_in_period: int
    remaining: int | None
    period_start: str
    period_end: str
    subscription_status: str

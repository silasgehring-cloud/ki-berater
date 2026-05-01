from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsPeriod(BaseModel):
    start: str
    end: str
    days: int


class ConversationStats(BaseModel):
    total: int
    converted: int
    conversion_rate_percent: float


class RevenueStats(BaseModel):
    total_eur: Decimal
    converted_orders: int


class ClickStats(BaseModel):
    total: int


class AttributionStats(BaseModel):
    """Conversion-Attribution-Aufteilung: cookie-only vs. strict (Produkt-Match)."""

    strict: int = 0
    cookie_only: int = 0


class AnalyticsOverview(BaseModel):
    period: AnalyticsPeriod
    conversations: ConversationStats
    revenue: RevenueStats
    clicks: ClickStats
    attribution: AttributionStats
    llm_cost_eur: Decimal


class ConversionEvent(BaseModel):
    """Plugin posts this to mark a conversation as converted (= led to a WC order)."""

    order_id: str = Field(min_length=1, max_length=64)
    order_total_eur: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    # Strict-Attribution: list of WC product external_ids in the order. Backend
    # intersects with conversation's products_referenced and stores
    # `attribution_type='strict'` if any match.
    line_item_external_ids: list[str] = Field(default_factory=list, max_length=200)


class ClickEvent(BaseModel):
    product_id: UUID
    message_id: UUID | None = None


class ClickRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    product_id: UUID
    message_id: UUID | None
    clicked_at: datetime


# Reserved for future Conversation.attribution_type enum.
AttributionType = Literal["strict", "cookie_only"]

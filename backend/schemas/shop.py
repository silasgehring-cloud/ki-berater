from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShopCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=255, examples=["shop.example.com"])
    plan: str = Field(default="starter", pattern=r"^(starter|growth|pro|enterprise)$")
    config: dict[str, Any] = Field(default_factory=dict)


class ShopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    plan: str
    api_key_prefix: str
    created_at: datetime


class ShopReadWithKey(ShopRead):
    """Returned exactly once, on POST /v1/shops. Neither secret is persisted as plain text."""

    api_key: str
    webhook_secret: str


class ShopDataExport(BaseModel):
    """DSGVO Art. 15 — full data dump for a shop. Pagination is intentionally
    omitted in Phase 3; if a shop accumulates >100k records before Phase 4
    paginates this, we reroute to a background-job download URL pattern.
    """

    shop: dict[str, Any]
    products: list[dict[str, Any]]
    conversations: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    llm_usage: list[dict[str, Any]]
    exported_at: datetime

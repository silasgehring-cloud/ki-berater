from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductIn(BaseModel):
    """Single product as the WP plugin pushes it. external_id is WC product ID."""

    external_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=20_000)
    categories: list[str] = Field(default_factory=list)
    price: Decimal | None = None
    currency: str = Field(default="EUR", max_length=8)
    stock_status: Literal["instock", "outofstock", "onbackorder"] = "instock"
    url: str | None = Field(default=None, max_length=1024)
    image_url: str | None = Field(default=None, max_length=1024)
    sku: str | None = Field(default=None, max_length=128)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    name: str
    stock_status: str
    price: Decimal | None
    currency: str
    url: str | None
    updated_at: datetime


class BulkSyncRequest(BaseModel):
    products: list[ProductIn] = Field(min_length=1, max_length=5000)


class BulkSyncStarted(BaseModel):
    job_id: UUID
    total: int
    status: Literal["queued"] = "queued"


class BulkSyncStatus(BaseModel):
    job_id: UUID
    status: Literal["queued", "running", "complete", "failed"]
    total: int
    processed: int
    failed: int
    error: str | None = None


class WebhookPayload(BaseModel):
    """Body of POST /v1/webhooks/products. WP plugin signs this with HMAC."""

    topic: Literal["product.created", "product.updated", "product.deleted"]
    product: ProductIn

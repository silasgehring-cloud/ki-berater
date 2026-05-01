from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models._mixins import ShopScopedMixin


class Conversation(Base, ShopScopedMixin):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    visitor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    converted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    # Conversion tracking (Sprint 4.2-light).
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_total_eur: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    order_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # 'strict' iff order line-items ∩ products_referenced ≠ ∅; else 'cookie_only'.
    attribution_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

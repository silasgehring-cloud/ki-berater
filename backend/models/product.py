from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models._mixins import ShopScopedMixin


class Product(Base, ShopScopedMixin):
    """Mirror of a WooCommerce product. Source of truth for tenant-scoped joins
    (consistency-sweep, references in Message.products_referenced)."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("shop_id", "external_id", name="uq_products_shop_external"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="EUR")
    stock_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="instock"
    )
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deleted: Mapped[bool] = mapped_column(
        nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

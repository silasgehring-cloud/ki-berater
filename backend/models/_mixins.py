"""Reusable model mixins.

`ShopScopedMixin` makes a model carry a non-null `shop_id` FK to `shops.id`.
Combined with the `tenant_query()` helper in `backend/db/tenant_query.py`,
this is the foundation of multi-tenant isolation. Direct queries bypassing
`tenant_query()` MUST be reviewed and avoided.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ShopScopedMixin:
    """Adds `shop_id` foreign key. Use with `tenant_query()` to enforce isolation."""

    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

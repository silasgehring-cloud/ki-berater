"""Tenant-scoped query helpers.

ALL queries against `ShopScopedMixin`-models MUST go through `tenant_select()`.
This is the single enforcement point for multi-tenant isolation in Sprint 1.x.

Example:
    stmt = tenant_select(Conversation, shop_id=current_shop.id)
    result = await db.execute(stmt)
"""
from uuid import UUID

from sqlalchemy import Select, select

from backend.models._mixins import ShopScopedMixin


def tenant_select[ModelT: ShopScopedMixin](
    model: type[ModelT], shop_id: UUID
) -> Select[tuple[ModelT]]:
    """Build a SELECT pre-filtered by shop_id. The only sanctioned read entrypoint."""
    return select(model).where(model.shop_id == shop_id)

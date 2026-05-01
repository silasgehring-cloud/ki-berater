"""conversion tracking columns + idempotency unique on (shop_id, order_id)

Revision ID: 005_conversion_tracking
Revises: 004_billing_columns
Create Date: 2026-05-01 00:01:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_conversion_tracking"
down_revision: str | None = "004_billing_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("order_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("order_total_eur", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("order_currency", sa.String(length=8), nullable=True),
    )
    # Partial unique index for idempotency: at most one conversation per (shop, order_id).
    op.create_index(
        "uq_conversations_shop_order",
        "conversations",
        ["shop_id", "order_id"],
        unique=True,
        postgresql_where=sa.text("order_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_conversations_shop_order", table_name="conversations")
    op.drop_column("conversations", "order_currency")
    op.drop_column("conversations", "order_total_eur")
    op.drop_column("conversations", "order_id")
    op.drop_column("conversations", "converted_at")

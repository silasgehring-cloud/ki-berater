"""product_clicks table + conversations.attribution_type

Revision ID: 006_product_clicks
Revises: 005_conversion_tracking
Create Date: 2026-05-01 00:02:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_product_clicks"
down_revision: str | None = "005_conversion_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_clicks_shop_clicked",
        "product_clicks",
        ["shop_id", sa.text("clicked_at DESC")],
    )
    op.create_index(
        "ix_product_clicks_conversation",
        "product_clicks",
        ["conversation_id"],
    )

    # Strict-Attribution flag.
    op.add_column(
        "conversations",
        sa.Column("attribution_type", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "attribution_type")
    op.drop_index("ix_product_clicks_conversation", table_name="product_clicks")
    op.drop_index("ix_product_clicks_shop_clicked", table_name="product_clicks")
    op.drop_table("product_clicks")

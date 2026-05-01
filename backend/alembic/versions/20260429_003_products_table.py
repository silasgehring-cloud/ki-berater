"""products table

Revision ID: 003_products_table
Revises: 002_initial_schema
Create Date: 2026-04-29 00:02:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_products_table"
down_revision: str | None = "002_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "categories",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="EUR"),
        sa.Column(
            "stock_status",
            sa.String(length=32),
            nullable=False,
            server_default="instock",
        ),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "external_id", name="uq_products_shop_external"),
    )
    op.create_index("ix_products_shop_deleted", "products", ["shop_id", "deleted"])


def downgrade() -> None:
    op.drop_index("ix_products_shop_deleted", table_name="products")
    op.drop_table("products")

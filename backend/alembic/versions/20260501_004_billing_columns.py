"""billing columns on shops

Revision ID: 004_billing_columns
Revises: 003_products_table
Create Date: 2026-05-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_billing_columns"
down_revision: str | None = "003_products_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shops",
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "shops",
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "shops",
        sa.Column(
            "subscription_status",
            sa.String(length=32),
            nullable=False,
            server_default="inactive",
        ),
    )


def downgrade() -> None:
    op.drop_column("shops", "subscription_status")
    op.drop_column("shops", "current_period_end")
    op.drop_column("shops", "current_period_start")

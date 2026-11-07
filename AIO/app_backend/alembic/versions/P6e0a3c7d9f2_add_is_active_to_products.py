"""add is_active to products for the business dashboard

Revision ID: P6e0a3c7d9f2
Revises: O5d9f2b6c8e1
Create Date: 2026-08-13

Lets a store owner hide a product from their storefront without deleting
it. Backs the Business Dashboard's "Hidden or Inactive Products" section
(app/services/dashboard_service.py) — there was previously no way for
that section to report anything real.
"""
from alembic import op
import sqlalchemy as sa

revision = "P6e0a3c7d9f2"
down_revision = "O5d9f2b6c8e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("products", "is_active")

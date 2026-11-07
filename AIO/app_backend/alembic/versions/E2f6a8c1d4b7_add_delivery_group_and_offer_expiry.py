"""add delivery_group_id and offer_expires_at to orders

Revision ID: E2f6a8c1d4b7
Revises: D7a2f4e9b1c3
Create Date: 2026-08-01

Supports zone-based delivery grouping: shop-orders from the same checkout
that fall within the same ~5km zone are clustered into one delivery_group_id
and offered together to a single driver (see geo_utils.cluster_shops_by_zone
and workers/driver_assignment_worker.py). offer_expires_at backs the
offer/accept flow — a driver is offered a group (driver_id set, status still
`pending`) rather than hard-assigned; if the offer isn't accepted before this
timestamp, the worker sweeps it and offers the next-nearest driver instead.
"""
from alembic import op
import sqlalchemy as sa

revision = "E2f6a8c1d4b7"
down_revision = "d7a2f4e9b1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_group_id", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_orders_delivery_group_id"), "orders", ["delivery_group_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_delivery_group_id"), table_name="orders")
    op.drop_column("orders", "offer_expires_at")
    op.drop_column("orders", "delivery_group_id")
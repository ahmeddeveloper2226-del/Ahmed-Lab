"""add AIO delivery architecture: delivery_stage, provider_type, ETA/fee snapshot

Revision ID: T0i4e7f1b3d6
Revises: S9h3d6f0a2c5
Create Date: 2026-09-01

Additive only. Every new column is nullable, so existing orders read as
NULL ("pre-granular-tracking") rather than needing backfill, and nothing
about the existing `status`/`payment_status` columns or their consumers
(payment_webhook_router, store_panel_router) changes. See
app/models/delivery.py's module docstring for why this is a parallel
field set rather than a rework of OrderStatus.
"""
from alembic import op
import sqlalchemy as sa

revision = "T0i4e7f1b3d6"
down_revision = "S9h3d6f0a2c5"
branch_labels = None
depends_on = None

_delivery_stage_values = (
    "order_created", "branch_validated", "inventory_validated", "delivery_validated",
    "fulfillment_selected", "provider_selected", "driver_assigned", "going_to_branch",
    "arrived_at_branch", "waiting_for_order", "picked_up", "in_transit",
    "arrived_at_customer", "delivered", "cancelled", "failed_delivery",
    "customer_unavailable", "branch_delay", "driver_rejected", "provider_failed",
    "inventory_unavailable",
)
_provider_values = ("aio_driver", "store_driver", "third_party")
_failure_reason_values = ("customer_unavailable", "wrong_address", "customer_refused", "driver_issue", "other")

delivery_stage_enum = sa.Enum(*_delivery_stage_values, name="deliverystage")
delivery_provider_enum = sa.Enum(*_provider_values, name="deliveryprovider")
delivery_failure_reason_enum = sa.Enum(*_failure_reason_values, name="deliveryfailurereason")


def upgrade() -> None:
    bind = op.get_bind()
    delivery_stage_enum.create(bind, checkfirst=True)
    delivery_provider_enum.create(bind, checkfirst=True)
    delivery_failure_reason_enum.create(bind, checkfirst=True)

    op.add_column("orders", sa.Column("delivery_stage", delivery_stage_enum, nullable=True))
    op.create_index(op.f("ix_orders_delivery_stage"), "orders", ["delivery_stage"], unique=False)

    op.add_column("orders", sa.Column("provider_type", delivery_provider_enum, nullable=True))
    op.add_column("orders", sa.Column("road_distance_km", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("eta_minutes", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=True))
    op.add_column("orders", sa.Column("live_eta_minutes", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("pickup_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("failure_reason", delivery_failure_reason_enum, nullable=True))
    op.add_column("orders", sa.Column("failure_notes", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "failure_notes")
    op.drop_column("orders", "failure_reason")
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "pickup_at")
    op.drop_column("orders", "live_eta_minutes")
    op.drop_column("orders", "delivery_fee")
    op.drop_column("orders", "eta_minutes")
    op.drop_column("orders", "road_distance_km")
    op.drop_column("orders", "provider_type")
    op.drop_index(op.f("ix_orders_delivery_stage"), table_name="orders")
    op.drop_column("orders", "delivery_stage")

    bind = op.get_bind()
    delivery_failure_reason_enum.drop(bind, checkfirst=True)
    delivery_provider_enum.drop(bind, checkfirst=True)
    delivery_stage_enum.drop(bind, checkfirst=True)

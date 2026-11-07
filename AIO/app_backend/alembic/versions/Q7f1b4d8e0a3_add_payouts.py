"""add vendor payout accounts and payouts

Revision ID: Q7f1b4d8e0a3
Revises: P6e0a3c7d9f2
Create Date: 2026-08-13

Scaffold for the Business Dashboard's Payout History / Invoices section.
The actual Paymob Disbursement API call is NOT wired up in this revision
(no API access as of this build) — see app/services/payout_service.py's
send_payout() for the clearly marked stub. Payouts created via this
schema will sit in `pending` status until that's connected.
"""
from alembic import op
import sqlalchemy as sa

revision = "Q7f1b4d8e0a3"
down_revision = "P6e0a3c7d9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendor_payout_accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shop_id", sa.String(), sa.ForeignKey("shops.id"), nullable=False, unique=True),
        sa.Column("destination_type", sa.Enum("bank_account", "mobile_wallet", name="payoutdestinationtype"), nullable=False),
        sa.Column("account_holder_name", sa.String(), nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("bank_name", sa.String(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_vendor_payout_accounts_shop_id"), "vendor_payout_accounts", ["shop_id"], unique=True)

    op.create_table(
        "payouts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shop_id", sa.String(), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(10, 2), nullable=False),
        sa.Column("platform_commission", sa.Numeric(10, 2), nullable=False),
        sa.Column("net_payout_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "paid", "failed", name="payoutstatus"), nullable=False, server_default="pending"),
        sa.Column("paymob_disbursement_id", sa.String(), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_payouts_shop_id"), "payouts", ["shop_id"], unique=False)

    op.create_table(
        "payout_orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("payout_id", sa.String(), sa.ForeignKey("payouts.id"), nullable=False),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_payout_orders_order_id"),
    )
    op.create_index(op.f("ix_payout_orders_payout_id"), "payout_orders", ["payout_id"], unique=False)
    op.create_index(op.f("ix_payout_orders_order_id"), "payout_orders", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_table("payout_orders")
    op.drop_index(op.f("ix_payouts_shop_id"), table_name="payouts")
    op.drop_table("payouts")
    op.drop_index(op.f("ix_vendor_payout_accounts_shop_id"), table_name="vendor_payout_accounts")
    op.drop_table("vendor_payout_accounts")
    sa.Enum(name="payoutstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payoutdestinationtype").drop(op.get_bind(), checkfirst=True)

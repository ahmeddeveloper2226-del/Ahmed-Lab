"""add prescriptions and prescription_items tables

Revision ID: H5c9d1f4a7e3
Revises: G4b8c0e3f6d2
Create Date: 2026-08-04

Backs the pharmacy prescription-upload feature: a customer photographs a
prescription for a specific pharmacy shop, the pharmacist transcribes it
into line items via the store management panel, and the customer reviews
(can remove items) and approves before anything is added to their cart.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = "H5c9d1f4a7e3"
down_revision = "G4b8c0e3f6d2"
branch_labels = None
depends_on = None

_PRESCRIPTION_STATUS_CREATE = ENUM(
    "pending_review",
    "awaiting_customer_approval",
    "approved",
    "rejected",
    "cancelled",
    name="prescriptionstatus",
)

# Used ONLY in table columns
_PRESCRIPTION_STATUS = ENUM(
    "pending_review",
    "awaiting_customer_approval",
    "approved",
    "rejected",
    "cancelled",
    name="prescriptionstatus",
    create_type=False,
)




def upgrade() -> None:
    _PRESCRIPTION_STATUS.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("shop_id", sa.String(), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column(
            "status",
            _PRESCRIPTION_STATUS,
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_prescriptions_user_id"), "prescriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_prescriptions_shop_id"), "prescriptions", ["shop_id"], unique=False)

    op.create_table(
        "prescription_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("prescription_id", sa.String(), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("product_id", sa.String(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("custom_name", sa.String(), nullable=True),
        sa.Column("custom_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        op.f("ix_prescription_items_prescription_id"), "prescription_items", ["prescription_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_prescription_items_prescription_id"), table_name="prescription_items")
    op.drop_table("prescription_items")

    op.drop_index(op.f("ix_prescriptions_shop_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_user_id"), table_name="prescriptions")
    op.drop_table("prescriptions")

    _PRESCRIPTION_STATUS.drop(op.get_bind(), checkfirst=True)
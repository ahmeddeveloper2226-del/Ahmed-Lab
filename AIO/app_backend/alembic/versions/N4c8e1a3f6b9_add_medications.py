"""add medications table for refill reminder

Revision ID: N4c8e1a3f6b9
Revises: M2b6d9f1a4c7
Create Date: 2026-08-08

Backs the Pharmacies-exclusive 'Refill Reminder' feature (see
app/services/medication_service.py and
workers/refill_reminder_worker.py). One row per chronic-condition
medication a customer tracks; run_out_date is computed on the fly from
pack_quantity/daily_dosage/last_refill_date rather than stored, so it's
never out of sync with the value the reminder worker uses.
"""
from alembic import op
import sqlalchemy as sa

revision = "N4c8e1a3f6b9"
down_revision = "M2b6d9f1a4c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("product_id", sa.String(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("medicine_name", sa.String(), nullable=False),
        sa.Column("condition", sa.String(), nullable=False, server_default="other"),
        sa.Column("pack_quantity", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("daily_dosage", sa.Numeric(5, 2), nullable=False, server_default="1"),
        sa.Column("last_refill_date", sa.Date(), nullable=False),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_reminded_for_run_out_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_medications_user_id"), "medications", ["user_id"], unique=False)
    op.create_index(op.f("ix_medications_product_id"), "medications", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_medications_product_id"), table_name="medications")
    op.drop_index(op.f("ix_medications_user_id"), table_name="medications")
    op.drop_table("medications")

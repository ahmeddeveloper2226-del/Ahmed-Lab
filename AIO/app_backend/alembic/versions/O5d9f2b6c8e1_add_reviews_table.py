"""add reviews table for ratings/reviews and the business dashboard

Revision ID: O5d9f2b6c8e1
Revises: N4c8e1a3f6b9
Create Date: 2026-08-13

Backs the customer-facing "rate your order" flow and the Business
Dashboard's Ratings & Reviews section (see app/services/review_service.py
and app/routers/dashboard_router.py). One review per order — enforced by
the unique constraint on order_id, not just app-level logic.
"""
from alembic import op
import sqlalchemy as sa

revision = "O5d9f2b6c8e1"
down_revision = "N4c8e1a3f6b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("shop_id", sa.String(), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("shop_reply", sa.Text(), nullable=True),
        sa.Column("shop_replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_reviews_shop_id"), "reviews", ["shop_id"], unique=False)
    op.create_index(op.f("ix_reviews_user_id"), "reviews", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reviews_user_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_shop_id"), table_name="reviews")
    op.drop_table("reviews")

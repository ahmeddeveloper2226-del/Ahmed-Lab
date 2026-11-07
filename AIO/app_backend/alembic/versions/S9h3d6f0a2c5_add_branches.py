"""add branches, branch_stock, and order.branch_id

Revision ID: S9h3d6f0a2c5
Revises: R8g2c5e9f1b4
Create Date: 2026-08-13

Multi-location support for vendors. A shop with zero branch rows behaves
exactly as before this migration — nothing here changes existing
behavior unless a shop owner actually adds a branch (see branch_service.py
and store_management_router.py's /branches endpoints).
"""
from alembic import op
import sqlalchemy as sa

revision = "S9h3d6f0a2c5"
down_revision = "R8g2c5e9f1b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("shop_id", sa.String(), sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_branches_shop_id"), "branches", ["shop_id"], unique=False)

    op.create_table(
        "branch_stock",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("branch_id", sa.String(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("product_id", sa.String(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("branch_id", "product_id", name="uq_branch_stock_branch_product"),
    )
    op.create_index(op.f("ix_branch_stock_branch_id"), "branch_stock", ["branch_id"], unique=False)
    op.create_index(op.f("ix_branch_stock_product_id"), "branch_stock", ["product_id"], unique=False)

    op.add_column("orders", sa.Column("branch_id", sa.String(), sa.ForeignKey("branches.id"), nullable=True))
    op.create_index(op.f("ix_orders_branch_id"), "orders", ["branch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_branch_id"), table_name="orders")
    op.drop_column("orders", "branch_id")
    op.drop_index(op.f("ix_branch_stock_product_id"), table_name="branch_stock")
    op.drop_index(op.f("ix_branch_stock_branch_id"), table_name="branch_stock")
    op.drop_table("branch_stock")
    op.drop_index(op.f("ix_branches_shop_id"), table_name="branches")
    op.drop_table("branches")

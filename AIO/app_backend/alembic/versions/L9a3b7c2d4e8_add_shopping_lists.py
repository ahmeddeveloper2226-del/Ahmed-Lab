"""add shopping_lists and shopping_list_items tables

Revision ID: L9a3b7c2d4e8
Revises: J7e1f3a6c9b5
Create Date: 2026-08-08

Backs the Grocery-exclusive 'Smart Shopping Lists' and 'AI Recipe
Shopping' features (see app/services/shopping_list_service.py). A list
is a reusable plan of named line items, only loosely tied to actual
catalog products (see shopping_list_items.product_id, nullable) — the
same list can be reused across restocks even after a specific product
goes out of stock or gets replaced.
"""
from alembic import op
import sqlalchemy as sa

revision = "L9a3b7c2d4e8"
down_revision = "k8f2a4c7e1b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("occasion", sa.String(), nullable=False, server_default="custom"),
        sa.Column("share_code", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_shopping_lists_user_id"), "shopping_lists", ["user_id"], unique=False)
    op.create_index(op.f("ix_shopping_lists_share_code"), "shopping_lists", ["share_code"], unique=True)

    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "shopping_list_id",
            sa.String(),
            sa.ForeignKey("shopping_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("product_id", sa.String(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        op.f("ix_shopping_list_items_shopping_list_id"), "shopping_list_items", ["shopping_list_id"], unique=False
    )
    op.create_index(op.f("ix_shopping_list_items_product_id"), "shopping_list_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shopping_list_items_product_id"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_shopping_list_id"), table_name="shopping_list_items")
    op.drop_table("shopping_list_items")

    op.drop_index(op.f("ix_shopping_lists_share_code"), table_name="shopping_lists")
    op.drop_index(op.f("ix_shopping_lists_user_id"), table_name="shopping_lists")
    op.drop_table("shopping_lists")

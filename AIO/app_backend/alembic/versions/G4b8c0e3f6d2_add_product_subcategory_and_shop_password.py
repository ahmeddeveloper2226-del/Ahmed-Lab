"""add products.subcategory_id and shops.password_hash

Revision ID: G4b8c0e3f6d2
Revises: F3a7b9d2e5c1
Create Date: 2026-08-02

Two independent additions:
  - products.subcategory_id — same subcategory tagging Shop already got,
    now on Product too, so the product list inside a shop screen can be
    filtered by the same pill-chip row.
  - shops.password_hash — backs the new store management panel (shop_id +
    password login, no separate user account) — see
    app/services/password_service.py and store_management_router.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "G4b8c0e3f6d2"
down_revision = "F3a7b9d2e5c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("subcategory_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_products_subcategory_id", "products", "subcategories", ["subcategory_id"], ["id"]
    )
    op.create_index(op.f("ix_products_subcategory_id"), "products", ["subcategory_id"], unique=False)

    op.add_column("shops", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shops", "password_hash")

    op.drop_index(op.f("ix_products_subcategory_id"), table_name="products")
    op.drop_constraint("fk_products_subcategory_id", "products", type_="foreignkey")
    op.drop_column("products", "subcategory_id")
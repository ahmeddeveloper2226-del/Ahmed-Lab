"""require product_id on prescription_items, drop custom name/price

Revision ID: I6d0e2f5b8a4
Revises: H5c9d1f4a7e3
Create Date: 2026-08-05

Tightens PrescriptionItem to always reference a real catalog Product —
removes the freeform "type in a medicine name/price" escape hatch. That
option could never actually be added to a customer's cart anyway (the cart
is strictly product_id-keyed — see cart_repository.dart), so this closes
the gap between "what the pharmacist can offer" and "what the customer can
actually accept into their cart" rather than leaving a UI path that always
dead-ended.

Any existing prescription_items rows with product_id NULL (i.e. someone
already used the custom-entry path before this migration) get deleted —
there's no real product to attach them to, and this is early enough in the
app's life that no live customer data is expected to depend on them. If
that's no longer true by the time you run this, back up prescription_items
first.
"""
from alembic import op
import sqlalchemy as sa

revision = "I6d0e2f5b8a4"
down_revision = "H5c9d1f4a7e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM prescription_items WHERE product_id IS NULL"))

    op.drop_column("prescription_items", "custom_name")
    op.drop_column("prescription_items", "custom_price")
    op.alter_column("prescription_items", "product_id", nullable=False)


def downgrade() -> None:
    op.alter_column("prescription_items", "product_id", nullable=True)
    op.add_column("prescription_items", sa.Column("custom_name", sa.String(), nullable=True))
    op.add_column("prescription_items", sa.Column("custom_price", sa.Numeric(10, 2), nullable=True))
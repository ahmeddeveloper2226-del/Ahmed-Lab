"""add sale_price to products (AIO Fast Picks)

Revision ID: J7e1f3a6c9d5
Revises: I6d0e2f5b8a4
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'J7e1f3a6c9d5'
down_revision: Union[str, Sequence[str], None] = 'I6d0e2f5b8a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable discounted price — NULL means "not on sale". A product
    # becomes an AIO Fast Picks candidate when sale_price is set and is
    # lower than price (see products_router.get_fast_picks and
    # categories_router.get_category_fast_picks).
    op.add_column('products', sa.Column('sale_price', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'sale_price')

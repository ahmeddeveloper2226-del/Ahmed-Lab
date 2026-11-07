"""add description/logo_url to shops and description/image_url to products

Revision ID: b3e7f1a9c5d2
Revises: 8fd02de07a50
Create Date: 2026-07-25 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e7f1a9c5d2'
down_revision: Union[str, Sequence[str], None] = '8fd02de07a50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('shops', sa.Column('description', sa.String(), nullable=True))
    op.add_column('shops', sa.Column('logo_url', sa.String(), nullable=True))
    op.add_column('products', sa.Column('description', sa.String(), nullable=True))
    op.add_column('products', sa.Column('image_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'image_url')
    op.drop_column('products', 'description')
    op.drop_column('shops', 'logo_url')
    op.drop_column('shops', 'description')
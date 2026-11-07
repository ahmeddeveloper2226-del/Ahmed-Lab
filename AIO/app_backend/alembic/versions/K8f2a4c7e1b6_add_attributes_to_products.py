"""add attributes to products

Revision ID: k8f2a4c7e1b6
Revises: J7e1f3a6c9d5
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k8f2a4c7e1b6'
down_revision: Union[str, Sequence[str], None] = 'J7e1f3a6c9d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('attributes', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'attributes')

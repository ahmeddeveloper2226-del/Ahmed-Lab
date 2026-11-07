"""merge heads

Revision ID: 8fd02de07a50
Revises: 9a1f3c7d2e4b, c47f412b3552
Create Date: 2026-07-25 07:26:40.320677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fd02de07a50'
down_revision: Union[str, Sequence[str], None] = ('9a1f3c7d2e4b', 'c47f412b3552')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

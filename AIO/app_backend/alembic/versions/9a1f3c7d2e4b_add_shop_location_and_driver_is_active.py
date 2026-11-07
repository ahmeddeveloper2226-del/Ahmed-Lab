"""add lat/lng to shops and is_active to drivers

Revision ID: 9a1f3c7d2e4b
Revises: 6afe51ff2762
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1f3c7d2e4b'
down_revision: Union[str, Sequence[str], None] = '6afe51ff2762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('shops', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('shops', sa.Column('lng', sa.Float(), nullable=True))
    op.add_column(
        'drivers',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # Drop the server_default after backfilling existing rows — new rows
    # will rely on the SQLAlchemy model's default=True instead, keeping the
    # column definition clean going forward (matches the style of other
    # boolean columns in this codebase, e.g. Driver.is_available).
    op.alter_column('drivers', 'is_active', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drivers', 'is_active')
    op.drop_column('shops', 'lng')
    op.drop_column('shops', 'lat')
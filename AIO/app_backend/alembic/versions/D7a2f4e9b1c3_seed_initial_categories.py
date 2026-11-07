"""seed initial categories

Revision ID: d7a2f4e9b1c3
Revises: c1d4e8f2a6b9
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a2f4e9b1c3'
down_revision: Union[str, Sequence[str], None] = 'c1d4e8f2a6b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    ("grocery", "بقالة"),
    ("clothes", "ملابس"),
    ("food", "مطاعم"),
    ("electronics", "إلكترونيات"),
    ("pharmacies", "صيدليات"),
]


def upgrade() -> None:
    """Upgrade schema."""
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
    )
    conn = op.get_bind()
    for category_id, name in CATEGORIES:
        # ON CONFLICT DO NOTHING — safe to re-run, and safe if any of these
        # ids happen to already exist from manual testing via the admin API.
        conn.execute(
            sa.text(
                "INSERT INTO categories (id, name) VALUES (:id, :name) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": category_id, "name": name},
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    for category_id, _ in CATEGORIES:
        conn.execute(
            sa.text("DELETE FROM categories WHERE id = :id"),
            {"id": category_id},
        )
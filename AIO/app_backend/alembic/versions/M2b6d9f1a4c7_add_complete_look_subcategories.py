"""add pants/bags/watches clothes subcategories

Revision ID: M2b6d9f1a4c7
Revises: L9a3b7c2d4e8
Create Date: 2026-08-08

Backs the 'Complete the Look' feature (see
app/services/complete_look_service.py): recommending pants/shoes/bags/
watches/accessories alongside a viewed clothing item needs each of those
to be an actual taggable subcategory. clothes_4 (الأحذية/shoes) and
clothes_5 (الإكسسوارات/accessories) already existed; this adds the three
that didn't.
"""
from alembic import op
import sqlalchemy as sa

revision = "M2b6d9f1a4c7"
down_revision = "L9a3b7c2d4e8"
branch_labels = None
depends_on = None

NEW_SUBCATEGORIES = [
    ("clothes_7", "clothes", "البنطلونات", 7),
    ("clothes_8", "clothes", "الحقائب", 8),
    ("clothes_9", "clothes", "الساعات", 9),
]


def upgrade() -> None:
    subcategories_table = sa.table(
        "subcategories",
        sa.column("id", sa.String),
        sa.column("category_id", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    conn = op.get_bind()
    for sub_id, category_id, name, sort_order in NEW_SUBCATEGORIES:
        conn.execute(
            sa.text(
                "INSERT INTO subcategories (id, category_id, name, sort_order) "
                "VALUES (:id, :category_id, :name, :sort_order) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": sub_id, "category_id": category_id, "name": name, "sort_order": sort_order},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for sub_id, _, _, _ in NEW_SUBCATEGORIES:
        conn.execute(sa.text("DELETE FROM subcategories WHERE id = :id"), {"id": sub_id})

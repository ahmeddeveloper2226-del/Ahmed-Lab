"""add subcategories table, shops.subcategory_id, and seed subcategory data

Revision ID: F3a7b9d2e5c1
Revises: E2f6a8c1d4b7
Create Date: 2026-08-02

Adds a second, optional level under the existing 5 categories
(grocery/clothes/food/electronics/pharmacies) so shops can be tagged more
specifically — e.g. an electronics shop tagged "الهواتف المحمولة" instead
of just "electronics" — and the app can show a pill-chip filter row per
category (see shops_screen.dart).
"""
from alembic import op
import sqlalchemy as sa

revision = "F3a7b9d2e5c1"
down_revision = "E2f6a8c1d4b7"
branch_labels = None
depends_on = None


# (id, category_id, name, sort_order) — sort_order preserves the exact
# ordering given for each category, so the pill row is stable and matches
# how the categories were actually listed, not alphabetical/insertion-order
# luck.
SUBCATEGORIES = [
    # الملابس (clothes)
    ("clothes_1", "clothes", "ملابس رجالية", 1),
    ("clothes_2", "clothes", "ملابس نسائية", 2),
    ("clothes_3", "clothes", "ملابس أطفال", 3),
    ("clothes_4", "clothes", "الأحذية", 4),
    ("clothes_5", "clothes", "الإكسسوارات", 5),
    ("clothes_6", "clothes", "العطور", 6),

    # البقالة (grocery)
    ("grocery_1", "grocery", "الخضروات والفواكه", 1),
    ("grocery_2", "grocery", "الألبان والبيض", 2),
    ("grocery_3", "grocery", "اللحوم والمأكولات البحرية", 3),
    ("grocery_4", "grocery", "المخبوزات", 4),
    ("grocery_5", "grocery", "الأرز والمكرونة والحبوب", 5),
    ("grocery_6", "grocery", "مستلزمات الطبخ", 6),
    ("grocery_7", "grocery", "المعلبات والأطعمة المعبأة", 7),
    ("grocery_8", "grocery", "الأطعمة المجمدة", 8),
    ("grocery_9", "grocery", "الوجبات الخفيفة", 9),
    ("grocery_10", "grocery", "المشروبات", 10),
    ("grocery_11", "grocery", "منتجات الإفطار", 11),
    ("grocery_12", "grocery", "أغذية الأطفال", 12),
    ("grocery_13", "grocery", "المنتجات الصحية والعضوية", 13),
    ("grocery_14", "grocery", "المستلزمات المنزلية", 14),
    ("grocery_15", "grocery", "مستلزمات التنظيف", 15),
    ("grocery_16", "grocery", "العناية الشخصية", 16),

    # الصيدليات (pharmacies)
    ("pharmacies_1", "pharmacies", "الأدوية", 1),
    ("pharmacies_2", "pharmacies", "الفيتامينات والمكملات", 2),
    ("pharmacies_3", "pharmacies", "العناية بالبشرة", 3),
    ("pharmacies_4", "pharmacies", "العناية بالشعر", 4),
    ("pharmacies_5", "pharmacies", "العناية بالفم والأسنان", 5),
    ("pharmacies_6", "pharmacies", "العناية بالأطفال", 6),
    ("pharmacies_7", "pharmacies", "المستلزمات الطبية", 7),
    ("pharmacies_8", "pharmacies", "الأجهزة الطبية", 8),
    ("pharmacies_9", "pharmacies", "العطور الطبية", 9),

    # الطعام (food)
    ("food_1", "food", "مطاعم", 1),
    ("food_2", "food", "وجبات سريعة", 2),
    ("food_3", "food", "بيتزا", 3),
    ("food_4", "food", "برجر", 4),
    ("food_5", "food", "مشويات", 5),
    ("food_6", "food", "مأكولات بحرية", 6),
    ("food_7", "food", "حلويات", 7),
    ("food_8", "food", "مخبوزات", 8),
    ("food_9", "food", "مشروبات", 9),
    ("food_10", "food", "قهوة ومقاهي", 10),

    # الإلكترونيات (electronics)
    ("electronics_1", "electronics", "الهواتف المحمولة", 1),
    ("electronics_2", "electronics", "أجهزة الكمبيوتر", 2),
    ("electronics_3", "electronics", "اللابتوبات", 3),
    ("electronics_4", "electronics", "الأجهزة اللوحية (تابلت)", 4),
    ("electronics_5", "electronics", "الساعات الذكية", 5),
    ("electronics_6", "electronics", "السماعات", 6),
    ("electronics_7", "electronics", "التلفزيونات", 7),
    ("electronics_8", "electronics", "الكاميرات", 8),
    ("electronics_9", "electronics", "أجهزة الألعاب", 9),
    ("electronics_10", "electronics", "الإكسسوارات", 10),
    ("electronics_11", "electronics", "الشبكات والراوترات", 11),
    ("electronics_12", "electronics", "الأجهزة المنزلية الذكية", 12),
]


def upgrade() -> None:
    op.create_table(
        "subcategories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("category_id", sa.String(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_subcategories_category_id"), "subcategories", ["category_id"], unique=False)

    op.add_column("shops", sa.Column("subcategory_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_shops_subcategory_id", "shops", "subcategories", ["subcategory_id"], ["id"]
    )
    op.create_index(op.f("ix_shops_subcategory_id"), "shops", ["subcategory_id"], unique=False)

    subcategories_table = sa.table(
        "subcategories",
        sa.column("id", sa.String),
        sa.column("category_id", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    conn = op.get_bind()
    for sub_id, category_id, name, sort_order in SUBCATEGORIES:
        conn.execute(
            sa.text(
                "INSERT INTO subcategories (id, category_id, name, sort_order) "
                "VALUES (:id, :category_id, :name, :sort_order) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": sub_id, "category_id": category_id, "name": name, "sort_order": sort_order},
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_shops_subcategory_id"), table_name="shops")
    op.drop_constraint("fk_shops_subcategory_id", "shops", type_="foreignkey")
    op.drop_column("shops", "subcategory_id")

    op.drop_index(op.f("ix_subcategories_category_id"), table_name="subcategories")
    op.drop_table("subcategories")
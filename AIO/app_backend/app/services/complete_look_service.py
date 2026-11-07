"""
Backs 'Complete the Look' (Clothes-exclusive): when a customer views a
clothing item, recommend one matching product from each of a fixed set of
complementary slots — pants, shoes, bags, watches, accessories — skipping
whichever slot the viewed product itself belongs to (don't recommend
pants while looking at pants).

Deliberately simple and deterministic (no LLM call, no ML model): each
slot maps 1:1 to an existing Subcategory id, seeded in
M2b6d9f1a4c7_add_complete_look_subcategories.py. A store owner tags a
product with one of these subcategories the same way they already tag
"shoes" or "accessories" products today — this feature just adds the
missing pants/bags/watches tags and a fixed presentation order for them.
"""
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import Product
from ..models.shop import Shop
from ..schemas.product_schemas import ProductResponse

logger = logging.getLogger("wasla.complete_look")

# (subcategory_id, slot key, Arabic label shown as the section chip)
_SLOTS: list[tuple[str, str, str]] = [
    ("clothes_7", "pants", "بنطلون"),
    ("clothes_4", "shoes", "حذاء"),
    ("clothes_8", "bags", "حقيبة"),
    ("clothes_9", "watches", "ساعة"),
    ("clothes_5", "accessories", "إكسسوار"),
]


async def get_complete_look(db: AsyncSession, product_id: str) -> list[dict]:
    result = await db.execute(
        select(Product, Shop).join(Shop, Product.shop_id == Shop.id).where(Product.id == product_id)
    )
    row = result.first()
    if row is None:
        return []
    product, shop = row

    # Clothes-only — a grocery or electronics product never gets an outfit rail.
    if shop.category_id != "clothes":
        return []

    suggestions = []
    for subcategory_id, slot, label in _SLOTS:
        if subcategory_id == product.subcategory_id:
            continue  # don't recommend more of the same slot as the item being viewed

        try:
            # Same shop first (a cohesive look from one store), then
            # anywhere else in the clothes category — either way, only
            # in-stock items are worth recommending.
            same_shop_stmt = (
                select(Product)
                .where(Product.subcategory_id == subcategory_id)
                .where(Product.shop_id == product.shop_id)
                .where(Product.stock_quantity > 0)
                .limit(1)
            )
            match_result = await db.execute(same_shop_stmt)
            match = match_result.scalar_one_or_none()

            if match is None:
                any_shop_stmt = (
                    select(Product)
                    .join(Shop, Product.shop_id == Shop.id)
                    .where(Product.subcategory_id == subcategory_id)
                    .where(Shop.category_id == "clothes")
                    .where(Product.stock_quantity > 0)
                    .order_by(Product.id.desc())
                    .limit(1)
                )
                match_result = await db.execute(any_shop_stmt)
                match = match_result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error("Complete-the-look lookup failed for slot=%s product=%s: %s", slot, product_id, e)
            continue

        if match is not None:
            suggestions.append({
                "slot": slot,
                "slot_label": label,
                "product": ProductResponse.from_product(match),
            })

    return suggestions

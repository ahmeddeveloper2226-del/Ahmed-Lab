import json
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import Product
from ..models.shop import Shop
from ..redis_client import redis_client
from ..schemas.cart_schemas import CartItemResponse, CartResponse

logger = logging.getLogger("wasla.cart")

CART_KEY_PREFIX = "cart"


def cart_key(uid: str) -> str:
    return f"{CART_KEY_PREFIX}:{uid}"


async def get_raw_cart(uid: str) -> dict[str, int]:
    """Returns {product_id: quantity}, or {} if no cart exists yet."""
    try:
        raw = await redis_client.get(cart_key(uid))
    except Exception as e:
        logger.error(f"Redis read failed for cart uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your cart right now. Please try again.",
        )
    return json.loads(raw) if raw else {}


async def save_raw_cart(uid: str, cart: dict[str, int]) -> None:
    try:
        if cart:
            await redis_client.set(cart_key(uid), json.dumps(cart))
        else:
            await redis_client.delete(cart_key(uid))
    except Exception as e:
        logger.error(f"Redis write failed for cart uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update your cart right now. Please try again.",
        )


async def clear_cart(uid: str) -> None:
    await save_raw_cart(uid, {})


def add_product_to_raw_cart(raw_cart: dict[str, int], product: Product, quantity: int = 1) -> bool:
    """
    Shared primitive for every 'add this product to the cart, clamped to
    what's actually in stock' spot in the codebase — previously this exact
    stock-check-then-increment logic was reimplemented separately in
    shopping_list_service.py (twice), medication_service.py (twice), and
    products_router.py's quick-add, each a slightly different copy of the
    same three lines. Consolidated here so there's one place that decides
    what "add N of this product" means, instead of N places that could
    quietly drift out of sync with each other.

    Mutates raw_cart in place. Returns False (and leaves raw_cart
    untouched) if the product has no stock at all or quantity < 1 — the
    caller is responsible for counting that as "skipped". Otherwise adds
    min(quantity, product.stock_quantity) and returns True.

    Deliberately does NOT read/write Redis itself — callers batch several
    of these against one in-memory dict, then call save_raw_cart() once at
    the end (see meal_builder_router.py's _add_meal_items_to_cart for the
    pattern), rather than one Redis round trip per item.
    """
    if quantity < 1 or product.stock_quantity < 1:
        return False
    clamped_quantity = min(quantity, product.stock_quantity)
    raw_cart[product.id] = raw_cart.get(product.id, 0) + clamped_quantity
    return True


async def build_cart_response(db: AsyncSession, uid: str, raw_cart: dict[str, int]) -> CartResponse:
    """
    Turns {product_id: quantity} into a full priced response, joined live
    against Postgres. Self-heals: drops (and persists the removal of) any
    product that no longer exists, rather than crashing or showing a ghost
    item forever.
    """
    if not raw_cart:
        return CartResponse(items=[], total=0.0)

    try:
        result = await db.execute(select(Product).where(Product.id.in_(raw_cart.keys())))
        products = {p.id: p for p in result.scalars().all()}

        shop_ids = {p.shop_id for p in products.values()}
        shops_result = await db.execute(select(Shop).where(Shop.id.in_(shop_ids)))
        shops = {s.id: s for s in shops_result.scalars().all()}
    except SQLAlchemyError as e:
        logger.error(f"Failed to build cart response for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your cart right now. Please try again.",
        )

    items: list[CartItemResponse] = []
    corrected_cart = dict(raw_cart)
    cart_changed = False

    for product_id, quantity in raw_cart.items():
        product = products.get(product_id)
        if product is None:
            del corrected_cart[product_id]
            cart_changed = True
            continue

        shop = shops.get(product.shop_id)
        price = float(product.price)
        items.append(
            CartItemResponse(
                product_id=product.id,
                shop_id=product.shop_id,
                shop_name=shop.name if shop else "Unknown shop",
                name=product.name,
                price=price,
                quantity=quantity,
                subtotal=round(price * quantity, 2),
            )
        )

    if cart_changed:
        await save_raw_cart(uid, corrected_cart)

    total = round(sum(item.subtotal for item in items), 2)
    return CartResponse(items=items, total=total)
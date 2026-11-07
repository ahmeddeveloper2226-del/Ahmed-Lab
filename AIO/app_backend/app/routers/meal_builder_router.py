import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.product import Product
from ..rate_limiter import limiter
from ..schemas.meal_builder_schemas import (
    MEAL_TYPES,
    AddMealToCartRequest,
    AddMealToCartResult,
    BuildMealRequest,
    BuildMealResponse,
    CrossRestaurantBuildMealRequest,
    CrossRestaurantBuildMealResponse,
    MealTypeOption,
)
from ..services.cart_service import add_product_to_raw_cart, get_raw_cart, save_raw_cart
from ..services.cross_restaurant_meal_builder_service import build_cross_restaurant_meal
from ..services.meal_builder_service import build_meal

logger = logging.getLogger("wasla.meal_builder")

router = APIRouter()


@router.get("/meal-types", response_model=list[MealTypeOption])
async def get_meal_types():
    return MEAL_TYPES


@router.post("/shops/{shop_id}/meal-builder", response_model=BuildMealResponse)
@limiter.limit("10/minute")
async def build_meal_for_shop(
    request: Request,
    shop_id: str,
    payload: BuildMealRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        meal_title, items, has_menu = await build_meal(db, shop_id, payload.meal_type, payload.party_size)
    except RuntimeError as e:
        logger.error("Meal Builder misconfigured: %s", e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ميزة بناء الوجبة غير متاحة حاليًا.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Meal Builder failed for shop=%s: %s", shop_id, e, exc_info=True)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر بناء الوجبة الآن، حاول مرة أخرى.")

    total_price = sum(item.product.price * item.quantity for item in items)

    return BuildMealResponse(
        meal_type=payload.meal_type,
        meal_title=meal_title,
        items=items,
        total_price=round(total_price, 2),
        has_menu=has_menu,
    )


async def _add_meal_items_to_cart(db: AsyncSession, uid: str, payload: AddMealToCartRequest) -> AddMealToCartResult:
    """Shared by both the per-restaurant and cross-restaurant add-to-cart
    endpoints — never actually needed a shop_id, since the cart already
    supports items from multiple shops (checkout splits them into
    separate per-shop orders under one checkout_group_id — see
    order_service.py) and it just looks products up by id regardless."""
    try:
        product_ids = [str(i.get("product_id")) for i in payload.items]
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products_by_id = {p.id: p for p in result.scalars().all()}
    except SQLAlchemyError as e:
        logger.error("Failed to load products for meal add-to-cart: %s", e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذرت إضافة الوجبة الآن.")

    raw_cart = await get_raw_cart(uid)
    added, skipped = 0, 0
    for item in payload.items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        product = products_by_id.get(product_id)
        if product is None or not isinstance(quantity, int) or quantity < 1 or quantity > product.stock_quantity:
            skipped += 1
            continue
        add_product_to_raw_cart(raw_cart, product, quantity)
        added += 1

    await save_raw_cart(uid, raw_cart)
    return AddMealToCartResult(added_count=added, skipped_count=skipped)


@router.post("/shops/{shop_id}/meal-builder/add-to-cart", response_model=AddMealToCartResult)
@limiter.limit("15/minute")
async def add_meal_to_cart(
    request: Request,
    shop_id: str,
    payload: AddMealToCartRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """Adds the whole built meal to the cart in one tap — one line per
    distinct product, at the quantity the meal called for."""
    return await _add_meal_items_to_cart(db, uid, payload)


# ─────────────────────────────────────────────────────────────────────────
#  Cross-restaurant meal builder — see cross_restaurant_meal_builder_service.py
#  for the full design. Rate-limited much more tightly than the
#  per-restaurant version above: each call does a search step PLUS a
#  larger Claude prompt covering up to 10 restaurants, so it costs
#  meaningfully more per request.
# ─────────────────────────────────────────────────────────────────────────


@router.post("/meal-builder/cross-restaurant", response_model=CrossRestaurantBuildMealResponse)
@limiter.limit("5/minute")
async def build_cross_restaurant_meal_endpoint(
    request: Request,
    payload: CrossRestaurantBuildMealRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        meal_title, items, has_results = await build_cross_restaurant_meal(db, payload.query, payload.party_size)
    except RuntimeError as e:
        logger.error("Cross-restaurant Meal Builder misconfigured: %s", e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ميزة بناء الوجبة من كل المطاعم غير متاحة حاليًا.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cross-restaurant Meal Builder failed for query=%r: %s", payload.query, e, exc_info=True)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر بناء الوجبة الآن، حاول مرة أخرى.")

    total_price = sum(item.product.price * item.quantity for item in items)
    restaurants_used = sorted({item.shop_name for item in items})

    return CrossRestaurantBuildMealResponse(
        meal_title=meal_title,
        items=items,
        total_price=round(total_price, 2),
        restaurants_used=restaurants_used,
        has_results=has_results,
    )


@router.post("/meal-builder/cross-restaurant/add-to-cart", response_model=AddMealToCartResult)
@limiter.limit("15/minute")
async def add_cross_restaurant_meal_to_cart(
    request: Request,
    payload: AddMealToCartRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await _add_meal_items_to_cart(db, uid, payload)

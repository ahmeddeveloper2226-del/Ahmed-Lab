import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.product import Product
from ..rate_limiter import limiter
from ..schemas.cart_schemas import CartResponse, UpdateCartItemRequest
from ..services.cart_service import build_cart_response, get_raw_cart, save_raw_cart

logger = logging.getLogger("wasla.cart")

router = APIRouter()


@router.get("/", response_model=CartResponse)
async def get_cart(
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    raw_cart = await get_raw_cart(uid)
    return await build_cart_response(db, uid, raw_cart)


@router.put("/items/{product_id}", response_model=CartResponse)
@limiter.limit("30/minute")
async def update_cart_item(
    request: Request,
    product_id: str,
    payload: UpdateCartItemRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Sets the exact quantity for one product (0 removes it). Idempotent.
    Stock is validated against Postgres here, at add-time — not just
    trusted from whatever the client last fetched.
    """
    if payload.quantity > 0:
        try:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Failed to validate product for cart update: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not update your cart right now. Please try again.",
            )

        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        if payload.quantity > product.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {product.stock_quantity} left in stock.",
            )

    raw_cart = await get_raw_cart(uid)

    if payload.quantity == 0:
        raw_cart.pop(product_id, None)
    else:
        raw_cart[product_id] = payload.quantity

    await save_raw_cart(uid, raw_cart)

    return await build_cart_response(db, uid, raw_cart)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    raw_cart = await get_raw_cart(uid)
    raw_cart.pop(product_id, None)
    await save_raw_cart(uid, raw_cart)
    return await build_cart_response(db, uid, raw_cart)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart_endpoint(uid: str = Depends(get_current_user_id)):
    await save_raw_cart(uid, {})
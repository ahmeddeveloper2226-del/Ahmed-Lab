import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_store_uid, get_db_session
from ..models.order import Order, OrderStatus
from ..models.product import Product
from ..models.shop import Shop
from ..rate_limiter import limiter
from ..schemas.product_schemas import ProductResponse
from ..schemas.store_schemas import (
    IncomingOrderResponse,
    MyShopResponse,
    MyShopUpdateRequest,
    StockUpdateRequest,
    StoreProductCreateRequest,
    StoreProductUpdateRequest,
    UpdateOrderStatusRequest,
)
from ..services.cache_service import invalidate_cached
from ..services.search_service import delete_product_from_index, index_product

logger = logging.getLogger("wasla.store_panel")

router = APIRouter()


async def _get_owned_shop_or_404(db: AsyncSession, store_uid: str) -> Shop:
    """
    Shared ownership lookup — every endpoint in this router needs to know
    "which shop does THIS store account actually own," and reject if none
    (a store-role account with no shop assigned yet, or a real permission
    problem) rather than silently letting them touch nothing or everything.
    """
    result = await db.execute(select(Shop).where(Shop.owner_user_id == store_uid))
    shop = result.scalar_one_or_none()

    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No shop is currently assigned to this store account.",
        )

    return shop


@router.get("/my-shop", response_model=MyShopResponse)
async def get_my_shop(
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    return await _get_owned_shop_or_404(db, store_uid)


@router.patch("/my-shop", response_model=MyShopResponse)
@limiter.limit("20/minute")
async def update_my_shop(
    request: Request,
    payload: MyShopUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Lets a store owner edit their own shop's name, description, logo, or
    location — self-service, no admin needed for routine updates like
    "we moved locations" or "update our logo."
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(my_shop, field, value)

    try:
        await db.commit()
        await db.refresh(my_shop)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update shop for store_uid={store_uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update your shop right now. Please try again.",
        )

    await invalidate_cached(f"shops:detail:{my_shop.id}")
    await invalidate_cached(f"shops:by_category:{my_shop.category_id}")

    return my_shop


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_my_product(
    request: Request,
    payload: StoreProductCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Lets a store owner add a new product to their own shop directly,
    instead of needing an admin to do it via products_router.py for every
    single item — the realistic day-to-day way a store actually manages
    its own menu/catalog.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    try:
        product = Product(
            id=payload.id,
            shop_id=my_shop.id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            price=payload.price,
            sale_price=payload.sale_price,
            stock_quantity=payload.stock_quantity,
            attributes=payload.attributes,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with id '{payload.id}' already exists.",
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create product for shop={my_shop.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create this product right now. Please try again.",
        )

    await invalidate_cached(f"products:by_shop:{my_shop.id}")
    await index_product(product, my_shop)

    return ProductResponse.from_product(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
@limiter.limit("60/minute")
async def update_my_product(
    request: Request,
    product_id: str,
    payload: StoreProductUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Full product edit (name/description/image/price/stock) for a store
    owner's OWN product — the stock-only endpoint below still exists
    unchanged for anything already calling it, this is the fuller version
    for actually managing a catalog.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if product is None or product.shop_id != my_shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update product={product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this product right now. Please try again.",
        )

    await invalidate_cached(f"products:by_shop:{product.shop_id}")
    await invalidate_cached(f"products:detail:{product.id}")
    await index_product(product, my_shop)

    return ProductResponse.from_product(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_my_product(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Deletes a product from the store owner's own shop. Same ownership
    pattern as update/stock above: 404 (not 403) whether the product
    doesn't exist at all or just belongs to someone else's shop, so this
    never leaks which is which.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if product is None or product.shop_id != my_shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        await db.delete(product)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to delete product={product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete this product right now. Please try again.",
        )

    await invalidate_cached(f"products:by_shop:{my_shop.id}")
    await invalidate_cached(f"products:detail:{product_id}")
    await delete_product_from_index(product_id)


@router.patch("/products/{product_id}/stock", response_model=None, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def update_product_stock(
    request: Request,
    product_id: str,
    payload: StockUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Updates a product's stock. Ownership is enforced via the product's
    PARENT shop, not just "any product exists with this id" — a store
    account can only ever touch products belonging to the one shop it owns.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if product is None or product.shop_id != my_shop.id:
            # Same deliberate 404-for-both pattern as profile_router's
            # addresses — doesn't leak whether the product exists at all
            # if it belongs to someone else's shop.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        product.stock_quantity = payload.stock_quantity
        await db.commit()
        await db.refresh(product)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update stock for product={product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update stock right now. Please try again.",
        )

    # No cache invalidation needed here: products_router.py never caches
    # stock_quantity/in_stock (only the static name/price/image/etc part
    # of a product), and always re-reads stock live from Postgres on every
    # request — see the block above _product_static_payload there for why.
    # So a pure stock change can't leave the cache stale. We still push to
    # Elasticsearch so search results reflect the new stock too.
    await index_product(product, my_shop)

    return {"id": product.id, "stock_quantity": product.stock_quantity}


@router.get("/orders", response_model=list[IncomingOrderResponse])
async def get_incoming_orders(
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Lists orders for the store's own shop only — scoping happens via the
    WHERE clause itself (Order.shop_id == my_shop.id), not by filtering a
    broader query after the fact, so there is no code path where this
    could accidentally return another shop's orders.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    try:
        result = await db.execute(
            select(Order).where(Order.shop_id == my_shop.id).order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch incoming orders for shop={my_shop.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load orders right now. Please try again.",
        )

    return orders


@router.patch("/orders/{order_id}/status", response_model=IncomingOrderResponse)
@limiter.limit("60/minute")
async def update_order_status(
    request: Request,
    order_id: str,
    payload: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db_session),
    store_uid: str = Depends(get_current_store_uid),
):
    """
    Lets the shop move an order through pending -> preparing ->
    out_for_delivery. Deliberately does NOT allow a shop to set
    'delivered' — that transition belongs to the driver app (Phase 3),
    since the shop has no way to actually know the food was handed over.
    """
    my_shop = await _get_owned_shop_or_404(db, store_uid)

    # A shop may only ever move an order forward through its own
    # fulfillment stages, never claim a delivery outcome it can't observe.
    allowed_transitions = {OrderStatus.pending, OrderStatus.preparing, OrderStatus.out_for_delivery}
    if payload.status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shops may only set status to pending, preparing, or out_for_delivery.",
        )

    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()

        if order is None or order.shop_id != my_shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        order.status = payload.status
        await db.commit()
        await db.refresh(order)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update status for order={order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this order right now. Please try again.",
        )

    return order
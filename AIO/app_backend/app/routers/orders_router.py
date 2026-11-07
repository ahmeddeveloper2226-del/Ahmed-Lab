"""
GET /orders        — list all orders belonging to the authenticated user.
GET /orders/{id}   — get a single order by ID.

Ownership is enforced on every read:

  /orders filters by user_id == uid at the SQL level — a user can never
  receive another user's orders, even if they guess a valid order ID.

  /orders/{id} fetches by primary key but then checks order.user_id == uid.
  If the order doesn't exist OR belongs to a different user, we return 404
  (not 403). A 403 would confirm that the order ID is valid, which is itself
  an information leak — an attacker could enumerate real order IDs.

Items are loaded with selectinload() — a single additional SELECT query for
all items in the result set, rather than N+1 lazy loads per order. This
matters at scale: a user with 50 orders would otherwise trigger 50 separate
item queries. Shop and driver are loaded the same way, for the same reason
— this response now includes enough to power the live tracking map and the
"chat/call your driver" entry point (shop location, delivery address,
driver's name), without the customer app needing extra round trips per order.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..dependencies import get_current_user_id, get_db_session
from ..models.address import Address
from ..models.driver import Driver
from ..models.order import Order, OrderItem
from ..models.review import Review
from ..schemas.order_schemas import OrderItemResponse, OrderResponse

router = APIRouter()
logger = logging.getLogger("wasla.orders")


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Returns all orders for the authenticated user, newest first.
    An empty list (no orders yet) is a valid 200 response, not a 404.
    """
    try:
        result = await db.execute(
            select(Order)
            .where(Order.user_id == uid)
            .options(
                selectinload(Order.items),
                selectinload(Order.shop),
                selectinload(Order.driver).selectinload(Driver.user),
                selectinload(Order.branch),
            )
            .order_by(Order.created_at.desc())
        )
        orders: list[Order] = list(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.error("Failed to list orders for uid=%s: %s", uid, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your orders right now. Please try again.",
        )

    addresses = await _load_addresses(db, orders)
    reviewed_order_ids = await _load_reviewed_order_ids(db, orders)
    return [_to_response(order, addresses, reviewed_order_ids) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.shop),
                selectinload(Order.driver).selectinload(Driver.user),
                selectinload(Order.branch),
            )
        )
        order: Order | None = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error(
            "Failed to fetch order=%s for uid=%s: %s", order_id, uid, exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load this order right now. Please try again.",
        )

    # Ownership check: return 404 whether the order doesn't exist OR belongs
    # to someone else. Never 403 — that leaks that the order ID is real.
    if order is None or order.user_id != uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    addresses = await _load_addresses(db, [order])
    reviewed_order_ids = await _load_reviewed_order_ids(db, [order])
    return _to_response(order, addresses, reviewed_order_ids)


async def _load_reviewed_order_ids(db: AsyncSession, orders: list[Order]) -> set[str]:
    order_ids = [o.id for o in orders]
    if not order_ids:
        return set()
    result = await db.execute(select(Review.order_id).where(Review.order_id.in_(order_ids)))
    return {row[0] for row in result.all()}


async def _load_addresses(db: AsyncSession, orders: list[Order]) -> dict[str, Address]:
    address_ids = [o.delivery_address_id for o in orders if o.delivery_address_id]
    if not address_ids:
        return {}
    result = await db.execute(select(Address).where(Address.id.in_(address_ids)))
    return {a.id: a for a in result.scalars().all()}


def _to_response(order: Order, addresses: dict[str, Address], reviewed_order_ids: set[str]) -> OrderResponse:
    address = addresses.get(order.delivery_address_id) if order.delivery_address_id else None
    driver_name = order.driver.user.full_name if order.driver and order.driver.user else None
    branch = order.branch

    return OrderResponse(
        id=order.id,
        checkout_group_id=order.checkout_group_id,
        shop_id=order.shop_id,
        shop_name=order.shop.name if order.shop else None,
        shop_lat=order.shop.lat if order.shop else None,
        shop_lng=order.shop.lng if order.shop else None,
        status=order.status.value,
        payment_status=order.payment_status.value,
        total=float(order.total),
        commission_amount=float(order.commission_amount),
        delivery_address=address.full_address if address else None,
        delivery_lat=address.lat if address else None,
        delivery_lng=address.lng if address else None,
        driver_name=driver_name,
        created_at=order.created_at,
        items=[_item_to_response(item) for item in order.items],
        has_review=order.id in reviewed_order_ids,
        delivery_stage=order.delivery_stage.value if order.delivery_stage else None,
        branch_id=branch.id if branch else None,
        branch_name=branch.name if branch else None,
        branch_lat=branch.lat if branch else None,
        branch_lng=branch.lng if branch else None,
        eta_minutes=order.eta_minutes,
        live_eta_minutes=order.live_eta_minutes,
        delivery_fee=float(order.delivery_fee) if order.delivery_fee is not None else None,
        road_distance_km=order.road_distance_km,
    )


def _item_to_response(item: OrderItem) -> OrderItemResponse:
    price = float(item.price_at_purchase)
    return OrderItemResponse(
        id=item.id,
        product_id=item.product_id,
        quantity=item.quantity,
        price_at_purchase=price,
        subtotal=round(price * item.quantity, 2),
    )
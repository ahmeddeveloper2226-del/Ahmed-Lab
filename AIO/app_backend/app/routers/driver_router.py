import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..dependencies import get_current_driver, get_db_session
from ..models.address import Address
from ..models.branch import Branch
from ..models.chat_message import ChatMessage, MessageStatus, MessageType
from ..models.delivery import DeliveryStage, DeliveryFailureReason
from ..models.driver import Driver
from ..models.order import Order, OrderItem, OrderStatus, PaymentStatus
from ..models.shop import Shop
from ..models.user import User
from ..redis_client import redis_client
from ..services import delivery_service
from ..schemas.driver_schemas import (
    AvailabilityUpdate,
    DeliveryFailureReport,
    DeliveryStageUpdate,
    DriverOrderItemResponse,
    DriverOrderResponse,
    DriverStatusUpdate,
    LocationUpdate,
)
from ..services.notification_service import notify_order_status_changed

router = APIRouter()
logger = logging.getLogger("wasla.driver")

# Order statuses that count as "this driver currently holds this order" —
# used both for the multi-order clustering check and the "my active orders" tab.
_ACTIVE_STATUSES = (OrderStatus.preparing, OrderStatus.out_for_delivery)

# Redis sorted-set key for the geo index of available drivers.
# GEOADD / GEOSEARCH / ZREM operations run against this key.
_DRIVERS_GEO_KEY = "wasla:drivers:available"

# Redis pub/sub channel prefix for order tracking — must match tracking_ws_router.py
_TRACKING_CHANNEL_PREFIX = "wasla:tracking:"

# Valid status transitions a driver can make, in order.
# Prevents backwards transitions (e.g. "delivered" → "preparing").
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending: {OrderStatus.preparing},
    OrderStatus.preparing: {OrderStatus.out_for_delivery},
    OrderStatus.out_for_delivery: {OrderStatus.delivered, OrderStatus.cancelled},
}


# ---------------------------------------------------------------------------
# GET /driver/orders/offers
# ---------------------------------------------------------------------------

@router.get("/orders/offers", response_model=list[DriverOrderResponse])
async def list_my_offers(
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Returns delivery groups the assignment worker has OFFERED to this
    driver specifically (driver_id already set to him, status still
    `pending` — he hasn't accepted yet, offer_expires_at hasn't passed).

    This is NOT a browsable list of nearby orders — a driver never sees
    orders that weren't offered to him. If this comes back empty, he has no
    pending offer right now; the app should poll or listen for the push
    notification driver_assignment_worker sends when one arrives.
    """
    try:
        result = await db.execute(
            select(Order)
            .where(
                Order.driver_id == driver.id,
                Order.status == OrderStatus.pending,
                Order.offer_expires_at.is_not(None),
                Order.offer_expires_at > datetime.now(tz=timezone.utc),
            )
            .options(
                selectinload(Order.items),
                selectinload(Order.shop),
                selectinload(Order.user),
                selectinload(Order.branch),
            )
            .order_by(Order.created_at.asc())
        )
        orders: list[Order] = list(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.error("Failed to list offers for driver=%s: %s", driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your offers. Please try again.",
        )

    address_ids = [o.delivery_address_id for o in orders if o.delivery_address_id]
    addresses: dict[str, Address] = {}
    if address_ids:
        addr_result = await db.execute(
            select(Address).where(Address.id.in_(address_ids))
        )
        addresses = {a.id: a for a in addr_result.scalars().all()}

    return [_to_driver_order_response(o, addresses) for o in orders]


# ---------------------------------------------------------------------------
# GET /driver/orders/active
# ---------------------------------------------------------------------------

@router.get("/orders/active", response_model=list[DriverOrderResponse])
async def list_active_orders(
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Returns every order this driver currently holds (accepted but not yet
    delivered/cancelled) — powers the "my orders" tab, as distinct from the
    nearby-orders map/list. A driver can hold more than one at once; see
    accept_order()'s clustering rule for how that's limited to nearby pickups.
    """
    try:
        result = await db.execute(
            select(Order)
            .where(
                Order.driver_id == driver.id,
                Order.status.in_(_ACTIVE_STATUSES),
            )
            .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
            .order_by(Order.created_at.asc())
        )
        orders: list[Order] = list(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.error("Failed to list active orders for driver=%s: %s", driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your active orders. Please try again.",
        )

    address_ids = [o.delivery_address_id for o in orders if o.delivery_address_id]
    addresses: dict[str, Address] = {}
    if address_ids:
        addr_result = await db.execute(
            select(Address).where(Address.id.in_(address_ids))
        )
        addresses = {a.id: a for a in addr_result.scalars().all()}

    return [_to_driver_order_response(o, addresses) for o in orders]


# ---------------------------------------------------------------------------
# GET /driver/orders/{order_id}
# ---------------------------------------------------------------------------
# IMPORTANT: this generic single-order route must be registered AFTER
# /orders/available and /orders/active above — FastAPI matches routes in
# registration order, and a path parameter route declared first would
# otherwise shadow those two literal paths (a request to /orders/active
# would incorrectly match here with order_id="active").

@router.get("/orders/{order_id}", response_model=DriverOrderResponse)
async def get_driver_order(
    order_id: str,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Fetches a single order's detail — used by the order detail screen when
    it isn't already available from a previously-loaded list (app restart,
    deep link, notification tap). Visible to this driver only if the order
    is either unassigned (still decidable) or already assigned to them.
    """
    try:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
        )
        order: Order | None = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error("Failed to load order=%s for driver=%s: %s", order_id, driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load this order. Please try again.",
        )

    if order is None or (order.driver_id is not None and order.driver_id != driver.id):
        # Don't distinguish "doesn't exist" from "belongs to someone else."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    addresses: dict[str, Address] = {}
    if order.delivery_address_id:
        addr_result = await db.execute(select(Address).where(Address.id == order.delivery_address_id))
        addr = addr_result.scalar_one_or_none()
        if addr:
            addresses[addr.id] = addr

    return _to_driver_order_response(order, addresses)


# ---------------------------------------------------------------------------
# POST /driver/orders/group/{delivery_group_id}/accept
# ---------------------------------------------------------------------------

@router.post("/orders/group/{delivery_group_id}/accept", response_model=list[DriverOrderResponse])
async def accept_group(
    delivery_group_id: str,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Accepts a delivery group that was OFFERED to this driver by
    driver_assignment_worker (driver_id already set to him on every order
    in the group; status still `pending`; offer_expires_at not yet passed).

    This is confirmation of an offer the system already made — not a claim
    off a browsable list. If the offer expired or was never his, this
    returns 409/404 rather than letting him grab it.

    Uses SELECT FOR UPDATE on all orders in the group so this can't race
    the assignment worker's expiry sweep or a concurrent decline.

    Side effects (all or nothing, applied to EVERY order in the group):
      - order.status         ← preparing
      - order.offer_expires_at ← cleared
      - driver.is_available   ← False, but ONLY once this group pushes the
        driver's concurrent-order count to the cap — otherwise he stays
        assignable for another nearby zone.
      - Redis pub/sub status update published per order
      - Opening chat message + FCM push sent to the customer per order
    """
    try:
        result = await db.execute(
            select(Order)
            .where(Order.delivery_group_id == delivery_group_id)
            .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
            .with_for_update()
        )
        group_orders: list[Order] = list(result.scalars().all())

        if not group_orders:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery group not found.")

        if any(o.driver_id != driver.id for o in group_orders):
            # Don't reveal whether it belongs to someone else or doesn't exist.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery group not found.")

        if any(o.status != OrderStatus.pending for o in group_orders):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This delivery group is no longer acceptable.",
            )

        now = datetime.now(tz=timezone.utc)
        if any(o.offer_expires_at is None or o.offer_expires_at < now for o in group_orders):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This offer has expired.",
            )

        active_result = await db.execute(
            select(Order)
            .where(
                Order.driver_id == driver.id,
                Order.delivery_group_id != delivery_group_id,
                Order.status.in_(_ACTIVE_STATUSES),
            )
        )
        active_orders_count = len(list(active_result.scalars().all()))

        for order in group_orders:
            order.status = OrderStatus.preparing
            order.offer_expires_at = None
            # Kicks off the granular AIO lifecycle (spec 1.8/2.4) the moment
            # the driver actually exists for this order — before this,
            # delivery_stage was whatever order_service.py set at checkout
            # (order_created/inventory_validated), since no driver existed
            # to assign yet.
            order.delivery_stage = DeliveryStage.driver_assigned

        will_be_at_cap = (active_orders_count + len(group_orders)) >= settings.driver_max_concurrent_orders
        if will_be_at_cap:
            driver.is_available = False

        await db.commit()
        for order in group_orders:
            await db.refresh(order)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB error accepting group=%s driver=%s: %s", delivery_group_id, driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not accept this delivery. Please try again.",
        )

    # --- Post-accept side effects (non-fatal) --------------------------------
    if not driver.is_available:
        await _remove_driver_from_geo(driver.id)

    for order in group_orders:
        await _publish_status_update(order.id, OrderStatus.preparing.value)
        await _publish_stage_update(order.id, DeliveryStage.driver_assigned.value)

        # Opening chat message — one per order, same as before.
        try:
            chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                order_id=order.id,
                sender_id=None,
                receiver_id=order.user_id,
                message_type=MessageType.system,
                status=MessageStatus.sent,
                content="تم قبول طلبك من قبل السائق. يمكنك الآن التواصل معه هنا.",
            )
            db.add(chat_message)
            await db.commit()
            await redis_client.publish(
                f"wasla:chat:{order.id}",
                json.dumps({
                    "type": "message",
                    "from": None,
                    "id": chat_message.id,
                    "order_id": order.id,
                    "content": chat_message.content,
                    "status": chat_message.status.value,
                    "created_at": chat_message.created_at.isoformat(),
                }),
            )
        except Exception:
            await db.rollback()
            logger.error("Failed to create opening chat message for order=%s", order.id)

        try:
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                await notify_order_status_changed(user.fcm_token, order.id, "preparing")
        except Exception:
            logger.error("Failed to send push on accept for order=%s", order.id)

    address_ids = [o.delivery_address_id for o in group_orders if o.delivery_address_id]
    addresses: dict[str, Address] = {}
    if address_ids:
        addr_result = await db.execute(select(Address).where(Address.id.in_(address_ids)))
        addresses = {a.id: a for a in addr_result.scalars().all()}

    return [_to_driver_order_response(o, addresses) for o in group_orders]


# ---------------------------------------------------------------------------
# POST /driver/orders/group/{delivery_group_id}/decline
# ---------------------------------------------------------------------------

@router.post("/orders/group/{delivery_group_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_group(
    delivery_group_id: str,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Declines a delivery group offered to this driver. Clears driver_id and
    offer_expires_at on every order in the group (only if it was actually
    offered to him) and re-publishes the group to driver.assignment so
    driver_assignment_worker offers it to the next-nearest driver, excluding
    this one.

    Functionally equivalent to letting the offer time out — this just does
    it immediately instead of making the customer wait out the full
    driver_offer_timeout_seconds window.
    """
    result = await db.execute(
        select(Order).where(Order.delivery_group_id == delivery_group_id).with_for_update()
    )
    group_orders: list[Order] = list(result.scalars().all())

    if not group_orders or any(o.driver_id != driver.id for o in group_orders):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery group not found.")

    if any(o.status != OrderStatus.pending for o in group_orders):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This delivery group is no longer offered.")

    order_ids = [o.id for o in group_orders]
    customer_uid = group_orders[0].user_id

    try:
        for order in group_orders:
            order.driver_id = None
            order.offer_expires_at = None
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB error declining group=%s driver=%s: %s", delivery_group_id, driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not decline this delivery. Please try again.",
        )

    try:
        await redis_client.sadd(f"wasla:offer_excluded:{delivery_group_id}", driver.id)
        await redis_client.expire(f"wasla:offer_excluded:{delivery_group_id}", 3600)

        import aio_pika
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({
                        "delivery_group_id": delivery_group_id,
                        "order_ids": order_ids,
                        "customer_uid": customer_uid,
                    }).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="driver.assignment",
            )
    except Exception as exc:
        logger.error("Failed to re-publish declined group=%s for reassignment: %s", delivery_group_id, exc)


# ---------------------------------------------------------------------------
# PATCH /driver/orders/{order_id}/status
# ---------------------------------------------------------------------------

@router.patch("/orders/{order_id}/status", response_model=DriverOrderResponse)
async def update_order_status(
    order_id: str,
    payload: DriverStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Moves the order through the delivery lifecycle.

    Valid transitions:
      preparing → out_for_delivery
      out_for_delivery → delivered | cancelled

    Ownership enforced: only the assigned driver can update this order.
    Backwards transitions (e.g. delivered → preparing) are rejected with 422.
    """
    try:
        new_status = OrderStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown status: {payload.status!r}. Valid values: "
                   f"{[s.value for s in OrderStatus]}",
        )

    try:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
            .with_for_update()
        )
        order: Order | None = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error("DB error loading order=%s: %s", order_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error.")

    if order is None or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {order.status.value!r} to {new_status.value!r}.",
        )

    order.status = new_status

    # When an order is delivered or cancelled, the driver becomes available again.
    if new_status in (OrderStatus.delivered, OrderStatus.cancelled):
        driver.is_available = True

    try:
        await db.commit()
        await db.refresh(order)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB commit failed for status update order=%s: %s", order_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update status.")

    # --- Side effects (non-fatal) -------------------------------------------
    await _publish_status_update(order_id, new_status.value)

    # If driver is now free, re-add them to the GEO set for future assignments.
    if driver.is_available and driver.current_lat and driver.current_lng:
        await _add_driver_to_geo(driver.id, driver.current_lat, driver.current_lng)

    try:
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await notify_order_status_changed(user.fcm_token, order_id, new_status.value)
    except Exception:
        logger.error("Failed to send push on status update for order=%s", order_id)

    addresses: dict[str, Address] = {}
    if order.delivery_address_id:
        addr_r = await db.execute(
            select(Address).where(Address.id == order.delivery_address_id)
        )
        addr = addr_r.scalar_one_or_none()
        if addr:
            addresses[addr.id] = addr

    return _to_driver_order_response(order, addresses)


# ---------------------------------------------------------------------------
# PATCH /driver/orders/{order_id}/delivery-stage
# ---------------------------------------------------------------------------

@router.patch("/orders/{order_id}/delivery-stage", response_model=DriverOrderResponse)
async def update_delivery_stage(
    order_id: str,
    payload: DeliveryStageUpdate,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Moves the order through the granular AIO delivery lifecycle (spec
    1.8/2.4-2.6/2.9), e.g. going_to_branch -> arrived_at_branch ->
    waiting_for_order -> picked_up -> in_transit -> arrived_at_customer ->
    delivered. This is DELIBERATELY separate from PATCH .../status above:
    that endpoint drives the coarse OrderStatus that payments/store-panel
    code depends on; this one drives the fine-grained DeliveryStage the
    Customer App's tracking screen and this driver's own step-by-step UI
    read from. See models/delivery.py's module docstring for why they're
    kept apart instead of merged.

    Ownership enforced exactly like the /status endpoint. Invalid
    transitions (skipping steps backward, moving out of a terminal stage)
    are rejected with 409 — see delivery_service.is_valid_transition.
    """
    try:
        new_stage = DeliveryStage(payload.stage)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown delivery stage: {payload.stage!r}. Valid values: "
                   f"{[s.value for s in DeliveryStage]}",
        )

    try:
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
            .with_for_update()
        )
        order: Order | None = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error("DB error loading order=%s: %s", order_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error.")

    if order is None or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if not delivery_service.is_valid_transition(order.delivery_stage, new_stage):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot move delivery stage from "
                   f"{order.delivery_stage.value if order.delivery_stage else 'None'!r} to {new_stage.value!r}.",
        )

    order.delivery_stage = new_stage
    now = delivery_service.now_utc()
    if new_stage == DeliveryStage.picked_up:
        order.pickup_at = now
        # Keeps the coarse OrderStatus (which store-panel/customer history
        # already read before granular stages existed) consistent with its
        # original meaning: "picked_up" is exactly the moment a driver had
        # previously called PATCH .../status with out_for_delivery.
        order.status = OrderStatus.out_for_delivery
    if new_stage == DeliveryStage.delivered:
        order.delivered_at = now
        order.status = OrderStatus.delivered  # keep the coarse status in sync at the one point that matters
        driver.is_available = True
    if new_stage == DeliveryStage.cancelled:
        order.status = OrderStatus.cancelled
        driver.is_available = True

    try:
        await db.commit()
        await db.refresh(order)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB commit failed for delivery-stage update order=%s: %s", order_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update stage.")

    await _publish_stage_update(order_id, new_stage.value)
    # Also publish the coarse "status" message when this stage transition
    # changed order.status above, so any client still listening only for
    # "status" messages (e.g. an older app build) stays correct too.
    if new_stage in (DeliveryStage.picked_up, DeliveryStage.delivered, DeliveryStage.cancelled):
        await _publish_status_update(order_id, order.status.value)

    if driver.is_available and driver.current_lat and driver.current_lng:
        await _add_driver_to_geo(driver.id, driver.current_lat, driver.current_lng)

    try:
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await notify_order_status_changed(user.fcm_token, order_id, new_stage.value)
    except Exception:
        logger.error("Failed to send push on delivery-stage update for order=%s", order_id)

    addresses: dict[str, Address] = {}
    if order.delivery_address_id:
        addr_r = await db.execute(select(Address).where(Address.id == order.delivery_address_id))
        addr = addr_r.scalar_one_or_none()
        if addr:
            addresses[addr.id] = addr

    return _to_driver_order_response(order, addresses)


# ---------------------------------------------------------------------------
# POST /driver/orders/{order_id}/failure  (spec 2.10)
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/failure", response_model=DriverOrderResponse)
async def report_delivery_failure(
    order_id: str,
    payload: DeliveryFailureReport,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """Reports a delivery exception (spec 2.10) — moves the order into
    DeliveryStage.failed_delivery with a recorded reason, and frees the
    driver. Does NOT auto-cancel the order/refund — that's an ops/support
    decision, made with the reason and notes recorded here."""
    try:
        reason = DeliveryFailureReason(payload.reason)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown failure reason: {payload.reason!r}. Valid values: "
                   f"{[r.value for r in DeliveryFailureReason]}",
        )

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.shop), selectinload(Order.user), selectinload(Order.branch))
        .with_for_update()
    )
    order: Order | None = result.scalar_one_or_none()
    if order is None or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order.delivery_stage = DeliveryStage.failed_delivery
    order.failure_reason = reason
    order.failure_notes = payload.notes
    driver.is_available = True

    try:
        await db.commit()
        await db.refresh(order)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB commit failed for failure report order=%s: %s", order_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not record failure.")

    await _publish_stage_update(order_id, DeliveryStage.failed_delivery.value)
    if driver.current_lat and driver.current_lng:
        await _add_driver_to_geo(driver.id, driver.current_lat, driver.current_lng)

    addresses: dict[str, Address] = {}
    if order.delivery_address_id:
        addr_r = await db.execute(select(Address).where(Address.id == order.delivery_address_id))
        addr = addr_r.scalar_one_or_none()
        if addr:
            addresses[addr.id] = addr

    return _to_driver_order_response(order, addresses)


# ---------------------------------------------------------------------------
# POST /driver/location
# ---------------------------------------------------------------------------

@router.post("/location", status_code=status.HTTP_204_NO_CONTENT)
async def update_location(
    payload: LocationUpdate,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Publishes the driver's current GPS coordinates.

    Two writes happen on every location update:
      1. Redis pub/sub publish → tracking WebSocket clients receive it immediately.
      2. Postgres snapshot update → driver.current_lat/lng — the "last known"
         position used for nearest-driver assignment queries. This is NOT the
         live position (that's Redis), just a checkpoint so we don't start
         from zero if the Redis key expires.

    The DB write failure is logged but does NOT fail the response — the pub/sub
    publish (which the customer sees) is the critical path. A stale DB snapshot
    is acceptable for a short period.

    Ownership + active-order checks (added): previously this endpoint would
    publish a location update for ANY order_id the driver sent, with no
    verification it was even assigned to them, and no check that the order
    was still in progress — meaning location updates for an already
    delivered/cancelled order would keep broadcasting indefinitely. Both
    were gaps against "only participants can access live location" and
    "stop sharing when the order is completed/cancelled."
    """
    order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
    order: Order | None = order_result.scalar_one_or_none()

    if order is None or order.driver_id != driver.id:
        # Don't confirm the order exists to a driver it doesn't belong to.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order is no longer active — location sharing has stopped.",
        )

    # --- Dynamic ETA (spec 1.9 / 2.8) ---------------------------------------
    # Recomputed from the driver's CURRENT position on every ping while the
    # order is active, and pushed in the SAME message as the location update
    # so the Customer App's tracking screen never has to poll separately for
    # a fresher ETA than the dot on the map.
    live_eta_minutes = None
    try:
        destination_lat, destination_lng = None, None
        if order.delivery_stage in (
            DeliveryStage.driver_assigned,
            DeliveryStage.going_to_branch,
            DeliveryStage.arrived_at_branch,
            DeliveryStage.waiting_for_order,
        ):
            if order.branch_id:
                branch_result = await db.execute(select(Branch).where(Branch.id == order.branch_id))
                branch = branch_result.scalar_one_or_none()
                if branch:
                    destination_lat, destination_lng = branch.lat, branch.lng
        else:
            destination_lat, destination_lng = order.delivery_lat, order.delivery_lng

        if destination_lat is not None and destination_lng is not None:
            live_eta_minutes = delivery_service.recalculate_live_eta_minutes(
                driver_lat=payload.lat,
                driver_lng=payload.lng,
                destination_lat=destination_lat,
                destination_lng=destination_lng,
                stage=order.delivery_stage or DeliveryStage.in_transit,
            )
            order.live_eta_minutes = live_eta_minutes
    except Exception as exc:
        # ETA is an enhancement, not the critical path — a failure here
        # must never block the location publish itself.
        logger.warning("Live ETA recalculation failed for order=%s: %s", payload.order_id, exc)

    location_message = json.dumps({
        "type": "location",
        "lat": payload.lat,
        "lng": payload.lng,
        "bearing": payload.bearing,
        "speed_kmh": payload.speed_kmh,
        "eta_minutes": live_eta_minutes,
        "ts": datetime.now(tz=timezone.utc).isoformat(),
    })

    try:
        await redis_client.publish(
            f"{_TRACKING_CHANNEL_PREFIX}{payload.order_id}",
            location_message,
        )
    except Exception as exc:
        logger.error(
            "Redis publish failed for driver=%s order=%s: %s",
            driver.id, payload.order_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not publish location update. Please retry.",
        )

    # --- Update DB snapshot (non-fatal if it fails) -------------------------
    try:
        driver.current_lat = payload.lat
        driver.current_lng = payload.lng
        await db.commit()
    except Exception as exc:
        logger.warning(
            "DB snapshot update failed for driver=%s (location still published): %s",
            driver.id, exc,
        )
        await db.rollback()

    # --- Update Redis GEO index if driver is available ----------------------
    if driver.is_available:
        await _add_driver_to_geo(driver.id, payload.lat, payload.lng)


# ---------------------------------------------------------------------------
# PATCH /driver/availability
# ---------------------------------------------------------------------------

@router.patch("/availability", status_code=status.HTTP_204_NO_CONTENT)
async def update_availability(
    payload: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db_session),
    driver: Driver = Depends(get_current_driver),
):
    """
    Marks the driver as available or unavailable for new order assignments.

    When going available, lat/lng must be provided so they can be added to
    the Redis GEO index immediately — otherwise the driver won't be discovered
    by the assignment worker.

    When going unavailable (e.g. driver going off-shift), they are removed
    from the Redis GEO index immediately.
    """
    if payload.is_available and (payload.lat is None or payload.lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lat and lng are required when setting availability to true.",
        )

    driver.is_available = payload.is_available
    if payload.lat is not None:
        driver.current_lat = payload.lat
    if payload.lng is not None:
        driver.current_lng = payload.lng

    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("DB error updating availability for driver=%s: %s", driver.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update availability. Please try again.",
        )

    if payload.is_available and payload.lat and payload.lng:
        await _add_driver_to_geo(driver.id, payload.lat, payload.lng)
    else:
        await _remove_driver_from_geo(driver.id)


# ---------------------------------------------------------------------------
# Redis GEO helpers
# ---------------------------------------------------------------------------

async def _add_driver_to_geo(driver_id: str, lat: float, lng: float) -> None:
    """Adds or updates a driver's position in the Redis GEO index."""
    try:
        # Redis GEOADD expects (longitude, latitude, member) — note lng first.
        await redis_client.geoadd(_DRIVERS_GEO_KEY, [lng, lat, driver_id])
    except Exception as exc:
        logger.error("Failed to GEOADD driver=%s: %s", driver_id, exc)


async def _remove_driver_from_geo(driver_id: str) -> None:
    """Removes a driver from the Redis GEO index (ZREM on the underlying sorted set)."""
    try:
        await redis_client.zrem(_DRIVERS_GEO_KEY, driver_id)
    except Exception as exc:
        logger.error("Failed to ZREM driver=%s from GEO: %s", driver_id, exc)


async def _publish_status_update(order_id: str, new_status: str) -> None:
    """Publishes an order status change to the tracking WebSocket channel."""
    try:
        await redis_client.publish(
            f"{_TRACKING_CHANNEL_PREFIX}{order_id}",
            json.dumps({
                "type": "status",
                "status": new_status,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }),
        )
    except Exception as exc:
        logger.error(
            "Failed to publish status update for order=%s status=%s: %s",
            order_id, new_status, exc,
        )


async def _publish_stage_update(order_id: str, new_stage: str) -> None:
    """
    Publishes a granular DeliveryStage change (spec 1.8) — a DIFFERENT
    message type ("stage") from the coarse "status" messages above, so
    the Customer App's tracking screen can tell "the order moved from
    preparing to out_for_delivery" (status) apart from "the driver just
    arrived at the branch" (stage) instead of the two being merged into
    one ambiguous field.
    """
    try:
        await redis_client.publish(
            f"{_TRACKING_CHANNEL_PREFIX}{order_id}",
            json.dumps({
                "type": "stage",
                "stage": new_stage,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }),
        )
    except Exception as exc:
        logger.error(
            "Failed to publish stage update for order=%s stage=%s: %s",
            order_id, new_stage, exc,
        )


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _to_driver_order_response(
    order: Order,
    addresses: dict[str, Address],
    distance_km: float | None = None,
) -> DriverOrderResponse:
    address = addresses.get(order.delivery_address_id) if order.delivery_address_id else None
    branch = order.branch  # requires selectinload(Order.branch) on the query — see callers
    return DriverOrderResponse(
        id=order.id,
        checkout_group_id=order.checkout_group_id,
        delivery_group_id=order.delivery_group_id,
        shop_id=order.shop_id,
        shop_name=order.shop.name if order.shop else "Unknown",
        customer_name=order.user.full_name if order.user else None,
        shop_lat=order.shop.lat if order.shop else None,
        shop_lng=order.shop.lng if order.shop else None,
        branch_id=branch.id if branch else None,
        branch_name=branch.name if branch else None,
        branch_lat=branch.lat if branch else None,
        branch_lng=branch.lng if branch else None,
        branch_address=branch.address if branch else None,
        branch_phone=branch.phone if branch else None,
        status=order.status.value,
        delivery_stage=order.delivery_stage.value if order.delivery_stage else None,
        payment_status=order.payment_status.value,
        total=float(order.total),
        delivery_address=address.full_address if address else None,
        delivery_lat=address.lat if address else None,
        delivery_lng=address.lng if address else None,
        eta_minutes=order.eta_minutes,
        live_eta_minutes=order.live_eta_minutes,
        delivery_fee=float(order.delivery_fee) if order.delivery_fee is not None else None,
        road_distance_km=order.road_distance_km,
        distance_km=distance_km,
        items=[
            DriverOrderItemResponse(
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_purchase=float(item.price_at_purchase),
            )
            for item in order.items
        ],
        created_at=order.created_at,
    )

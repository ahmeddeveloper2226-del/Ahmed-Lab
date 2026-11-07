"""
Driver Assignment Worker — standalone async process.

Consumes from the driver.assignment queue (published by order_events_worker
after payment confirmation, ONE message per delivery zone — see
geo_utils.cluster_shops_by_zone) and OFFERS the whole zone's shop-orders to
the single nearest available driver, who then accepts or declines. The
driver never browses a list; the system finds him.

Assignment algorithm, per delivery_group_id:
  1. Load every order in the group and their shops' coordinates from
     Postgres, and compute the group's centroid (arithmetic mean of the
     shop coordinates) — the reference point for "nearest driver to this
     zone", not any single shop and not the delivery address.
  2. Query Redis GEO index (wasla:drivers:available) for up to 5 nearest
     available drivers to the centroid, within settings.delivery_zone_radius_km.
  3. For each candidate, nearest first:
     a. Skip drivers already excluded for this group (declined or timed out
        — tracked in Redis with a short TTL so retries don't re-offer to
        someone who just said no).
     b. Verify the driver is still available/active in Postgres.
     c. Verify EVERY shop in the group is within settings.delivery_zone_radius_km
        of the candidate's current position — the centroid can be close
        while one outlier shop in the group is not.
     d. Verify the existing multi-order clustering rule against the
        driver's OTHER active orders (mirrors driver_router.py's accept
        endpoint) so this offer doesn't stack a driver with pickups on
        opposite sides of the city.
     e. If a candidate passes all checks: atomically set driver_id and
        offer_expires_at (now + settings.driver_offer_timeout_seconds) on
        EVERY order in the group using SELECT FOR UPDATE — status stays
        `pending`, this is an OFFER, not a hard assignment — then push an
        FCM "new delivery offer" notification to that driver.
     f. If a candidate fails any check, try the next-nearest immediately.
  4. If no candidate in this pass succeeds, retry up to MAX_RETRIES times
     with RETRY_DELAY_SECONDS between attempts; after that, log prominently
     for ops. Orders stay pending — no browsing fallback.

A SEPARATE background loop (`_sweep_expired_offers`) runs continuously and
reclaims offers a driver didn't respond to in time: any order still
`pending` with driver_id set and offer_expires_at in the past gets its
driver_id/offer_expires_at cleared for the whole group, that driver is
added to the group's exclusion set, and the group is re-published to
driver.assignment to find the next-nearest driver. This is what makes
"driver accepts" actually mean something instead of a formality — a driver
who doesn't respond loses the offer, exactly like an explicit decline.

Run with:
  python -m app.workers.driver_assignment_worker
"""

import asyncio
import json
import logging
import signal
from datetime import datetime, timedelta, timezone

import aio_pika
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.models.driver import Driver
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.user import User
from app.redis_client import redis_client
from app.services.geo_utils import centroid, haversine_km
from app.services.notification_service import notify_driver_assigned

configure_logging()
logger = logging.getLogger("wasla.worker.driver_assignment")

_shutdown = asyncio.Event()

# How many times to retry finding a driver before giving up on a group.
_MAX_RETRIES = 5

# Seconds between retries — total wait before giving up: 5 x 30 = 150 s.
_RETRY_DELAY_SECONDS = 30.0

# How often the expired-offer sweep checks for timed-out offers.
_SWEEP_INTERVAL_SECONDS = 5.0

_DRIVERS_GEO_KEY = "wasla:drivers:available"
_TRACKING_CHANNEL_PREFIX = "wasla:tracking:"

# Redis key (per delivery_group_id) holding the set of driver_ids who
# already declined or timed out on this group, so the retry loop and the
# sweep don't re-offer to them. TTL just needs to outlive the group's
# assignment lifetime.
_EXCLUSION_KEY_PREFIX = "wasla:offer_excluded:"
_EXCLUSION_TTL_SECONDS = 3600


def _handle_signal(sig) -> None:
    logger.info("Received signal %s — shutting down", sig)
    _shutdown.set()


# ---------------------------------------------------------------------------
# Nearest-driver lookup
# ---------------------------------------------------------------------------

async def _find_nearest_available_drivers(lat: float, lng: float, radius_km: float, count: int = 5) -> list[str]:
    """
    Nearest-first candidates from the Redis GEO index, within radius_km of
    (lat, lng). Returns up to `count` so the caller can skip a candidate
    that fails a check and try the next-nearest immediately instead of
    waiting for the next retry cycle.
    """
    try:
        results = await redis_client.geosearch(
            _DRIVERS_GEO_KEY,
            longitude=lng,   # Redis GEO uses (lng, lat) — note the order
            latitude=lat,
            unit="km",
            radius=radius_km,
            sort="ASC",
            count=count,
        )
        return list(results) if results else []
    except Exception as exc:
        logger.error("Redis GEOSEARCH failed: %s", exc)
        return []


async def _get_excluded_drivers(delivery_group_id: str) -> set[str]:
    try:
        members = await redis_client.smembers(f"{_EXCLUSION_KEY_PREFIX}{delivery_group_id}")
        return set(members) if members else set()
    except Exception as exc:
        logger.error("Failed to read exclusion set for group=%s: %s", delivery_group_id, exc)
        return set()


async def _exclude_driver(delivery_group_id: str, driver_id: str) -> None:
    key = f"{_EXCLUSION_KEY_PREFIX}{delivery_group_id}"
    try:
        await redis_client.sadd(key, driver_id)
        await redis_client.expire(key, _EXCLUSION_TTL_SECONDS)
    except Exception as exc:
        logger.error("Failed to add driver=%s to exclusion set for group=%s: %s", driver_id, delivery_group_id, exc)


# ---------------------------------------------------------------------------
# Offer (not a hard assignment — driver still has to accept)
# ---------------------------------------------------------------------------

async def _offer_group_to_driver(delivery_group_id: str, driver_id: str) -> bool:
    """
    Atomically OFFERS every order in the delivery group to this driver:
    sets driver_id + offer_expires_at on all of them, but leaves status at
    `pending` — the driver still has to call the accept endpoint. Uses
    SELECT FOR UPDATE on both the orders and the driver row so a concurrent
    offer/accept/decline can't race this.

    Returns True if the offer was made, False if any order in the group is
    no longer offerable (already assigned/accepted, cancelled, etc.) or the
    driver failed the clustering/availability checks — caller should try
    the next-nearest candidate in that case.
    """
    async with AsyncSessionLocal() as db:
        try:
            orders_result = await db.execute(
                select(Order)
                .where(Order.delivery_group_id == delivery_group_id)
                .options(selectinload(Order.shop))
                .with_for_update()
            )
            group_orders: list[Order] = list(orders_result.scalars().all())

            if not group_orders:
                logger.info("Group=%s has no orders — skipping", delivery_group_id)
                return False

            if any(o.driver_id is not None or o.status != OrderStatus.pending for o in group_orders):
                logger.info("Group=%s already offered/assigned elsewhere — skipping", delivery_group_id)
                return False

            driver_result = await db.execute(
                select(Driver).where(Driver.id == driver_id).with_for_update()
            )
            driver: Driver | None = driver_result.scalar_one_or_none()

            if driver is None or not driver.is_available or not driver.is_active:
                logger.info("Driver=%s no longer available — will try next nearest", driver_id)
                return False

            if driver.current_lat is None or driver.current_lng is None:
                logger.info("Driver=%s has no known position — skipping", driver_id)
                return False

            # --- Every shop in the group must be within zone radius of driver ---
            for order in group_orders:
                if order.shop is None or order.shop.lat is None or order.shop.lng is None:
                    logger.info("Order=%s's shop has no location — group=%s not offerable", order.id, delivery_group_id)
                    return False
                distance = haversine_km(driver.current_lat, driver.current_lng, order.shop.lat, order.shop.lng)
                if distance > settings.delivery_zone_radius_km:
                    logger.info(
                        "Driver=%s is %.1fkm from shop of order=%s (> %.1fkm zone radius) — skipping",
                        driver_id, distance, order.id, settings.delivery_zone_radius_km,
                    )
                    return False

            # --- Clustering check against driver's OTHER active orders -----------
            # (mirrors driver_router.py's accept_order)
            active_result = await db.execute(
                select(Order)
                .where(
                    Order.driver_id == driver.id,
                    Order.status.in_((OrderStatus.preparing, OrderStatus.out_for_delivery)),
                )
                .options(selectinload(Order.shop))
            )
            active_orders = list(active_result.scalars().all())

            if active_orders:
                if len(active_orders) + len(group_orders) > settings.driver_max_concurrent_orders:
                    logger.info(
                        "Driver=%s would exceed max concurrent orders (%d) with this group — skipping",
                        driver_id, settings.driver_max_concurrent_orders,
                    )
                    return False
                for active in active_orders:
                    if active.shop is None or active.shop.lat is None or active.shop.lng is None:
                        continue
                    for order in group_orders:
                        distance = haversine_km(
                            order.shop.lat, order.shop.lng, active.shop.lat, active.shop.lng
                        )
                        if distance > settings.driver_cluster_distance_km:
                            logger.info(
                                "Driver=%s's existing order shop is %.1fkm from group=%s's shop — skipping",
                                driver_id, distance, delivery_group_id,
                            )
                            return False

            # --- Make the offer ---------------------------------------------------
            expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=settings.driver_offer_timeout_seconds)
            for order in group_orders:
                order.driver_id = driver.id
                order.offer_expires_at = expires_at

            await db.commit()
            return True

        except SQLAlchemyError as exc:
            await db.rollback()
            logger.error("DB error offering group=%s to driver=%s: %s", delivery_group_id, driver_id, exc)
            return False


async def _notify_driver_of_offer(delivery_group_id: str, driver_id: str, customer_uid: str) -> None:
    """Best-effort push notification to the driver about a new delivery offer."""
    try:
        async with AsyncSessionLocal() as db:
            driver_result = await db.execute(select(Driver).where(Driver.id == driver_id))
            driver = driver_result.scalar_one_or_none()
            if driver is None:
                return
            user_result = await db.execute(select(User).where(User.id == driver.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.fcm_token:
                await notify_driver_assigned(user.fcm_token, delivery_group_id, None)
    except Exception as exc:
        logger.error("Failed to notify driver=%s of offer group=%s: %s", driver_id, delivery_group_id, exc)


# ---------------------------------------------------------------------------
# Message handler — attempts to find & offer a driver for one delivery group
# ---------------------------------------------------------------------------

async def _handle_assignment_message(body: dict) -> None:
    delivery_group_id: str = body.get("delivery_group_id", "")
    order_ids: list[str] = body.get("order_ids", [])
    customer_uid: str = body.get("customer_uid", "")

    if not delivery_group_id or not order_ids:
        logger.error("driver.assignment: missing delivery_group_id/order_ids in message: %s", body)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order)
            .where(Order.delivery_group_id == delivery_group_id)
            .options(selectinload(Order.shop))
        )
        group_orders: list[Order] = list(result.scalars().all())

    if not group_orders:
        logger.error("driver.assignment: group=%s not found", delivery_group_id)
        return

    unassignable = [o for o in group_orders if o.status != OrderStatus.pending or o.payment_status != PaymentStatus.paid]
    if unassignable:
        logger.info("driver.assignment: group=%s not in assignable state — skipping", delivery_group_id)
        return

    if any(o.driver_id is not None for o in group_orders):
        logger.info("driver.assignment: group=%s already has a pending offer — skipping", delivery_group_id)
        return

    shop_points = [(o.shop.lat, o.shop.lng) for o in group_orders if o.shop and o.shop.lat is not None and o.shop.lng is not None]
    if len(shop_points) != len(group_orders):
        logger.error(
            "driver.assignment: group=%s has shop(s) with no location — cannot assign. "
            "Orders remain pending.",
            delivery_group_id,
        )
        return

    zone_lat, zone_lng = centroid(shop_points)

    for attempt in range(1, _MAX_RETRIES + 1):
        logger.info(
            "driver.assignment: searching for driver for group=%s (orders=%s) "
            "attempt=%d/%d centroid=(%.4f,%.4f)",
            delivery_group_id, order_ids, attempt, _MAX_RETRIES, zone_lat, zone_lng,
        )

        excluded = await _get_excluded_drivers(delivery_group_id)
        candidate_ids = await _find_nearest_available_drivers(
            zone_lat, zone_lng, settings.delivery_zone_radius_km
        )
        candidate_ids = [c for c in candidate_ids if c not in excluded]

        if not candidate_ids:
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "driver.assignment: no eligible driver within %skm for group=%s — retrying in %ss",
                    settings.delivery_zone_radius_km, delivery_group_id, _RETRY_DELAY_SECONDS,
                )
                await asyncio.sleep(_RETRY_DELAY_SECONDS)
                continue
            logger.error(
                "driver.assignment: EXHAUSTED all %d attempts for group=%s — "
                "no available driver within %skm. Orders remain pending. "
                "MANUAL INTERVENTION REQUIRED.",
                _MAX_RETRIES, delivery_group_id, settings.delivery_zone_radius_km,
            )
            return

        offered_driver_id: str | None = None
        for candidate_id in candidate_ids:
            if await _offer_group_to_driver(delivery_group_id, candidate_id):
                offered_driver_id = candidate_id
                break

        if offered_driver_id:
            logger.info(
                "driver.assignment: OFFERED group=%s -> driver=%s (attempt %d)",
                delivery_group_id, offered_driver_id, attempt,
            )
            await _notify_driver_of_offer(delivery_group_id, offered_driver_id, customer_uid)
            return

        logger.info(
            "driver.assignment: all candidates rejected for group=%s — retrying in %ss",
            delivery_group_id, _RETRY_DELAY_SECONDS,
        )
        if attempt < _MAX_RETRIES:
            await asyncio.sleep(_RETRY_DELAY_SECONDS)
        else:
            logger.error(
                "driver.assignment: EXHAUSTED all %d attempts for group=%s — "
                "MANUAL INTERVENTION REQUIRED.",
                _MAX_RETRIES, delivery_group_id,
            )


# ---------------------------------------------------------------------------
# Expired-offer sweep — reclaims offers the driver didn't respond to in time
# ---------------------------------------------------------------------------

async def _sweep_expired_offers(channel: aio_pika.abc.AbstractChannel) -> None:
    """
    Runs continuously. Finds delivery groups whose offer window passed
    without the driver accepting (order still `pending`, driver_id set,
    offer_expires_at in the past), clears the offer, excludes that driver
    from future offers for this group, and re-publishes the group to
    driver.assignment so the next-nearest driver gets a shot.
    """
    while not _shutdown.is_set():
        try:
            now = datetime.now(tz=timezone.utc)
            groups: dict[str, tuple[str, list[str], str]] = {}
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Order).where(
                        Order.status == OrderStatus.pending,
                        Order.driver_id.is_not(None),
                        Order.offer_expires_at.is_not(None),
                        Order.offer_expires_at < now,
                    )
                )
                expired_orders: list[Order] = list(result.scalars().all())

                for order in expired_orders:
                    if order.delivery_group_id is None:
                        continue
                    driver_id, ids, uid = groups.setdefault(order.delivery_group_id, (order.driver_id, [], order.user_id))
                    ids.append(order.id)
                    groups[order.delivery_group_id] = (driver_id, ids, uid)

                for delivery_group_id in groups:
                    logger.info(
                        "driver.assignment: offer for group=%s EXPIRED — reclaiming", delivery_group_id,
                    )
                    await db.execute(
                        update(Order)
                        .where(Order.delivery_group_id == delivery_group_id)
                        .values(driver_id=None, offer_expires_at=None)
                    )
                await db.commit()

            for delivery_group_id, (driver_id, order_ids, customer_uid) in groups.items():
                await _exclude_driver(delivery_group_id, driver_id)
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
            logger.error("Error in expired-offer sweep: %s", exc, exc_info=True)

        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Consumer and entry point
# ---------------------------------------------------------------------------

async def _consume(channel: aio_pika.abc.AbstractChannel) -> None:
    queue = await channel.declare_queue("driver.assignment", durable=True)

    async def on_message(message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body.decode())
                await _handle_assignment_message(body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in driver.assignment: %r", message.body[:200])
            except Exception as exc:
                logger.error("Unhandled error in assignment handler: %s", exc, exc_info=True)

    await queue.consume(on_message)
    logger.info("Consuming from queue: driver.assignment")


async def main() -> None:
    logger.info("Driver assignment worker starting...")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    connection = await aio_pika.connect_robust(settings.rabbitmq_url, reconnect_interval=5)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)
        await _consume(channel)

        sweep_task = asyncio.create_task(_sweep_expired_offers(channel))

        logger.info("Driver assignment worker ready.")
        await _shutdown.wait()
        sweep_task.cancel()

    logger.info("Driver assignment worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
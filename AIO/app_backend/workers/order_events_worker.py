"""
Order Events Worker — standalone async process.

Consumes from two RabbitMQ queues:
  order.created     — fires when a checkout succeeds and orders are written
                      to the DB, BEFORE payment is confirmed. At this point,
                      no money has moved. We don't notify the shop yet
                      (shop shouldn't start preparing unpaid orders) — we
                      just log for observability.

  payment.confirmed — fires after Paymob's webhook confirms the transaction.
                      This is the real "go" signal. We:
                        1. Notify the customer: "Payment successful ✓"
                        2. Notify each shop: "New order received"
                        3. Cluster this checkout's shop-orders into delivery
                           zones (shops within settings.delivery_zone_radius_km
                           of each other chain into ONE zone — see
                           geo_utils.cluster_shops_by_zone), stamp each Order
                           with its delivery_group_id, and publish ONE
                           driver.assignment message per zone so
                           driver_assignment_worker offers the whole zone's
                           shops to a single nearest driver in one trip.

Message format for both queues (JSON):
  order.created:
    {"checkout_group_id": "...", "order_ids": [...], "uid": "...", "total": 150.0}

  payment.confirmed:
    {"checkout_group_id": "...", "order_ids": [...], "transaction_id": 12345}

Run with:
  python -m app.workers.order_events_worker

The worker reconnects automatically (aio_pika robust connection) and logs
permanently failed messages for ops review rather than crashing.
"""

import asyncio
import json
import logging
import signal

import aio_pika

import uuid

from sqlalchemy import update

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.models.order import Order
from app.models.shop import Shop
from app.models.user import User
from app.services.geo_utils import cluster_shops_by_zone
from app.services.notification_service import (
    notify_new_order_to_shop,
    notify_payment_confirmed,
)

configure_logging()
logger = logging.getLogger("wasla.worker.order_events")

# Graceful shutdown flag — set by SIGTERM/SIGINT handler.
_shutdown = asyncio.Event()


def _handle_signal(sig) -> None:
    logger.info("Received signal %s — initiating graceful shutdown", sig)
    _shutdown.set()


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def _handle_order_created(body: dict) -> None:
    """
    order.created: Orders written to DB but payment not confirmed yet.

    We only log here — don't notify the shop until payment is confirmed.
    Shops starting preparation on unpaid orders is a real operational problem.
    """
    logger.info(
        "order.created received: checkout_group=%s order_count=%d total=%.2f",
        body.get("checkout_group_id"),
        len(body.get("order_ids", [])),
        body.get("total", 0),
    )


async def _handle_payment_confirmed(body: dict) -> None:
    """
    payment.confirmed: Money moved. Send notifications and trigger driver assignment.
    """
    checkout_group_id: str = body.get("checkout_group_id", "")
    order_ids: list[str] = body.get("order_ids", [])
    transaction_id = body.get("transaction_id")

    logger.info(
        "payment.confirmed: checkout_group=%s orders=%s transaction=%s",
        checkout_group_id, order_ids, transaction_id,
    )

    if not order_ids:
        logger.error("payment.confirmed: empty order_ids for checkout_group=%s", checkout_group_id)
        return

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Order)
            .where(Order.id.in_(order_ids))
            .options(selectinload(Order.items))
        )
        orders: list[Order] = list(result.scalars().all())

        if not orders:
            logger.error(
                "payment.confirmed: no orders found for order_ids=%s checkout_group=%s",
                order_ids, checkout_group_id,
            )
            return

        # Load the customer for their FCM token.
        customer_uid = orders[0].user_id
        user_result = await db.execute(select(User).where(User.id == customer_uid))
        user = user_result.scalar_one_or_none()

        # Load all shops to get their notification tokens.
        shop_ids = list({o.shop_id for o in orders})
        shops_result = await db.execute(select(Shop).where(Shop.id.in_(shop_ids)))
        shops: dict[str, Shop] = {s.id: s for s in shops_result.scalars().all()}

    # --- Customer notification -----------------------------------------------
    await notify_payment_confirmed(
        user_fcm_token=user.fcm_token if user else None,
        order_count=len(orders),
    )

    # --- Shop notifications (one per shop in this checkout group) ------------
    for order in orders:
        shop = shops.get(order.shop_id)
        await notify_new_order_to_shop(
            shop_notification_token=shop.notification_token if shop else None,
            order_id=order.id,
            total=float(order.total),
        )

    # --- Cluster into delivery zones, then trigger driver assignment ---------
    # Orders whose shop has no location yet can't be zoned — they're skipped
    # here and stay pending; ops can locate the shop and re-trigger manually.
    zonable = [(o.id, shops[o.shop_id].lat, shops[o.shop_id].lng)
               for o in orders
               if shops.get(o.shop_id) and shops[o.shop_id].lat is not None
               and shops[o.shop_id].lng is not None]
    skipped_ids = {o.id for o in orders} - {order_id for order_id, _, _ in zonable}
    if skipped_ids:
        logger.error(
            "payment.confirmed: shop(s) with no location — orders %s left "
            "unzoned, remain pending. MANUAL INTERVENTION REQUIRED.",
            skipped_ids,
        )

    zones: list[list[str]] = cluster_shops_by_zone(zonable, settings.delivery_zone_radius_km)

    # Stamp each order with the delivery_group_id for its zone, and publish
    # one driver.assignment message per zone (not per order) — so a single
    # nearest driver is offered ALL the shops in that zone, in one trip.
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue("driver.assignment", durable=True)

            for zone_order_ids in zones:
                delivery_group_id = str(uuid.uuid4())

                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Order)
                        .where(Order.id.in_(zone_order_ids))
                        .values(delivery_group_id=delivery_group_id)
                    )
                    await db.commit()

                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps({
                            "delivery_group_id": delivery_group_id,
                            "order_ids": zone_order_ids,
                            "checkout_group_id": checkout_group_id,
                            "customer_uid": customer_uid,
                        }).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key="driver.assignment",
                )
                logger.debug(
                    "Published driver.assignment for delivery_group=%s orders=%s",
                    delivery_group_id, zone_order_ids,
                )
    except Exception as exc:
        logger.error(
            "Failed to publish driver.assignment for checkout_group=%s: %s",
            checkout_group_id, exc,
        )
        # Don't re-raise — customer and shop already notified. Driver assignment
        # failure is handled separately (ops can manually assign or re-trigger).


# ---------------------------------------------------------------------------
# Consumer setup
# ---------------------------------------------------------------------------

async def _consume_queue(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    handler,
) -> None:
    queue = await channel.declare_queue(queue_name, durable=True)

    async def on_message(message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body.decode())
                await handler(body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in %s: %r", queue_name, message.body[:200])
            except Exception as exc:
                # Log and DO NOT requeue — a bad message that keeps failing
                # would loop forever. In production, configure a Dead Letter
                # Exchange (DLX) in RabbitMQ to catch these for ops review.
                logger.error(
                    "Unhandled error processing %s message: %s", queue_name, exc,
                    exc_info=True,
                )

    await queue.consume(on_message)
    logger.info("Consuming from queue: %s", queue_name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("Order events worker starting...")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    connection = await aio_pika.connect_robust(
        settings.rabbitmq_url,
        reconnect_interval=5,
    )

    async with connection:
        channel = await connection.channel()
        # Limit to 10 unacknowledged messages at once — prevents the worker
        # from being overwhelmed on a backlog and ensures fair distribution
        # if multiple worker instances are running.
        await channel.set_qos(prefetch_count=10)

        await _consume_queue(channel, "order.created", _handle_order_created)
        await _consume_queue(channel, "payment.confirmed", _handle_payment_confirmed)

        logger.info("Order events worker ready.")
        await _shutdown.wait()

    logger.info("Order events worker shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
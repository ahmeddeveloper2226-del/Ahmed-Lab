"""
WebSocket endpoint: GET /tracking/{order_id}

Streams real-time driver location and order status updates to the customer
while their order is in transit. Messages arrive via Redis pub/sub — the
driver publishes from driver_router.py, this handler forwards to the client.

Authentication:
  Standard WebSocket clients (including Flutter's WebSocket library) cannot
  set custom HTTP headers, so we can't use the Authorization: Bearer scheme
  used by REST endpoints. Instead, the Firebase JWT is passed as a query
  parameter: /tracking/{order_id}?token=<firebase_jwt>

  The connection is accepted first (required by the WebSocket protocol before
  we can close with a meaningful code), then auth and ownership are verified.
  If either fails, we close with a 4xxx code the Flutter client can interpret:
    4001 — authentication failure (invalid/expired token)
    4003 — authorization failure (order doesn't belong to this user)
    4004 — order not found

Redis pub/sub:
  Channel name: wasla:tracking:{order_id}
  Message format (JSON):
    Location update: {"type": "location", "lat": 30.05, "lng": 31.23,
                      "bearing": 180.0, "speed_kmh": 25.0,
                      "eta_minutes": 12, "ts": "ISO8601"}
    Status update:   {"type": "status", "status": "out_for_delivery",
                      "ts": "ISO8601"}
    Stage update:    {"type": "stage", "stage": "arrived_at_branch",
                      "ts": "ISO8601"} — granular AIO delivery lifecycle
                      (spec 1.8), published by driver_router.py's
                      delivery-stage/failure endpoints; a parallel, more
                      detailed signal alongside "status" above, not a
                      replacement for it.
    Ping (keepalive):{"type": "ping"}

Lifecycle:
  1. Client connects with ?token=...
  2. Token verified, order fetched, ownership confirmed.
  3. Current order status is sent immediately as a "status" message.
  4. Redis subscription opens; location/status messages forwarded as they arrive.
  5. A ping frame is sent every 25 s so routers/proxies don't time out idle connections.
  6. On WebSocket disconnect (normal or abnormal), Redis subscription is closed cleanly.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal
from ..models.order import Order, OrderStatus, PaymentStatus
from ..redis_client import redis_client

router = APIRouter()
logger = logging.getLogger("wasla.tracking")

# Redis channel prefix — must match what driver_router.py publishes to.
_TRACKING_CHANNEL_PREFIX = "wasla:tracking:"

# How often to send a keepalive ping to prevent proxy/NAT timeouts.
_PING_INTERVAL_SECONDS = 25

# WebSocket close codes (4000–4999 are reserved for application use).
_WS_CLOSE_AUTH_FAILED = 4001
_WS_CLOSE_FORBIDDEN = 4003
_WS_CLOSE_NOT_FOUND = 4004


async def _verify_ws_token(token: str | None) -> str | None:
    """
    Verifies a Firebase JWT and returns the uid, or None if invalid.
    Done synchronously (firebase_admin uses the requests library internally)
    so wrapped in asyncio.to_thread to avoid blocking the event loop.
    """
    if not token:
        return None
    try:
        from firebase_admin import auth as firebase_auth
        decoded = await asyncio.to_thread(
            firebase_auth.verify_id_token, token, check_revoked=True
        )
        return decoded["uid"]
    except Exception:
        return None


@router.websocket("/tracking/{order_id}")
async def tracking_websocket(
    websocket: WebSocket,
    order_id: str,
    token: str | None = Query(None, description="Firebase ID token"),
):
    """
    Streams driver location and order status updates to the customer.

    The WebSocket must be accepted before we can send a meaningful close code,
    so accept() is always called first. Auth and ownership checks happen
    immediately after, before any real data is sent.
    """
    await websocket.accept()

    # --- Auth ----------------------------------------------------------------
    uid = await _verify_ws_token(token)
    if uid is None:
        logger.warning("Tracking WS: auth failed for order=%s", order_id)
        await websocket.close(code=_WS_CLOSE_AUTH_FAILED, reason="Authentication failed.")
        return

    # --- Ownership check -----------------------------------------------------
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order: Order | None = result.scalar_one_or_none()

    if order is None:
        logger.warning("Tracking WS: order=%s not found uid=%s", order_id, uid)
        await websocket.close(code=_WS_CLOSE_NOT_FOUND, reason="Order not found.")
        return

    if order.user_id != uid:
        # Return a not-found close reason — same as REST convention: never
        # confirm an order exists to someone who doesn't own it.
        logger.warning(
            "Tracking WS: ownership check failed order=%s uid=%s owner=%s",
            order_id, uid, order.user_id,
        )
        await websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="Order not found.")
        return

    # --- Send current state immediately --------------------------------------
    # The client opens the tracking screen and needs to know the current state
    # right away — not just when the next pub/sub message arrives.
    await websocket.send_text(json.dumps({
        "type": "status",
        "status": order.status.value,
        "ts": datetime.now(tz=timezone.utc).isoformat(),
    }))

    # Granular AIO delivery stage (spec 1.8), if this order has one — a
    # SEPARATE message from "status" above (see driver_router.py's
    # _publish_stage_update docstring for why they're kept distinct).
    # Also includes the checkout-time/live ETA snapshot (spec 1.9) so the
    # tracking screen has a number to show before the first driver GPS
    # ping arrives.
    if order.delivery_stage is not None:
        await websocket.send_text(json.dumps({
            "type": "stage",
            "stage": order.delivery_stage.value,
            "eta_minutes": order.live_eta_minutes or order.eta_minutes,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }))

    if order.status == OrderStatus.delivered or order.status == OrderStatus.cancelled:
        # Order is already terminal — nothing to track.
        await websocket.close(code=1000, reason="Order already completed.")
        return

    logger.info("Tracking WS: uid=%s connected to order=%s", uid, order_id)

    # --- Subscribe to Redis pub/sub ------------------------------------------
    channel = f"{_TRACKING_CHANNEL_PREFIX}{order_id}"
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(channel)
        await _stream_until_disconnect(websocket, pubsub, order_id)
    except Exception as exc:
        logger.error("Tracking WS: error for order=%s uid=%s: %s", order_id, uid, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
        logger.info("Tracking WS: uid=%s disconnected from order=%s", uid, order_id)


async def _stream_until_disconnect(websocket: WebSocket, pubsub, order_id: str) -> None:
    """
    Core streaming loop: polls Redis for messages and forwards them to the
    WebSocket, sending pings in between to keep the connection alive.

    Exits cleanly on WebSocketDisconnect or when the connection is closed.
    """
    while True:
        try:
            # Poll Redis with a timeout so we can send periodic pings even
            # when there are no driver location updates coming.
            message = await asyncio.wait_for(
                pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1),
                timeout=_PING_INTERVAL_SECONDS,
            )
        except asyncio.TimeoutError:
            # No messages in _PING_INTERVAL_SECONDS — send a keepalive ping.
            try:
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                }))
            except WebSocketDisconnect:
                return
            continue

        if message is None:
            continue

        if message.get("type") == "message":
            try:
                await websocket.send_text(message["data"])
            except WebSocketDisconnect:
                return

            # If this message signals delivery/cancellation, close cleanly.
            # Checked for BOTH message types: a coarse "status" update (the
            # original behavior) and a granular "stage" update reaching
            # delivered/cancelled (spec 1.8) — either can be the one that
            # actually lands last, depending on which endpoint the driver
            # app called.
            try:
                payload = json.loads(message["data"])
                terminal_values = ("delivered", "cancelled")
                is_terminal_status = payload.get("type") == "status" and payload.get("status") in terminal_values
                is_terminal_stage = payload.get("type") == "stage" and payload.get("stage") in terminal_values
                if is_terminal_status or is_terminal_stage:
                    await websocket.close(code=1000, reason="Order completed.")
                    return
            except (json.JSONDecodeError, KeyError):
                pass
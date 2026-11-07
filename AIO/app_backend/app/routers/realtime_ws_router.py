"""
WebSocket endpoint: /realtime/{order_id}?token=<firebase_jwt>

One connection per participant per order, multiplexing everything that
needs to be truly real-time for the chat/call feature:
  - Text message send/receive
  - Typing indicator
  - Online/offline presence
  - Delivered/read receipts
  - WebRTC call signaling (offer/answer/ICE candidates/hangup/reject/busy/timeout)

Voice message UPLOAD is a plain REST call (chat_router.py) since it's a
file upload, not naturally a WS message — but once uploaded, the client
sends a small {"type": "voice_message", "message_id": ...} notice over
this socket so the other side gets a real-time nudge if they're connected.

Why one socket instead of separate chat/call endpoints: an order has
exactly two participants, and multiplexing keeps client connection
management simple (one socket per order screen), consistent with how the
existing tracking_ws_router.py already does one-socket-per-concern.

Authentication: same pattern as tracking_ws_router.py — accept() first
(required before we can send a meaningful close code), then verify the
token from the query string (WebSocket clients can't set custom headers),
then verify the caller is actually a participant (customer or assigned
driver) of this specific order. Every one of these checks exists because
of the security requirement that only order participants can access chat,
calls, or location — never just "any authenticated user."

Redis pub/sub relay: channel wasla:chat:{order_id}, shared by both
participants' connections (which may be on different backend worker
processes). Every message this handler publishes includes "from": <uid>,
and each connection's forwarding loop skips re-delivering a message back
to its own sender (otherwise a client would see its own messages echoed).

Presence: tracked via a short-TTL Redis key (wasla:presence:{uid}),
refreshed on every inbound message and periodic ping. TTL expiry acts as a
safety net for ungraceful disconnects (app killed, network drop) where a
clean "offline" event never gets a chance to fire.

Call "busy" state: tracked via wasla:incall:{uid}, set when a call is
answered and cleared on hangup/reject/timeout — this is a pragmatic
approach for the busy-state requirement, not a full call state machine;
TTL expiry is the safety net for calls that end without a clean signal.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ..database import AsyncSessionLocal
from ..models.chat_message import ChatMessage, MessageStatus, MessageType
from ..redis_client import redis_client
from ..services.chat_service import verify_participant

router = APIRouter()
logger = logging.getLogger("wasla.realtime")

_CHAT_CHANNEL_PREFIX = "wasla:chat:"
_PRESENCE_KEY_PREFIX = "wasla:presence:"
_INCALL_KEY_PREFIX = "wasla:incall:"

_PRESENCE_TTL_SECONDS = 40
_INCALL_TTL_SECONDS = 4 * 60 * 60  # safety-net expiry for calls that never get a clean hangup
_PING_INTERVAL_SECONDS = 25

_WS_CLOSE_AUTH_FAILED = 4001
_WS_CLOSE_FORBIDDEN = 4003
_WS_CLOSE_NOT_FOUND = 4004

# Signaling message types relayed verbatim (plus a "from" field) to the
# other participant — never persisted, purely ephemeral.
_SIGNALING_TYPES = {"offer", "answer", "ice_candidate", "hangup", "reject", "busy", "call_timeout"}


async def _verify_ws_token(token: str | None) -> str | None:
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


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@router.websocket("/realtime/{order_id}")
async def realtime_websocket(
    websocket: WebSocket,
    order_id: str,
    token: str | None = Query(None, description="Firebase ID token"),
):
    await websocket.accept()

    uid = await _verify_ws_token(token)
    if uid is None:
        logger.warning("Realtime WS: auth failed for order=%s", order_id)
        await websocket.close(code=_WS_CLOSE_AUTH_FAILED, reason="Authentication failed.")
        return

    async with AsyncSessionLocal() as db:
        access = await verify_participant(db, order_id, uid)

    if access is None:
        logger.warning("Realtime WS: participant check failed order=%s uid=%s", order_id, uid)
        # Same convention as REST: never confirm the order/chat exists to a
        # non-participant — could mean "not found", "no driver assigned
        # yet", or "you're not one of the two people on this order."
        await websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="Chat not found.")
        return

    order, other_uid = access
    channel = f"{_CHAT_CHANNEL_PREFIX}{order_id}"
    presence_key = f"{_PRESENCE_KEY_PREFIX}{uid}"

    logger.info("Realtime WS: uid=%s connected to order=%s", uid, order_id)

    # --- Mark online + notify the other participant --------------------------
    try:
        await redis_client.set(presence_key, "1", ex=_PRESENCE_TTL_SECONDS)
        await redis_client.publish(channel, json.dumps({
            "type": "presence", "from": uid, "online": True, "ts": _now_iso(),
        }))
    except Exception as exc:
        logger.error("Realtime WS: presence set failed uid=%s: %s", uid, exc)

    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe(channel)
        await _run_connection(websocket, pubsub, uid, other_uid, order_id, channel, presence_key)
    except Exception as exc:
        logger.error("Realtime WS: error for order=%s uid=%s: %s", order_id, uid, exc)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
        try:
            await redis_client.delete(presence_key)
            await redis_client.publish(channel, json.dumps({
                "type": "presence", "from": uid, "online": False, "ts": _now_iso(),
            }))
        except Exception:
            pass
        logger.info("Realtime WS: uid=%s disconnected from order=%s", uid, order_id)


async def _run_connection(
    websocket: WebSocket,
    pubsub,
    uid: str,
    other_uid: str,
    order_id: str,
    channel: str,
    presence_key: str,
) -> None:
    """
    Runs the two concurrent halves of this connection's life:
      - _receive_loop: reads client -> server messages, handles them.
      - _forward_loop: reads Redis pub/sub -> forwards to this client.
    Whichever finishes first (typically a disconnect) cancels the other.
    """
    receive_task = asyncio.create_task(_receive_loop(websocket, uid, other_uid, order_id, channel, presence_key))
    forward_task = asyncio.create_task(_forward_loop(websocket, pubsub, uid))

    done, pending = await asyncio.wait(
        {receive_task, forward_task}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


async def _forward_loop(websocket: WebSocket, pubsub, uid: str) -> None:
    """Forwards Redis pub/sub messages to this client, skipping echoes of
    this same uid's own messages (both participants share one channel)."""
    while True:
        try:
            message = await asyncio.wait_for(
                pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1),
                timeout=_PING_INTERVAL_SECONDS,
            )
        except asyncio.TimeoutError:
            try:
                await websocket.send_text(json.dumps({"type": "ping", "ts": _now_iso()}))
            except WebSocketDisconnect:
                return
            continue

        if message is None or message.get("type") != "message":
            continue

        try:
            payload = json.loads(message["data"])
        except json.JSONDecodeError:
            continue

        if payload.get("from") == uid:
            # Don't echo a participant's own message/event back to themselves.
            continue

        try:
            await websocket.send_text(json.dumps(payload))
        except WebSocketDisconnect:
            return


async def _receive_loop(
    websocket: WebSocket,
    uid: str,
    other_uid: str,
    order_id: str,
    channel: str,
    presence_key: str,
) -> None:
    while True:
        raw = await websocket.receive_text()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = payload.get("type")

        # Any inbound activity refreshes this participant's presence TTL —
        # cheaper than a separate heartbeat message type, and correct since
        # an actively-chatting client is trivially "online."
        try:
            await redis_client.set(presence_key, "1", ex=_PRESENCE_TTL_SECONDS)
        except Exception:
            pass

        if msg_type == "ping":
            try:
                await websocket.send_text(json.dumps({"type": "pong", "ts": _now_iso()}))
            except WebSocketDisconnect:
                return
            continue

        if msg_type == "message":
            await _handle_text_message(payload, uid, other_uid, order_id, channel)
            continue

        if msg_type == "typing":
            await _publish(channel, {
                "type": "typing",
                "from": uid,
                "is_typing": bool(payload.get("is_typing", False)),
                "ts": _now_iso(),
            })
            continue

        if msg_type == "read":
            await _handle_read_receipt(payload, uid, order_id, channel)
            continue

        if msg_type == "voice_message":
            # Client already uploaded via REST (chat_router.py); this is
            # just a real-time nudge that a new one exists.
            message_id = payload.get("message_id")
            if message_id:
                await _publish(channel, {
                    "type": "voice_message", "from": uid, "message_id": message_id, "ts": _now_iso(),
                })
            continue

        if msg_type in _SIGNALING_TYPES:
            await _handle_signaling(msg_type, payload, uid, other_uid, channel)
            continue

        logger.warning("Realtime WS: unknown message type=%r from uid=%s order=%s", msg_type, uid, order_id)


async def _publish(channel: str, payload: dict) -> None:
    try:
        await redis_client.publish(channel, json.dumps(payload))
    except Exception as exc:
        logger.error("Realtime WS: publish failed on channel=%s: %s", channel, exc)


async def _handle_text_message(payload: dict, uid: str, other_uid: str, order_id: str, channel: str) -> None:
    content = payload.get("content")
    if not content or not isinstance(content, str):
        return

    # A connected receiver means this can be marked "delivered" immediately
    # rather than just "sent" — same convention WhatsApp-style apps use.
    receiver_online = False
    try:
        receiver_online = bool(await redis_client.exists(f"{_PRESENCE_KEY_PREFIX}{other_uid}"))
    except Exception:
        pass

    message_id = str(uuid.uuid4())
    initial_status = MessageStatus.delivered if receiver_online else MessageStatus.sent

    async with AsyncSessionLocal() as db:
        try:
            message = ChatMessage(
                id=message_id,
                order_id=order_id,
                sender_id=uid,
                receiver_id=other_uid,
                message_type=MessageType.text,
                status=initial_status,
                content=content,
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)
        except Exception as exc:
            await db.rollback()
            logger.error("Realtime WS: failed to persist message order=%s uid=%s: %s", order_id, uid, exc)
            return

    await _publish(channel, {
        "type": "message",
        "from": uid,
        "id": message.id,
        "order_id": order_id,
        "content": content,
        "status": message.status.value,
        "created_at": message.created_at.isoformat(),
    })


async def _handle_read_receipt(payload: dict, uid: str, order_id: str, channel: str) -> None:
    message_ids = payload.get("message_ids")
    if not message_ids or not isinstance(message_ids, list):
        return

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(ChatMessage).where(
                    ChatMessage.id.in_(message_ids),
                    ChatMessage.order_id == order_id,
                    # Only the RECEIVER of a message can mark it read — a
                    # sender claiming their own message as "read" would be
                    # meaningless and could be used to spoof receipts.
                    ChatMessage.receiver_id == uid,
                )
            )
            messages = list(result.scalars().all())
            for m in messages:
                m.status = MessageStatus.read
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Realtime WS: failed to mark read order=%s uid=%s: %s", order_id, uid, exc)
            return

    if messages:
        await _publish(channel, {
            "type": "read_receipt",
            "from": uid,
            "message_ids": [m.id for m in messages],
            "ts": _now_iso(),
        })


async def _handle_signaling(msg_type: str, payload: dict, uid: str, other_uid: str, channel: str) -> None:
    """
    Relays WebRTC signaling verbatim to the other participant, with basic
    busy-state handling for "offer" — see module docstring for the
    limits of this approach.
    """
    caller_key = f"{_INCALL_KEY_PREFIX}{uid}"
    callee_key = f"{_INCALL_KEY_PREFIX}{other_uid}"

    if msg_type == "offer":
        try:
            callee_busy = bool(await redis_client.exists(callee_key))
        except Exception:
            callee_busy = False

        if callee_busy:
            # Don't relay the offer at all — tell the CALLER it's busy.
            await _publish(channel, {"type": "busy", "from": other_uid, "to": uid, "ts": _now_iso()})
            return

    if msg_type == "answer":
        # Call is now active — mark both participants "in call" so a THIRD
        # party calling either of them gets busy instead of ringing through.
        try:
            await redis_client.set(caller_key, "1", ex=_INCALL_TTL_SECONDS)
            await redis_client.set(callee_key, "1", ex=_INCALL_TTL_SECONDS)
        except Exception:
            pass

    if msg_type in ("hangup", "reject", "call_timeout"):
        try:
            await redis_client.delete(caller_key)
            await redis_client.delete(callee_key)
        except Exception:
            pass

    relay = dict(payload)
    relay["from"] = uid
    relay.setdefault("ts", _now_iso())
    await _publish(channel, relay)
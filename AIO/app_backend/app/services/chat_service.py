"""
Shared helpers for the chat/call/live-location realtime system — used by
chat_router.py (REST: history, voice upload, media serving),
realtime_ws_router.py (WS: messages, typing, presence, WebRTC signaling),
and driver_router.py (to insert the "driver accepted" system message).

Storage note: voice messages are stored on local disk under
settings.media_storage_path, served ONLY through the authenticated
GET /chat/media/{message_id} endpoint — never as a public static file
mount. This means every single fetch re-checks that the requester is an
actual participant in that message's order, not just the initial upload.
For real production scale this should move to S3/Cloud Storage with
short-lived signed URLs, but that requires cloud storage credentials this
project doesn't have configured yet; local disk + authenticated serving is
the self-contained equivalent that still satisfies "only participants can
access" without introducing new infra dependencies.
"""

import os
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.driver import Driver
from ..models.order import Order

# Audio formats accepted for voice messages — matches what
# flutter_sound / record (the common Flutter recording packages) produce.
ALLOWED_AUDIO_EXTENSIONS = {".m4a", ".aac", ".mp3", ".wav", ".ogg"}

_MEDIA_ROOT = Path(settings.media_storage_path) / "voice_messages"


def ensure_media_root() -> None:
    _MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def audio_storage_path(message_id: str, extension: str) -> Path:
    return _MEDIA_ROOT / f"{message_id}{extension}"


async def get_order_participants(db: AsyncSession, order_id: str) -> tuple[Order, str, str | None] | None:
    """
    Returns (order, customer_uid, driver_uid_or_none) for the given order,
    or None if the order doesn't exist. driver_uid is None until a driver
    has accepted the order — the chat/call/location features aren't
    meaningful before that point since there's only one participant.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        return None

    driver_uid: str | None = None
    if order.driver_id:
        driver_result = await db.execute(select(Driver).where(Driver.id == order.driver_id))
        driver = driver_result.scalar_one_or_none()
        if driver:
            driver_uid = driver.user_id

    return order, order.user_id, driver_uid


async def verify_participant(db: AsyncSession, order_id: str, uid: str) -> tuple[Order, str] | None:
    """
    Verifies `uid` is a participant (customer or assigned driver) of this
    order. Returns (order, other_participant_uid) on success — the "other
    participant" being exactly who chat messages/calls/location updates
    should be relayed to — or None if the order doesn't exist, has no
    driver assigned yet, or `uid` isn't one of the two participants.

    This is the single choke point every chat/call/location entry point
    (REST and WS) goes through — per the security requirement that only
    participants of an order can access any of these features.
    """
    participants = await get_order_participants(db, order_id)
    if participants is None:
        return None

    order, customer_uid, driver_uid = participants

    if driver_uid is None:
        # No driver assigned yet — nothing to chat/call about, and no
        # second participant to relay to.
        return None

    if uid == customer_uid:
        return order, driver_uid
    if uid == driver_uid:
        return order, customer_uid

    return None
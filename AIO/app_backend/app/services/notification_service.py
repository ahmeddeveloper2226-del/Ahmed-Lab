"""
Firebase Cloud Messaging push notification service.

Design principles:
  - Every public function is async and never raises. A failed push notification
    must NEVER crash the caller's business logic. If the user's device doesn't
    receive a push, the UI can still poll or the user can pull-to-refresh —
    that's a degraded but fully functional state. Raising an exception here
    would be trading a cosmetic failure (missed push) for a total failure
    (failed request, failed RabbitMQ message ack, etc.).

  - firebase_admin.messaging.send() is synchronous (it uses the requests lib
    internally). We wrap it in asyncio.to_thread() so it never blocks the
    event loop. This is important: a slow FCM response would otherwise stall
    every other coroutine sharing that event loop.

  - FCM token management: tokens expire, rotate on reinstall, and can become
    invalid. When firebase_admin raises UnregisteredError, we log the stale
    token. Proactive cleanup (deleting the token from the DB) is NOT done here
    to keep this service stateless — a separate maintenance job should do that.

  - Firebase initialization: the Firebase app is initialized in dependencies.py
    when the FastAPI server starts, and re-checked here so this service also
    works correctly inside standalone worker processes that don't import the
    FastAPI app.
"""

import asyncio
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from ..config import settings

logger = logging.getLogger("wasla.notifications")


def _ensure_firebase_initialized() -> None:
    """
    Idempotent Firebase initialization guard.

    dependencies.py initializes Firebase at import time when the FastAPI server
    starts. Workers that don't import the FastAPI app call this before any
    messaging function to ensure the SDK is ready.

    firebase_admin._apps is the SDK's internal dict of initialized apps;
    checking it avoids the "default app already exists" error on double-init.
    """
    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            credentials.Certificate(settings.firebase_credentials_path)
        )


async def send_push(
    token: str | None,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> None:
    """
    Sends a single FCM push notification to the given device token.

    If token is None or empty, skips silently — this is the normal case for
    users who haven't granted push permission or whose token isn't set yet.

    data values must be strings (FCM requirement). The caller is responsible
    for converting non-string values before passing them here.

    Never raises — all errors are logged and swallowed.
    """
    if not token:
        return

    _ensure_firebase_initialized()

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
                channel_id="wasla_orders",
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1),
            ),
        ),
    )

    try:
        # messaging.send() is blocking — run it in a thread pool so it doesn't
        # stall the event loop during the HTTP round-trip to FCM servers.
        message_id = await asyncio.to_thread(messaging.send, message)
        logger.debug("FCM push sent: message_id=%s title=%r", message_id, title)
    except messaging.UnregisteredError:
        # Token is no longer valid (app uninstalled, user signed out, etc.).
        # Log for token cleanup job — don't raise.
        logger.warning("FCM token unregistered — token should be cleared: %.20s...", token)
    except messaging.SenderIdMismatchError:
        # Token belongs to a different Firebase project — config error.
        logger.error("FCM sender ID mismatch — check FIREBASE_CREDENTIALS_PATH config")
    except Exception as exc:
        logger.error("FCM push failed: title=%r error=%s", title, exc)


# ---------------------------------------------------------------------------
# Domain-specific notification helpers
# ---------------------------------------------------------------------------
# These functions centralize the copy and routing logic for every
# notification the app sends, so changing wording or adding new platforms
# is always a one-file change.

async def notify_payment_confirmed(user_fcm_token: str | None, order_count: int) -> None:
    """Customer: payment succeeded, order(s) confirmed."""
    body = (
        f"Your {order_count} order{'s' if order_count > 1 else ''} "
        f"{'are' if order_count > 1 else 'is'} confirmed and being prepared."
    )
    await send_push(
        token=user_fcm_token,
        title="Payment confirmed ✓",
        body=body,
        data={"type": "payment_confirmed"},
    )


async def notify_new_order_to_shop(
    shop_notification_token: str | None,
    order_id: str,
    total: float,
) -> None:
    """Shop: a new paid order arrived — needs preparation."""
    await send_push(
        token=shop_notification_token,
        title="New order received 🛍️",
        body=f"Order #{order_id[:8]} — EGP {total:.2f}. Tap to view.",
        data={"type": "new_order", "order_id": order_id},
    )


async def notify_driver_assigned(
    user_fcm_token: str | None,
    order_id: str,
    driver_name: str | None,
) -> None:
    """Customer: a driver has accepted their order."""
    name = driver_name or "A driver"
    await send_push(
        token=user_fcm_token,
        title="Driver assigned 🛵",
        body=f"{name} is picking up your order.",
        data={"type": "driver_assigned", "order_id": order_id},
    )


async def notify_order_status_changed(
    user_fcm_token: str | None,
    order_id: str,
    new_status: str,
) -> None:
    """Customer: order moved to a new status (preparing, out_for_delivery, delivered)."""
    copy: dict[str, tuple[str, str]] = {
        "preparing": ("Your order is being prepared 👨‍🍳", "The shop has started on your order."),
        "out_for_delivery": ("Driver is on the way 🛵", "Your order has been picked up and is heading to you."),
        "delivered": ("Order delivered! 🎉", "Enjoy your order. Tap to rate your experience."),
        "cancelled": ("Order cancelled", "Your order has been cancelled. Contact support if this was unexpected."),
    }
    title, body = copy.get(new_status, ("Order update", f"Your order status: {new_status}"))
    await send_push(
        token=user_fcm_token,
        title=title,
        body=body,
        data={"type": "order_status", "order_id": order_id, "status": new_status},
    )


async def notify_refill_reminder(
    user_fcm_token: str | None,
    medication_id: str,
    medicine_name: str,
    days_left: int,
    added_to_cart: bool,
) -> None:
    """Customer: a tracked chronic-condition medication (Refill Reminder,
    see services/medication_service.py) is about to run out. When
    added_to_cart is True, the worker has already put the refill in the
    customer's cart (see auto_add_to_cart_for_reminder) — the push copy
    reflects that so the customer knows all that's left is to confirm the
    order, not to go find and add the item themselves."""
    urgency = (
        f"من المفترض إن {medicine_name} خلص."
        if days_left <= 0
        else f"{medicine_name} هيخلص خلال {days_left} يوم تقريبًا."
    )
    if added_to_cart:
        body = f"{urgency} ضفناه في سلتك — يلا أكّد الطلب."
    else:
        body = f"{urgency} الدواء مش متوفر حاليًا، دور عليه يدويًا لما يرجع متاح."
    await send_push(
        token=user_fcm_token,
        title="حان وقت إعادة الصرف 💊",
        body=body,
        data={"type": "refill_reminder", "medication_id": medication_id, "added_to_cart": str(added_to_cart)},
    )
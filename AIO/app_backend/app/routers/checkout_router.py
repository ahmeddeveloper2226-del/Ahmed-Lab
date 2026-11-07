"""
POST /checkout — converts a confirmed cart into orders and initiates payment.

Sequence:
  1. Validate billing_data fields (Paymob rejects incomplete billing early,
     so we catch it here with a useful error instead of a cryptic 500 from
     Paymob).
  2. create_orders_from_cart() — atomically creates Order rows, decrements
     stock, clears the cart (order_service handles the DB transaction).
  3. create_payment_url() — runs the Paymob 4-step flow and returns an
     iframe URL for Flutter to open.
  4. Publish order.created to RabbitMQ for downstream services.

Edge case — Paymob fails AFTER orders are committed:
  We intentionally do NOT roll back the orders. Stock was already
  decremented; rolling it back would re-open a race condition. The order
  exists in a payable state. The response includes the checkout_group_id
  as a support reference so the customer can contact us and we can
  manually re-trigger payment. This is safer than silently losing the order.
"""

import json
import logging

import aio_pika
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..rabbitmq_client import get_rabbitmq_channel
from ..schemas.order_schemas import CheckoutRequest, CheckoutResponse
from ..services.order_service import (
    EmptyCartError,
    InsufficientStockError,
    create_orders_from_cart,
)
from ..services.paymob_service import PaymobError, create_payment_url

router = APIRouter()
logger = logging.getLogger("wasla.checkout")

# Paymob validates these fields server-side and returns an opaque error when
# any are missing. Validating here gives the Flutter client a clear message.
_REQUIRED_BILLING_FIELDS: frozenset[str] = frozenset({
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "city",
    "country",
    "street",
    "building",
    "floor",
    "apartment",
})


@router.post("", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    # --- Billing data pre-flight ----------------------------------------
    missing = _REQUIRED_BILLING_FIELDS - set(payload.billing_data.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required billing fields: {sorted(missing)}",
        )

    # --- Step 1: create orders and decrement stock atomically -----------
    try:
        result = await create_orders_from_cart(db, uid, payload.address_id, payload.branch_selections)

    except EmptyCartError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty.",
        )

    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Some items are out of stock. Please update your cart and try again.",
                "shortages": exc.shortages,
            },
        )

    except SQLAlchemyError:
        # A transient DB problem (connection blip, momentary contention on
        # the FOR UPDATE lock) is not the same failure as a genuine bug —
        # 503 tells the client "retry", not "something is broken".
        logger.error("Database error during order creation for uid=%s", uid, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create your order right now. Please try again.",
        )

    except Exception:
        logger.exception("Unexpected error during order creation for uid=%s", uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create your order. Please try again.",
        )

    # Paymob works in piastres (smallest EGP unit). 1 EGP = 100 piastres.
    amount_cents = int(round(result.total * 100))

    # --- Step 2: initiate payment ----------------------------------------
    try:
        payment_url = await create_payment_url(
            checkout_group_id=result.checkout_group_id,
            amount_cents=amount_cents,
            billing_data=payload.billing_data,
        )

    except PaymobError:
        # Orders exist and stock is committed. Surface the group ID so the
        # customer can reach support. We log as error for alerting.
        logger.error(
            "Paymob initiation failed after order creation — "
            "checkout_group=%s uid=%s amount_cents=%s",
            result.checkout_group_id,
            uid,
            amount_cents,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Payment provider is temporarily unavailable. "
                "Your order was saved — please contact support with reference: "
                f"{result.checkout_group_id}"
            ),
        )

    # --- Step 3: publish order.created (non-fatal) -----------------------
    # Downstream services (push notifications, kitchen display, analytics)
    # subscribe to this event. If publishing fails, the checkout still
    # succeeded — the payment URL is ready and the order is in the DB.
    try:
        channel = get_rabbitmq_channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({
                    "checkout_group_id": result.checkout_group_id,
                    "order_ids": [o.id for o in result.orders],
                    "uid": uid,
                    "total": result.total,
                }).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="order.created",
        )
    except Exception:
        logger.error(
            "Failed to publish order.created for checkout_group=%s — "
            "checkout succeeded, continuing",
            result.checkout_group_id,
        )

    return CheckoutResponse(
        checkout_group_id=result.checkout_group_id,
        payment_url=payment_url,
        total=result.total,
    )
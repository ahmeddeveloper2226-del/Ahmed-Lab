"""
POST /webhooks/paymob — receives Paymob transaction-processed callbacks.

Security:
  Paymob includes a HMAC-SHA512 signature as the `hmac` query parameter.
  We verify it BEFORE reading any payload content or touching the database.
  Any request that fails HMAC verification is rejected with 403 — never
  partially processed. Without this check, any attacker who knows your
  endpoint URL can POST a fake "payment succeeded" body and get orders
  marked paid for free.

HTTP response semantics (matters for Paymob retry behavior):
  200  → Paymob considers delivery successful. Will NOT retry.
  4xx  → Paymob treats as explicit rejection. Will NOT retry.
  5xx  → Paymob WILL retry (exponential backoff). We return 500 only when
         the DB update fails, because the payment is real and we want
         another attempt to record it.

Consequence: we return 200 for logically unactionable events (unknown
merchant_order_id, non-TRANSACTION event types) after logging them.
Only return 500 when a DB write that SHOULD succeed, fails.
"""

import hashlib
import hmac as hmac_lib
import json
import logging

import aio_pika
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..dependencies import get_db_session
from ..models.order import Order, PaymentStatus
from ..rabbitmq_client import get_rabbitmq_channel

router = APIRouter()
logger = logging.getLogger("wasla.webhook")

# ---------------------------------------------------------------------------
# HMAC verification
# ---------------------------------------------------------------------------

# Exact field names and order Paymob uses to build the HMAC message string.
# Source: Paymob Accept API docs, "Transaction Processed Callback" section.
# The order is significant — a different order produces a different hash.
# 'error_occured' is Paymob's own spelling (one 'r') — do not correct it.
_HMAC_FIELDS: tuple[str, ...] = (
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",            # Paymob typo — one 'r' — intentional
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order",                    # mapped to obj.order.id (Paymob's integer order ID)
    "owner",
    "pending",
    "source_data_pan",          # from obj.source_data.pan
    "source_data_sub_type",     # from obj.source_data.sub_type
    "source_data_type",         # from obj.source_data.type
    "success",
)


def _field_to_str(val) -> str:
    """
    Converts a transaction field value to the string form Paymob uses
    when building the HMAC message.

    Booleans MUST be lower-cased ('true'/'false'). Python's str(True)
    gives 'True' (capital T), which produces a different hash and breaks
    verification for every boolean field.

    None becomes empty string — matches Paymob's behavior for absent fields.
    """
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


def _build_hmac_message(obj: dict) -> str:
    """
    Extracts the HMAC-relevant values from the transaction object and
    concatenates them in Paymob's specified field order.

    The message is built from obj fields, NOT from the outer body — Paymob
    signs the transaction object ('obj'), not the whole POST body.
    """
    source_data = obj.get("source_data") or {}
    order_data = obj.get("order") or {}

    data: dict[str, str] = {
        "amount_cents":           _field_to_str(obj.get("amount_cents")),
        "created_at":             _field_to_str(obj.get("created_at")),
        "currency":               _field_to_str(obj.get("currency")),
        "error_occured":          _field_to_str(obj.get("error_occured")),
        "has_parent_transaction": _field_to_str(obj.get("has_parent_transaction")),
        "id":                     _field_to_str(obj.get("id")),
        "integration_id":         _field_to_str(obj.get("integration_id")),
        "is_3d_secure":           _field_to_str(obj.get("is_3d_secure")),
        "is_auth":                _field_to_str(obj.get("is_auth")),
        "is_capture":             _field_to_str(obj.get("is_capture")),
        "is_refunded":            _field_to_str(obj.get("is_refunded")),
        "is_standalone_payment":  _field_to_str(obj.get("is_standalone_payment")),
        "is_voided":              _field_to_str(obj.get("is_voided")),
        "order":                  _field_to_str(order_data.get("id")),
        "owner":                  _field_to_str(obj.get("owner")),
        "pending":                _field_to_str(obj.get("pending")),
        "source_data_pan":        _field_to_str(source_data.get("pan")),
        "source_data_sub_type":   _field_to_str(source_data.get("sub_type")),
        "source_data_type":       _field_to_str(source_data.get("type")),
        "success":                _field_to_str(obj.get("success")),
    }

    return "".join(data[field] for field in _HMAC_FIELDS)


def verify_paymob_hmac(transaction_obj: dict, received_hmac: str) -> bool:
    """
    Verifies the HMAC-SHA512 signature Paymob sends in the ?hmac= query param.

    Uses hmac.compare_digest for constant-time comparison to prevent timing
    attacks where small response-time differences reveal how many characters
    of the expected hash the received value shares.

    Returns True only when signatures match exactly.
    """
    message = _build_hmac_message(transaction_obj)
    expected = hmac_lib.new(
        settings.paymob_hmac_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()
    return hmac_lib.compare_digest(expected, received_hmac)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/paymob", status_code=status.HTTP_200_OK)
async def paymob_webhook(
    request: Request,
    hmac: str = Query(..., alias="hmac"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receives Paymob's transaction-processed callback.

    Paymob fires this for every terminal transaction state: successful
    payment, failed payment, refund, void, etc. We only update order state
    for TRANSACTION events where success is determined.
    """
    # --- Parse body ------------------------------------------------------
    try:
        body = await request.json()
    except Exception:
        logger.warning("Paymob webhook: received unparseable body")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is not valid JSON.",
        )

    transaction_obj: dict = body.get("obj") or {}

    # --- HMAC verification (gate on everything below) --------------------
    if not verify_paymob_hmac(transaction_obj, hmac):
        logger.warning(
            "Paymob webhook: HMAC mismatch — possible spoofed request "
            "transaction_id=%s",
            transaction_obj.get("id"),
        )
        # 403 is explicit rejection. Paymob will NOT retry on 4xx.
        # This is correct — if the signature is wrong, we don't want retries.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signature verification failed.",
        )

    # --- Event type filter -----------------------------------------------
    event_type: str = body.get("type", "")
    if event_type != "TRANSACTION":
        logger.info(
            "Paymob webhook: ignoring non-TRANSACTION event type=%s", event_type
        )
        return {"status": "ok"}

    # --- Extract fields --------------------------------------------------
    transaction_id = transaction_obj.get("id")
    is_success: bool = bool(transaction_obj.get("success", False))
    is_pending: bool = bool(transaction_obj.get("pending", False))

    # merchant_order_id is OUR checkout_group_id, echoed back by Paymob.
    # It lives at obj.order.merchant_order_id in the callback body.
    merchant_order_id: str | None = (
        (transaction_obj.get("order") or {}).get("merchant_order_id")
    )

    if not merchant_order_id:
        logger.error(
            "Paymob webhook: merchant_order_id missing from transaction_id=%s "
            "— cannot update orders. Full obj logged at DEBUG.",
            transaction_id,
        )
        logger.debug("Paymob webhook full obj: %s", transaction_obj)
        # 200 — Paymob won't retry; log for manual review.
        return {"status": "ok"}

    new_status = PaymentStatus.paid if is_success else PaymentStatus.failed

    # --- Update payment_status on all orders in this checkout group ------
    try:
        result = await db.execute(
            select(Order).where(Order.checkout_group_id == merchant_order_id)
        )
        orders: list[Order] = list(result.scalars().all())

        if not orders:
            logger.error(
                "Paymob webhook: no orders found for checkout_group_id=%s "
                "transaction_id=%s — possible data inconsistency",
                merchant_order_id,
                transaction_id,
            )
            # 200 — not a Paymob error, don't trigger retries.
            return {"status": "ok"}

        for order in orders:
            order.payment_status = new_status

        await db.commit()

    except Exception as exc:
        await db.rollback()
        logger.error(
            "Paymob webhook: DB update FAILED for checkout_group=%s "
            "transaction_id=%s new_status=%s error=%s",
            merchant_order_id,
            transaction_id,
            new_status.value,
            exc,
        )
        # 500 → Paymob retries. We WANT that here: the payment happened,
        # we just couldn't record it. Don't return 200 and silently lose it.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error processing payment notification.",
        )

    # --- Publish payment.confirmed (non-fatal) ---------------------------
    # Only publish for genuinely settled successful transactions.
    # Pending=True means 3-D Secure is still in progress — not yet final.
    if is_success and not is_pending:
        try:
            channel = get_rabbitmq_channel()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({
                        "checkout_group_id": merchant_order_id,
                        "order_ids": [o.id for o in orders],
                        "transaction_id": transaction_id,
                    }).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="payment.confirmed",
            )
        except Exception:
            # The DB is already updated — the payment IS recorded correctly.
            # A publish failure here must NOT cause a 500 response, because
            # that would trigger a Paymob retry and attempt to mark the same
            # orders paid again. Log the failure for alerting; do not raise.
            logger.error(
                "Paymob webhook: failed to publish payment.confirmed for "
                "checkout_group=%s transaction_id=%s — DB is correct, message lost",
                merchant_order_id,
                transaction_id,
            )

    logger.info(
        "Paymob webhook processed — checkout_group=%s transaction_id=%s "
        "success=%s pending=%s new_status=%s",
        merchant_order_id,
        transaction_id,
        is_success,
        is_pending,
        new_status.value,
    )
    return {"status": "ok"}
"""
Paymob Accept payment gateway integration.

Paymob uses a 4-step flow to initiate a hosted payment page:
  1. Authenticate  → get a short-lived auth token (valid ~1 hour).
  2. Register order → Paymob assigns its own integer order ID.
  3. Payment key   → a single-use token that encodes order + integration details.
  4. iFrame URL    → the hosted page Flutter opens for the user to pay.

Each step is a separate function so failures are named precisely in logs.
The public entry point is create_payment_url(), which sequences all four.

All HTTP calls use explicit timeouts. Any non-success response raises
PaymobError with a safe message suitable for surfacing to callers — the
raw Paymob response body is only in the logs, not returned to clients.
"""

import logging

import httpx

from ..config import settings

logger = logging.getLogger("wasla.paymob")

_PAYMOB_BASE = "https://accept.paymob.com/api"
# Paymob can be slow under peak load — 15 s is generous but avoids premature
# timeouts when their infrastructure is busy.
_HTTP_TIMEOUT = 15.0


class PaymobError(Exception):
    """Raised when any Paymob API step fails. Message is safe to return to clients."""


async def _get_auth_token() -> str:
    """
    Step 1 — Authenticates with Paymob using the API key from settings.
    Returns a short-lived token used for all subsequent calls in this flow.
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{_PAYMOB_BASE}/auth/tokens",
            json={"api_key": settings.paymob_api_key},
        )

    if resp.status_code != 201:
        logger.error(
            "Paymob auth failed — status=%s body=%.300s",
            resp.status_code,
            resp.text,
        )
        raise PaymobError("Payment provider authentication failed.")

    token: str | None = resp.json().get("token")
    if not token:
        logger.error("Paymob auth: response contained no token — body=%.300s", resp.text)
        raise PaymobError("Payment provider returned an unexpected auth response.")

    return token


async def _register_order(
    auth_token: str,
    amount_cents: int,
    merchant_order_id: str,
) -> int:
    """
    Step 2 — Registers the order with Paymob and returns Paymob's integer order ID.

    merchant_order_id is our checkout_group_id (UUID) — Paymob stores this
    and echoes it back in the webhook callback as merchant_order_id, which is
    exactly how the webhook handler identifies which of our orders to update.
    It must be unique per checkout attempt; checkout_group_id guarantees that.

    delivery_needed=False because Wasla handles delivery independently.
    items=[] is intentional — Paymob accepts an empty list; the full line-item
    breakdown isn't needed for the hosted payment flow.
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{_PAYMOB_BASE}/ecommerce/orders",
            json={
                "auth_token": auth_token,
                "delivery_needed": False,
                "amount_cents": amount_cents,
                "currency": "EGP",
                "merchant_order_id": merchant_order_id,
                "items": [],
            },
        )

    if resp.status_code not in (200, 201):
        logger.error(
            "Paymob order registration failed — status=%s body=%.300s",
            resp.status_code,
            resp.text,
        )
        raise PaymobError("Payment provider order registration failed.")

    paymob_order_id = resp.json().get("id")
    if not paymob_order_id:
        logger.error(
            "Paymob register_order: id missing from response — body=%.300s", resp.text
        )
        raise PaymobError("Payment provider returned an unexpected order response.")

    return int(paymob_order_id)


async def _get_payment_key(
    auth_token: str,
    paymob_order_id: int,
    amount_cents: int,
    billing_data: dict,
) -> str:
    """
    Step 3 — Requests a single-use payment key for the given Paymob order.

    The payment key encodes the order, amount, and integration — it's what
    Paymob's hosted iframe validates when the user submits card details.

    integration_id must be an int (Paymob rejects it as a string).
    lock_order_when_paid=True prevents the same order from being paid twice
    if the user somehow navigates back and submits again.

    billing_data fields required by Paymob:
      first_name, last_name, email, phone_number, city, country,
      street, building, floor, apartment.
    Missing fields cause Paymob to return a validation error — the caller
    (checkout_router) validates these before calling here.
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{_PAYMOB_BASE}/acceptance/payment_keys",
            json={
                "auth_token": auth_token,
                "amount_cents": amount_cents,
                "expiration": 3600,          # token expires in 1 hour
                "order_id": paymob_order_id,
                "billing_data": billing_data,
                "currency": "EGP",
                "integration_id": int(settings.paymob_integration_id),
                "lock_order_when_paid": True,
            },
        )

    if resp.status_code != 201:
        logger.error(
            "Paymob payment key request failed — status=%s body=%.300s",
            resp.status_code,
            resp.text,
        )
        raise PaymobError("Payment provider payment key request failed.")

    token: str | None = resp.json().get("token")
    if not token:
        logger.error(
            "Paymob payment_key: token missing from response — body=%.300s", resp.text
        )
        raise PaymobError("Payment provider returned an unexpected payment key response.")

    return token


def _build_iframe_url(payment_token: str) -> str:
    """
    Step 4 — Assembles the hosted payment iframe URL.
    The Flutter client opens this in a WebView; Paymob renders the card form.
    """
    return (
        f"https://accept.paymob.com/api/acceptance/iframes/"
        f"{settings.paymob_iframe_id}?payment_token={payment_token}"
    )


async def create_payment_url(
    checkout_group_id: str,
    amount_cents: int,
    billing_data: dict,
) -> str:
    """
    Executes the complete 4-step Paymob hosted payment flow.

    Returns the iframe URL for Flutter to open.

    Args:
        checkout_group_id: Used as Paymob's merchant_order_id. Must be unique
            per checkout. Paymob echoes this back in the webhook so we can
            identify which orders to update. We use checkout_group_id (a UUID
            from order_service) which is already guaranteed unique.

        amount_cents: Total order amount in Egyptian Piastres
            (150.00 EGP → 15000). Must match the sum of all orders in the
            checkout group.

        billing_data: Dict with Paymob-required fields. The checkout router
            validates required keys before calling here.

    Raises:
        PaymobError: If any step fails. The message is safe to surface to clients.
    """
    auth_token = await _get_auth_token()
    paymob_order_id = await _register_order(auth_token, amount_cents, checkout_group_id)
    payment_token = await _get_payment_key(
        auth_token, paymob_order_id, amount_cents, billing_data
    )
    return _build_iframe_url(payment_token)
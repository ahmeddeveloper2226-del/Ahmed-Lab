"""
Tests for routers/checkout_router.py.

Tests cover:
  - Missing billing fields → 422
  - Empty cart → 400
  - Stock shortage → 409 with shortages list
  - Unexpected order service failure → 500
  - Paymob failure after orders committed → 502
  - Success path → 201 with payment_url
  - RabbitMQ failure does NOT fail the checkout
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_id, get_db_session
from app.main import app
from app.routers import checkout_router
from app.services.order_service import (
    EmptyCartError,
    InsufficientStockError,
    OrderCreationResult,
)
from app.services.paymob_service import PaymobError

# ---------------------------------------------------------------------------
# Test client factory
# ---------------------------------------------------------------------------

_VALID_BILLING = {
    "first_name": "Ahmed",
    "last_name": "Hassan",
    "email": "ahmed@example.com",
    "phone_number": "+201001234567",
    "city": "Cairo",
    "country": "EG",
    "street": "El Tahrir St",
    "building": "12",
    "floor": "3",
    "apartment": "7",
}

_CHECKOUT_PAYLOAD = {
    "address_id": "addr-uuid-1",
    "billing_data": _VALID_BILLING,
}


def _fake_order_result(total: float = 150.0):
    """Creates a minimal OrderCreationResult-like fake."""
    order1 = MagicMock()
    order1.id = "order-id-1"
    order2 = MagicMock()
    order2.id = "order-id-2"

    result = MagicMock(spec=OrderCreationResult)
    result.checkout_group_id = "checkout-group-uuid"
    result.orders = [order1, order2]
    result.total = total
    return result


async def _client(uid: str = "test-uid-999"):
    app.dependency_overrides[get_current_user_id] = lambda: uid
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _cleanup():
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# Billing validation
# ---------------------------------------------------------------------------

async def test_checkout_missing_billing_fields_returns_422():
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post(
            "/checkout",
            json={
                "address_id": "addr-1",
                "billing_data": {"first_name": "Ahmed"},  # many fields missing
            },
        )

    assert response.status_code == 422
    assert "Missing required billing fields" in response.json()["detail"]
    _cleanup()


async def test_checkout_all_billing_fields_present_passes_validation(monkeypatch):
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(return_value=_fake_order_result()),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_payment_url",
        AsyncMock(return_value="https://pay.example.com/iframe"),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=AsyncMock())
        )),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 201
    _cleanup()


# ---------------------------------------------------------------------------
# Empty cart
# ---------------------------------------------------------------------------

async def test_checkout_empty_cart_returns_400(monkeypatch):
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(side_effect=EmptyCartError()),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
    _cleanup()


# ---------------------------------------------------------------------------
# Insufficient stock
# ---------------------------------------------------------------------------

async def test_checkout_insufficient_stock_returns_409_with_shortages(monkeypatch):
    shortages = [{"product_id": "p1", "requested": 5, "available": 2}]
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(side_effect=InsufficientStockError(shortages)),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["shortages"] == shortages
    _cleanup()


# ---------------------------------------------------------------------------
# Unexpected service error
# ---------------------------------------------------------------------------

async def test_checkout_unexpected_order_error_returns_500(monkeypatch):
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(side_effect=RuntimeError("unexpected DB crash")),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 500
    _cleanup()


# ---------------------------------------------------------------------------
# Paymob failure AFTER orders are committed
# ---------------------------------------------------------------------------

async def test_checkout_paymob_failure_after_orders_created_returns_502(monkeypatch):
    """
    If orders are committed but Paymob fails, we return 502 with the
    checkout_group_id as a support reference — we must NOT roll back.
    """
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(return_value=_fake_order_result(total=200.0)),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_payment_url",
        AsyncMock(side_effect=PaymobError("Paymob is down")),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 502
    # The checkout_group_id must be in the error response as a support reference.
    assert "checkout-group-uuid" in response.json()["detail"]
    _cleanup()


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

async def test_checkout_success_returns_201_with_payment_url(monkeypatch):
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(return_value=_fake_order_result(total=150.75)),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_payment_url",
        AsyncMock(return_value="https://accept.paymob.com/api/acceptance/iframes/42?payment_token=tok"),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=AsyncMock())
        )),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["checkout_group_id"] == "checkout-group-uuid"
    assert body["total"] == 150.75
    assert "payment_token=tok" in body["payment_url"]
    _cleanup()


async def test_checkout_amount_cents_conversion_is_correct(monkeypatch):
    """Verifies EGP → piastres conversion: 150.75 EGP = 15075 piastres."""
    create_payment_url_mock = AsyncMock(
        return_value="https://accept.paymob.com/iframe?payment_token=t"
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(return_value=_fake_order_result(total=150.75)),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_payment_url",
        create_payment_url_mock,
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=AsyncMock())
        )),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    # Second positional arg to create_payment_url is amount_cents
    call_kwargs = create_payment_url_mock.call_args
    assert call_kwargs.kwargs["amount_cents"] == 15075
    _cleanup()


# ---------------------------------------------------------------------------
# RabbitMQ publish failure is non-fatal
# ---------------------------------------------------------------------------

async def test_checkout_rabbitmq_failure_does_not_fail_the_response(monkeypatch):
    """
    If publishing order.created fails, the checkout must still return 201.
    The payment URL is ready; the order exists. Messaging is non-fatal.
    """
    monkeypatch.setattr(
        "app.routers.checkout_router.create_orders_from_cart",
        AsyncMock(return_value=_fake_order_result()),
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.create_payment_url",
        AsyncMock(return_value="https://pay.example.com/iframe"),
    )
    # RabbitMQ channel raises on publish
    broken_channel = MagicMock()
    broken_channel.default_exchange.publish = AsyncMock(
        side_effect=Exception("RabbitMQ connection lost")
    )
    monkeypatch.setattr(
        "app.routers.checkout_router.get_rabbitmq_channel",
        MagicMock(return_value=broken_channel),
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    client = await _client()
    async with client as c:
        response = await c.post("/checkout", json=_CHECKOUT_PAYLOAD)

    # Must still succeed despite RabbitMQ being broken.
    assert response.status_code == 201
    _cleanup()
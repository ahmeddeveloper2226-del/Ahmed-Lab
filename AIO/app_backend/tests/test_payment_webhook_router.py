"""
Tests for routers/payment_webhook_router.py.

The most security-critical tests in this file:
  - HMAC mismatch → 403 (never processed).
  - Valid HMAC → orders updated to `paid` or `failed`.
  - DB failure → 500 so Paymob retries (payment is real, we must record it).
  - RabbitMQ publish failure → still 200 (DB already correct; don't trigger
    Paymob retries that would double-mark orders as paid).
"""

import hashlib
import hmac as hmac_lib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_db_session
from app.main import app
from app.models.order import Order, OrderStatus, PaymentStatus
from app.routers.payment_webhook_router import verify_paymob_hmac, _build_hmac_message

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HMAC_SECRET = "test-hmac-secret-for-unit-tests"


def _make_transaction_obj(
    *,
    success: bool = True,
    pending: bool = False,
    merchant_order_id: str = "checkout-group-uuid-1",
    transaction_id: int = 12345,
):
    return {
        "id": transaction_id,
        "pending": pending,
        "amount_cents": 15000,
        "success": success,
        "is_auth": False,
        "is_capture": False,
        "is_standalone_payment": True,
        "is_voided": False,
        "is_refunded": False,
        "is_3d_secure": False,
        "integration_id": 999,
        "has_parent_transaction": False,
        "order": {
            "id": 88888,
            "merchant_order_id": merchant_order_id,
        },
        "created_at": "2024-01-15T10:30:00+02:00",
        "currency": "EGP",
        "error_occured": False,
        "owner": 54321,
        "pending": pending,
        "source_data": {
            "pan": "2346",
            "type": "card",
            "sub_type": "Visa",
        },
    }


def _compute_valid_hmac(transaction_obj: dict, secret: str) -> str:
    """Computes the HMAC the same way the router does — for building valid test requests."""
    message = _build_hmac_message(transaction_obj)
    return hmac_lib.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def _fake_scalar_result(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


def _fake_scalars_result(items):
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _fake_order(checkout_group_id: str = "checkout-group-uuid-1"):
    order = Order(
        id="order-id-1",
        checkout_group_id=checkout_group_id,
        user_id="uid-abc",
        shop_id="shop-1",
        status=OrderStatus.pending,
        payment_status=PaymentStatus.pending,
        total=150.00,
        commission_amount=22.50,
    )
    return order


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _cleanup():
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# Unit tests for verify_paymob_hmac
# ---------------------------------------------------------------------------

async def test_verify_hmac_returns_true_for_correct_signature(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )
    obj = _make_transaction_obj()
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    assert verify_paymob_hmac(obj, valid_hmac) is True


async def test_verify_hmac_returns_false_for_wrong_signature(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )
    obj = _make_transaction_obj()
    assert verify_paymob_hmac(obj, "completely-wrong-signature") is False


async def test_verify_hmac_returns_false_when_a_field_differs(monkeypatch):
    """Modifying any field in the transaction object invalidates the HMAC."""
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )
    obj = _make_transaction_obj(success=True)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    # Attacker changes success to True but HMAC was computed for success=True
    # — same here. Now flip success to False and check the old HMAC is invalid.
    tampered_obj = dict(obj)
    tampered_obj["success"] = False
    assert verify_paymob_hmac(tampered_obj, valid_hmac) is False


async def test_verify_hmac_booleans_must_be_lowercased(monkeypatch):
    """
    Python's str(True) = 'True' (capital T), but Paymob uses 'true' (lowercase).
    If booleans aren't lower-cased, HMAC will mismatch on every real callback.
    This test catches that regression.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )
    obj = _make_transaction_obj(success=True, pending=False)
    # Manually compute HMAC with lower-cased booleans (what Paymob sends)
    message = _build_hmac_message(obj)
    assert "true" in message or "false" in message
    # Python capital-T True must NOT appear in the message string
    assert "True" not in message
    assert "False" not in message


# ---------------------------------------------------------------------------
# Integration tests via HTTP
# ---------------------------------------------------------------------------

async def test_webhook_invalid_hmac_returns_403(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    obj = _make_transaction_obj()
    body = {"type": "TRANSACTION", "obj": obj}

    client = await _client()
    async with client as c:
        response = await c.post(
            "/webhooks/paymob?hmac=bad-signature",
            json=body,
        )

    assert response.status_code == 403
    _cleanup()


async def test_webhook_valid_hmac_successful_payment_marks_orders_paid(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    order = _fake_order()
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([order])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.routers.payment_webhook_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=AsyncMock())
        )),
    )

    obj = _make_transaction_obj(success=True, pending=False)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 200
    # Order must have been updated to paid
    assert order.payment_status == PaymentStatus.paid
    fake_db.commit.assert_called_once()
    _cleanup()


async def test_webhook_valid_hmac_failed_payment_marks_orders_failed(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    order = _fake_order()
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([order])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    obj = _make_transaction_obj(success=False, pending=False)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 200
    assert order.payment_status == PaymentStatus.failed
    _cleanup()


async def test_webhook_db_failure_returns_500_for_paymob_retry(monkeypatch):
    """
    If the DB update fails, we MUST return 500 so Paymob retries. Returning
    200 here would silently drop a real payment notification.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    from sqlalchemy.exc import SQLAlchemyError
    fake_db = AsyncMock()
    fake_db.execute.side_effect = SQLAlchemyError("DB is down")
    app.dependency_overrides[get_db_session] = lambda: fake_db

    obj = _make_transaction_obj()
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 500
    _cleanup()


async def test_webhook_unknown_checkout_group_returns_200(monkeypatch):
    """
    Unknown merchant_order_id → log and return 200, don't crash or 404.
    Paymob should not retry this; it's a data inconsistency for manual review.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    fake_db = AsyncMock()
    # No orders found for this checkout group
    fake_db.execute.return_value = _fake_scalars_result([])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    obj = _make_transaction_obj(merchant_order_id="nonexistent-group-id")
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 200
    # No commit should have been attempted
    fake_db.commit.assert_not_called()
    _cleanup()


async def test_webhook_non_transaction_event_returns_200_without_db(monkeypatch):
    """Non-TRANSACTION events are ignored — no DB reads, no RabbitMQ publishes."""
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    fake_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: fake_db

    obj = _make_transaction_obj()
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "DELIVERY_STATUS_UPDATE", "obj": obj},
        )

    assert response.status_code == 200
    fake_db.execute.assert_not_called()
    _cleanup()


async def test_webhook_missing_merchant_order_id_returns_200(monkeypatch):
    """
    If merchant_order_id is absent from the callback, we can't match orders.
    Return 200 (don't trigger retry) and log for manual review.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    fake_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: fake_db

    obj = _make_transaction_obj()
    # Remove merchant_order_id from the obj
    obj["order"] = {"id": 88888}  # no merchant_order_id key

    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 200
    fake_db.execute.assert_not_called()
    _cleanup()


async def test_webhook_publishes_payment_confirmed_on_success(monkeypatch):
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    order = _fake_order()
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([order])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=publish_mock)
        )),
    )

    obj = _make_transaction_obj(success=True, pending=False)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    publish_mock.assert_called_once()
    published_body = json.loads(publish_mock.call_args[0][0].body)
    assert published_body["checkout_group_id"] == "checkout-group-uuid-1"
    assert "order-id-1" in published_body["order_ids"]
    _cleanup()


async def test_webhook_does_not_publish_for_pending_3ds_transaction(monkeypatch):
    """
    Pending=True means 3-D Secure is still in progress. We update payment_status
    to paid (optimistically) but must NOT publish payment.confirmed yet.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    order = _fake_order()
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([order])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(publish=publish_mock)
        )),
    )

    # success=True but pending=True — 3DS in progress
    obj = _make_transaction_obj(success=True, pending=True)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    assert response.status_code == 200
    publish_mock.assert_not_called()
    _cleanup()


async def test_webhook_rabbitmq_failure_does_not_cause_500(monkeypatch):
    """
    If RabbitMQ publish fails AFTER the DB is updated, we must still return 200.
    Returning 500 would cause Paymob to retry and try to mark the order paid again.
    """
    monkeypatch.setattr(
        "app.routers.payment_webhook_router.settings.paymob_hmac_secret",
        _HMAC_SECRET,
    )

    order = _fake_order()
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([order])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.routers.payment_webhook_router.get_rabbitmq_channel",
        MagicMock(return_value=MagicMock(
            default_exchange=MagicMock(
                publish=AsyncMock(side_effect=Exception("RabbitMQ down"))
            )
        )),
    )

    obj = _make_transaction_obj(success=True, pending=False)
    valid_hmac = _compute_valid_hmac(obj, _HMAC_SECRET)

    client = await _client()
    async with client as c:
        response = await c.post(
            f"/webhooks/paymob?hmac={valid_hmac}",
            json={"type": "TRANSACTION", "obj": obj},
        )

    # DB is updated; return 200 despite messaging failure.
    assert response.status_code == 200
    assert order.payment_status == PaymentStatus.paid
    _cleanup()
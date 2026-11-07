"""
Tests for services/paymob_service.py.

All HTTP calls are intercepted with httpx.MockTransport — no real network
calls are made, and no Paymob credentials are required to run these tests.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services import paymob_service
from app.services.paymob_service import (
    PaymobError,
    _get_auth_token,
    _register_order,
    _get_payment_key,
    _build_iframe_url,
    create_payment_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_body: dict) -> httpx.Response:
    """Builds a fake httpx.Response with the given status and JSON body."""
    return httpx.Response(status_code=status_code, json=json_body)


# ---------------------------------------------------------------------------
# _get_auth_token
# ---------------------------------------------------------------------------

async def test_get_auth_token_returns_token_on_201(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"token": "test-auth-token"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    token = await _get_auth_token()
    assert token == "test-auth-token"


async def test_get_auth_token_raises_on_non_201(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(401, {"detail": "Invalid API key"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="authentication failed"):
        await _get_auth_token()


async def test_get_auth_token_raises_when_token_missing(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"other_field": "no token here"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="unexpected auth response"):
        await _get_auth_token()


# ---------------------------------------------------------------------------
# _register_order
# ---------------------------------------------------------------------------

async def test_register_order_returns_paymob_order_id(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"id": 99999})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    paymob_id = await _register_order("token", 15000, "checkout-group-uuid")
    assert paymob_id == 99999
    assert isinstance(paymob_id, int)


async def test_register_order_accepts_200_as_well(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(200, {"id": 12345})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    paymob_id = await _register_order("token", 5000, "group-id")
    assert paymob_id == 12345


async def test_register_order_raises_on_failure(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(400, {"message": "Bad request"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="order registration failed"):
        await _register_order("token", 15000, "group-id")


async def test_register_order_raises_when_id_missing(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"no_id_field": True})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="unexpected order response"):
        await _register_order("token", 15000, "group-id")


# ---------------------------------------------------------------------------
# _get_payment_key
# ---------------------------------------------------------------------------

async def test_get_payment_key_returns_token_on_201(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"token": "payment-token-xyz"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    token = await _get_payment_key("auth-token", 99999, 15000, {"first_name": "Ahmed"})
    assert token == "payment-token-xyz"


async def test_get_payment_key_raises_on_non_201(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(422, {"error": "missing billing field"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="payment key request failed"):
        await _get_payment_key("auth-token", 99999, 15000, {})


async def test_get_payment_key_raises_when_token_missing(monkeypatch):
    async def _fake_post(*args, **kwargs):
        return _mock_response(201, {"not_token": "something else"})

    monkeypatch.setattr(
        "app.services.paymob_service.httpx.AsyncClient",
        lambda **_: _fake_async_ctx(_fake_post),
    )

    with pytest.raises(PaymobError, match="unexpected payment key response"):
        await _get_payment_key("auth-token", 99999, 15000, {})


# ---------------------------------------------------------------------------
# _build_iframe_url
# ---------------------------------------------------------------------------

async def test_build_iframe_url_format(monkeypatch):
    monkeypatch.setattr(paymob_service.settings, "paymob_iframe_id", "iframe-42")

    url = _build_iframe_url("my-payment-token")

    assert "iframes/iframe-42" in url
    assert "payment_token=my-payment-token" in url
    assert url.startswith("https://accept.paymob.com")


# ---------------------------------------------------------------------------
# create_payment_url (full 4-step flow)
# ---------------------------------------------------------------------------

async def test_create_payment_url_calls_all_steps_in_order(monkeypatch):
    """
    Verifies the 4 steps are called in sequence and the final URL is built
    from the payment token returned by step 3.
    """
    auth_token_mock = AsyncMock(return_value="auth-tok")
    register_mock = AsyncMock(return_value=55555)
    payment_key_mock = AsyncMock(return_value="pay-tok-abc")

    monkeypatch.setattr(paymob_service, "_get_auth_token", auth_token_mock)
    monkeypatch.setattr(paymob_service, "_register_order", register_mock)
    monkeypatch.setattr(paymob_service, "_get_payment_key", payment_key_mock)
    monkeypatch.setattr(paymob_service.settings, "paymob_iframe_id", "frame-1")

    url = await create_payment_url(
        checkout_group_id="group-uuid-123",
        amount_cents=20000,
        billing_data={"first_name": "Ahmed"},
    )

    auth_token_mock.assert_called_once()
    register_mock.assert_called_once_with("auth-tok", 20000, "group-uuid-123")
    payment_key_mock.assert_called_once_with(
        "auth-tok", 55555, 20000, {"first_name": "Ahmed"}
    )
    assert "pay-tok-abc" in url
    assert "frame-1" in url


async def test_create_payment_url_propagates_paymob_error_from_step1(monkeypatch):
    monkeypatch.setattr(
        paymob_service, "_get_auth_token", AsyncMock(side_effect=PaymobError("auth failed"))
    )

    with pytest.raises(PaymobError, match="auth failed"):
        await create_payment_url("group-id", 10000, {})


async def test_create_payment_url_propagates_paymob_error_from_step3(monkeypatch):
    monkeypatch.setattr(paymob_service, "_get_auth_token", AsyncMock(return_value="tok"))
    monkeypatch.setattr(paymob_service, "_register_order", AsyncMock(return_value=1))
    monkeypatch.setattr(
        paymob_service,
        "_get_payment_key",
        AsyncMock(side_effect=PaymobError("payment key failed")),
    )

    with pytest.raises(PaymobError, match="payment key failed"):
        await create_payment_url("group-id", 10000, {})


# ---------------------------------------------------------------------------
# Async context manager helper (replaces httpx.AsyncClient in monkeypatching)
# ---------------------------------------------------------------------------

class _FakeClient:
    """Minimal async context manager that wraps a fake post function."""

    def __init__(self, post_fn):
        self._post_fn = post_fn

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, *args, **kwargs):
        return await self._post_fn(*args, **kwargs)


def _fake_async_ctx(post_fn):
    return _FakeClient(post_fn)
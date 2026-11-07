"""
Tests for cart_router.py. Run with: pytest
"""
import json
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_id, get_db_session
from app.main import app
from app.models.product import Product
from app.models.shop import Shop


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


async def _client():
    app.dependency_overrides[get_current_user_id] = lambda: "fake-uid-123"
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_get_empty_cart(monkeypatch):
    fake_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.services.cart_service.redis_client.get", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.get("/cart/")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0.0}

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_update_cart_item_rejects_quantity_over_stock(monkeypatch):
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=3)
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(product)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.put("/cart/items/p1", json={"quantity": 10})

    assert response.status_code == 409
    assert "3 left in stock" in response.json()["detail"]

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_update_cart_item_rejects_unknown_product(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.put("/cart/items/does-not-exist", json={"quantity": 1})

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_update_cart_item_success_and_correct_totals(monkeypatch):
    product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=10)
    shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(product),          # stock validation lookup
        _fake_scalars_result([product]),        # products lookup in build_cart_response
        _fake_scalars_result([shop]),           # shops lookup in build_cart_response
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    redis_set = AsyncMock()
    monkeypatch.setattr("app.services.cart_service.redis_client.get", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.cart_service.redis_client.set", redis_set)

    client = await _client()
    async with client as c:
        response = await c.put("/cart/items/p1", json={"quantity": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["subtotal"] == 135.0
    assert body["total"] == 135.0
    redis_set.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_cart_self_heals_when_product_was_deleted(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalars_result([]),  # product no longer exists in Postgres
        _fake_scalars_result([]),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.services.cart_service.redis_client.get",
        AsyncMock(return_value=json.dumps({"deleted-product": 2})),
    )
    redis_delete = AsyncMock()
    monkeypatch.setattr("app.services.cart_service.redis_client.delete", redis_delete)

    client = await _client()
    async with client as c:
        response = await c.get("/cart/")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0.0
    redis_delete.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_setting_quantity_to_zero_removes_item(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalars_result([]),
        _fake_scalars_result([]),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.services.cart_service.redis_client.get",
        AsyncMock(return_value=json.dumps({"p1": 2})),
    )
    redis_delete = AsyncMock()
    monkeypatch.setattr("app.services.cart_service.redis_client.delete", redis_delete)

    client = await _client()
    async with client as c:
        response = await c.put("/cart/items/p1", json={"quantity": 0})

    assert response.status_code == 200
    assert response.json()["items"] == []
    redis_delete.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)
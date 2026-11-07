"""
Tests for store_panel_router.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from datetime import datetime
from app.dependencies import get_current_store_uid, get_db_session
from app.main import app
from app.models.order import Order, OrderStatus
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
    app.dependency_overrides[get_current_store_uid] = lambda: "store-uid-1"
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_get_my_shop_returns_404_when_no_shop_assigned():
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/store/my-shop")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_get_my_shop_returns_owned_shop():
    my_shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7, owner_user_id="store-uid-1")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(my_shop)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/store/my-shop")

    assert response.status_code == 200
    assert response.json()["id"] == "s1"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_update_stock_rejected_for_product_belonging_to_another_shop(monkeypatch):
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    someone_elses_product = Product(id="p1", shop_id="s2", name="Not mine", price=10.0, stock_quantity=5)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(my_shop),               # _get_owned_shop_or_404
        _fake_scalar_result(someone_elses_product),  # product lookup
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/store/products/p1/stock", json={"stock_quantity": 20})

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_update_stock_success_invalidates_cache_and_reindexes(monkeypatch):
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    my_product = Product(id="p1", shop_id="s1", name="Koshary", price=45.0, stock_quantity=5)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(my_shop),
        _fake_scalar_result(my_product),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    invalidate_mock = AsyncMock()
    index_mock = AsyncMock()
    monkeypatch.setattr("app.routers.store_panel_router.invalidate_cached", invalidate_mock)
    monkeypatch.setattr("app.routers.store_panel_router.index_product", index_mock)

    client = await _client()
    async with client as c:
        response = await c.patch("/store/products/p1/stock", json={"stock_quantity": 25})

    assert response.status_code == 200
    assert my_product.stock_quantity == 25
    assert invalidate_mock.call_count == 2  # by_shop cache + detail cache
    index_mock.assert_called_once_with(my_product, my_shop)

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_incoming_orders_scoped_to_own_shop_only():
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    my_order = Order(
        id="o1",
        checkout_group_id="g1",
        user_id="u1",
        shop_id="s1",
        status=OrderStatus.pending,
        total=45.0,
        commission_amount=6.75,
        created_at=datetime.utcnow(),
)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(my_shop),
        _fake_scalars_result([my_order]),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/store/orders")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "o1"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_update_order_status_rejects_delivered():
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(my_shop)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/store/orders/o1/status", json={"status": "delivered"})

    assert response.status_code == 400
    assert "pending, preparing, or out_for_delivery" in response.json()["detail"]

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_update_order_status_rejected_for_order_belonging_to_another_shop():
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    someone_elses_order = Order(
        id="o1", checkout_group_id="g1", user_id="u1", shop_id="s2",
        status=OrderStatus.pending, total=45.0, commission_amount=6.75,
    )

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(my_shop),
        _fake_scalar_result(someone_elses_order),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/store/orders/o1/status", json={"status": "preparing"})

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)


async def test_update_order_status_success():
    my_shop = Shop(id="s1", category_id="c1", name="Mine", rating=4.7, owner_user_id="store-uid-1")
    my_order = Order(
    id="o1",
    checkout_group_id="g1",
    user_id="u1",
    shop_id="s1",
    status=OrderStatus.pending,
    total=45.0,
    commission_amount=6.75,
    created_at=datetime.utcnow(),
)

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(my_shop),
        _fake_scalar_result(my_order),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/store/orders/o1/status", json={"status": "preparing"})

    assert response.status_code == 200
    assert my_order.status == OrderStatus.preparing

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_store_uid, None)
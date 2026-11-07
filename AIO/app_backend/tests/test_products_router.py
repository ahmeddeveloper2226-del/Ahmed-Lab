"""
Tests for products_router.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.dependencies import get_current_admin_uid, get_current_user_id, get_db_session
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


async def test_get_products_for_unknown_shop_returns_404(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.products_router.get_cached", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.get("/shops/does-not-exist/products")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_product_in_stock_flag_reflects_stock_quantity(monkeypatch):
    fake_shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)
    fake_products = [
        Product(id="p1", shop_id="s1", name="Koshary Regular", price=45.0, stock_quantity=5),
        Product(id="p2", shop_id="s1", name="Koshary Large", price=65.0, stock_quantity=0),
    ]

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(fake_shop),
        _fake_scalars_result(fake_products),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.products_router.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.routers.products_router.set_cached", AsyncMock())

    client = await _client()
    async with client as c:
        response = await c.get("/shops/s1/products")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["in_stock"] is True
    assert body[1]["in_stock"] is False

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_get_product_detail_returns_404_for_missing_product(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.products_router.get_cached", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.get("/products/does-not-exist")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_create_product_rejected_for_non_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops/s1/products",
            json={"id": "p1", "name": "New Product", "price": 50.0, "stock_quantity": 10},
        )

    assert response.status_code in (401, 403)


async def test_create_product_succeeds_for_admin_and_invalidates_cache(monkeypatch):
    fake_shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_shop)
    app.dependency_overrides[get_db_session] = lambda: fake_db
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    invalidate_mock = AsyncMock()
    monkeypatch.setattr("app.routers.products_router.invalidate_cached", invalidate_mock)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops/s1/products",
            json={"id": "p1", "name": "Koshary Regular", "price": 45.0, "stock_quantity": 10},
        )

    assert response.status_code == 201
    assert response.json()["in_stock"] is True
    invalidate_mock.assert_called_once_with("products:by_shop:s1")

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_admin_uid, None)


async def test_create_product_returns_409_on_duplicate_id():
    fake_shop = Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_shop)
    fake_db.commit.side_effect = IntegrityError("stmt", "params", Exception("dup key"))
    app.dependency_overrides[get_db_session] = lambda: fake_db
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops/s1/products",
            json={"id": "p1", "name": "Duplicate", "price": 10.0, "stock_quantity": 1},
        )

    assert response.status_code == 409
    fake_db.rollback.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_admin_uid, None)
"""
Tests for shops_router.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.dependencies import get_current_admin_uid, get_current_user_id, get_db_session
from app.main import app
from app.models.category import Category
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


async def test_get_shops_for_unknown_category_returns_404(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)  # category lookup fails
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.shops_router.get_cached", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.get("/categories/does-not-exist/shops")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_get_shops_for_category_returns_data_on_cache_miss(monkeypatch):
    fake_category = Category(id="c1", name="Food")
    fake_shops = [Shop(id="s1", category_id="c1", name="Koshary El Tahrir", rating=4.7)]

    fake_db = AsyncMock()
    fake_db.execute.side_effect = [
        _fake_scalar_result(fake_category),
        _fake_scalars_result(fake_shops),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.shops_router.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.routers.shops_router.set_cached", AsyncMock())

    client = await _client()
    async with client as c:
        response = await c.get("/categories/c1/shops")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Koshary El Tahrir"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_get_shop_detail_returns_404_for_missing_shop(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.shops_router.get_cached", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.get("/shops/does-not-exist")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_create_shop_rejected_for_non_admin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops", json={"id": "s1", "category_id": "c1", "name": "New Shop"}
        )

    assert response.status_code in (401, 403)


async def test_create_shop_succeeds_for_admin_and_invalidates_cache(monkeypatch):
    fake_category = Category(id="c1", name="Food")

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_category)
    app.dependency_overrides[get_db_session] = lambda: fake_db
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    invalidate_mock = AsyncMock()
    monkeypatch.setattr("app.routers.shops_router.invalidate_cached", invalidate_mock)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops", json={"id": "s2", "category_id": "c1", "name": "Zooba"}
        )

    assert response.status_code == 201
    invalidate_mock.assert_called_once_with("shops:by_category:c1")

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_admin_uid, None)


async def test_create_shop_returns_409_on_duplicate_id():
    fake_category = Category(id="c1", name="Food")

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_category)
    fake_db.commit.side_effect = IntegrityError("stmt", "params", Exception("dup key"))
    app.dependency_overrides[get_db_session] = lambda: fake_db
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/shops", json={"id": "s1", "category_id": "c1", "name": "Duplicate"}
        )

    assert response.status_code == 409
    fake_db.rollback.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_admin_uid, None)

    
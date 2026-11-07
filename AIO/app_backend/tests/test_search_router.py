"""
Tests for search_router.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_id, get_db_session
from app.main import app
from app.models.category import Category


def _fake_scalar_result(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


async def _client():
    app.dependency_overrides[get_current_user_id] = lambda: "fake-uid-123"
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_search_rejects_unknown_category(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/search/", params={"q": "koshary", "category_id": "does-not-exist"})

    assert response.status_code == 400

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_search_returns_results_on_cache_miss(monkeypatch):
    fake_category = Category(id="c1", name="Food")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_category)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.search_router.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.routers.search_router.set_cached", AsyncMock())

    fake_results = [
        {
            "id": "p1",
            "shop_id": "s1",
            "shop_name": "Koshary El Tahrir",
            "category_id": "c1",
            "name": "Koshary Regular",
            "price": 45.0,
            "stock_quantity": 10,
            "in_stock": True,
        }
    ]
    monkeypatch.setattr(
        "app.routers.search_router.search_products", AsyncMock(return_value=fake_results)
    )

    client = await _client()
    async with client as c:
        response = await c.get("/search/", params={"q": "koshary", "category_id": "c1"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["shop_name"] == "Koshary El Tahrir"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_search_returns_cached_results_without_querying_elasticsearch(monkeypatch):
    fake_category = Category(id="c1", name="Food")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_category)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    cached_payload = [{"id": "p1", "shop_id": "s1", "shop_name": "X", "category_id": "c1",
                        "name": "Koshary", "price": 45.0, "stock_quantity": 5, "in_stock": True}]
    monkeypatch.setattr(
        "app.routers.search_router.get_cached", AsyncMock(return_value=cached_payload)
    )
    search_mock = AsyncMock()
    monkeypatch.setattr("app.routers.search_router.search_products", search_mock)

    client = await _client()
    async with client as c:
        response = await c.get("/search/", params={"q": "koshary", "category_id": "c1"})

    assert response.status_code == 200
    search_mock.assert_not_called()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_search_returns_503_when_elasticsearch_fails(monkeypatch):
    fake_category = Category(id="c1", name="Food")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_category)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.search_router.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.routers.search_router.search_products",
        AsyncMock(side_effect=Exception("ES down")),
    )

    client = await _client()
    async with client as c:
        response = await c.get("/search/", params={"q": "koshary", "category_id": "c1"})

    assert response.status_code == 503

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)
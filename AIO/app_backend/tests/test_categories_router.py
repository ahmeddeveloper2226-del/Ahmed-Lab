"""
Tests for categories_router.py.

Run with: pytest
(pytest.ini sets asyncio_mode = auto, so async test functions run correctly
without needing an explicit @pytest.mark.asyncio on each one.)

These tests override get_current_user_id / get_current_admin_uid / and the
DB session, so they never touch a real Firebase token or a real Postgres
database — fast, isolated, runnable in CI with zero live infrastructure.
"""
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import pytest

from app.dependencies import get_current_admin_uid, get_current_user_id, get_db_session
from app.main import app
from app.models.category import Category


class FakeScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalarsResult(self._items)


@pytest.fixture(autouse=True)
def override_auth():
    """Every test runs as if already authenticated as a fake regular user."""
    app.dependency_overrides[get_current_user_id] = lambda: "fake-uid-123"
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_get_categories_returns_data_from_db_on_cache_miss(monkeypatch):
    fake_categories = [
        Category(id="c1", name="Food"),
        Category(id="c2", name="Grocery"),
    ]

    fake_db = AsyncMock()
    fake_db.execute.return_value = FakeExecuteResult(fake_categories)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.categories_router.get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr("app.routers.categories_router.set_cached", AsyncMock())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/categories/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == "c1"
    assert body[0]["name"] == "Food"

    app.dependency_overrides.pop(get_db_session, None)


async def test_get_categories_returns_cached_data_without_touching_db(monkeypatch):
    cached_payload = [{"id": "c1", "name": "Food"}]

    fake_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.routers.categories_router.get_cached", AsyncMock(return_value=cached_payload)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/categories/")

    assert response.status_code == 200
    assert response.json() == cached_payload
    fake_db.execute.assert_not_called()

    app.dependency_overrides.pop(get_db_session, None)


async def test_get_categories_returns_503_on_db_failure(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.side_effect = SQLAlchemyError("connection lost")
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.categories_router.get_cached", AsyncMock(return_value=None))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/categories/")

    assert response.status_code == 503

    app.dependency_overrides.pop(get_db_session, None)


async def test_create_category_rejected_for_non_admin():
    """
    get_current_admin_uid is NOT overridden here on purpose — with no real
    Firebase token supplied, the real _verify_token dependency rejects the
    request before the admin-role check even runs, proving the endpoint is
    closed by default rather than open unless checked.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/categories/", json={"id": "c1", "name": "Food"})

    assert response.status_code in (401, 403)


async def test_create_category_succeeds_for_admin_and_invalidates_cache(monkeypatch):
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    fake_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: fake_db

    invalidate_mock = AsyncMock()
    monkeypatch.setattr("app.routers.categories_router.invalidate_cached", invalidate_mock)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/categories/", json={"id": "c3", "name": "Marketplace"})

    assert response.status_code == 201
    invalidate_mock.assert_called_once_with("categories:all")

    app.dependency_overrides.pop(get_current_admin_uid, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_create_category_returns_409_on_duplicate_id():
    app.dependency_overrides[get_current_admin_uid] = lambda: "fake-admin-uid"

    fake_db = AsyncMock()
    fake_db.commit.side_effect = IntegrityError("stmt", "params", Exception("dup key"))
    app.dependency_overrides[get_db_session] = lambda: fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/categories/", json={"id": "c1", "name": "Food"})

    assert response.status_code == 409
    fake_db.rollback.assert_called_once()

    app.dependency_overrides.pop(get_current_admin_uid, None)
    app.dependency_overrides.pop(get_db_session, None)
"""
Tests for profile_router.py. Run with: pytest
"""
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_id, get_db_session
from app.main import app
from app.models.address import Address
from app.models.user import User


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


async def test_get_profile_returns_user():
    from datetime import datetime, timezone
    fake_user = User(
        id="fake-uid-123",
        full_name="Ahmed",
        phone_number="+201234567890",
        email=None,
        email_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_user)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/me/")

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ahmed"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_update_profile_only_changes_full_name():
    from datetime import datetime, timezone
    fake_user = User(
        id="fake-uid-123",
        full_name="Old Name",
        phone_number="+201234567890",
        email=None,
        email_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_user)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/me/", json={"full_name": "New Name"})

    assert response.status_code == 200
    assert fake_user.full_name == "New Name"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_cannot_update_someone_elses_address():
    other_users_address = Address(id="addr-1", user_id="a-different-uid", full_address="Somewhere")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(other_users_address)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.patch("/me/addresses/addr-1", json={"label": "Hacked"})

    assert response.status_code == 404  # NOT 403 -- deliberately indistinguishable from "doesn't exist"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_cannot_delete_someone_elses_address():
    other_users_address = Address(id="addr-1", user_id="a-different-uid", full_address="Somewhere")
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(other_users_address)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.delete("/me/addresses/addr-1")

    assert response.status_code == 404

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_creating_default_address_unsets_previous_default():
    existing_default = Address(
        id="addr-old", user_id="fake-uid-123", full_address="Old default", is_default=True
    )

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([existing_default])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.post(
            "/me/addresses",
            json={"full_address": "New default address", "is_default": True},
        )

    assert response.status_code == 201
    assert existing_default.is_default is False  # the old one got unset

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_set_default_address_unsets_others():
    target_address = Address(id="addr-new", user_id="fake-uid-123", full_address="Target", is_default=False)
    other_default = Address(id="addr-old", user_id="fake-uid-123", full_address="Old", is_default=True)

    fake_db = AsyncMock()
    # First call (ownership check) returns the target address; second call
    # (existing defaults query) returns the other_default address.
    fake_db.execute.side_effect = [
        _fake_scalar_result(target_address),
        _fake_scalars_result([other_default]),
    ]
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.post("/me/addresses/addr-new/set-default")

    assert response.status_code == 200
    assert target_address.is_default is True
    assert other_default.is_default is False

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_list_addresses_only_returns_own():
    my_address = Address(
        id="addr-1", user_id="fake-uid-123", full_address="Mine", label=None,
        lat=None, lng=None, is_default=False,
    )
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalars_result([my_address])
    app.dependency_overrides[get_db_session] = lambda: fake_db

    client = await _client()
    async with client as c:
        response = await c.get("/me/addresses")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "addr-1"

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)
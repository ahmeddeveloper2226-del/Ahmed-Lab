"""
Tests for auth_router.py. Run with: pytest

Redis and the DB are both mocked — these tests validate the LOGIC (attempt
counting, cooldowns, uniqueness checks), not real infrastructure.
"""
import json
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_claims, get_current_user_id, get_db_session
from app.main import app
from app.models.user import User


def _fake_scalar_result(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


async def _client():
    app.dependency_overrides[get_current_user_id] = lambda: "fake-uid-123"
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_create_session_creates_new_user_on_first_login(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)  # no existing user

    async def fake_refresh(obj):
        obj.id = "fake-uid-123"
        obj.phone_number = None
        obj.email = None
        obj.email_verified = False
        from datetime import datetime, timezone
        obj.created_at = datetime.now(timezone.utc)

    fake_db.refresh.side_effect = fake_refresh
    app.dependency_overrides[get_db_session] = lambda: fake_db
    # /auth/session depends on get_current_user_claims (needs phone_number/
    # email claims), not the simpler get_current_user_id used elsewhere.
    app.dependency_overrides[get_current_user_claims] = lambda: {
        "uid": "fake-uid-123",
        "phone_number": None,
        "email": None,
        "email_verified": False,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post("/auth/session")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "fake-uid-123"
    assert body["email_verified"] is False
    fake_db.add.assert_called_once()

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_claims, None)


async def test_send_email_code_blocked_by_cooldown(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    # Simulate an active cooldown already set for this uid.
    fake_redis_get = AsyncMock(return_value="1")
    monkeypatch.setattr("app.routers.auth_router.redis_client.get", fake_redis_get)

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/send-code", json={"email": "test@example.com"})

    assert response.status_code == 429

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_send_email_code_rejects_email_already_verified_on_another_account(monkeypatch):
    other_user = User(id="other-uid", email="taken@example.com", email_verified=True)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(other_user)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.auth_router.redis_client.get", AsyncMock(return_value=None))

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/send-code", json={"email": "taken@example.com"})

    assert response.status_code == 409

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_send_email_code_success(monkeypatch):
    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(None)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr("app.routers.auth_router.redis_client.get", AsyncMock(return_value=None))
    monkeypatch.setattr("app.routers.auth_router.redis_client.set", AsyncMock())
    monkeypatch.setattr("app.routers.auth_router.send_verification_email", AsyncMock())

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/send-code", json={"email": "new@example.com"})

    assert response.status_code == 200
    assert response.json()["expires_in_seconds"] == 600

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)


async def test_verify_email_code_wrong_code_decrements_attempts(monkeypatch):
    stored = {"code": "123456", "email": "test@example.com", "attempts": 0}

    monkeypatch.setattr(
        "app.routers.auth_router.redis_client.get", AsyncMock(return_value=json.dumps(stored))
    )
    monkeypatch.setattr("app.routers.auth_router.redis_client.set", AsyncMock())
    monkeypatch.setattr("app.routers.auth_router.redis_client.ttl", AsyncMock(return_value=500))

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/verify-code", json={"code": "999999"})

    assert response.status_code == 400
    assert "remaining" in response.json()["detail"]

    app.dependency_overrides.pop(get_current_user_id, None)


async def test_verify_email_code_locks_out_after_max_attempts(monkeypatch):
    stored = {"code": "123456", "email": "test@example.com", "attempts": 5}

    monkeypatch.setattr(
        "app.routers.auth_router.redis_client.get", AsyncMock(return_value=json.dumps(stored))
    )
    monkeypatch.setattr("app.routers.auth_router.redis_client.delete", AsyncMock())

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/verify-code", json={"code": "123456"})

    assert response.status_code == 400
    assert "Too many" in response.json()["detail"]

    app.dependency_overrides.pop(get_current_user_id, None)


async def test_verify_email_code_success_updates_user(monkeypatch):
    stored = {"code": "123456", "email": "test@example.com", "attempts": 0}
    fake_user = User(id="fake-uid-123", email=None, email_verified=False)

    fake_db = AsyncMock()
    fake_db.execute.return_value = _fake_scalar_result(fake_user)
    app.dependency_overrides[get_db_session] = lambda: fake_db

    monkeypatch.setattr(
        "app.routers.auth_router.redis_client.get", AsyncMock(return_value=json.dumps(stored))
    )
    monkeypatch.setattr("app.routers.auth_router.redis_client.delete", AsyncMock())

    client = await _client()
    async with client as c:
        response = await c.post("/auth/email/verify-code", json={"code": "123456"})

    assert response.status_code == 200
    assert response.json()["email_verified"] is True
    assert fake_user.email == "test@example.com"
    assert fake_user.email_verified is True

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user_id, None)
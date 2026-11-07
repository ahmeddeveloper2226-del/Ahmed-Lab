from fastapi.testclient import TestClient


def test_health_endpoint():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_protected_route_requires_auth():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401

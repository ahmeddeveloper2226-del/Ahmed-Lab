"""
Rate limiting, built on slowapi (a Flask-limiter-style wrapper around
`limits`). Keys requests by the authenticated Firebase UID when a valid
bearer token is present, falling back to the client IP for anonymous
endpoints (e.g. /auth/*). This stops one abusive account from being able to
dodge limits by rotating IPs, and stops pre-auth brute forcing by IP.

Storage: in-memory by default (fine for a single instance / dev). Set
RATE_LIMIT_STORAGE_URI=redis://<host>:6379 in production so limits are
shared correctly across multiple uvicorn workers / replicas.
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        # Cheap, non-verifying reuse of the token as a bucket key; a fake or
        # stolen token still only ever punishes the token holder, never
        # actually authenticates anything (that still happens separately in
        # security.py). This just gives per-user buckets without a second
        # Firebase round-trip on every single request.
        token = auth_header[7:]
        return f"user:{hash(token) & 0xFFFFFFFF}"
    return f"ip:{get_remote_address(request)}"


def _build_limiter() -> Limiter:
    # Loaded lazily (not at import time) so importing this module never
    # requires settings/secrets to already be configured - matters for
    # tooling (tests, alembic-style scripts, docs generation) that imports
    # route modules before the app's env is fully set up.
    settings = get_settings()
    return Limiter(
        key_func=_rate_limit_key,
        storage_uri=settings.RATE_LIMIT_STORAGE_URI,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        headers_enabled=False,  # exposes X-RateLimit-* headers to the frontend
        strategy="fixed-window",
    )


limiter = _build_limiter()

"""
Authentication dependency used by every protected route.

The frontend authenticates with Firebase Auth (Google popup or
email/password) and attaches the resulting ID token as:

    Authorization: Bearer <firebase_id_token>

This module verifies that token on every request, rejects revoked/expired
tokens, and exposes the decoded claims (uid, email, ...) to route handlers
via `Depends(get_current_user)`.
"""
from __future__ import annotations

import hashlib
import threading
import time

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth

from app.core.firebase import verify_id_token

log = structlog.get_logger()

bearer_scheme = HTTPBearer(auto_error=False)

# verify_id_token(check_revoked=True) makes a NETWORK call to Google on every request
# (that's the `accounts:lookup` line in the log), ~0.2-0.5s each, and every page fires
# several requests. Remember a successfully verified token for a few minutes instead.
# Trade-off: a token revoked by an admin keeps working for at most _TOKEN_CACHE_SECONDS.
_TOKEN_CACHE_SECONDS = 300
_token_cache: dict[str, tuple[float, dict]] = {}
_token_cache_lock = threading.Lock()


def _verify_cached(token: str) -> dict:
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    with _token_cache_lock:
        hit = _token_cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    decoded = verify_id_token(token)
    valid_until = min(now + _TOKEN_CACHE_SECONDS, float(decoded.get("exp", now)) - 30)
    with _token_cache_lock:
        if len(_token_cache) > 500:
            for k in [k for k, (until, _) in _token_cache.items() if until <= now]:
                _token_cache.pop(k, None)
        _token_cache[key] = (valid_until, decoded)
    return decoded


class CurrentUser:
    """Lightweight, typed view over the decoded Firebase token claims."""

    __slots__ = ("uid", "email", "email_verified", "claims")

    def __init__(self, claims: dict):
        self.uid: str = claims["uid"]
        self.email: str | None = claims.get("email")
        self.email_verified: bool = bool(claims.get("email_verified", False))
        self.claims = claims


def get_current_user(  # plain `def`: FastAPI runs it in a worker thread, so the network call never freezes the server

    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        decoded = _verify_cached(token)
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired, please sign in again")
    except fb_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Session revoked, please sign in again")
    except fb_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception:  # noqa: BLE001 - never leak internals of auth failures
        log.warning("auth.verify_failed", exc_info=True)
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    return CurrentUser(decoded)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)  # type: ignore[arg-type]
    except HTTPException:
        return None
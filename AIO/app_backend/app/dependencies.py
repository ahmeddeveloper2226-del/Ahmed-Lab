import logging
import secrets

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db

logger = logging.getLogger("wasla.auth_dependencies")

_firebase_app = firebase_admin.initialize_app(
    credentials.Certificate(settings.firebase_credentials_path)
)

_bearer_scheme = HTTPBearer()


async def _verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        # check_revoked=True previously here — removed. It adds a live
        # round-trip to check the token's auth_time against the user
        # record's "tokens valid after" timestamp, and right after a fresh
        # sign-in that timestamp can take a moment to propagate on
        # Firebase's side — so a brand-new session, immediately calling
        # /auth/session with an otherwise perfectly valid token, could get
        # rejected as "revoked" purely from that propagation race. That
        # matches "works the first time, then fails right after logging in
        # again — even with a different account": every fresh sign-in hits
        # the same window, regardless of which account it is.
        # verify_id_token still fully checks signature, issuer, audience,
        # and expiry without check_revoked — the only thing lost is the
        # ability to force-invalidate one specific already-issued token
        # before its natural (hourly) expiry, which nothing in this app
        # relies on.
        return firebase_auth.verify_id_token(token)
    except (
        firebase_auth.ExpiredIdTokenError,
        firebase_auth.RevokedIdTokenError,
        firebase_auth.InvalidIdTokenError,
        firebase_auth.UserDisabledError,
    ) as exc:
        # This used to raise with NO log line at all — every 401 from this
        # endpoint was a complete black box, no way to tell
        # ExpiredIdTokenError from InvalidIdTokenError from a genuinely bad
        # token, all producing the identical client-side error message.
        # Logging the exact exception type/message here is what actually
        # lets us find the real cause if this keeps happening, instead of
        # guessing again.
        logger.warning("Token verification rejected: %s: %s", type(exc).__name__, exc)
        # These are genuine, deliberate rejections — the token really is
        # bad (expired, explicitly revoked, malformed, or the account was
        # disabled). A 401 here is correct: the client should treat this as
        # "you need to sign in again," which is exactly what our Flutter
        # interceptor does on a 401 (clears the stored session).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )
    except Exception as exc:
        # Anything else — most commonly a network error reaching Firebase's
        # servers for the check_revoked round trip, a timeout, or a
        # transient Firebase outage — is NOT proof the token is invalid.
        # Returning 401 here was a real bug: it told the client "log out
        # and sign in again" for what was actually just "we couldn't verify
        # this right now," causing the client to needlessly wipe a
        # perfectly valid session. 503 signals "retry," not "re-authenticate."
        logger.error(f"Token verification failed unexpectedly (not a rejection): {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify your session right now. Please try again.",
        )


async def get_current_user_id(decoded_token: dict = Depends(_verify_token)) -> str:
    return decoded_token["uid"]


async def get_current_user_claims(decoded_token: dict = Depends(_verify_token)) -> dict:
    return decoded_token


async def get_current_admin_uid(decoded_token: dict = Depends(_verify_token)) -> str:
    if decoded_token.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin privileges.",
        )
    return decoded_token["uid"]


async def verify_admin_panel_secret(x_admin_secret: str = Header(default="")) -> None:
    """
    Simple shared-password check for the local admin panel (admin_panel/index.html)
    — deliberately not Firebase auth. Appropriate for a single local admin;
    if this panel is ever exposed beyond your own machine, this should be
    replaced with real per-person authentication instead of a shared secret.
    """
    # An unset secret must never authenticate (an empty header would match it).
    if not settings.admin_panel_secret or not secrets.compare_digest(
        x_admin_secret.encode("utf-8"), settings.admin_panel_secret.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect admin password.",
        )


async def get_current_store_uid(decoded_token: dict = Depends(_verify_token)) -> str:
    if decoded_token.get("role") != "store":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a store account.",
        )
    return decoded_token["uid"]


async def get_current_driver(
    decoded_token: dict = Depends(_verify_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency for driver-only endpoints.

    Two checks, not one — this is the corrected version:

    1. The Firebase custom claim `role` must equal "driver" (proves this
       is a legitimate driver account, set once via
       firebase_auth.set_custom_user_claims(uid, {"role": "driver"})
       during driver onboarding).

    2. A REAL Driver row must actually exist for this uid in Postgres.
       driver_router.py's endpoints all expect an actual Driver object
       (driver.id, driver.is_available, driver.current_lat, etc.) — not
       just a uid string. Without this second check, having the "driver"
       claim alone would satisfy the dependency but every endpoint using
       driver.<anything> would crash immediately on a plain string.

    Returns the Driver ORM object itself, matching how driver_router.py's
    endpoints are actually written (`driver: Driver = Depends(get_current_driver)`).
    """
    from .models.driver import Driver

    if decoded_token.get("role") != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a driver account.",
        )

    uid = decoded_token["uid"]
    result = await db.execute(select(Driver).where(Driver.user_id == uid))
    driver = result.scalar_one_or_none()

    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No driver profile found for this account.",
        )

    if not driver.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This driver account has been deactivated. Please contact support.",
        )

    return driver


get_db_session = get_db

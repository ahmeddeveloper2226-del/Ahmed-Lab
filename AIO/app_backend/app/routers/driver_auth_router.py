"""
Driver login — deliberately NOT the same flow as customer phone login.

Customers verify their phone via Firebase's client-side OTP flow. Drivers
do not: per the product decision, every driver account is created manually
by an admin after an in-person interview (see admin_router.py), so simply
proving "I know this phone number" is not how we establish trust here —
the trust was already established at onboarding time. A driver logging in
just needs to identify WHICH pre-approved account is theirs.

Flow:
  1. Admin creates the driver (admin_router.py) — Firebase user + Postgres
     User + Driver rows, custom claim role="driver" already set.
  2. Driver app calls POST /driver/auth/login with their phone number.
  3. If a matching, active driver account exists, we mint a Firebase
     "custom token" for that uid and hand it back.
  4. The driver app signs in with that token via Firebase client SDK's
     signInWithCustomToken() — from that point on it's a completely normal
     Firebase-authenticated session, and every existing dependency
     (get_current_driver, etc.) keeps working unchanged.

Rate limiting matters more here than on most endpoints, since this is an
unauthenticated, no-OTP lookup keyed only on phone number — see the
limiter decorator below.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_session
from ..models.driver import Driver
from ..models.user import User
from ..rate_limiter import limiter
from ..schemas.driver_schemas import DriverLoginResponse, DriverPhoneLoginRequest

router = APIRouter()
logger = logging.getLogger("wasla.driver_auth")


@router.post("/login", response_model=DriverLoginResponse)
@limiter.limit("10/minute")
async def driver_login(
    request: Request,
    payload: DriverPhoneLoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await db.execute(
            select(User, Driver)
            .join(Driver, Driver.user_id == User.id)
            .where(User.phone_number == payload.phone_number)
        )
        row = result.first()
    except SQLAlchemyError as e:
        logger.error("Driver login lookup failed for phone_number=%s: %s", payload.phone_number, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not sign you in right now. Please try again.",
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No driver account found for this phone number. "
                   "Please contact support to be onboarded.",
        )

    user, driver = row

    if not driver.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This driver account has been deactivated. Please contact support.",
        )

    try:
        custom_token = firebase_auth.create_custom_token(user.id)
    except Exception as exc:
        logger.error("Failed to mint custom token for driver uid=%s: %s", user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not sign you in right now. Please try again.",
        )

    # create_custom_token returns bytes — decode for a clean JSON string field.
    token_str = custom_token.decode("utf-8") if isinstance(custom_token, bytes) else custom_token

    return DriverLoginResponse(
        custom_token=token_str,
        driver_id=driver.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
    )
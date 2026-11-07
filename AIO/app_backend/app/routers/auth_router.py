import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_claims, get_current_user_id, get_db_session
from ..models.user import User
from ..rate_limiter import limiter
from ..redis_client import redis_client
from ..schemas.auth_schemas import (
    SendEmailCodeRequest,
    SendEmailCodeResponse,
    UserSessionResponse,
    VerifyEmailCodeRequest,
    VerifyEmailCodeResponse,
)
from ..services.email_service import EmailSendError, send_verification_email

logger = logging.getLogger("wasla.auth")

router = APIRouter()

# --- Tunables for the email-code flow, named so the "why" is visible at a glance ---
EMAIL_CODE_TTL_SECONDS = 600          # code is valid for 10 minutes
EMAIL_CODE_RESEND_COOLDOWN_SECONDS = 60  # can't request a new code more than once/minute
EMAIL_CODE_MAX_ATTEMPTS = 5            # after 5 wrong guesses, the code is invalidated


def _email_code_key(uid: str) -> str:
    return f"email_verify:{uid}"


def _email_code_cooldown_key(uid: str) -> str:
    return f"email_verify_cooldown:{uid}"


@router.post("/session", response_model=UserSessionResponse)
async def create_or_get_session(
    db: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_current_user_claims),
):
    """
    Called once, right after the Flutter app signs in with Firebase — via
    phone OTP, Google, or Apple, it doesn't matter which. All three produce
    a Firebase ID token, verified identically by get_current_user_claims.

    Firebase embeds provider-verified data directly in the token itself:
    - Phone sign-in -> token contains a `phone_number` claim, already
      verified by the OTP check Firebase did client-side. We never see or
      handle the OTP itself — we just trust Firebase's own verification,
      exactly as intended.
    - Google/Apple sign-in -> token contains an `email` claim, already
      verified by that provider (no OTP involved at all for those).

    This endpoint's job: create the User row on first login, and keep
    phone_number/email in sync with whatever Firebase's token says is
    verified — every single call, not just the first one. This matters
    because a user might add phone sign-in as a second method later; the
    next time they call /session, this keeps Postgres correctly in sync
    with Firebase's own source of truth, without ever handling a raw OTP
    ourselves.
    """
    uid = claims["uid"]
    verified_phone = claims.get("phone_number")
    # Google/Apple only count as "email verified" here if Firebase itself
    # marked the token's email as verified — never trust an unverified
    # email claim as if it were confirmed.
    verified_email = claims.get("email") if claims.get("email_verified") else None

    try:
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                id=uid,
                phone_number=verified_phone,
                email=verified_email,
                email_verified=verified_email is not None,
            )
            db.add(user)
            logger.info(f"Created new user row for uid={uid}")
        else:
            # Keep existing verified fields in sync on every login, without
            # ever downgrading a value that's already set to something new
            # missing from this particular token (e.g. a phone-login token
            # won't carry an email claim — that's fine, don't erase it).
            if verified_phone and user.phone_number != verified_phone:
                user.phone_number = verified_phone
            if verified_email and not user.email_verified:
                user.email = verified_email
                user.email_verified = True

        await db.commit()
        await db.refresh(user)

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create/fetch session for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not complete sign-in right now. Please try again.",
        )

    return user


@router.post("/email/send-code", response_model=SendEmailCodeResponse)
@limiter.limit("5/minute")
async def send_email_verification_code(
    request: Request,
    payload: SendEmailCodeRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Sends a 6-digit code to the given email for the currently authenticated
    user to verify ownership of that address.

    Two layers of abuse protection, deliberately different from each other:
    - @limiter.limit("5/minute") — IP-based, stops one machine hammering
      this endpoint across many accounts.
    - The Redis cooldown below — PER-ACCOUNT, stops a single compromised or
      malicious account spamming an inbox even from many different IPs
      (e.g. a botnet). Both matter; neither replaces the other.
    """
    # Per-account cooldown check — independent of the IP-based rate limit above.
    cooldown_key = _email_code_cooldown_key(uid)
    if await redis_client.get(cooldown_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait before requesting another code.",
        )

    # Reject if this email is already verified on a DIFFERENT account —
    # prevents two accounts silently claiming the same email address.
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        existing = result.scalar_one_or_none()
        if existing is not None and existing.id != uid and existing.email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already in use by another account.",
            )
    except SQLAlchemyError as e:
        logger.error(f"Failed to check email uniqueness for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not process this request right now. Please try again.",
        )

    # secrets.randbelow — cryptographically secure, unlike the plain
    # `random` module, which must never be used for anything
    # security-sensitive like a verification code.
    code = f"{secrets.randbelow(1_000_000):06d}"

    code_data = {"code": code, "email": payload.email, "attempts": 0}

    try:
        await redis_client.set(_email_code_key(uid), json.dumps(code_data), ex=EMAIL_CODE_TTL_SECONDS)
        await redis_client.set(cooldown_key, "1", ex=EMAIL_CODE_RESEND_COOLDOWN_SECONDS)
    except Exception as e:
        logger.error(f"Redis failure while storing email code for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send verification code right now. Please try again.",
        )

    try:
        await send_verification_email(payload.email, code)
    except EmailSendError as e:
        logger.error(f"Email provider failed for uid={uid}: {e}")
        # Roll back the Redis state we just wrote — no point leaving a code
        # active that the user never actually received.
        await redis_client.delete(_email_code_key(uid))
        await redis_client.delete(cooldown_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Please try again shortly.",
        )

    return SendEmailCodeResponse(
        message=f"A verification code was sent to {payload.email}.",
        expires_in_seconds=EMAIL_CODE_TTL_SECONDS,
    )


@router.post("/email/verify-code", response_model=VerifyEmailCodeResponse)
@limiter.limit("10/minute")
async def verify_email_verification_code(
    request: Request,
    payload: VerifyEmailCodeRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Verifies the code sent by send_email_verification_code. Tracks attempts
    IN THE STORED RECORD ITSELF (not just via the rate limiter) so that the
    attempt count survives correctly even if the code is checked from
    different requests/IPs — the rate limiter alone would not catch a slow,
    distributed brute-force attempt against one specific code.
    """
    key = _email_code_key(uid)
    raw = await redis_client.get(key)

    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new one.",
        )

    code_data = json.loads(raw)

    if code_data["attempts"] >= EMAIL_CODE_MAX_ATTEMPTS:
        await redis_client.delete(key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many incorrect attempts. Please request a new code.",
        )

    if payload.code != code_data["code"]:
        code_data["attempts"] += 1
        # Preserve the remaining TTL rather than resetting it — an attacker
        # shouldn't be able to extend their guessing window just by guessing wrong.
        remaining_ttl = await redis_client.ttl(key)
        await redis_client.set(key, json.dumps(code_data), ex=max(remaining_ttl, 1))

        attempts_left = EMAIL_CODE_MAX_ATTEMPTS - code_data["attempts"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code. {attempts_left} attempt(s) remaining.",
        )

    # Correct code — commit the email to the real User row.
    try:
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please sign in again.",
            )

        user.email = code_data["email"]
        user.email_verified = True
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to save verified email for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save your verified email right now. Please try again.",
        )

    await redis_client.delete(key)

    return VerifyEmailCodeResponse(email=code_data["email"], email_verified=True)
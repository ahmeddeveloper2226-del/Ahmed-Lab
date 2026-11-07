import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.address import Address
from ..models.user import User
from ..schemas.profile_schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)

logger = logging.getLogger("wasla.profile")

router = APIRouter()


async def _get_owned_address_or_404(db: AsyncSession, address_id: str, uid: str) -> Address:
    """
    Shared helper for every endpoint below that touches a SPECIFIC address.
    This is the ownership-check pattern flagged as mandatory back when we
    discussed database security — every single-resource-by-id lookup in
    this app must confirm the resource actually belongs to the calling
    user, not just that the user is logged in. Centralized here so every
    address endpoint uses the exact same check, rather than each one
    reimplementing it slightly differently (and potentially missing it).
    """
    result = await db.execute(select(Address).where(Address.id == address_id))
    address = result.scalar_one_or_none()

    if address is None or address.user_id != uid:
        # Deliberately the SAME error for "doesn't exist" and "exists but
        # isn't yours" — returning a different message for the second case
        # would let an attacker enumerate other users' address IDs by
        # noticing which ones return a different error.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    return address


@router.get("/", response_model=UserProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch profile for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your profile right now. Please try again.",
        )

    if user is None:
        # Should be unreachable in practice — /auth/session always creates
        # the row first — but a valid token for a since-deleted user is a
        # real possible state, so it's handled explicitly rather than
        # crashing on a None attribute access below.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


@router.patch("/", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        user.full_name = payload.full_name
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update profile for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update your profile right now. Please try again.",
        )

    return user


@router.get("/addresses", response_model=list[AddressResponse])
async def list_my_addresses(
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(select(Address).where(Address.user_id == uid))
        addresses = result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Failed to list addresses for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load your addresses right now. Please try again.",
        )

    return addresses


@router.post("/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    payload: AddressCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        if payload.is_default:
            # Enforce "at most one default address" atomically, in the
            # same transaction as creating the new one — never leave two
            # addresses both marked default, even briefly.
            existing = await db.execute(
                select(Address).where(Address.user_id == uid, Address.is_default == True)  # noqa: E712
            )
            for addr in existing.scalars().all():
                addr.is_default = False

        address = Address(
            id=str(uuid.uuid4()),
            user_id=uid,
            label=payload.label,
            full_address=payload.full_address,
            lat=payload.lat,
            lng=payload.lng,
            is_default=payload.is_default,
        )
        db.add(address)
        await db.commit()
        await db.refresh(address)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create address for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save this address right now. Please try again.",
        )

    return address


@router.patch("/addresses/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: str,
    payload: AddressUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    address = await _get_owned_address_or_404(db, address_id, uid)

    try:
        if payload.label is not None:
            address.label = payload.label
        if payload.full_address is not None:
            address.full_address = payload.full_address
        if payload.lat is not None:
            address.lat = payload.lat
        if payload.lng is not None:
            address.lng = payload.lng

        await db.commit()
        await db.refresh(address)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update address {address_id} for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this address right now. Please try again.",
        )

    return address


@router.post("/addresses/{address_id}/set-default", response_model=AddressResponse)
async def set_default_address(
    address_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    address = await _get_owned_address_or_404(db, address_id, uid)

    try:
        existing = await db.execute(
            select(Address).where(Address.user_id == uid, Address.is_default == True)  # noqa: E712
        )
        for addr in existing.scalars().all():
            addr.is_default = False

        address.is_default = True
        await db.commit()
        await db.refresh(address)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to set default address {address_id} for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update your default address right now. Please try again.",
        )

    return address


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    address = await _get_owned_address_or_404(db, address_id, uid)

    try:
        await db.delete(address)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to delete address {address_id} for uid={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete this address right now. Please try again.",
        )
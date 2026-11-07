import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..dependencies import get_current_user_id, get_db_session
from ..models.prescription import Prescription, PrescriptionItem, PrescriptionStatus
from ..models.shop import Shop
from ..rate_limiter import limiter
from ..schemas.prescription_schemas import PrescriptionCreateRequest, PrescriptionResponse

logger = logging.getLogger("wasla.prescriptions")

router = APIRouter()


async def _load_owned_prescription(db: AsyncSession, prescription_id: str, user_id: str) -> Prescription:
    result = await db.execute(
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .options(selectinload(Prescription.items).selectinload(PrescriptionItem.product))
    )
    prescription = result.scalar_one_or_none()
    if prescription is None or prescription.user_id != user_id:
        # Same 404 either way — don't reveal whether a prescription ID
        # exists but belongs to someone else.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")
    return prescription


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_prescription(
    request: Request,
    payload: PrescriptionCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Registers a prescription photo (already uploaded to Cloudinary
    client-side — see cloudinary_upload_service.dart — this endpoint just
    records the resulting URL) against a specific pharmacy shop. The
    pharmacist picks it up from the store management panel next.
    """
    try:
        shop_result = await db.execute(select(Shop).where(Shop.id == payload.shop_id))
        shop = shop_result.scalar_one_or_none()
        if shop is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pharmacy not found.")
        if shop.category_id != "pharmacies":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prescriptions can only be sent to a pharmacy.",
            )

        prescription = Prescription(
            id=str(uuid.uuid4()),
            user_id=uid,
            shop_id=payload.shop_id,
            image_url=payload.image_url,
            status=PrescriptionStatus.pending_review,
        )
        db.add(prescription)
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create prescription for user={uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not submit your prescription right now. Please try again.",
        )

    return PrescriptionResponse.from_prescription(prescription, shop.name)


@router.get("/prescriptions", response_model=list[PrescriptionResponse])
async def list_my_prescriptions(
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Prescription, Shop)
        .join(Shop, Prescription.shop_id == Shop.id)
        .where(Prescription.user_id == uid)
        .options(selectinload(Prescription.items).selectinload(PrescriptionItem.product))
        .order_by(Prescription.created_at.desc())
    )
    rows = result.all()
    return [PrescriptionResponse.from_prescription(p, shop.name) for p, shop in rows]


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    prescription = await _load_owned_prescription(db, prescription_id, uid)
    shop_result = await db.execute(select(Shop).where(Shop.id == prescription.shop_id))
    shop = shop_result.scalar_one()
    return PrescriptionResponse.from_prescription(prescription, shop.name)


@router.delete("/prescriptions/{prescription_id}/items/{item_id}", response_model=PrescriptionResponse)
async def remove_prescription_item(
    prescription_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    The customer's "remove this medicine, it's too expensive" action.
    Marks the item excluded rather than deleting the row — see
    PrescriptionItem.included's docstring — so re-fetching the prescription
    afterward simply won't include it in what gets added to the cart.
    """
    prescription = await _load_owned_prescription(db, prescription_id, uid)

    if prescription.status != PrescriptionStatus.awaiting_customer_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription isn't ready for review yet.",
        )

    item = next((i for i in prescription.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    try:
        item.included = False
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to remove item={item_id} from prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not remove this item.")

    shop_result = await db.execute(select(Shop).where(Shop.id == prescription.shop_id))
    shop = shop_result.scalar_one()
    return PrescriptionResponse.from_prescription(prescription, shop.name)


@router.post("/prescriptions/{prescription_id}/approve", response_model=PrescriptionResponse)
@limiter.limit("20/minute")
async def approve_prescription(
    request: Request,
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    Marks the prescription approved. Deliberately does NOT create an Order
    or touch stock here — this app has no server-side cart (see
    cart_provider.dart), so the Flutter side adds the returned `items`
    (whichever still have included=true) into the local cart the exact
    same way any other "add to cart" tap does, and checkout proceeds
    through the normal multi-shop flow from there.
    """
    prescription = await _load_owned_prescription(db, prescription_id, uid)

    if prescription.status != PrescriptionStatus.awaiting_customer_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription isn't ready for approval yet.",
        )

    if not any(i.included for i in prescription.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one medicine must stay included to approve.",
        )

    try:
        prescription.status = PrescriptionStatus.approved
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to approve prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not approve this prescription.")

    shop_result = await db.execute(select(Shop).where(Shop.id == prescription.shop_id))
    shop = shop_result.scalar_one()
    return PrescriptionResponse.from_prescription(prescription, shop.name)


@router.post("/prescriptions/{prescription_id}/cancel", response_model=PrescriptionResponse)
async def cancel_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """Lets the customer back out at any point before approval — e.g. they
    uploaded the wrong photo, or don't want any of what the pharmacist
    proposed."""
    prescription = await _load_owned_prescription(db, prescription_id, uid)

    if prescription.status in (PrescriptionStatus.approved, PrescriptionStatus.cancelled):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This prescription can no longer be cancelled.")

    try:
        prescription.status = PrescriptionStatus.cancelled
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to cancel prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not cancel this prescription.")

    shop_result = await db.execute(select(Shop).where(Shop.id == prescription.shop_id))
    shop = shop_result.scalar_one()
    return PrescriptionResponse.from_prescription(prescription, shop.name)
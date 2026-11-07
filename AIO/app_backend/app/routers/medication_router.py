import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..models.product import Product
from ..rate_limiter import limiter
from ..schemas.medication_schemas import (
    CONDITIONS,
    ConditionOption,
    MedicationCreateRequest,
    MedicationResponse,
    MedicationUpdateRequest,
    ReorderMedicationResult,
)
from ..schemas.product_schemas import ProductResponse
from ..services import medication_service as service

logger = logging.getLogger("wasla.medications")

router = APIRouter()


@router.get("/conditions", response_model=list[ConditionOption])
async def get_conditions():
    return CONDITIONS


async def _to_response(db: AsyncSession, medication) -> MedicationResponse:
    product_response = None
    pharmacy_name = None
    if medication.product_id is not None:
        result = await db.execute(select(Product).where(Product.id == medication.product_id))
        product = result.scalar_one_or_none()
        if product is not None:
            product_response = ProductResponse.from_product(product)
            pharmacy_name = await service.get_pharmacy_name(db, medication.product_id)

    run_out_date, days_left, needs_refill_soon = service.compute_status(medication)
    return MedicationResponse(
        id=medication.id,
        product_id=medication.product_id,
        product=product_response,
        pharmacy_name=pharmacy_name,
        medicine_name=medication.medicine_name,
        condition=medication.condition,
        pack_quantity=medication.pack_quantity,
        daily_dosage=float(medication.daily_dosage),
        last_refill_date=medication.last_refill_date,
        reminder_days_before=medication.reminder_days_before,
        is_active=medication.is_active,
        run_out_date=run_out_date,
        days_left=days_left,
        needs_refill_soon=needs_refill_soon,
    )


@router.get("/", response_model=list[MedicationResponse])
async def get_my_medications(db: AsyncSession = Depends(get_db_session), uid: str = Depends(get_current_user_id)):
    medications = await service.list_medications(db, uid)
    return [await _to_response(db, m) for m in medications]


@router.post("/", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_medication(
    request: Request,
    payload: MedicationCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    """
    condition can be one of the predefined CONDITIONS ids (diabetes,
    high_blood_pressure, ...) OR any free-typed text the user entered for
    their own condition — we no longer require it to match the predefined
    list, only that it's non-empty (already enforced by the schema's
    min_length). The predefined ids just give a nicer emoji/label in the
    UI; a custom condition is stored and shown back exactly as typed.
    """
    medication = await service.create_medication(db, uid, payload)
    return await _to_response(db, medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: str,
    payload: MedicationUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    medication = await service.update_medication(db, uid, medication_id, payload)
    return await _to_response(db, medication)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: str, db: AsyncSession = Depends(get_db_session), uid: str = Depends(get_current_user_id)
):
    await service.delete_medication(db, uid, medication_id)


@router.post("/{medication_id}/reorder", response_model=ReorderMedicationResult)
@limiter.limit("20/minute")
async def reorder_medication(
    request: Request,
    medication_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.reorder_medication(db, uid, medication_id)

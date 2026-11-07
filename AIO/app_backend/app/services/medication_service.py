"""
Backs 'Refill Reminder' (Pharmacies-exclusive): a customer adds a chronic
medication once (pack size + daily dosage), and this module owns the run-
out date math shared by the API responses (medication_router.py) and the
background push worker (workers/refill_reminder_worker.py) — one formula,
used in exactly one place, so the "days left" shown in the app always
matches when the reminder actually fires.
"""
import logging
import math
import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.medication import Medication
from ..models.product import Product
from ..models.shop import Shop
from ..schemas.medication_schemas import (
    MedicationCreateRequest,
    MedicationUpdateRequest,
    ReorderMedicationResult,
)
from ..services.cart_service import add_product_to_raw_cart, get_raw_cart, save_raw_cart

logger = logging.getLogger("wasla.medications")

_REFILL_SOON_THRESHOLD_DAYS = 3  # matches the default reminder_days_before; "needs_refill_soon" badge in the app


def _new_id() -> str:
    return f"med_{uuid.uuid4().hex[:16]}"


def compute_run_out_date(last_refill_date: date, pack_quantity: int, daily_dosage: float) -> date:
    if daily_dosage <= 0:
        return last_refill_date
    days_supply = math.floor(pack_quantity / daily_dosage)
    return last_refill_date + timedelta(days=days_supply)


def compute_status(medication: Medication, today: date | None = None) -> tuple[date, int, bool]:
    today = today or date.today()
    run_out_date = compute_run_out_date(medication.last_refill_date, medication.pack_quantity, float(medication.daily_dosage))
    days_left = (run_out_date - today).days
    needs_refill_soon = days_left <= max(medication.reminder_days_before, _REFILL_SOON_THRESHOLD_DAYS)
    return run_out_date, days_left, needs_refill_soon


async def create_medication(db: AsyncSession, uid: str, payload: MedicationCreateRequest) -> Medication:
    # Required, and must actually be a pharmacy product — this is what
    # "connected to a specific pharmacy" means concretely: product.shop_id
    # IS that pharmacy, so a refill can genuinely be auto-added to the
    # cart from that exact shop when the reminder fires, not just tracked
    # as a name with nowhere real to reorder from.
    result = await db.execute(
        select(Product).join(Shop, Product.shop_id == Shop.id).where(Product.id == payload.product_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "الدواء غير موجود في الكتالوج.")

    shop_result = await db.execute(select(Shop).where(Shop.id == product.shop_id))
    shop = shop_result.scalar_one_or_none()
    if shop is None or shop.category_id != "pharmacies":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "لازم تختار دواء من صيدلية فعلية.")

    medication = Medication(
        id=_new_id(),
        user_id=uid,
        product_id=payload.product_id,
        medicine_name=payload.medicine_name,
        condition=payload.condition,
        pack_quantity=payload.pack_quantity,
        daily_dosage=payload.daily_dosage,
        last_refill_date=payload.last_refill_date or date.today(),
        reminder_days_before=payload.reminder_days_before,
    )
    db.add(medication)
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create medication for uid=%s: %s", uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذرت إضافة الدواء الآن.")
    await db.refresh(medication)
    return medication


async def get_pharmacy_name(db: AsyncSession, product_id: str | None) -> str | None:
    if product_id is None:
        return None
    try:
        result = await db.execute(
            select(Shop.name).join(Product, Product.shop_id == Shop.id).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to look up pharmacy name for product_id=%s: %s", product_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل بيانات الدواء الآن.")


async def list_medications(db: AsyncSession, uid: str) -> list[Medication]:
    try:
        result = await db.execute(
            select(Medication).where(Medication.user_id == uid).order_by(Medication.created_at.desc())
        )
        return list(result.scalars().all())
    except SQLAlchemyError as e:
        logger.error("Failed to list medications for uid=%s: %s", uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل الأدوية الآن.")


async def _get_owned(db: AsyncSession, uid: str, medication_id: str) -> Medication:
    try:
        result = await db.execute(select(Medication).where(Medication.id == medication_id))
        medication = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to look up medication_id=%s for uid=%s: %s", medication_id, uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل الدواء الآن.")
    if medication is None or medication.user_id != uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "هذا الدواء غير موجود.")
    return medication


async def update_medication(
    db: AsyncSession, uid: str, medication_id: str, payload: MedicationUpdateRequest
) -> Medication:
    medication = await _get_owned(db, uid, medication_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medication, field, value)
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update medication_id=%s for uid=%s: %s", medication_id, uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر حفظ التعديل الآن.")
    await db.refresh(medication)
    return medication


async def delete_medication(db: AsyncSession, uid: str, medication_id: str) -> None:
    medication = await _get_owned(db, uid, medication_id)
    try:
        await db.delete(medication)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete medication_id=%s for uid=%s: %s", medication_id, uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر حذف الدواء الآن.")


async def reorder_medication(db: AsyncSession, uid: str, medication_id: str) -> ReorderMedicationResult:
    """
    'Reorder with a single tap' — an explicit, customer-initiated action
    (the button in the app), distinct from the automatic add-to-cart the
    worker does when a reminder fires (see auto_add_to_cart_for_reminder
    below). Because tapping this means "I'm getting this refill right
    now," it resets last_refill_date to today and clears the reminder
    snapshot immediately — unlike the automatic path, which deliberately
    leaves last_refill_date untouched until the customer actually
    confirms the order.
    """
    medication = await _get_owned(db, uid, medication_id)

    try:
        added_to_cart = False
        message = "الدواء غير متوفر حاليًا في الصيدلية."
        if medication.product_id is not None:
            result = await db.execute(select(Product).where(Product.id == medication.product_id))
            product = result.scalar_one_or_none()
            if product is not None and product.stock_quantity > 0:
                raw_cart = await get_raw_cart(uid)
                add_product_to_raw_cart(raw_cart, product, 1)
                await save_raw_cart(uid, raw_cart)
                added_to_cart = True
                message = "تمت إضافة الدواء للسلة."

        medication.last_refill_date = date.today()
        medication.last_reminded_for_run_out_date = None
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to reorder medication_id=%s for uid=%s: %s", medication_id, uid, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إعادة الطلب الآن، حاول مرة أخرى.")
    await db.refresh(medication)

    run_out_date, _, _ = compute_status(medication)

    return ReorderMedicationResult(
        added_to_cart=added_to_cart,
        new_last_refill_date=medication.last_refill_date,
        new_run_out_date=run_out_date,
        message=message,
    )


async def auto_add_to_cart_for_reminder(db: AsyncSession, medication: Medication) -> bool:
    """
    Called by workers/refill_reminder_worker.py right before it sends the
    push: adds one pack of the linked pharmacy product straight to the
    customer's cart, so by the time they open the notification the refill
    is already sitting there and all that's left is for THEM to confirm
    the order — not to hunt the item down and add it themselves.

    Deliberately does NOT touch last_refill_date or
    last_reminded_for_run_out_date — those represent "the customer
    actually started a new pack," which hasn't happened yet just because
    it's in the cart. That reset still only happens via the explicit
    reorder_medication() action (or, implicitly, once they check out —
    left as a future hook into the checkout flow) so the run-out math
    doesn't drift ahead of reality.
    """
    if medication.product_id is None:
        return False
    result = await db.execute(select(Product).where(Product.id == medication.product_id))
    product = result.scalar_one_or_none()
    if product is None:
        return False

    raw_cart = await get_raw_cart(medication.user_id)
    if not add_product_to_raw_cart(raw_cart, product, 1):
        return False
    await save_raw_cart(medication.user_id, raw_cart)
    return True

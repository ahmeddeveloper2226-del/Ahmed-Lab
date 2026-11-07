from datetime import date, datetime

from pydantic import BaseModel, Field

from .product_schemas import ProductResponse


class ConditionOption(BaseModel):
    id: str
    label_ar: str
    emoji: str


CONDITIONS: list[ConditionOption] = [
    ConditionOption(id="diabetes", label_ar="السكري", emoji="💉"),
    ConditionOption(id="high_blood_pressure", label_ar="ضغط الدم المرتفع", emoji="❤️"),
    ConditionOption(id="heart_disease", label_ar="أمراض القلب", emoji="🫀"),
    ConditionOption(id="thyroid", label_ar="اضطرابات الغدة الدرقية", emoji="🦋"),
    ConditionOption(id="high_cholesterol", label_ar="ارتفاع الكوليسترول", emoji="🩸"),
    ConditionOption(id="other", label_ar="أخرى", emoji="💊"),
]
_VALID_CONDITION_IDS = {c.id for c in CONDITIONS}


class MedicationCreateRequest(BaseModel):
    # Required — every reminder must be tied to a real pharmacy product so
    # a refill can actually be added to the cart automatically when the
    # reminder fires (see medication_service.auto_add_to_cart_for_reminder).
    # A medication with nowhere real to reorder from can't fulfill that.
    product_id: str = Field(..., min_length=1)
    medicine_name: str = Field(..., min_length=1, max_length=150)
    condition: str = Field(default="other", min_length=1, max_length=100)
    pack_quantity: int = Field(..., ge=1, le=1000)
    daily_dosage: float = Field(..., gt=0, le=50)
    # Defaults to today — when the customer actually started this pack.
    last_refill_date: date | None = None
    reminder_days_before: int = Field(default=3, ge=0, le=30)


class MedicationUpdateRequest(BaseModel):
    medicine_name: str | None = Field(None, min_length=1, max_length=150)
    condition: str | None = Field(None, min_length=1, max_length=100)
    pack_quantity: int | None = Field(None, ge=1, le=1000)
    daily_dosage: float | None = Field(None, gt=0, le=50)
    reminder_days_before: int | None = Field(None, ge=0, le=30)
    is_active: bool | None = None


class MedicationResponse(BaseModel):
    id: str
    product_id: str | None
    product: ProductResponse | None
    pharmacy_name: str | None
    medicine_name: str
    condition: str
    pack_quantity: int
    daily_dosage: float
    last_refill_date: date
    reminder_days_before: int
    is_active: bool

    # Computed, not stored — the single source of truth for "when does
    # this run out" and "should the app show a refill-soon badge", so the
    # math lives in exactly one place (see medication_service.py) instead
    # of being re-derived slightly differently client-side.
    run_out_date: date
    days_left: int
    needs_refill_soon: bool

    class Config:
        from_attributes = True


class ReorderMedicationResult(BaseModel):
    added_to_cart: bool
    new_last_refill_date: date
    new_run_out_date: date
    message: str

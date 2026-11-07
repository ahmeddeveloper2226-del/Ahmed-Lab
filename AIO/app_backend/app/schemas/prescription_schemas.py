from datetime import datetime

from pydantic import BaseModel, Field


class PrescriptionCreateRequest(BaseModel):
    shop_id: str = Field(..., min_length=1, max_length=64)
    image_url: str = Field(..., min_length=1, max_length=500)


class PrescriptionItemResponse(BaseModel):
    id: str
    product_id: str
    name: str
    price: float
    quantity: int
    included: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_item(cls, item) -> "PrescriptionItemResponse":
        """item is a PrescriptionItem ORM row with `product` eager-loaded.
        Every item is now guaranteed catalog-linked (see PrescriptionItem's
        docstring), so name/price always come live from the Product —
        never stale, never a hand-typed guess."""
        return cls(
            id=item.id,
            product_id=item.product_id,
            name=item.product.name,
            price=float(item.product.price),
            quantity=item.quantity,
            included=item.included,
        )


class PrescriptionResponse(BaseModel):
    id: str
    shop_id: str
    shop_name: str
    image_url: str
    status: str
    submitted_at: datetime | None
    created_at: datetime
    items: list[PrescriptionItemResponse]

    class Config:
        from_attributes = True

    @classmethod
    def from_prescription(cls, p, shop_name: str) -> "PrescriptionResponse":
        return cls(
            id=p.id,
            shop_id=p.shop_id,
            shop_name=shop_name,
            image_url=p.image_url,
            status=p.status.value,
            submitted_at=p.submitted_at,
            created_at=p.created_at,
            items=[PrescriptionItemResponse.from_item(i) for i in p.items],
        )


# --- Store management panel (pharmacist) side --------------------------------

class PrescriptionItemCreateRequest(BaseModel):
    """Always a real catalog product now — see PrescriptionItem's
    docstring for why the old freeform name/price path was removed."""
    product_id: str = Field(..., min_length=1, max_length=64)
    quantity: int = Field(1, ge=1, le=50)


class PrescriptionItemUpdateRequest(BaseModel):
    """Lets the pharmacist correct a quantity mistake without deleting and
    re-adding the item — same pending_review-only restriction as add/remove."""
    quantity: int = Field(..., ge=1, le=50)


class PrescriptionForPharmacyResponse(BaseModel):
    """Same shape as PrescriptionResponse but without shop_name (the
    pharmacist already knows which shop they're logged into) — kept as a
    separate schema so the two sides can diverge later without entangling."""
    id: str
    user_id: str
    image_url: str
    status: str
    submitted_at: datetime | None
    created_at: datetime
    items: list[PrescriptionItemResponse]

    class Config:
        from_attributes = True

    @classmethod
    def from_prescription(cls, p) -> "PrescriptionForPharmacyResponse":
        return cls(
            id=p.id,
            user_id=p.user_id,
            image_url=p.image_url,
            status=p.status.value,
            submitted_at=p.submitted_at,
            created_at=p.created_at,
            items=[PrescriptionItemResponse.from_item(i) for i in p.items],
        )
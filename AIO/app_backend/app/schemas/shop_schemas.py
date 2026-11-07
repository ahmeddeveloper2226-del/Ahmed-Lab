from pydantic import BaseModel, Field


class ShopResponse(BaseModel):
    id: str
    category_id: str
    subcategory_id: str | None
    name: str
    description: str | None
    logo_url: str | None
    rating: float
    lat: float | None
    lng: float | None

    class Config:
        from_attributes = True


class ShopCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    category_id: str = Field(..., min_length=1, max_length=64)
    subcategory_id: str | None = Field(None, min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)


class ShopUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics: only provided fields change.
    Deliberately excludes category_id/id, which shouldn't change after
    creation without a deliberate admin migration path."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    # Explicit sentinel, not just Optional: PATCH omits this key entirely to
    # mean "leave unchanged", but a shop legitimately needs a way to clear
    # subcategory_id back to null too (e.g. re-tagging or an admin mistake).
    # Callers that want to clear it should send the literal string "" —
    # the router below treats that as "set to NULL", any other value as the
    # new subcategory_id, and an omitted field as "no change" (Pydantic's
    # normal exclude_unset behavior).
    subcategory_id: str | None = Field(None, min_length=0, max_length=64)
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)
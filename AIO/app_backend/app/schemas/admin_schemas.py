from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateDriverRequest(BaseModel):
    """Body for POST /admin/drivers.

    No password/OTP field on purpose — per the product decision, drivers are
    onboarded in person (an interview, per the business process) and the
    admin creates the account on their behalf here. The driver later logs
    in with just their phone number (see driver_auth_router.py); there is
    deliberately no self-serve driver signup endpoint.
    """
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., examples=["+201234567890"])


class DriverAdminResponse(BaseModel):
    driver_id: str
    user_id: str
    full_name: str | None
    phone_number: str | None
    is_active: bool
    is_available: bool
    current_lat: float | None
    current_lng: float | None
    active_order_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateDriverActiveRequest(BaseModel):
    is_active: bool


class AdminOrderResponse(BaseModel):
    id: str
    checkout_group_id: str
    shop_id: str
    shop_name: str
    customer_name: str | None
    driver_name: str | None
    status: str
    payment_status: str
    total: float
    commission_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Store panel — shop and product management (see store_panel/index.html)
# ---------------------------------------------------------------------------

class AdminShopResponse(BaseModel):
    id: str
    category_id: str
    category_name: str | None
    subcategory_id: str | None
    subcategory_name: str | None
    name: str
    description: str | None
    logo_url: str | None
    rating: float
    lat: float | None
    lng: float | None
    product_count: int

    model_config = {"from_attributes": True}


class AdminShopCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    category_id: str = Field(..., min_length=1, max_length=64)
    subcategory_id: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)
    # Required for every newly created shop — backs the store management
    # panel login (shop_id + this password, see store_management_router.py).
    # Never echoed back in AdminShopResponse.
    password: str = Field(..., min_length=4, max_length=100)


class AdminShopUpdateRequest(BaseModel):
    """PATCH semantics — only provided fields change. subcategory_id follows
    the same "" == clear-to-null convention as ShopUpdateRequest."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    subcategory_id: str | None = Field(None, min_length=0, max_length=64)
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)


class AdminProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    subcategory_id: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    # Optional discounted price — set this (lower than price) to list the
    # product on the AIO Fast Picks rails (home, its category, and its
    # shop's own page). Left unset, the product behaves exactly as before.
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int = Field(0, ge=0)
    # Free-form per-category details (see app/constants/product_attributes.py)
    attributes: dict[str, Any] | None = None


class AdminProductUpdateRequest(BaseModel):
    """PATCH semantics — only provided fields change. subcategory_id
    follows the "" == clear-to-null convention (see AdminShopUpdateRequest).
    Sending sale_price: null explicitly clears an existing discount
    (removes the product from the Fast Picks rails); omitting the field
    leaves it untouched."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    subcategory_id: str | None = Field(None, min_length=0, max_length=64)
    price: float | None = Field(None, gt=0)
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int | None = Field(None, ge=0)
    attributes: dict[str, Any] | None = None


class AdminCategoryResponse(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}

class AdminSubcategoryResponse(BaseModel):
    id: str
    category_id: str
    name: str
    sort_order: int

    model_config = {"from_attributes": True}
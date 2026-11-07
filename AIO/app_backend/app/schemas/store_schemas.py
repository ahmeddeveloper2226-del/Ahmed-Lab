from typing import Any

from pydantic import BaseModel, Field
from datetime import datetime

from ..models.order import OrderStatus


class MyShopResponse(BaseModel):
    id: str
    category_id: str
    name: str
    description: str | None
    logo_url: str | None
    rating: float
    lat: float | None
    lng: float | None

    class Config:
        from_attributes = True


class MyShopUpdateRequest(BaseModel):
    """PATCH semantics — only provided fields change. A store owner may
    edit their own name/description/logo/location, but not category_id
    (that's an admin-level change, see shops_router.py)."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)


class StoreProductCreateRequest(BaseModel):
    """Body for POST /store/products — lets a store owner add a NEW
    product to their own shop directly, instead of relying on an admin to
    do it via products_router.py."""
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    # Optional discounted price — set this to list the product on the AIO
    # Fast Picks rails (home, its category, and the shop's own page). Left
    # unset, the product behaves exactly as before.
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int = Field(0, ge=0)
    # Free-form per-category details (see app/constants/product_attributes.py)
    attributes: dict[str, Any] | None = None


class StoreProductUpdateRequest(BaseModel):
    """PATCH semantics — only provided fields change. Sending
    `sale_price: null` explicitly clears an existing discount (takes the
    product off the Fast Picks rails); omitting the field leaves it as-is."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int | None = Field(None, ge=0)
    attributes: dict[str, Any] | None = None


class StockUpdateRequest(BaseModel):
    stock_quantity: int = Field(..., ge=0)


class IncomingOrderItemResponse(BaseModel):
    product_id: str
    quantity: int
    price_at_purchase: float


class IncomingOrderResponse(BaseModel):
    id: str
    status: OrderStatus
    total: float
    created_at: datetime
    items: list[IncomingOrderItemResponse]

    class Config:
        from_attributes = True


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus
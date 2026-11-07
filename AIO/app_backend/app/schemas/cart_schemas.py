from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    product_id: str
    shop_id: str
    shop_name: str
    name: str
    price: float
    quantity: int
    subtotal: float


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: float


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=0)  # 0 means "remove this item"
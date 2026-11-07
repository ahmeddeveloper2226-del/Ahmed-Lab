from typing import Any

from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    id: str
    shop_id: str
    subcategory_id: str | None
    name: str
    description: str | None
    image_url: str | None
    price: float
    sale_price: float | None
    stock_quantity: int

    # Free-form per-category details (grocery weight/expiry, clothes
    # size/colour, food add-on choices, electronics company/colour,
    # pharmacy dosage, etc). See app/constants/product_attributes.py for
    # the schema each key follows per shop category. None/omitted keys
    # simply aren't shown — the app only renders whatever is present.
    attributes: dict[str, Any] | None = None

    # Computed, not a real column — the Flutter app should key its "Add to
    # Cart" button availability off this, not off stock_quantity > 0 itself,
    # so the threshold logic lives in exactly one place (here) rather than
    # being re-implemented client-side too.
    in_stock: bool = False

    # Computed — true only when sale_price is set AND actually lower than
    # price. This is the single source of truth for "does this product
    # belong on an AIO Fast Picks rail," kept in one place rather than
    # re-derived with slightly different logic on the client.
    is_on_sale: bool = False

    # Computed — whole-number percentage off, for the "fire" sale badge.
    # None when not on sale, so the client never has to guess whether 0
    # means "no discount" or "not on sale at all."
    discount_percent: int | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_product(cls, product) -> "ProductResponse":
        price = float(product.price)
        sale_price = float(product.sale_price) if product.sale_price is not None else None
        is_on_sale = sale_price is not None and sale_price < price
        discount_percent = round((1 - (sale_price / price)) * 100) if is_on_sale and price > 0 else None

        return cls(
            id=product.id,
            shop_id=product.shop_id,
            subcategory_id=product.subcategory_id,
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            price=price,
            sale_price=sale_price,
            stock_quantity=product.stock_quantity,
            in_stock=product.stock_quantity > 0,
            is_on_sale=is_on_sale,
            discount_percent=discount_percent,
            attributes=product.attributes,
        )


class ProductCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    subcategory_id: str | None = Field(None, min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int = Field(0, ge=0)
    attributes: dict[str, Any] | None = None


class ProductUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics: only provided fields change.
    subcategory_id follows the "" == clear-to-null convention used
    elsewhere (see ShopUpdateRequest) since Optional alone can't
    distinguish "omitted" from "explicitly cleared" in a PATCH body."""
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=2000)
    image_url: str | None = Field(None, max_length=500)
    subcategory_id: str | None = Field(None, min_length=0, max_length=64)
    price: float | None = Field(None, gt=0)
    # Explicitly sending sale_price: null clears the discount (product
    # leaves the Fast Picks rails) — omitting the field entirely leaves it
    # untouched, same PATCH semantics as every other field here.
    sale_price: float | None = Field(None, gt=0)
    stock_quantity: int | None = Field(None, ge=0)
    # Sending attributes: {} clears every attribute; omitting the field
    # leaves existing attributes untouched — same PATCH semantics as the
    # rest of this request.
    attributes: dict[str, Any] | None = Field(None)
    is_active: bool | None = Field(None)


class CompleteLookSlot(BaseModel):
    """One outfit-completing suggestion — see complete_look_service.py."""
    slot: str
    slot_label: str
    product: ProductResponse


class CompleteLookResponse(BaseModel):
    product_id: str
    suggestions: list[CompleteLookSlot]


class CompleteLookAddToCartRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=1, max_length=10)

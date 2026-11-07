from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Smart Shopping Lists
# ---------------------------------------------------------------------------

class ShoppingListItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(default=1, gt=0, le=1000)
    unit: str | None = Field(default=None, max_length=20)
    product_id: str | None = None


class ShoppingListItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: float | None = Field(default=None, gt=0, le=1000)
    unit: str | None = None
    is_checked: bool | None = None


class ShoppingListItemResponse(BaseModel):
    id: str
    name: str
    quantity: float
    unit: str | None
    is_checked: bool
    product_id: str | None

    class Config:
        from_attributes = True


class ShoppingListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    occasion: str = Field(default="custom", max_length=30)
    items: list[ShoppingListItemCreate] = Field(default_factory=list, max_length=200)


class ShoppingListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    occasion: str | None = Field(default=None, max_length=30)


class ShoppingListSummary(BaseModel):
    """Lightweight shape for the lists index screen — item count instead
    of the full items array, so opening 'My Lists' doesn't pull every
    line item of every list at once."""
    id: str
    name: str
    occasion: str
    item_count: int
    checked_count: int
    updated_at: datetime

    class Config:
        from_attributes = True


class ShoppingListResponse(BaseModel):
    id: str
    name: str
    occasion: str
    share_code: str
    items: list[ShoppingListItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddListToCartResult(BaseModel):
    added_count: int
    skipped_count: int
    skipped_names: list[str]


# ---------------------------------------------------------------------------
# AI Recipe Shopping
# ---------------------------------------------------------------------------

class RecipeParseRequest(BaseModel):
    dish_name: str = Field(..., min_length=1, max_length=120)
    servings: int = Field(default=4, ge=1, le=50)


class RecipeIngredientMatch(BaseModel):
    ingredient_name: str
    quantity_label: str  # e.g. "500 جم", "2 كوب" — human-readable, already scaled to servings
    product_id: str | None
    product_name: str | None
    shop_name: str | None
    price: float | None
    matched: bool


class RecipeParseResponse(BaseModel):
    dish_name: str
    servings: int
    ingredients: list[RecipeIngredientMatch]


class RecipeAddToCartRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=1, max_length=60)

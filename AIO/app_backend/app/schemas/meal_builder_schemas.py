from pydantic import BaseModel, Field

from .product_schemas import ProductResponse


class MealTypeOption(BaseModel):
    id: str
    label_ar: str
    emoji: str


# Fixed, small set — matches the six meal types the feature was scoped
# for. Kept as plain data (not a DB table) since these are a product
# decision, not something a store owner configures per shop.
MEAL_TYPES: list[MealTypeOption] = [
    MealTypeOption(id="healthy", label_ar="وجبة صحية", emoji="🥗"),
    MealTypeOption(id="family", label_ar="وجبة عائلية", emoji="👨‍👩‍👧‍👦"),
    MealTypeOption(id="gym", label_ar="وجبة الجيم", emoji="💪"),
    MealTypeOption(id="kids", label_ar="وجبة أطفال", emoji="🧒"),
    MealTypeOption(id="high_protein", label_ar="وجبة عالية البروتين", emoji="🍗"),
    MealTypeOption(id="spicy", label_ar="وجبة حارة", emoji="🌶️"),
]

_VALID_MEAL_TYPE_IDS = {m.id for m in MEAL_TYPES}


class BuildMealRequest(BaseModel):
    meal_type: str = Field(..., description="One of: " + ", ".join(sorted(_VALID_MEAL_TYPE_IDS)))
    # Only meaningfully used for 'family' (how many portions to scale
    # quantities for) but accepted for any meal type for a consistent API.
    party_size: int = Field(default=1, ge=1, le=15)


class MealBuilderItem(BaseModel):
    product: ProductResponse
    quantity: int
    reason: str


class BuildMealResponse(BaseModel):
    meal_type: str
    meal_title: str
    items: list[MealBuilderItem]
    total_price: float
    # False only when the shop itself has no food products at all —
    # distinct from "has a menu, but nothing suited this particular meal
    # type" (items == [] with has_menu == True). The two need different
    # messages to the customer: "this restaurant has no food listed yet"
    # vs. "nothing here fits a gym meal, try another type".
    has_menu: bool = True


class AddMealToCartRequest(BaseModel):
    items: list[dict] = Field(..., min_length=1, max_length=15)  # [{product_id, quantity}]


class AddMealToCartResult(BaseModel):
    added_count: int
    skipped_count: int


# ─────────────────────────────────────────────────────────────────────────
#  Cross-restaurant meal builder — same idea as the per-restaurant one
#  above, but instead of a fixed meal type + one restaurant's menu, the
#  customer writes free text describing what they want and Claude can pull
#  items from SEVERAL different restaurants to put the meal together.
#
#  This is the expensive version (a much bigger prompt covering up to 10
#  restaurants' menus instead of 1), so it's a deliberately separate,
#  more tightly rate-limited endpoint rather than a mode toggle on the
#  cheap per-restaurant one — see cross_restaurant_meal_builder_service.py.
# ─────────────────────────────────────────────────────────────────────────


class CrossRestaurantBuildMealRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=300)
    party_size: int = Field(default=1, ge=1, le=15)


class CrossRestaurantMealBuilderItem(BaseModel):
    product: ProductResponse
    quantity: int
    reason: str
    shop_id: str
    shop_name: str


class CrossRestaurantBuildMealResponse(BaseModel):
    meal_title: str
    items: list[CrossRestaurantMealBuilderItem]
    total_price: float
    restaurants_used: list[str]
    # False only when the search engine itself found no matching
    # restaurants at all — distinct from "found restaurants, but Claude
    # couldn't assemble a fitting meal from what they had in stock"
    # (items == [] with has_results == True), same split as has_menu above.
    has_results: bool = True

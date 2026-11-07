from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Checkout request / response
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    address_id: str

    # Passed through directly to Paymob's payment_keys endpoint.
    # Required fields: first_name, last_name, email, phone_number,
    # city, country, street, building, floor, apartment.
    # checkout_router validates these keys before calling paymob_service.
    billing_data: dict

    # Customer's explicit branch choice per branch-aware shop in the cart
    # (spec 1.1: "The customer selects Store -> Branch"), keyed by shop_id.
    # Sourced from GET /products/shops/{shop_id}/branches/delivery-options.
    # Optional and backward-compatible: any shop NOT in this dict falls
    # back to the existing automatic nearest-fulfilling-branch selection,
    # so old app builds that don't send this keep working unchanged.
    branch_selections: dict[str, str] | None = None


class BranchDeliveryOption(BaseModel):
    branch_id: str
    name: str
    address: str | None
    lat: float
    lng: float
    phone: str | None
    road_distance_km: float
    eta_minutes: int
    delivery_fee: float


class CheckoutResponse(BaseModel):
    checkout_group_id: str
    payment_url: str
    total: float = Field(description="Total in EGP, two decimal places")


# ---------------------------------------------------------------------------
# Order read schemas
# ---------------------------------------------------------------------------

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    price_at_purchase: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: str
    checkout_group_id: str
    shop_id: str
    shop_name: str | None
    shop_lat: float | None
    shop_lng: float | None
    status: str
    payment_status: str
    total: float
    commission_amount: float
    delivery_address: str | None
    delivery_lat: float | None
    delivery_lng: float | None
    # Driver's name only — NEVER their phone number. Contact happens through
    # the in-app chat/call (chat_router.py / realtime_ws_router.py), which is
    # the whole reason phone numbers are never exposed between customer and
    # driver in the first place.
    driver_name: str | None
    created_at: datetime
    items: list[OrderItemResponse]
    # Whether the customer has already reviewed this order — lets the
    # Flutter app show/hide the "Rate this order" action without a
    # separate round trip per order.
    has_review: bool = False

    # --- AIO delivery-architecture fields (spec 1.8/1.9) ------------------
    # Granular lifecycle stage — see models/delivery.py. Null for orders
    # from before this existed, or shops with no branch/tracking yet; the
    # Flutter app falls back to `status` alone in that case, same as today.
    delivery_stage: str | None = None
    # Exact branch fulfilling this order, when the shop is branch-aware.
    branch_id: str | None = None
    branch_name: str | None = None
    branch_lat: float | None = None
    branch_lng: float | None = None
    # Checkout-time snapshot (spec 1.6) vs the continuously-recalculated
    # value pushed over the tracking WebSocket once a driver is en route
    # (spec 1.9). The Customer App should prefer live_eta_minutes once it
    # starts receiving WebSocket updates, and fall back to eta_minutes
    # (or its own polling of this endpoint) before that.
    eta_minutes: int | None = None
    live_eta_minutes: int | None = None
    delivery_fee: float | None = None
    road_distance_km: float | None = None

    model_config = {"from_attributes": True}
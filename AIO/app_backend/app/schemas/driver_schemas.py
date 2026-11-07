from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DriverStatusUpdate(BaseModel):
    """Body for PATCH /driver/orders/{order_id}/status"""
    status: str = Field(
        ...,
        description="One of: preparing, out_for_delivery, delivered, cancelled",
        examples=["out_for_delivery"],
    )


class DeliveryStageUpdate(BaseModel):
    """Body for PATCH /driver/orders/{order_id}/delivery-stage — the
    granular AIO lifecycle (spec 1.8/2.x), separate from the coarser
    `status` field above. See models/delivery.py for the full stage list."""
    stage: str = Field(..., examples=["going_to_branch"])


class DeliveryFailureReport(BaseModel):
    """Body for POST /driver/orders/{order_id}/failure (spec 2.10)."""
    reason: str = Field(..., examples=["customer_unavailable"])
    notes: str | None = Field(None, max_length=500)


class LocationUpdate(BaseModel):
    """Body for POST /driver/location"""
    order_id: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    bearing: float | None = Field(None, ge=0.0, le=360.0, description="Heading in degrees")
    speed_kmh: float | None = Field(None, ge=0.0, description="Speed in km/h")


class AvailabilityUpdate(BaseModel):
    """Body for PATCH /driver/availability"""
    is_available: bool
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lng: float | None = Field(None, ge=-180.0, le=180.0)


class DriverOrderItemResponse(BaseModel):
    product_id: str
    quantity: int
    price_at_purchase: float


class DriverOrderResponse(BaseModel):
    """Represents an available or active order from the driver's perspective."""
    id: str
    checkout_group_id: str
    # All orders sharing this ID are part of the SAME delivery offer — one
    # driver, one trip, possibly several shops. Lets the driver app group
    # multiple order cards under one "accept/decline this delivery" action.
    delivery_group_id: str | None
    shop_id: str
    shop_name: str
    # Customer's name only — never their phone number, same rationale as
    # order_schemas.OrderResponse.driver_name on the customer side. Contact
    # happens through the in-app chat/call.
    customer_name: str | None
    # Store pickup location — the driver's first destination after accepting.
    shop_lat: float | None
    shop_lng: float | None
    # The EXACT branch fulfilling this order (spec 2.4: "The branch in the
    # delivery job must always be the exact branch associated with the
    # order") — null for shops with no branches, in which case shop_lat/
    # shop_lng above IS the pickup location, unchanged from before.
    branch_id: str | None = None
    branch_name: str | None = None
    branch_lat: float | None = None
    branch_lng: float | None = None
    branch_address: str | None = None
    branch_phone: str | None = None
    status: str
    # Granular AIO lifecycle stage (spec 1.8/2.x) — see models/delivery.py.
    # Null for orders created before this existed, or shops with no branch
    # (which don't get the granular stage tracking today).
    delivery_stage: str | None = None
    payment_status: str
    total: float
    # Delivery address for navigation — included so the driver can see
    # where they're going before accepting.
    delivery_address: str | None
    delivery_lat: float | None
    delivery_lng: float | None
    # Checkout-time delivery quote snapshot (spec 1.6).
    eta_minutes: int | None = None
    live_eta_minutes: int | None = None
    delivery_fee: float | None = None
    road_distance_km: float | None = None
    # Straight-line distance in km from the driver's current position to
    # this order's shop, when the driver's location was provided to the
    # available-orders endpoint. Null otherwise (e.g. for the "my active
    # orders" list, where this ranking doesn't apply).
    distance_km: float | None = None
    items: list[DriverOrderItemResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverPhoneLoginRequest(BaseModel):
    """Body for POST /driver/auth/login — no OTP: drivers are pre-registered
    by an admin (see admin_router.py), so a matching phone number alone is
    enough to prove identity here."""
    phone_number: str = Field(..., examples=["+201234567890"])


class DriverLoginResponse(BaseModel):
    """Returned by POST /driver/auth/login. custom_token is a Firebase
    custom token — the driver app signs in with it via Firebase client SDK's
    signInWithCustomToken(), after which everything else (Bearer ID tokens,
    get_current_driver, etc.) works exactly like any other Firebase user."""
    custom_token: str
    driver_id: str
    full_name: str | None
    phone_number: str | None
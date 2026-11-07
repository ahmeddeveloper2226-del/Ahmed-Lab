import enum
from datetime import datetime
 
from sqlalchemy import String, ForeignKey, Numeric, Integer, Enum, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.database import Base
from app.models.delivery import DeliveryStage, DeliveryProvider, DeliveryFailureReason

 
class OrderStatus(enum.Enum):
    pending = "pending"
    preparing = "preparing"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
 
 
class PaymentStatus(enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
 
 
class Order(Base):
    """
    One row per SHOP, not one row per checkout. A single cart checkout
    spanning 3 shops creates 3 Order rows here, all sharing the same
    checkout_group_id — that's how the customer's order history can still
    show "these 3 orders came from one checkout" without conflating shops.
    """
    __tablename__ = "orders"
 
    id: Mapped[str] = mapped_column(String, primary_key=True)
 
    # Links multiple per-shop Order rows back to a single checkout event.
    checkout_group_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
 
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    # Which physical branch fulfilled this order — null for shops that
    # don't use branches (the overwhelming majority, unaffected by this
    # field existing at all). Set at checkout time by order_service.py's
    # branch selection logic (see branch_service.py), and is what
    # branch_stock decrements actually happen against instead of the
    # product's own global stock_quantity, for shops that DO have branches.
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
 
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False
    )
 
    # This shop's subtotal for this order — NOT the whole cart's total.
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
 
    # Wasla's cut of this specific order, stored explicitly rather than
    # recomputed later — protects against the commission rate changing
    # in the future and silently altering historical order records.
    commission_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
 
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)

    # Groups this shop-order with the other shop-orders (from the SAME
    # checkout_group_id) that were clustered into one delivery zone — see
    # geo_utils.cluster_shops_by_zone. Every Order sharing a delivery_group_id
    # is offered to, accepted by, and carried by the SAME driver in ONE trip.
    # A checkout spanning shops in two different zones ends up with two
    # distinct delivery_group_id values, each getting its own driver.
    delivery_group_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Set the moment a driver is OFFERED this delivery group (driver_id is
    # set at the same time, but status stays `pending` — the driver hasn't
    # accepted yet). If this passes with the order still `pending`, the offer
    # timed out: driver_assignment_worker's sweep clears driver_id/this field
    # and offers the group to the next-nearest driver instead.
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
 
    delivery_address_id: Mapped[str | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)
 
    # Live-ish delivery coordinates snapshot, shown on the tracking map
    # alongside the WebSocket-streamed live position.
    delivery_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- AIO delivery-architecture fields (see models/delivery.py) --------
    # Granular operational stage, kept alongside `status` rather than
    # replacing it — see delivery.py's module docstring for why. Nullable
    # so existing rows created before this migration read as NULL (the
    # customer app treats NULL as "pre-granular-tracking", not an error).
    delivery_stage: Mapped[DeliveryStage | None] = mapped_column(Enum(DeliveryStage), nullable=True, index=True)

    # Which fleet is carrying this delivery — decided by
    # delivery_service.select_provider() after DELIVERY_VALIDATED. Null
    # until a provider is actually chosen.
    provider_type: Mapped[DeliveryProvider | None] = mapped_column(Enum(DeliveryProvider), nullable=True)

    # Delivery-quote snapshot captured at checkout time (see 1.6 in the
    # spec doc: "order must retain the necessary delivery snapshot so
    # historical orders remain consistent even if branch data or pricing
    # rules change later"). road_distance_km is actual routed distance,
    # NOT haversine — see delivery_service.estimate_route().
    road_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_fee: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Recalculated continuously once IN_TRANSIT (see delivery_service);
    # this is the value the Customer App's tracking screen actually shows,
    # distinct from the checkout-time eta_minutes snapshot above.
    live_eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    failure_reason: Mapped[DeliveryFailureReason | None] = mapped_column(
        Enum(DeliveryFailureReason), nullable=True
    )
    failure_notes: Mapped[str | None] = mapped_column(String, nullable=True)
 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    user: Mapped["User"] = relationship(back_populates="orders")
    shop: Mapped["Shop"] = relationship(back_populates="orders")
    driver: Mapped["Driver | None"] = relationship(back_populates="orders")
    # No back_populates on Branch — Branch doesn't need a reverse "orders"
    # collection today, and adding one isn't required just to read this side.
    branch: Mapped["Branch | None"] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
 
 
class OrderItem(Base):
    __tablename__ = "order_items"
 
    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
 
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
 
    # Price captured AT THE TIME OF PURCHASE — deliberately not a live
    # reference to Product.price. If a shop changes a price next week, past
    # orders must still reflect what the customer actually paid.
    price_at_purchase: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
 
    order: Mapped["Order"] = relationship(back_populates="items")
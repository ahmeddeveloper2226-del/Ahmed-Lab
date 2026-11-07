import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, Numeric, Enum, DateTime, func, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PayoutDestinationType(enum.Enum):
    bank_account = "bank_account"
    mobile_wallet = "mobile_wallet"


class VendorPayoutAccount(Base):
    """
    Where a shop's money actually gets sent — one active destination per
    shop. Kept as its own table (not columns on Shop) because this is
    sensitive financial data with its own lifecycle: it can be verified,
    replaced, or temporarily suspended without touching the shop's other
    settings, and it's the kind of data worth being able to audit/rotate
    independently.

    account_number is stored ENCRYPTED at rest via app/services/
    payout_encryption.py (Fernet, keyed by settings.payout_encryption_key)
    — never the raw bank account / wallet number. Encrypt before writing,
    decrypt only when needed (and even then, only mask it before it
    reaches any UI — see payout_encryption.mask_account_number).
    """
    __tablename__ = "vendor_payout_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, unique=True, index=True)

    destination_type: Mapped[PayoutDestinationType] = mapped_column(Enum(PayoutDestinationType), nullable=False)
    account_holder_name: Mapped[str] = mapped_column(String, nullable=False)
    account_number: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted ciphertext
    bank_name: Mapped[str | None] = mapped_column(String, nullable=True)  # only meaningful for bank_account

    # Set once Paymob's Disbursement API (or a manual admin check, before
    # that's wired up) has confirmed this destination is real and
    # reachable. A shop with no verified account simply won't be included
    # in a payout run — see payout_service.py.
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    shop: Mapped["Shop"] = relationship()


class PayoutStatus(enum.Enum):
    pending = "pending"  # calculated, not yet sent to Paymob
    processing = "processing"  # disbursement call made, awaiting Paymob confirmation
    paid = "paid"  # Paymob confirmed the money landed
    failed = "failed"  # Paymob disbursement call failed or was rejected


class Payout(Base):
    """
    One row per (shop, payout period) — e.g. one shop's weekly payout.
    Deliberately snapshots amounts at creation time (same principle as
    Order.commission_amount) rather than recomputing from live order data
    later, so a payout record stays historically accurate even if
    commission_rate or order data changes afterward.

    paymob_disbursement_id is nullable because the ACTUAL Paymob
    Disbursement API call is not wired up yet (no API access as of this
    build) — see payout_service.py's send_payout() stub. Every payout
    created today will sit in `pending` until that's connected.
    """
    __tablename__ = "payouts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    gross_revenue: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    platform_commission: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    net_payout_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    order_count: Mapped[int] = mapped_column(nullable=False)

    status: Mapped[PayoutStatus] = mapped_column(Enum(PayoutStatus), default=PayoutStatus.pending, nullable=False)
    paymob_disbursement_id: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shop: Mapped["Shop"] = relationship()
    orders: Mapped[list["PayoutOrder"]] = relationship(back_populates="payout")


class PayoutOrder(Base):
    """
    Links a Payout to the exact Order rows it covers — this is what makes
    a Payout auditable ("which orders is this EGP 4,230 actually for?")
    and is also how an order gets marked as "already paid out" so it's
    never accidentally included in a second payout run.
    """
    __tablename__ = "payout_orders"
    __table_args__ = (UniqueConstraint("order_id", name="uq_payout_orders_order_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    payout_id: Mapped[str] = mapped_column(ForeignKey("payouts.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)

    payout: Mapped["Payout"] = relationship(back_populates="orders")
    order: Mapped["Order"] = relationship()

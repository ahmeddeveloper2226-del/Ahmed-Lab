import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Enum, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrescriptionStatus(enum.Enum):
    # Customer just uploaded the photo — pharmacist hasn't looked at it yet.
    pending_review = "pending_review"
    # Pharmacist has added at least one medicine and submitted their list —
    # now waiting on the customer to review/remove items and accept.
    awaiting_customer_approval = "awaiting_customer_approval"
    # Customer accepted — items are now the customer's problem to check out
    # (added to their local cart client-side; see prescriptions_router.py).
    approved = "approved"
    # Either side can end it here: pharmacist can't fill it (out of stock,
    # illegible photo, controlled substance needing an in-person visit,
    # etc.) or the customer walks away without accepting.
    rejected = "rejected"
    cancelled = "cancelled"


class Prescription(Base):
    """
    A customer-uploaded prescription photo for one pharmacy shop. The
    pharmacist transcribes it into PrescriptionItem rows via the store
    management panel (POST/DELETE .../items), then submits — flipping
    status to awaiting_customer_approval — at which point the customer can
    remove items they don't want (too expensive, don't need it right now,
    etc.) and approve. Approval does NOT create an Order here; it just
    marks the prescription approved and the customer's app adds the
    remaining items to their LOCAL cart (this app has no server-side cart —
    see cart_provider.dart) the same way any other "add to cart" works, so
    checkout goes through the exact same multi-shop flow as everything else.
    """
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)

    image_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus), nullable=False, default=PrescriptionStatus.pending_review
    )

    # Set once, when the pharmacist hits "submit" — before that, the
    # customer's approval screen has nothing to show yet.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship()
    items: Mapped[list["PrescriptionItem"]] = relationship(back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    """
    One medicine line the pharmacist added while transcribing a
    prescription photo — always picked from their OWN shop's product
    catalog (see store_management_router.py's product picker), never
    freeform. This is deliberate: the cart (see cart_repository.dart) is
    strictly product_id-keyed, so a freeform "name it and hope" entry could
    never actually be added to the customer's cart on approval — requiring
    a real catalog Product keeps price/stock consistent AND guarantees
    every approved item is actually orderable.
    """
    __tablename__ = "prescription_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    prescription_id: Mapped[str] = mapped_column(ForeignKey("prescriptions.id"), nullable=False, index=True)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # The customer's "remove a medicine because it's expensive" action sets
    # this to False rather than deleting the row outright — keeps a record
    # of what the pharmacist actually offered, in case of a dispute or a
    # "why wasn't X included" support question later.
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prescription: Mapped["Prescription"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
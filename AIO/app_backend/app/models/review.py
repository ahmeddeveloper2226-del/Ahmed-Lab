from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    """
    One review per order — a customer can review each (per-shop) order
    once, matching the "1 order = 1 review" model most marketplaces use.
    Backs the Business Dashboard's Ratings & Reviews section AND is the
    only place Shop.rating's aggregate actually comes from (see
    review_service.py's recompute_shop_rating).
    """
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5, enforced in the schema layer
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The vendor's public reply, shown back to the customer — separate
    # from `comment` (the customer's own text) so a shop can respond
    # without ever being able to edit what the customer actually said.
    shop_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    shop_replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship()
    shop: Mapped["Shop"] = relationship()
    user: Mapped["User"] = relationship()

from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, DateTime, Numeric, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ShoppingList(Base):
    """
    A user-owned, reusable grocery shopping list — 'Smart Shopping Lists'.
    occasion is a free-form tag ('weekly', 'ramadan', 'family_gathering',
    'bbq', 'diet_plan', 'custom', ...) purely for the icon/label shown in
    the app; it has no effect on behavior server-side.
    """
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    occasion: Mapped[str] = mapped_column(String, nullable=False, default="custom")

    # A short random token used to build a shareable link
    # (/lists/shared/{share_code}) that lets a list be *copied* into
    # another user's account without exposing their real list id or
    # granting write access to the original.
    share_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list", cascade="all, delete-orphan", order_by="ShoppingListItem.created_at"
    )


class ShoppingListItem(Base):
    """
    One line item on a shopping list. Deliberately NOT locked to a single
    product/shop — a list is a plan ('2kg rice'), not a cart; matching a
    line to an actual purchasable product happens at add-to-cart time
    (see shopping_list_service.add_list_to_cart), the same way a person
    picks whichever brand is on the shelf when they actually go shopping.
    product_id is an optional pin when the user (or the recipe importer)
    already knows exactly which catalog product this line means.
    """
    __tablename__ = "shopping_list_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    shopping_list_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)  # 'kg', 'g', 'piece', 'pack', ...
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shopping_list: Mapped["ShoppingList"] = relationship(back_populates="items")

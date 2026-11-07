from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)

    # Optional finer-grained tag within the category (e.g. a category="food"
    # shop tagged subcategory="food_3" for "بيتزا") — used purely for
    # filtering the shop list in the app (see GET /categories/{id}/shops'
    # subcategory_id query param). Nullable so shops created before this
    # existed, or ones that genuinely don't fit one subcategory, still work
    # — they just won't appear when a specific subcategory pill is selected.
    subcategory_id: Mapped[str | None] = mapped_column(ForeignKey("subcategories.id"), nullable=True, index=True)

    # Links a shop to the store-role account that manages it. Nullable
    # because shops are created by an admin first (see shops_router.py) —
    # ownership may be assigned at that point or afterward, once the real
    # shop owner's account exists.
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True, index=True
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    # Backs the store management panel's login (shop_id + password, no
    # separate user account) — see app/services/password_service.py and
    # store_management_router.py. Nullable only so existing shops created
    # before this existed don't break; the admin panel requires a password
    # for every NEWLY created shop (see AdminShopCreateRequest). Never
    # returned in any response — see AdminShopResponse, which deliberately
    # has no password/password_hash field.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # Store's physical pickup location. Required for the driver app to:
    #   1. Show orders on a map relative to the driver's current position.
    #   2. Compute distance for "nearest orders" sorting/filtering.
    #   3. Cluster multiple accepted orders by pickup proximity (see
    #      driver_router.py's accept_order — a driver may only hold more
    #      than one active order at a time if their shops are close together).
    # Nullable so existing shops created before this field don't break;
    # such shops simply won't appear in the driver's nearby-orders view
    # until an admin/store owner sets a location.
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    category: Mapped["Category"] = relationship(back_populates="shops")
    subcategory: Mapped["Subcategory | None"] = relationship(back_populates="shops")
    products: Mapped[list["Product"]] = relationship(back_populates="shop")
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")
    notification_token: Mapped[str | None] = mapped_column(String, nullable=True)
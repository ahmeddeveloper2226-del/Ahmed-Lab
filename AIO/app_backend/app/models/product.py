from sqlalchemy import String, ForeignKey, Numeric, Integer, JSON
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.database import Base

 
 
class Product(Base):
    __tablename__ = "products"
 
    id: Mapped[str] = mapped_column(String, primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Optional finer-grained tag within the shop's own category — e.g. a
    # shop in category="electronics" tagging one product subcategory=
    # "electronics_1" ("الهواتف المحمولة"). Nullable so products created
    # before this existed keep working; they just won't appear when a
    # specific subcategory pill is selected on the shop's product list.
    subcategory_id: Mapped[str | None] = mapped_column(ForeignKey("subcategories.id"), nullable=True, index=True)
 
    # Numeric, not Float — exact decimal storage for money, avoids floating
    # point rounding errors accumulating across many orders.
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Nullable "discounted" price. When set (and lower than `price`), the
    # product is considered "on sale" and becomes eligible for the AIO Fast
    # Picks rails (home screen, its category, and its own shop page) — this
    # single column is the one source of truth for that instead of a
    # separate boolean flag, so a store owner can't accidentally leave a
    # product flagged as on-sale with no actual discount attached to it.
    sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    shop: Mapped["Shop"] = relationship(back_populates="products")
    attributes: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        )

    # Lets a store owner take a product off their storefront without
    # deleting it (and losing its order history / stock count). Added for
    # the Business Dashboard's "Hidden or Inactive Products" section,
    # which had nothing to actually report before this existed.
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, server_default=sa.true())
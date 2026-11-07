from datetime import datetime

from sqlalchemy import String, ForeignKey, Float, Integer, Boolean, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Branch(Base):
    """
    A physical location belonging to a Shop. Shop stays the "business"
    entity (name, category, owner login, product catalog, pricing) —
    Branch is purely about WHERE that business's inventory physically
    sits and gets fulfilled from.

    A shop with ZERO branches behaves exactly as it always has: the
    product's own Product.stock_quantity is the single source of truth,
    and orders aren't attributed to any particular branch (Order.branch_id
    stays null). Nothing about existing shops changes unless a shop
    owner actually adds a branch — see BranchStock and Order.branch_id
    for what changes once they do.
    """
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "فرع المعادي"
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship()


class BranchStock(Base):
    """
    Per-branch inventory for a product — only meaningful for a shop that
    actually has branches. One row per (branch, product); stock_quantity
    here is what a branch actually has on its own shelf, independent of
    any other branch of the same shop.

    This is what lets 'nearest branch that actually has this product'
    (see branch_service.py) mean something real instead of just picking
    the geographically nearest branch and hoping.
    """
    __tablename__ = "branch_stock"
    __table_args__ = (UniqueConstraint("branch_id", "product_id", name="uq_branch_stock_branch_product"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    branch: Mapped["Branch"] = relationship()
    product: Mapped["Product"] = relationship()

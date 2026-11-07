from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subcategory(Base):
    """
    A subcategory belongs to exactly one top-level Category (e.g. "الهواتف
    المحمولة" belongs to "electronics") and is used to tag Shops for
    filtering — see Shop.subcategory_id. A shop picks at most one
    subcategory; there's no subcategory-to-subcategory nesting beyond this
    single level, matching the two-level تصنيفات/subcategory list this was
    seeded from.
    """
    __tablename__ = "subcategories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Preserves the order given when these were seeded (e.g. "ملابس رجالية"
    # before "ملابس نسائية") — without this, the pill row in the app would
    # come back in whatever order Postgres feels like, and reshuffle on
    # every request.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped["Category"] = relationship(back_populates="subcategories")
    shops: Mapped[list["Shop"]] = relationship(back_populates="subcategory")
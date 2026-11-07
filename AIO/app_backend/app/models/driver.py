from sqlalchemy import String, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    # A driver is still an authenticated user (same Firebase phone login),
    # just with a driver profile attached — one-to-one with users.
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, default=False)

    # Set to False by an admin (via admin_router.py) to immediately block
    # this driver from logging in or accepting new orders, without deleting
    # their account/order history. Does NOT affect orders already assigned
    # to them — those still need to be completed or reassigned manually.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Last known location snapshot — used for the initial nearest-driver
    # assignment query. The LIVE location during an active delivery is
    # streamed through Redis pub/sub, not read from here on every update.
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="driver_profile")
    orders: Mapped[list["Order"]] = relationship(back_populates="driver")
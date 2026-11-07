from datetime import datetime 
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base



class User(Base):
    __tablename__ = 'users'

    # Firebase uid — used directly as the primary key, so there's no separate
    # "map Firebase identity to internal user id" table needed.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    fcm_token: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    addresses: Mapped[list["Address"]] = relationship(back_populates='user', cascade='all, delete-orphan')

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    driver_profile: Mapped["Driver | None"] = relationship(back_populates="user", uselist=False)
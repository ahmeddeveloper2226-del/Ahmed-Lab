from sqlalchemy import String, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Address(Base):
    __tablename__ = 'addresses'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)

    label: Mapped[str | None] = mapped_column(String, nullable=True)
    full_address: Mapped[str] = mapped_column(Text, nullable=False)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped['User'] = relationship(back_populates='addresses')
import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, Enum, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageType(enum.Enum):
    text = "text"
    voice = "voice"
    # Sent by the backend itself (e.g. "Driver accepted your order") rather
    # than typed by either participant — lets the chat double as the
    # "private chat room" that's automatically created the moment a driver
    # accepts an order, per the product requirement, without needing a
    # separate ChatRoom table (see the module docstring below for why).
    system = "system"


class MessageStatus(enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"


class ChatMessage(Base):
    """
    One-to-one chat between a customer and their assigned driver, scoped
    entirely by order_id — there is deliberately NO separate "ChatRoom"
    table. An order already uniquely identifies exactly one customer
    (order.user_id) and, once accepted, exactly one driver
    (order.driver_id → driver.user_id), which is precisely the 1:1 pairing
    a "chat room" would otherwise exist to represent. Reusing the order as
    the room avoids a redundant join table and keeps "who can access this
    chat" defined in exactly one place (see chat_service.py).

    The chat becomes usable the moment order.driver_id is set (i.e. the
    instant accept_order() runs in driver_router.py) — that's what
    "automatically create a private chat room when a driver accepts an
    order" means in this design: there's no explicit creation step, the
    room simply becomes addressable at that point, and a system message is
    inserted then (see driver_router.py's accept_order) as the first
    message in it.
    """
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)

    # Both nullable=False except for system messages, where sender_id is
    # deliberately NULL — a system message isn't "from" either participant.
    sender_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    receiver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.sent, nullable=False
    )

    # For message_type == text or system.
    content: Mapped[str | None] = mapped_column(String, nullable=True)

    # For message_type == voice. audio_path is a server-relative storage
    # path (see chat_service.py's MEDIA_ROOT), never exposed directly to
    # clients — only through the authenticated GET /chat/media/{id}
    # endpoint, so access control is enforced on every fetch, not just the
    # initial upload.
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    order: Mapped["Order"] = relationship()
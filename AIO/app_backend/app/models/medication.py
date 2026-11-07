from datetime import date, datetime

from sqlalchemy import String, ForeignKey, Integer, Numeric, Date, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Medication(Base):
    """
    One chronic-condition medication a customer takes regularly — backs
    'Refill Reminder' (Pharmacies-exclusive). The customer adds it once;
    a background worker (workers/refill_reminder_worker.py) computes when
    they're expected to run out and pushes a reminder a few days ahead,
    and 'reorder with a single tap' both adds product_id to the cart AND
    resets last_refill_date so the next run-out date rolls forward
    automatically — no need to re-enter anything each refill.

    product_id is nullable: a customer can track a medication that isn't
    in the AIO catalog yet (still gets reminders, just no one-tap
    reorder — the app shows "search manually" instead for those).
    """
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    medicine_name: Mapped[str] = mapped_column(String, nullable=False)

    # Free-form condition tag purely for the app's icon/label and for
    # letting a customer filter/group "My Medications" by condition —
    # has no effect on the reminder math itself.
    condition: Mapped[str] = mapped_column(String, nullable=False, default="other")

    # Reminder math: run_out_date = last_refill_date + (pack_quantity /
    # daily_dosage) days. Numeric (not float) for daily_dosage since a
    # dose like "half a tablet twice a day" (0.5 * 2 = 1) is common enough
    # to need exact decimal handling, not floating point.
    pack_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    daily_dosage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1)
    last_refill_date: Mapped[date] = mapped_column(Date, nullable=False)

    # How many days BEFORE the computed run-out date to send the push.
    reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Snapshot of which run_out_date a reminder was already sent for —
    # compared against the CURRENT computed run_out_date on every worker
    # pass, so a reminder fires exactly once per refill cycle instead of
    # every single poll between the reminder date and the actual run-out,
    # and automatically re-arms itself after every reorder (which moves
    # run_out_date forward, so it no longer matches this snapshot).
    last_reminded_for_run_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship()

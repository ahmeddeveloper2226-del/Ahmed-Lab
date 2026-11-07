"""
Scheduled Refill Reminder push worker — same standalone-process pattern
as workers/connector_sync_worker.py.

Every _POLL_INTERVAL_SECONDS, checks every active medication and, once
its computed run_out_date is within reminder_days_before of today, adds
the linked pharmacy product straight to the customer's cart (see
medication_service.auto_add_to_cart_for_reminder) and THEN pushes the
reminder — so by the time the customer opens the notification, the
refill is already sitting in their cart and all they need to do is
confirm the order. Records last_reminded_for_run_out_date so the same
refill cycle never re-notifies (or re-adds to cart) on every subsequent
poll. Reordering (medication_service.reorder_medication) — or, later, an
actual checkout — clears that snapshot and moves last_refill_date
forward, so the next cycle re-arms itself automatically.

Run with:
  python -m workers.refill_reminder_worker
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.models.medication import Medication
from app.models.user import User
from app.services.medication_service import auto_add_to_cart_for_reminder, compute_status
from app.services.notification_service import notify_refill_reminder

configure_logging()
logger = logging.getLogger("wasla.worker.refill_reminder")

# Once every 6 hours is plenty for a reminder measured in days, not
# minutes — no reason to poll as tightly as the order-assignment workers.
_POLL_INTERVAL_SECONDS = 6 * 60 * 60
_shutdown = asyncio.Event()


async def _run_due_reminders() -> None:
    today = date.today()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Medication).where(Medication.is_active.is_(True)))
        medications = list(result.scalars().all())

        for medication in medications:
            run_out_date, days_left, needs_refill_soon = compute_status(medication, today)
            if not needs_refill_soon:
                continue
            if medication.last_reminded_for_run_out_date == run_out_date:
                continue  # already reminded (and cart-added) for this exact refill cycle

            user_result = await db.execute(select(User).where(User.id == medication.user_id))
            user = user_result.scalar_one_or_none()
            if user is None:
                continue

            try:
                added_to_cart = await auto_add_to_cart_for_reminder(db, medication)
                await notify_refill_reminder(
                    user_fcm_token=user.fcm_token,
                    medication_id=medication.id,
                    medicine_name=medication.medicine_name,
                    days_left=days_left,
                    added_to_cart=added_to_cart,
                )
                medication.last_reminded_for_run_out_date = run_out_date
                await db.commit()
                logger.info(
                    "Refill reminder sent: medication=%s user=%s days_left=%d added_to_cart=%s",
                    medication.id, medication.user_id, days_left, added_to_cart,
                )
            except Exception as e:
                await db.rollback()
                logger.error("Failed to send refill reminder for medication=%s: %s", medication.id, e, exc_info=True)


async def main() -> None:
    logger.info("Refill reminder worker starting...")
    while not _shutdown.is_set():
        try:
            await _run_due_reminders()
        except Exception as e:
            logger.error("Error in refill reminder poll loop: %s", e, exc_info=True)
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())

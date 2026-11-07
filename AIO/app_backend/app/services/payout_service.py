"""
Payout & Invoice system — backs the Business Dashboard's "Payout History"
and "Invoices" cards, which had nothing real to show before this existed.

IMPORTANT — read before wiring this into a real payout run:

  1. send_payout() below is a STUB. There is no Paymob Disbursement API
     access configured in this project as of this build (that's a
     separate Paymob product from the Accept API already integrated for
     collecting payments — see paymob_service.py — and Paymob typically
     requires its own business verification before granting it). Calling
     create_payout_for_shop() calculates a real, correct payout amount
     and creates a real Payout row in `pending` status — it does NOT
     move any money. Money only moves once send_payout() is implemented
     against real Disbursement API credentials and explicitly called.

  2. account_number on VendorPayoutAccount is stored as plain text in
     this scaffold. Before any real bank/wallet numbers are stored here,
     that column needs application-level encryption at rest (e.g. a
     Fernet key, same idea the old connector_crypto sketch was for) —
     this is flagged in the model too, but repeating it here because
     it's the difference between a scaffold and something safe to use
     with real vendor financial data.

  3. calculate_payout_amount() only ever considers DELIVERED orders that
     don't already belong to a payout (via the PayoutOrder unique
     constraint on order_id) — an order can never be paid out twice, and
     a cancelled/pending order is never included.
"""
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Order, OrderStatus
from ..models.payout import Payout, PayoutOrder, PayoutStatus, VendorPayoutAccount
from .payout_encryption import decrypt_account_number, encrypt_account_number

logger = logging.getLogger("wasla.payout_service")


async def get_payout_account(db: AsyncSession, shop_id: str) -> VendorPayoutAccount | None:
    try:
        result = await db.execute(select(VendorPayoutAccount).where(VendorPayoutAccount.shop_id == shop_id))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to load payout account for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل بيانات الحساب البنكي الآن.")


async def upsert_payout_account(
    db: AsyncSession,
    shop_id: str,
    destination_type: str,
    account_holder_name: str,
    account_number: str,
    bank_name: str | None,
) -> VendorPayoutAccount:
    """
    Replacing an existing account resets is_verified to False — a changed
    account number is a DIFFERENT destination as far as Paymob (or a
    manual admin check, until Disbursement API access exists) is
    concerned, and must be re-verified before any payout can go to it.

    account_number is encrypted before it ever touches the database —
    see payout_encryption.py. The raw number passed in here should never
    be logged.
    """
    encrypted_account_number = encrypt_account_number(account_number)
    try:
        existing = await get_payout_account(db, shop_id)
        if existing is not None:
            existing.destination_type = destination_type
            existing.account_holder_name = account_holder_name
            existing.account_number = encrypted_account_number
            existing.bank_name = bank_name
            existing.is_verified = False
            account = existing
        else:
            account = VendorPayoutAccount(
                id=str(uuid.uuid4()),
                shop_id=shop_id,
                destination_type=destination_type,
                account_holder_name=account_holder_name,
                account_number=encrypted_account_number,
                bank_name=bank_name,
                is_verified=False,
            )
            db.add(account)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to save payout account for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر حفظ بيانات الحساب البنكي الآن.")

    await db.refresh(account)
    return account


async def _unpaid_delivered_orders(
    db: AsyncSession, shop_id: str, period_start: datetime, period_end: datetime
) -> list[Order]:
    already_paid_out = select(PayoutOrder.order_id)
    result = await db.execute(
        select(Order)
        .where(Order.shop_id == shop_id)
        .where(Order.status == OrderStatus.delivered)
        .where(Order.created_at >= period_start)
        .where(Order.created_at < period_end)
        .where(Order.id.notin_(already_paid_out))
    )
    return list(result.scalars().all())


async def preview_payout(db: AsyncSession, shop_id: str, period_start: datetime, period_end: datetime) -> dict:
    """What create_payout_for_shop() WOULD create, without creating it —
    lets the dashboard show 'your next payout will be ~X EGP' before an
    actual payout run happens."""
    try:
        orders = await _unpaid_delivered_orders(db, shop_id, period_start, period_end)
    except SQLAlchemyError as e:
        logger.error("Payout preview query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر حساب المستحقات الآن.")

    gross = sum(float(o.total) for o in orders)
    commission = sum(float(o.commission_amount) for o in orders)
    return {
        "order_count": len(orders),
        "gross_revenue": round(gross, 2),
        "platform_commission": round(commission, 2),
        "net_payout_amount": round(gross - commission, 2),
    }


async def create_payout_for_shop(db: AsyncSession, shop_id: str, period_start: datetime, period_end: datetime) -> Payout:
    """
    Creates a real Payout row covering every DELIVERED, not-yet-paid-out
    order in the period — but does NOT send money (see module docstring).
    Meant to be called by a scheduled job (e.g. weekly), one shop at a
    time, same shape as any other worker task in workers/.
    """
    try:
        orders = await _unpaid_delivered_orders(db, shop_id, period_start, period_end)
        if not orders:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "لا توجد طلبات مستحقة الدفع في هذه الفترة.")

        gross = sum(float(o.total) for o in orders)
        commission = sum(float(o.commission_amount) for o in orders)

        payout = Payout(
            id=str(uuid.uuid4()),
            shop_id=shop_id,
            period_start=period_start,
            period_end=period_end,
            gross_revenue=round(gross, 2),
            platform_commission=round(commission, 2),
            net_payout_amount=round(gross - commission, 2),
            order_count=len(orders),
            status=PayoutStatus.pending,
        )
        db.add(payout)
        await db.flush()  # need payout.id for the PayoutOrder rows below

        for order in orders:
            db.add(PayoutOrder(id=str(uuid.uuid4()), payout_id=payout.id, order_id=order.id))

        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create payout for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إنشاء عملية الصرف الآن.")

    await db.refresh(payout)
    return payout


async def list_payouts(db: AsyncSession, shop_id: str, limit: int = 20) -> list[Payout]:
    try:
        result = await db.execute(
            select(Payout).where(Payout.shop_id == shop_id).order_by(Payout.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
    except SQLAlchemyError as e:
        logger.error("Failed to list payouts for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل سجل المدفوعات الآن.")


async def send_payout(db: AsyncSession, payout_id: str) -> Payout:
    """
    STUB — see module docstring. This is where the real Paymob
    Disbursement API call goes once that access exists:

        1. POST to Paymob's disbursement endpoint with the vendor's
           VendorPayoutAccount details and payout.net_payout_amount.
        2. On success: payout.status = PayoutStatus.processing,
           payout.paymob_disbursement_id = <id from Paymob's response>.
        3. Paymob's disbursement webhook (a NEW webhook, separate from
           payment_webhook_router.py which only handles incoming
           payments) confirms success/failure asynchronously — that
           webhook is what actually sets status to `paid` or `failed`,
           the same way payment_webhook_router.py confirms an incoming
           payment rather than trusting the initial API response alone.

    Until that's built, this raises rather than silently pretending
    money moved — a payout sitting in `pending` forever is an honest
    signal that the vendor hasn't actually been paid; the wrong failure
    mode here would be quietly marking it `paid` when nothing happened.
    """
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "الصرف الفعلي عبر Paymob غير مفعّل بعد — يحتاج صلاحية Disbursement API من Paymob.",
    )

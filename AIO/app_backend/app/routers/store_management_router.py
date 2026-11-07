"""
Store management panel — a separate, lighter-weight alternative to
store_panel_router.py (which requires a real Firebase-authenticated store
owner account with Shop.owner_user_id). This one needs no account at all:
whoever creates a shop in the admin panel sets a password for it
(AdminShopCreateRequest.password), and that password alone is how the shop
gets into its own orders view — matching this codebase's existing pattern
for internal panels (compare verify_admin_panel_secret's plain header
check in dependencies.py) rather than building a second JWT/session system.

Flow:
  1. Admin creates the shop with a password (admin_router.py) — hashed via
     app/services/password_service.py, stored in Shop.password_hash.
  2. The store management panel's login screen posts {shop_id, password}
     to POST /store-management/login purely to validate and show a
     friendly error — it does not issue a token.
  3. Every subsequent request (GET /store-management/orders) sends the
     SAME shop_id + password as headers (X-Shop-Id / X-Store-Password),
     verified fresh on every call via get_shop_by_store_credentials below.
     There is no session to expire or steal — the panel just re-sends the
     credentials it already asked for, exactly like the admin panel resends
     X-Admin-Secret on every request.

This is intentionally NOT the same trust model as store_panel_router.py.
That one assumes a real, individually-provisioned owner account and can
scope per-owner actions (editing a shop's own name, adding products,
etc). This router is read-mostly (orders) plus the one order-status
action a shop genuinely needs day-to-day, gated by a single shared
password — appropriate for "let a small shop see and manage its own
incoming orders without an admin setting up a full account," not for
anything more sensitive.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..dependencies import get_db_session
from ..models.order import Order, OrderStatus
from ..models.prescription import Prescription, PrescriptionItem, PrescriptionStatus
from ..models.product import Product
from ..models.shop import Shop
from ..rate_limiter import limiter
from ..schemas.prescription_schemas import PrescriptionForPharmacyResponse, PrescriptionItemCreateRequest, PrescriptionItemUpdateRequest
from ..schemas.store_schemas import IncomingOrderResponse, UpdateOrderStatusRequest
from ..services.password_service import verify_password
from pydantic import BaseModel, Field

logger = logging.getLogger("wasla.store_management")

router = APIRouter()


class StoreManagementLoginRequest(BaseModel):
    shop_id: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=100)


class StoreManagementLoginResponse(BaseModel):
    shop_id: str
    shop_name: str
    # So the panel can hide/show category-specific tabs (e.g. Prescriptions
    # is pharmacies-only) without a second round trip.
    category_id: str


async def get_shop_by_store_credentials(
    x_shop_id: str = Header(default=""),
    x_store_password: str = Header(default=""),
    db: AsyncSession = Depends(get_db_session),
) -> Shop:
    """
    Re-verified on EVERY request, not just at login — there is no session
    token to trust instead. Deliberately returns the same 401 whether the
    shop_id doesn't exist, has no password set yet, or the password is
    wrong — distinguishing those would let someone probe which shop_ids
    are real.
    """
    if not x_shop_id or not x_store_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing store credentials.",
        )

    result = await db.execute(select(Shop).where(Shop.id == x_shop_id))
    shop = result.scalar_one_or_none()

    if shop is None or not verify_password(x_store_password, shop.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid store ID or password.",
        )

    return shop


@router.post("/login", response_model=StoreManagementLoginResponse)
@limiter.limit("10/minute")
async def store_management_login(
    request: Request,
    payload: StoreManagementLoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Validates credentials up front so the panel can show a clean error on
    its login screen — the actual gate on every following request is still
    get_shop_by_store_credentials above, not anything issued here.
    """
    result = await db.execute(select(Shop).where(Shop.id == payload.shop_id))
    shop = result.scalar_one_or_none()

    if shop is None or not verify_password(payload.password, shop.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid store ID or password.",
        )

    return StoreManagementLoginResponse(shop_id=shop.id, shop_name=shop.name, category_id=shop.category_id)


@router.get("/orders", response_model=list[IncomingOrderResponse])
async def list_orders_for_store_management(
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    try:
        result = await db.execute(
            select(Order)
            .where(Order.shop_id == shop.id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to fetch orders for shop=%s: %s", shop.id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load orders right now. Please try again.",
        )

    return orders


@router.patch("/orders/{order_id}/status", response_model=IncomingOrderResponse)
@limiter.limit("60/minute")
async def update_order_status_for_store_management(
    request: Request,
    order_id: str,
    payload: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """Same allowed-transitions rule as store_panel_router.py's version —
    a shop can move an order forward through its own fulfillment stages,
    never claim a delivery outcome (out_for_delivery -> delivered) that
    belongs to the driver app instead."""
    allowed_transitions = {OrderStatus.pending, OrderStatus.preparing, OrderStatus.out_for_delivery}
    if payload.status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shops may only set status to pending, preparing, or out_for_delivery.",
        )

    try:
        result = await db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        order = result.scalar_one_or_none()

        if order is None or order.shop_id != shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        order.status = payload.status
        await db.commit()
        await db.refresh(order)
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update status for order=%s: %s", order_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update this order right now. Please try again.",
        )

    return order


# ─────────────────────────────────────────────────────────────────────────────
#  Own product catalog — feeds the prescription item "pick from catalog"
#  dropdown in the panel (see add_prescription_item below). This is the
#  store-password-gated equivalent of the admin-secret-gated
#  GET /admin/shops/{shop_id}/products.
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[dict])
async def list_products_for_store_management(
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """
    Feeds the prescription item picker in the panel — deliberately returns
    enough to render actual product cards (image, name, price, stock),
    the same information the customer sees browsing this shop, rather than
    a bare-bones dropdown. See PrescriptionItem's docstring for why this
    replaced a freeform name/price text entry.
    """
    result = await db.execute(select(Product).where(Product.shop_id == shop.id))
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "image_url": p.image_url,
            "stock_quantity": p.stock_quantity,
        }
        for p in products
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  Prescriptions — pharmacy shops only, enforced server-side. A non-pharmacy
#  shop's session gets a clean 403 from every endpoint below rather than
#  relying only on the panel hiding the tab (a hidden tab is a UI nicety,
#  not a security boundary).
# ─────────────────────────────────────────────────────────────────────────────

def _require_pharmacy_shop(shop: Shop) -> None:
    if shop.category_id != "pharmacies":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prescriptions are only available for pharmacy shops.",
        )


async def _load_shop_prescription(db: AsyncSession, prescription_id: str, shop: Shop) -> Prescription:
    _require_pharmacy_shop(shop)
    result = await db.execute(
        select(Prescription)
        .where(Prescription.id == prescription_id)
        .options(selectinload(Prescription.items).selectinload(PrescriptionItem.product))
    )
    prescription = result.scalar_one_or_none()
    if prescription is None or prescription.shop_id != shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")
    return prescription


@router.get("/prescriptions", response_model=list[PrescriptionForPharmacyResponse])
async def list_prescriptions_for_store_management(
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    _require_pharmacy_shop(shop)
    result = await db.execute(
        select(Prescription)
        .where(Prescription.shop_id == shop.id)
        .options(selectinload(Prescription.items).selectinload(PrescriptionItem.product))
        .order_by(Prescription.created_at.desc())
    )
    prescriptions = result.scalars().all()
    return [PrescriptionForPharmacyResponse.from_prescription(p) for p in prescriptions]


@router.post("/prescriptions/{prescription_id}/items", response_model=PrescriptionForPharmacyResponse)
@limiter.limit("60/minute")
async def add_prescription_item(
    request: Request,
    prescription_id: str,
    payload: PrescriptionItemCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """
    Adds one medicine line while the pharmacist is transcribing the photo.
    Only allowed before the list is submitted — once a customer is
    reviewing it (or has approved/rejected/cancelled it), the pharmacist
    can't silently add more behind their back.
    """
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status != PrescriptionStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription has already been submitted for customer review.",
        )

    product_result = await db.execute(
        select(Product).where(Product.id == payload.product_id, Product.shop_id == shop.id)
    )
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That product doesn't belong to your store's catalog.",
        )

    try:
        item = PrescriptionItem(
            id=str(uuid.uuid4()),
            prescription_id=prescription.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            included=True,
        )
        db.add(item)
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to add item to prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not add this item.")

    return PrescriptionForPharmacyResponse.from_prescription(prescription)


@router.delete("/prescriptions/{prescription_id}/items/{item_id}", response_model=PrescriptionForPharmacyResponse)
async def remove_prescription_item_for_store_management(
    prescription_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """The pharmacist's own "oops, wrong medicine" undo — before submit
    only, same reasoning as add_prescription_item above. Hard-deletes
    (unlike the customer-facing remove, which just flags included=false)
    since this never went out for the customer to see in the first place."""
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status != PrescriptionStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription has already been submitted for customer review.",
        )

    item = next((i for i in prescription.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    try:
        await db.delete(item)
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to remove item={item_id} from prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not remove this item.")

    return PrescriptionForPharmacyResponse.from_prescription(prescription)


@router.patch("/prescriptions/{prescription_id}/items/{item_id}", response_model=PrescriptionForPharmacyResponse)
async def update_prescription_item(
    prescription_id: str,
    item_id: str,
    payload: PrescriptionItemUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """Corrects a quantity mistake without a delete-then-re-add round trip.
    Same pending_review-only restriction as add/remove — once the list is
    submitted, the pharmacist can't quietly change what the customer sees."""
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status != PrescriptionStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription has already been submitted for customer review.",
        )

    item = next((i for i in prescription.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    try:
        item.quantity = payload.quantity
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update item={item_id} on prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not update this item.")

    return PrescriptionForPharmacyResponse.from_prescription(prescription)


@router.post("/prescriptions/{prescription_id}/submit", response_model=PrescriptionForPharmacyResponse)
@limiter.limit("20/minute")
async def submit_prescription(
    request: Request,
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """Finalizes the pharmacist's medicine list and hands it to the
    customer for review — no more additions/removals from the pharmacy
    side after this."""
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status != PrescriptionStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This prescription has already been submitted.",
        )

    if not prescription.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one medicine before submitting.",
        )

    try:
        prescription.status = PrescriptionStatus.awaiting_customer_approval
        prescription.submitted_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to submit prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not submit this prescription.")

    return PrescriptionForPharmacyResponse.from_prescription(prescription)


@router.post("/prescriptions/{prescription_id}/reject", response_model=PrescriptionForPharmacyResponse)
async def reject_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """For an illegible photo, an out-of-stock/controlled medicine, or
    anything else the pharmacy can't fill — lets them close it out instead
    of leaving it sitting in pending_review forever."""
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status in (PrescriptionStatus.approved, PrescriptionStatus.cancelled, PrescriptionStatus.rejected):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This prescription can no longer be rejected.")

    try:
        prescription.status = PrescriptionStatus.rejected
        await db.commit()
        await db.refresh(prescription, attribute_names=["items"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to reject prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not reject this prescription.")

    return PrescriptionForPharmacyResponse.from_prescription(prescription)


@router.delete("/prescriptions/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription_for_store_management(
    prescription_id: str,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """
    Lets the pharmacist clear a prescription out of their list once it's
    done — approved, rejected, or cancelled. Deliberately blocked while
    still pending_review or awaiting_customer_approval: those are still
    live for the customer (who's either waiting on the pharmacist or
    actively reviewing what was submitted), so deleting one out from under
    them would silently break their side of the flow.
    """
    prescription = await _load_shop_prescription(db, prescription_id, shop)

    if prescription.status not in (
        PrescriptionStatus.approved,
        PrescriptionStatus.rejected,
        PrescriptionStatus.cancelled,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a finished (approved, rejected, or cancelled) prescription can be removed.",
        )

    try:
        await db.delete(prescription)  # cascades to its items — see Prescription.items' cascade config
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to delete prescription={prescription_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not remove this prescription.")

# ─────────────────────────────────────────────────────────────────────────────
#  Product visibility — the store itself hides/shows its own product.
#  Scoped to Product.shop_id == shop.id, same ownership check pattern as
#  _load_shop_prescription above. Invalidates the same product caches
#  products_router.py's own update_product endpoint invalidates — toggling
#  is_active changes which products even appear in the shop's cached
#  product list, unlike a pure stock change (see products_router.py's
#  cache design notes), so this genuinely needs the invalidation.
# ─────────────────────────────────────────────────────────────────────────────

class SetProductActiveRequest(BaseModel):
    is_active: bool


@router.patch("/products/{product_id}/active")
@limiter.limit("30/minute")
async def set_product_active(
    request: Request,
    product_id: str,
    payload: SetProductActiveRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    from .products_router import _product_detail_cache_key, _products_by_shop_cache_key
    from ..services.cache_service import invalidate_cached

    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Failed to look up product={product_id} for visibility toggle: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="تعذر تحديث المنتج الآن.")

    if product is None or product.shop_id != shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المنتج غير موجود.")

    try:
        product.is_active = payload.is_active
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to toggle is_active for product={product_id}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="تعذر تحديث المنتج الآن.")

    await invalidate_cached(_product_detail_cache_key(product_id))
    await invalidate_cached(_products_by_shop_cache_key(shop.id))

    return {"id": product.id, "is_active": product.is_active}


# ─────────────────────────────────────────────────────────────────────────────
#  Business Dashboard — see app/services/dashboard_service.py for what each
#  endpoint actually computes and, just as importantly, which sections from
#  the original spec were deliberately NOT built (conversion rate, branch
#  management, payout history/invoices) because the underlying data doesn't
#  exist in this schema yet. Every number returned below is real.
#
#  All results are cached briefly (see cache_service.DEFAULT_TTL_SECONDS,
#  5 minutes) — a dashboard is checked often but doesn't need to the
#  second, and these are read-heavy aggregation queries worth not
#  re-running on every tab click.
# ─────────────────────────────────────────────────────────────────────────────
from ..services import dashboard_service  # noqa: E402
from ..services.cache_service import get_cached, set_cached  # noqa: E402


def _dashboard_cache_key(shop_id: str, section: str, *parts: str) -> str:
    suffix = ":".join(parts)
    return f"dashboard:{shop_id}:{section}:{suffix}" if suffix else f"dashboard:{shop_id}:{section}"


@router.get("/dashboard/overview")
@limiter.limit("60/minute")
async def dashboard_overview(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    # Deliberately NOT cached — this is the "right now" number a merchant
    # checks first, and it changes every time an order comes in.
    return await dashboard_service.get_overview(db, shop.id)


@router.get("/dashboard/products")
@limiter.limit("60/minute")
async def dashboard_products(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    cache_key = _dashboard_cache_key(shop.id, "products")
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    data = await dashboard_service.get_product_insights(db, shop.id)
    await set_cached(cache_key, data)
    return data


@router.get("/dashboard/sales-analytics")
@limiter.limit("60/minute")
async def dashboard_sales_analytics(
    request: Request,
    period: str = "daily",
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    cache_key = _dashboard_cache_key(shop.id, "sales", period)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    data = await dashboard_service.get_sales_analytics(db, shop.id, period)
    await set_cached(cache_key, data)
    return data


@router.get("/dashboard/customers")
@limiter.limit("60/minute")
async def dashboard_customers(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    cache_key = _dashboard_cache_key(shop.id, "customers")
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    data = await dashboard_service.get_customer_analytics(db, shop.id)
    await set_cached(cache_key, data)
    return data


@router.get("/dashboard/reviews")
@limiter.limit("60/minute")
async def dashboard_reviews(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    # Not cached — a merchant replying to a review needs to see that reply
    # reflected immediately, not after a 5-minute-stale cache expires.
    return await dashboard_service.get_reviews_summary(db, shop.id)


@router.post("/dashboard/reviews/{review_id}/reply")
@limiter.limit("20/minute")
async def dashboard_reply_to_review(
    request: Request,
    review_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    from ..services.review_service import reply_to_review

    reply_text = str(payload.get("reply", "")).strip()
    if not reply_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اكتب ردًا أولاً.")
    review = await reply_to_review(db, shop.id, review_id, reply_text)
    return {"id": review.id, "shop_reply": review.shop_reply}


@router.get("/dashboard/inventory-insights")
@limiter.limit("60/minute")
async def dashboard_inventory_insights(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    cache_key = _dashboard_cache_key(shop.id, "inventory")
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    data = await dashboard_service.get_inventory_insights(db, shop.id)
    await set_cached(cache_key, data)
    return data


@router.get("/dashboard/financials")
@limiter.limit("60/minute")
async def dashboard_financials(
    request: Request,
    period: str = "monthly",
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    cache_key = _dashboard_cache_key(shop.id, "financials", period)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached
    data = await dashboard_service.get_financial_report(db, shop.id, period)
    await set_cached(cache_key, data)
    return data


@router.get("/dashboard/growth-advisor")
@limiter.limit("10/minute")
async def dashboard_growth_advisor(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """
    See growth_advisor_service.py. Cached for a full day per shop (NOT
    the usual 5 minutes) — this calls Claude, and "today's 3
    recommendations" genuinely doesn't need to change on every dashboard
    open the way a revenue number does. That's also the real cost
    control here: one Claude call per shop per day, not one per click.
    """
    from ..services.growth_advisor_service import get_daily_growth_recommendations

    return await get_daily_growth_recommendations(db, shop.id)


# ─────────────────────────────────────────────────────────────────────────────
#  Payouts & Invoices — see app/services/payout_service.py's module
#  docstring for the full picture. In short: everything below computes
#  and stores REAL numbers from real orders, but no money actually moves
#  yet — that needs Paymob Disbursement API access this project doesn't
#  have. A Payout created here sits in `pending` until that's connected.
# ─────────────────────────────────────────────────────────────────────────────
from ..services import payout_service  # noqa: E402
from ..models.payout import PayoutDestinationType  # noqa: E402
from ..services.payout_encryption import decrypt_account_number, mask_account_number  # noqa: E402


class SetPayoutAccountRequest(BaseModel):
    destination_type: str  # "bank_account" | "mobile_wallet"
    account_holder_name: str
    account_number: str
    bank_name: str | None = None


def _payout_account_to_dict(account) -> dict:
    # account_number is stored ENCRYPTED (see payout_encryption.py) — it
    # must be decrypted before masking. The panel never receives the full
    # decrypted number, only the last 4 digits, and the decrypted value
    # never gets logged or persisted anywhere else.
    raw_account_number = decrypt_account_number(account.account_number)
    return {
        "destination_type": account.destination_type.value,
        "account_holder_name": account.account_holder_name,
        "account_number_masked": mask_account_number(raw_account_number),
        "bank_name": account.bank_name,
        "is_verified": account.is_verified,
    }


@router.get("/payout-account")
@limiter.limit("30/minute")
async def get_payout_account_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    account = await payout_service.get_payout_account(db, shop.id)
    if account is None:
        return None
    return _payout_account_to_dict(account)


@router.put("/payout-account")
@limiter.limit("10/minute")
async def set_payout_account_endpoint(
    request: Request,
    payload: SetPayoutAccountRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    if payload.destination_type not in {t.value for t in PayoutDestinationType}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع حساب غير صالح.")
    account = await payout_service.upsert_payout_account(
        db, shop.id, payload.destination_type, payload.account_holder_name, payload.account_number, payload.bank_name
    )
    return _payout_account_to_dict(account)


def _payout_to_dict(payout) -> dict:
    return {
        "id": payout.id,
        "period_start": payout.period_start.isoformat(),
        "period_end": payout.period_end.isoformat(),
        "gross_revenue": float(payout.gross_revenue),
        "platform_commission": float(payout.platform_commission),
        "net_payout_amount": float(payout.net_payout_amount),
        "order_count": payout.order_count,
        "status": payout.status.value,
        "created_at": payout.created_at.isoformat(),
        "paid_at": payout.paid_at.isoformat() if payout.paid_at else None,
    }


@router.get("/dashboard/payouts")
@limiter.limit("30/minute")
async def dashboard_payouts(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    """
    Real payout records + a live preview of what the NEXT payout would be
    if run right now — both computed from real, unpaid delivered orders.
    Not cached: a merchant checking this right after a payout account
    change or a delivery should see it reflect immediately.
    """
    payouts = await payout_service.list_payouts(db, shop.id)

    # Preview window: since the last payout's period_end, or the shop's
    # entire history if it's never had one.
    since = payouts[0].period_end if payouts else datetime.min.replace(tzinfo=timezone.utc)
    preview = await payout_service.preview_payout(db, shop.id, since, datetime.now(timezone.utc))
    account = await payout_service.get_payout_account(db, shop.id)

    return {
        "payouts": [_payout_to_dict(p) for p in payouts],
        "next_payout_preview": preview,
        "payout_account": _payout_account_to_dict(account) if account else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Branch Management — see app/services/branch_service.py and
#  app/models/branch.py for the full design. A shop that never adds a
#  branch here is completely unaffected by any of this existing.
# ─────────────────────────────────────────────────────────────────────────────
from ..services import branch_service  # noqa: E402


class CreateBranchRequest(BaseModel):
    name: str
    address: str | None = None
    lat: float
    lng: float
    phone: str | None = None


def _branch_to_dict(branch) -> dict:
    return {
        "id": branch.id,
        "name": branch.name,
        "address": branch.address,
        "lat": branch.lat,
        "lng": branch.lng,
        "phone": branch.phone,
        "is_active": branch.is_active,
    }


@router.get("/branches")
@limiter.limit("30/minute")
async def list_branches_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    branches = await branch_service.list_branches(db, shop.id)
    return [_branch_to_dict(b) for b in branches]


@router.post("/branches", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_branch_endpoint(
    request: Request,
    payload: CreateBranchRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    branch = await branch_service.create_branch(
        db, shop.id, payload.name, payload.address, payload.lat, payload.lng, payload.phone
    )
    return _branch_to_dict(branch)


class UpdateBranchRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    phone: str | None = None


@router.patch("/branches/{branch_id}")
@limiter.limit("30/minute")
async def update_branch_endpoint(
    request: Request,
    branch_id: str,
    payload: UpdateBranchRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    # exclude_unset, not just filtering out None: a field the client left
    # OUT of the JSON body means "don't touch it", but a field sent as
    # null (e.g. clearing the address) must still go through as a real
    # value, not get silently skipped.
    fields = payload.model_dump(exclude_unset=True)
    branch = await branch_service.update_branch(db, shop.id, branch_id, fields)
    return _branch_to_dict(branch)


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_branch_endpoint(
    request: Request,
    branch_id: str,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    await branch_service.delete_branch(db, shop.id, branch_id)


class SetBranchStockRequest(BaseModel):
    product_id: str
    stock_quantity: int = Field(..., ge=0)


@router.put("/branches/{branch_id}/stock")
@limiter.limit("60/minute")
async def set_branch_stock_endpoint(
    request: Request,
    branch_id: str,
    payload: SetBranchStockRequest,
    db: AsyncSession = Depends(get_db_session),
    shop: Shop = Depends(get_shop_by_store_credentials),
):
    branch_stock = await branch_service.update_branch_stock(
        db, shop.id, branch_id, payload.product_id, payload.stock_quantity
    )
    return {"branch_id": branch_stock.branch_id, "product_id": branch_stock.product_id, "stock_quantity": branch_stock.stock_quantity}
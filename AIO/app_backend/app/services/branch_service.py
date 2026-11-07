"""
Multi-location support for a shop. See app/models/branch.py for the
schema design and the backward-compatibility guarantee: a shop with
zero Branch rows is completely unaffected by any of this.

Distance is plain haversine (no PostGIS dependency) — fine at this
scale (comparing a handful of branches per shop, not searching millions
of points), and keeps this from needing a new database extension.
"""
import logging
import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.branch import Branch, BranchStock

logger = logging.getLogger("wasla.branch_service")

_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def has_branches(db: AsyncSession, shop_id: str) -> bool:
    try:
        result = await db.execute(
            select(Branch.id).where(Branch.shop_id == shop_id).where(Branch.is_active.is_(True)).limit(1)
        )
        return result.first() is not None
    except SQLAlchemyError as e:
        logger.error("Failed to check has_branches for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل بيانات الفروع الآن.")


async def list_branches(db: AsyncSession, shop_id: str) -> list[Branch]:
    try:
        result = await db.execute(
            select(Branch).where(Branch.shop_id == shop_id).where(Branch.is_active.is_(True)).order_by(Branch.name)
        )
        return list(result.scalars().all())
    except SQLAlchemyError as e:
        logger.error("Failed to list branches for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل الفروع الآن.")


async def list_branches_with_product_stock(
    db: AsyncSession, shop_id: str, product_id: str, user_lat: float | None, user_lng: float | None
) -> list[dict]:
    """
    Every branch of this shop, each annotated with whether/how much stock
    it has of this specific product, and (when the customer's location is
    known) distance — sorted so the nearest branch that actually HAS the
    product comes first. This is the data behind both 'preview all
    branches' and 'pick the nearest one for me' in the customer app —
    same endpoint, the app just decides how much of it to show.
    """
    branches = await list_branches(db, shop_id)
    if not branches:
        return []

    try:
        stock_result = await db.execute(
            select(BranchStock.branch_id, BranchStock.stock_quantity)
            .where(BranchStock.product_id == product_id)
            .where(BranchStock.branch_id.in_([b.id for b in branches]))
        )
        stock_by_branch = dict(stock_result.all())
    except SQLAlchemyError as e:
        logger.error("Failed to load branch stock for product_id=%s: %s", product_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل مخزون الفروع الآن.")

    entries = []
    for branch in branches:
        stock_quantity = stock_by_branch.get(branch.id, 0)
        distance_km = (
            round(haversine_km(user_lat, user_lng, branch.lat, branch.lng), 2)
            if user_lat is not None and user_lng is not None
            else None
        )
        entries.append({
            "branch_id": branch.id,
            "name": branch.name,
            "address": branch.address,
            "lat": branch.lat,
            "lng": branch.lng,
            "phone": branch.phone,
            "stock_quantity": stock_quantity,
            "in_stock": stock_quantity > 0,
            "distance_km": distance_km,
        })

    # Nearest-with-stock first (what a customer actually wants to see at
    # the top), then nearest-without-stock, both by distance when known;
    # unknown-distance entries sort last within their group rather than
    # crashing the sort.
    def sort_key(e):
        distance = e["distance_km"] if e["distance_km"] is not None else float("inf")
        return (0 if e["in_stock"] else 1, distance)

    entries.sort(key=sort_key)
    return entries


async def list_eligible_branches_with_delivery_quote(
    db: AsyncSession,
    shop_id: str,
    customer_lat: float,
    customer_lng: float,
    branch_prep_minutes: int = 15,
) -> list[dict]:
    """
    Every active branch of this shop is eligible, city-wide — see spec
    section 1.2: "Do Not Restrict Stores/Branches by Proximity". This is
    what lets the Customer App present Store -> Branch as an actual
    customer choice (spec 1.1) instead of the backend silently picking
    the nearest one for them, which is all `find_fulfilling_branch` /
    `nearest_branch_fallback` above do (and still do, for the default
    "just check out" flow — this function is for the "let me pick my
    branch" flow, they coexist).

    Each branch is annotated with its own ETA and delivery fee (spec 1.3 /
    1.4), computed from real branch->customer routing — distance affects
    price and time here, but every branch stays listed regardless of how
    far it is. No branch is filtered out or hidden for being "too far".
    """
    from . import delivery_service  # local import: avoids a circular import
                                      # at module load time (delivery_service
                                      # doesn't need branch_service, but this
                                      # keeps the dependency direction explicit)

    branches = await list_branches(db, shop_id)
    if not branches:
        return []

    entries = []
    for branch in branches:
        eta_minutes, road_distance_km = delivery_service.estimate_checkout_eta_minutes(
            branch_prep_minutes=branch_prep_minutes,
            branch_lat=branch.lat,
            branch_lng=branch.lng,
            customer_lat=customer_lat,
            customer_lng=customer_lng,
        )
        delivery_fee = delivery_service.calculate_delivery_fee(road_distance_km)
        entries.append({
            "branch_id": branch.id,
            "name": branch.name,
            "address": branch.address,
            "lat": branch.lat,
            "lng": branch.lng,
            "phone": branch.phone,
            "road_distance_km": road_distance_km,
            "eta_minutes": eta_minutes,
            "delivery_fee": delivery_fee,
        })

    # Sorted by ETA (fastest first) rather than distance — a farther
    # branch with faster roads/less prep time can legitimately beat a
    # closer one, and ETA is what customers actually care about.
    entries.sort(key=lambda e: e["eta_minutes"])
    return entries


async def find_fulfilling_branch(
    db: AsyncSession, shop_id: str, item_requirements: dict[str, int], ref_lat: float, ref_lng: float
) -> str | None:
    """
    Used at checkout (order_service.py) for a shop that has branches:
    picks the nearest branch (to the delivery address) that has enough
    stock of EVERY item in item_requirements ({product_id: quantity}).

    Returns None if no single branch can fully cover the order — the
    caller falls back to the nearest branch regardless (see
    order_service.py's comment on that trade-off) rather than blocking
    checkout entirely over a partial-availability edge case.
    """
    branches = await list_branches(db, shop_id)
    if not branches:
        return None

    try:
        product_ids = list(item_requirements.keys())
        stock_result = await db.execute(
            select(BranchStock.branch_id, BranchStock.product_id, BranchStock.stock_quantity)
            .where(BranchStock.product_id.in_(product_ids))
            .where(BranchStock.branch_id.in_([b.id for b in branches]))
        )
        stock_rows = stock_result.all()
    except SQLAlchemyError as e:
        logger.error("Failed to load branch stock for shop_id=%s checkout: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحديد الفرع المناسب الآن.")

    stock_by_branch: dict[str, dict[str, int]] = {}
    for branch_id, product_id, qty in stock_rows:
        stock_by_branch.setdefault(branch_id, {})[product_id] = qty

    def branch_can_fulfill(branch_id: str) -> bool:
        branch_stock = stock_by_branch.get(branch_id, {})
        return all(branch_stock.get(pid, 0) >= qty for pid, qty in item_requirements.items())

    candidates = sorted(
        (b for b in branches if branch_can_fulfill(b.id)),
        key=lambda b: haversine_km(ref_lat, ref_lng, b.lat, b.lng),
    )
    return candidates[0].id if candidates else None


async def nearest_branch_fallback(db: AsyncSession, shop_id: str, ref_lat: float, ref_lng: float) -> str | None:
    """The 'nobody can fully cover it' fallback — just the geographically
    nearest active branch, so checkout still completes and the order is
    still attributed to somewhere real rather than left unbranched."""
    branches = await list_branches(db, shop_id)
    if not branches:
        return None
    nearest = min(branches, key=lambda b: haversine_km(ref_lat, ref_lng, b.lat, b.lng))
    return nearest.id


async def create_branch(
    db: AsyncSession, shop_id: str, name: str, address: str | None, lat: float, lng: float, phone: str | None
) -> Branch:
    try:
        branch = Branch(id=str(uuid.uuid4()), shop_id=shop_id, name=name, address=address, lat=lat, lng=lng, phone=phone)
        db.add(branch)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create branch for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إضافة الفرع الآن.")
    await db.refresh(branch)
    return branch


async def update_branch(db: AsyncSession, shop_id: str, branch_id: str, fields: dict) -> Branch:
    """
    `fields` only contains keys the caller actually sent (see the router's
    exclude_unset) — anything not in it is left untouched, but a key that
    IS present gets applied even if its value is None/null (e.g. clearing
    an optional field like address or phone).
    """
    allowed_keys = {"name", "address", "lat", "lng", "phone"}
    try:
        result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = result.scalar_one_or_none()
        if branch is None or branch.shop_id != shop_id or not branch.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "الفرع غير موجود.")

        for key, value in fields.items():
            if key in allowed_keys:
                setattr(branch, key, value)

        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update branch_id=%s for shop_id=%s: %s", branch_id, shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحديث بيانات الفرع الآن.")
    await db.refresh(branch)
    return branch


async def delete_branch(db: AsyncSession, shop_id: str, branch_id: str) -> None:
    """
    Soft delete (is_active = False) rather than an actual row delete —
    list_branches/has_branches already filter on is_active, so a deleted
    branch just disappears from every read path immediately. Keeping the
    row (instead of a hard DELETE) preserves it as the historical
    Order.branch_id reference for any past orders fulfilled from there,
    and avoids a FK violation against BranchStock/Order rows that point
    at it.
    """
    try:
        result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = result.scalar_one_or_none()
        if branch is None or branch.shop_id != shop_id or not branch.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "الفرع غير موجود.")

        branch.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete branch_id=%s for shop_id=%s: %s", branch_id, shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر حذف الفرع الآن.")


async def update_branch_stock(
    db: AsyncSession, shop_id: str, branch_id: str, product_id: str, stock_quantity: int
) -> BranchStock:
    try:
        branch_result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = branch_result.scalar_one_or_none()
        if branch is None or branch.shop_id != shop_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "الفرع غير موجود.")

        existing_result = await db.execute(
            select(BranchStock).where(BranchStock.branch_id == branch_id).where(BranchStock.product_id == product_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            existing.stock_quantity = stock_quantity
            branch_stock = existing
        else:
            branch_stock = BranchStock(
                id=str(uuid.uuid4()), branch_id=branch_id, product_id=product_id, stock_quantity=stock_quantity
            )
            db.add(branch_stock)
        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update branch stock for branch_id=%s product_id=%s: %s", branch_id, product_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحديث مخزون الفرع الآن.")
    await db.refresh(branch_stock)
    return branch_stock

"""
Backs the Business Dashboard inside the store management panel
(panels/store_management_panel/index.html's "Dashboard" tab).

Every number here comes from a real SQL aggregation over this shop's own
Orders/OrderItems/Reviews (and, for Conversion Rate, real Redis-tracked
product views — see analytics_service.py) — nothing here is mocked or
estimated. One section from the original spec is still deliberately NOT
implemented:

  - Branch Management: now built — see app/models/branch.py and
    app/services/branch_service.py.

See dashboard_router.py for the endpoints, and growth_advisor_service.py
for the AI Growth Advisor section specifically.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Order, OrderItem, OrderStatus
from ..models.product import Product
from ..models.review import Review
from ..models.user import User

logger = logging.getLogger("wasla.dashboard_service")

# "Delivered" is the only status that counts as real, collected revenue —
# a pending/preparing order can still be cancelled, and a cancelled one
# was never actually paid out to the shop.
_REVENUE_STATUSES = (OrderStatus.delivered,)


async def get_overview(db: AsyncSession, shop_id: str) -> dict:
    from .analytics_service import get_view_count

    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)

    try:
        today_result = await db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0),
                func.count(Order.id),
            )
            .where(Order.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .where(Order.created_at >= today_start)
        )
        today_revenue, today_orders = today_result.one()

        cancelled_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.shop_id == shop_id)
            .where(Order.status == OrderStatus.cancelled)
            .where(Order.created_at >= today_start)
        )
        cancelled_today = cancelled_result.scalar_one()

        # Returning-customer rate over the last 30 days: what fraction of
        # customers who ordered in that window had ALSO ordered from this
        # shop before that window started.
        window_start = datetime.now(timezone.utc) - timedelta(days=30)
        recent_customers_result = await db.execute(
            select(Order.user_id)
            .where(Order.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .where(Order.created_at >= window_start)
            .distinct()
        )
        recent_customer_ids = [row[0] for row in recent_customers_result.all()]

        returning_count = 0
        if recent_customer_ids:
            prior_result = await db.execute(
                select(Order.user_id)
                .where(Order.shop_id == shop_id)
                .where(Order.status.in_(_REVENUE_STATUSES))
                .where(Order.created_at < window_start)
                .where(Order.user_id.in_(recent_customer_ids))
                .distinct()
            )
            returning_count = len(prior_result.all())

        returning_rate = (returning_count / len(recent_customer_ids) * 100) if recent_customer_ids else 0.0
    except SQLAlchemyError as e:
        logger.error("Dashboard overview query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل نظرة عامة الآن.")

    today_revenue = float(today_revenue)
    average_order_value = (today_revenue / today_orders) if today_orders else 0.0

    today_views = await get_view_count(shop_id, date.today())
    # Real conversion rate now that product views are actually tracked
    # (see analytics_service.py) — orders today ÷ product views today.
    # None (not 0%) when there's no view data yet, so the dashboard can
    # show "not enough data" instead of a misleading 0%.
    conversion_rate = round((today_orders / today_views) * 100, 1) if today_views > 0 else None

    return {
        "today_revenue": round(today_revenue, 2),
        "today_orders": today_orders,
        "average_order_value": round(average_order_value, 2),
        "returning_customer_rate": round(returning_rate, 1),
        "cancelled_orders_today": cancelled_today,
        "today_product_views": today_views,
        "conversion_rate": conversion_rate,
    }


async def get_product_insights(db: AsyncSession, shop_id: str, limit: int = 10) -> dict:
    try:
        sold_result = await db.execute(
            select(
                Product.id,
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Product.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .group_by(Product.id, Product.name)
        )
        sales_by_product = sold_result.all()

        all_products_result = await db.execute(select(Product).where(Product.shop_id == shop_id))
        all_products = all_products_result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Product insights query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل بيانات المنتجات الآن.")

    sales_sorted = sorted(sales_by_product, key=lambda r: r.units_sold, reverse=True)
    best_selling = [{"id": r.id, "name": r.name, "units_sold": r.units_sold} for r in sales_sorted[:limit]]
    lowest_selling = [
        {"id": r.id, "name": r.name, "units_sold": r.units_sold}
        for r in sales_sorted[-limit:][::-1]
        if r.units_sold > 0
    ]

    out_of_stock = [{"id": p.id, "name": p.name} for p in all_products if p.stock_quantity == 0]
    low_stock = [
        {"id": p.id, "name": p.name, "stock_quantity": p.stock_quantity}
        for p in all_products
        if 0 < p.stock_quantity <= 5
    ]
    hidden_or_inactive = [{"id": p.id, "name": p.name} for p in all_products if not p.is_active]

    return {
        "best_selling": best_selling,
        "lowest_selling": lowest_selling,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "hidden_or_inactive": hidden_or_inactive,
    }


_PERIOD_TRUNC = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}
_PERIOD_LOOKBACK_DAYS = {"daily": 30, "weekly": 90, "monthly": 365, "yearly": 365 * 3}


async def get_sales_analytics(db: AsyncSession, shop_id: str, period: str) -> list[dict]:
    if period not in _PERIOD_TRUNC:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "فترة غير صالحة.")

    since = datetime.now(timezone.utc) - timedelta(days=_PERIOD_LOOKBACK_DAYS[period])
    bucket = func.date_trunc(_PERIOD_TRUNC[period], Order.created_at)

    try:
        result = await db.execute(
            select(bucket.label("bucket"), func.coalesce(func.sum(Order.total), 0).label("revenue"))
            .where(Order.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .where(Order.created_at >= since)
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = result.all()
    except SQLAlchemyError as e:
        logger.error("Sales analytics query failed for shop_id=%s period=%s: %s", shop_id, period, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل تحليلات المبيعات الآن.")

    return [{"period": row.bucket.date().isoformat(), "revenue": round(float(row.revenue), 2)} for row in rows]


async def get_customer_analytics(db: AsyncSession, shop_id: str, top_n: int = 5) -> dict:
    try:
        per_customer_result = await db.execute(
            select(
                Order.user_id,
                User.full_name,
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total), 0).label("total_spent"),
                func.min(Order.created_at).label("first_order_at"),
            )
            .join(User, User.id == Order.user_id)
            .where(Order.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .group_by(Order.user_id, User.full_name)
        )
        per_customer = per_customer_result.all()
    except SQLAlchemyError as e:
        logger.error("Customer analytics query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل بيانات العملاء الآن.")

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    total_customers = len(per_customer)
    new_customers = sum(
        1 for c in per_customer if c.first_order_at and c.first_order_at.replace(tzinfo=timezone.utc) >= thirty_days_ago
    )
    returning_customers = sum(1 for c in per_customer if c.order_count > 1)
    average_orders_per_customer = (
        sum(c.order_count for c in per_customer) / total_customers if total_customers else 0.0
    )
    top_customers = sorted(per_customer, key=lambda c: c.total_spent, reverse=True)[:top_n]

    return {
        "total_customers": total_customers,
        "new_customers_30d": new_customers,
        "returning_customers": returning_customers,
        "average_orders_per_customer": round(average_orders_per_customer, 2),
        "top_customers": [
            {
                "user_id": c.user_id,
                "name": c.full_name,
                "order_count": c.order_count,
                "total_spent": round(float(c.total_spent), 2),
            }
            for c in top_customers
        ],
    }


async def get_reviews_summary(db: AsyncSession, shop_id: str, limit: int = 20) -> dict:
    try:
        agg_result = await db.execute(
            select(func.count(Review.id), func.coalesce(func.avg(Review.rating), 0)).where(Review.shop_id == shop_id)
        )
        review_count, average_rating = agg_result.one()

        recent_result = await db.execute(
            select(Review, User.full_name)
            .join(User, User.id == Review.user_id)
            .where(Review.shop_id == shop_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        recent = recent_result.all()
    except SQLAlchemyError as e:
        logger.error("Reviews summary query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل التقييمات الآن.")

    return {
        "review_count": review_count,
        "average_rating": round(float(average_rating), 2),
        "recent_reviews": [
            {
                "id": r.Review.id,
                "customer_name": r.full_name,
                "rating": r.Review.rating,
                "comment": r.Review.comment,
                "shop_reply": r.Review.shop_reply,
                "created_at": r.Review.created_at.isoformat(),
            }
            for r in recent
        ],
    }


async def get_inventory_insights(db: AsyncSession, shop_id: str, limit: int = 10) -> dict:
    """
    Slow-moving vs high-demand, over the last 30 days of DELIVERED order
    items — deliberately excludes products with zero sales entirely from
    "slow-moving" (that's what out_of_stock/hidden already covers in
    get_product_insights); this is about products that DO sell, just
    much slower than the rest of the shop's catalog.
    """
    since = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        result = await db.execute(
            select(
                Product.id,
                Product.name,
                Product.stock_quantity,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold_30d"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id, isouter=True)
            .join(
                Order,
                and_(Order.id == OrderItem.order_id, Order.status.in_(_REVENUE_STATUSES), Order.created_at >= since),
                isouter=True,
            )
            .where(Product.shop_id == shop_id)
            .where(Product.is_active.is_(True))
            .group_by(Product.id, Product.name, Product.stock_quantity)
        )
        rows = result.all()
    except SQLAlchemyError as e:
        logger.error("Inventory insights query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل رؤى المخزون الآن.")

    sold = [r for r in rows if r.units_sold_30d > 0]
    sold_sorted = sorted(sold, key=lambda r: r.units_sold_30d)

    return {
        "slow_moving": [
            {"id": r.id, "name": r.name, "units_sold_30d": r.units_sold_30d, "stock_quantity": r.stock_quantity}
            for r in sold_sorted[:limit]
        ],
        "high_demand": [
            {"id": r.id, "name": r.name, "units_sold_30d": r.units_sold_30d, "stock_quantity": r.stock_quantity}
            for r in sold_sorted[-limit:][::-1]
        ],
    }


async def get_financial_report(db: AsyncSession, shop_id: str, period: str) -> dict:
    """
    Real numbers only: revenue, platform commission, and net profit — all
    directly derivable from Order rows. Deliberately does NOT include
    "Payout History" or "Invoices" from the original spec — there's no
    payout scheduling or invoicing system in this codebase yet, and
    faking a payout schedule would be actively misleading to a vendor
    looking at real money.
    """
    if period not in _PERIOD_TRUNC:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "فترة غير صالحة.")
    since = datetime.now(timezone.utc) - timedelta(days=_PERIOD_LOOKBACK_DAYS[period])

    try:
        result = await db.execute(
            select(
                func.coalesce(func.sum(Order.total), 0),
                func.coalesce(func.sum(Order.commission_amount), 0),
                func.count(Order.id),
            )
            .where(Order.shop_id == shop_id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .where(Order.created_at >= since)
        )
        revenue, commission, order_count = result.one()
    except SQLAlchemyError as e:
        logger.error("Financial report query failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل التقرير المالي الآن.")

    revenue = float(revenue)
    commission = float(commission)
    return {
        "period": period,
        "revenue": round(revenue, 2),
        "platform_commission": round(commission, 2),
        "net_profit": round(revenue - commission, 2),
        "order_count": order_count,
    }

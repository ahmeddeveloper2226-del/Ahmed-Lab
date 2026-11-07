"""
The Business Dashboard's 'AI Growth Advisor' — instead of showing a
merchant raw charts and making them figure out what to do, this turns
their OWN real data (best/worst sellers, low stock, dormant customers)
into 2-3 short, concrete action recommendations in Egyptian Arabic.

Cost control, matching this codebase's existing pattern for AI features
(see meal_builder_service.py, ai_assistant_service.py):
  - Cached for a full CALENDAR DAY per shop, not the usual 5-minute TTL —
    "today's opportunities" doesn't need to regenerate every time the
    merchant opens the dashboard tab. One Claude call per shop per day.
  - The candidate data fed to Claude is small and pre-aggregated (top 5
    best-sellers, top 5 low-stock items, a dormant-customer count) — not
    a product catalog dump.

Same anti-hallucination guardrail as every other AI feature here: Claude
is only shown real product names and real numbers already computed by
dashboard_service.py; it is not asked to invent data, only to phrase
recommendations FROM the data it's given. The recommendations themselves
are advisory text, not actions Claude can take — the merchant still has
to go create the discount / restock the item / send the coupon
themselves; nothing here writes to the database.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

import anthropic
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.order import Order, OrderItem, OrderStatus
from ..models.product import Product
from ..services.cache_service import get_cached, set_cached

logger = logging.getLogger("wasla.growth_advisor")

_SYSTEM_PROMPT = """أنت مستشار نمو لتاجر على منصة AIO. سيصلك ملخص بيانات حقيقية عن متجره (أفضل المنتجات مبيعًا، منتجات قاربت على النفاد، عملاء لم يطلبوا منذ فترة). لا تخترع أي بيانات غير موجودة في الملخص.

أرجع 2-3 توصيات عملية قصيرة ومباشرة بالعربية المصرية، كل توصية جملة واحدة قابلة للتنفيذ فعليًا (مثل تفعيل خصم، إعادة تخزين منتج، إرسال كوبون لعملاء غائبين) — مبنية فقط على الأرقام المرسلة لك.

أرجع ردك كـ JSON فقط بدون أي نص خارجه:
{"greeting": "تحية قصيرة بالعربية المصرية (مثل 'صباح الخير!')", "recommendations": ["توصية 1", "توصية 2", "توصية 3"]}"""


async def _build_candidate_summary(db: AsyncSession, shop_id: str) -> dict:
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        best_sellers_result = await db.execute(
            select(Product.name, func.coalesce(func.sum(OrderItem.quantity), 0).label("units"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Product.shop_id == shop_id)
            .where(Order.status == OrderStatus.delivered)
            .where(Order.created_at >= since_7d)
            .group_by(Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
        )
        best_sellers = [{"name": r.name, "units_sold_7d": r.units} for r in best_sellers_result.all()]

        low_stock_result = await db.execute(
            select(Product.name, Product.stock_quantity)
            .where(Product.shop_id == shop_id)
            .where(Product.is_active.is_(True))
            .where(Product.stock_quantity > 0)
            .where(Product.stock_quantity <= 5)
            .order_by(Product.stock_quantity)
            .limit(5)
        )
        low_stock = [{"name": r.name, "stock_quantity": r.stock_quantity} for r in low_stock_result.all()]

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        dormant_result = await db.execute(
            select(func.count(func.distinct(Order.user_id)))
            .where(Order.shop_id == shop_id)
            .where(Order.status == OrderStatus.delivered)
            .where(Order.created_at < thirty_days_ago)
            .where(
                Order.user_id.notin_(
                    select(Order.user_id)
                    .where(Order.shop_id == shop_id)
                    .where(Order.status == OrderStatus.delivered)
                    .where(Order.created_at >= thirty_days_ago)
                )
            )
        )
        dormant_customer_count = dormant_result.scalar_one()
    except SQLAlchemyError as e:
        logger.error("Failed to build growth advisor candidate summary for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل توصيات النمو الآن.")

    return {
        "best_sellers_last_7_days": best_sellers,
        "low_stock_products": low_stock,
        "customers_inactive_30_days_plus": dormant_customer_count,
    }


async def get_daily_growth_recommendations(db: AsyncSession, shop_id: str) -> dict:
    cache_key = f"growth-advisor:{shop_id}:{date.today().isoformat()}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    if not settings.anthropic_api_key:
        raise RuntimeError("Growth Advisor is not configured (ANTHROPIC_API_KEY missing).")

    summary = await _build_candidate_summary(db, shop_id)

    # Nothing to say yet — a brand-new shop with no order history. Return
    # a plain, honest empty state instead of spending a Claude call on
    # data that doesn't exist.
    if not summary["best_sellers_last_7_days"] and not summary["low_stock_products"] and not summary["customers_inactive_30_days_plus"]:
        result = {"greeting": "أهلاً بيك!", "recommendations": ["لسه معندناش بيانات كفاية عن متجرك — تابع لوحة التحكم بعد أول أسبوع مبيعات."]}
        await set_cached(cache_key, result, ttl_seconds=60 * 60 * 24)
        return result

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model=settings.ai_assistant_model,
            max_tokens=400,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(summary, ensure_ascii=False)}],
        )
    except Exception as e:
        logger.error("Growth Advisor Claude call failed for shop_id=%s: %s", shop_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر تحميل توصيات النمو الآن.")

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        import re
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.error("Growth Advisor returned non-JSON for shop_id=%s: %r", shop_id, raw_text[:300])
        # Fail soft here rather than 422 — this is a "nice to have" advisory
        # panel, not a core flow; a friendly fallback beats an error banner.
        result = {"greeting": "أهلاً بيك!", "recommendations": ["تابع أداء منتجاتك في تبويب المنتجات لمعرفة الفرص المتاحة."]}
        await set_cached(cache_key, result, ttl_seconds=60 * 60 * 24)
        return result

    result = {
        "greeting": str(parsed.get("greeting", "أهلاً بيك!"))[:100],
        "recommendations": [str(r)[:200] for r in (parsed.get("recommendations") or [])][:3],
    }
    await set_cached(cache_key, result, ttl_seconds=60 * 60 * 24)
    return result

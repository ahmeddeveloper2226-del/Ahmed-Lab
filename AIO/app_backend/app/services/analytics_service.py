"""
Lightweight page-view tracking — the piece that was missing for a real
Conversion Rate on the Business Dashboard.

Deliberately NOT a full analytics/event pipeline (no user_id, no
per-product breakdown, no session tracking) — just what's needed to
answer 'how many people looked at this shop's products today, vs how
many actually ordered.' Stored in Redis as a simple per-shop daily
counter (not Postgres) because:

  1. It's a write on every single product-detail view — the highest-
     volume write path in the whole app by far. Redis INCR is cheap;
     inserting a Postgres row on every product view is not.
  2. It doesn't need to be queried relationally (joined against other
     tables, filtered by arbitrary conditions) — just "today's count for
     this shop," which is exactly what a counter is for.

Counters expire after 40 days — long enough for the dashboard's own
lookback windows (30 days, see dashboard_service.py) with room to spare,
without accumulating forever.
"""
from datetime import date, datetime, timedelta, timezone

from ..redis_client import redis_client

_VIEW_TTL_SECONDS = 60 * 60 * 24 * 40


def _view_key(shop_id: str, day: date) -> str:
    return f"analytics:views:{shop_id}:{day.isoformat()}"


async def record_product_view(shop_id: str) -> None:
    """
    Fire-and-forget from products_router.py's get_product_detail, on
    every successful (non-404) product view. Never allowed to break the
    actual product-view request if Redis hiccups — a missed analytics
    counter is a rounding error; a broken product page is not.
    """
    try:
        key = _view_key(shop_id, datetime.now(timezone.utc).date())
        await redis_client.incr(key)
        await redis_client.expire(key, _VIEW_TTL_SECONDS)
    except Exception:
        pass


async def get_view_count(shop_id: str, day: date) -> int:
    try:
        value = await redis_client.get(_view_key(shop_id, day))
        return int(value) if value else 0
    except Exception:
        return 0


async def get_view_count_range(shop_id: str, days: int) -> int:
    """Sum of views over the last N days (including today)."""
    today = datetime.now(timezone.utc).date()
    total = 0
    for offset in range(days):
        total += await get_view_count(shop_id, today - timedelta(days=offset))
    return total

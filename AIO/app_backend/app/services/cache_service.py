import json
import logging
from typing import Any

from ..redis_client import redis_client

logger = logging.getLogger("wasla.cache")

# Default cache lifetime for read-mostly, rarely-changing data like
# categories/shops/products. Short enough that a shop editing its menu
# isn't stale for long; long enough to meaningfully cut load off Postgres.
DEFAULT_TTL_SECONDS = 300


async def get_cached(key: str) -> Any | None:
    """
    Returns the cached, deserialized value for `key`, or None on a cache miss
    OR if Redis itself is unreachable. Deliberately never raises — a cache
    failure must never take down a request that could still be served by
    Postgres directly. This is a hard production rule: caching is an
    optimization, not a dependency the app can fail on.
    """
    try:
        raw = await redis_client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Redis GET failed for key={key}: {e}")
        return None


async def set_cached(key: str, value: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """
    Best-effort cache write. Failures are logged, never raised — the request
    that computed `value` already succeeded from Postgres; a failed cache
    write shouldn't turn that into a failed response.
    """
    try:
        await redis_client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as e:
        logger.warning(f"Redis SET failed for key={key}: {e}")


async def invalidate_cached(key: str) -> None:
    """Call this whenever underlying Postgres data changes (e.g. a shop edits a product)."""
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Redis DELETE failed for key={key}: {e}")
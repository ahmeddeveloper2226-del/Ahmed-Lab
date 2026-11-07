import redis.asyncio as redis

from .config import settings

# A single shared connection pool — every part of the app (cache_service,
# cart_router, driver location pub/sub, etc.) reuses this instead of opening
# its own connection to Redis.
redis_client: redis.Redis = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def check_redis_connection() -> bool:
    """Called once at startup (see main.py) to fail fast if Redis is unreachable."""
    try:
        return await redis_client.ping()
    except Exception as e:
        raise RuntimeError(f"Could not connect to Redis: {e}")
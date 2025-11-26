"""Redis caching service."""

import json
from typing import Any

import redis.asyncio as redis
import structlog

from backend.app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Global Redis client
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis | None:
    """Get Redis client instance."""
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_connection_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await _redis_client.ping()
            logger.info("Redis client connected")
        except Exception as e:
            logger.warning("Failed to connect to Redis", error=str(e))
            _redis_client = None

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


class CacheService:
    """Caching service with Redis backend."""

    # Default TTL values (in seconds)
    TTL_SHORT = 300  # 5 minutes
    TTL_MEDIUM = 3600  # 1 hour
    TTL_LONG = 86400  # 24 hours

    def __init__(self, prefix: str = "stocktool") -> None:
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        client = await get_redis_client()
        if not client:
            return None

        try:
            value = await client.get(self._make_key(key))
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning("Cache get error", key=key, error=str(e))

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        client = await get_redis_client()
        if not client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await client.setex(self._make_key(key), ttl, serialized)
            else:
                await client.set(self._make_key(key), serialized)
            return True
        except Exception as e:
            logger.warning("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        client = await get_redis_client()
        if not client:
            return False

        try:
            await client.delete(self._make_key(key))
            return True
        except Exception as e:
            logger.warning("Cache delete error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = await get_redis_client()
        if not client:
            return False

        try:
            return bool(await client.exists(self._make_key(key)))
        except Exception as e:
            logger.warning("Cache exists error", key=key, error=str(e))
            return False

    async def get_or_set(
        self,
        key: str,
        factory: Any,  # Callable that returns the value
        ttl: int | None = None,
    ) -> Any:
        """Get from cache or compute and store value."""
        # Try cache first
        value = await self.get(key)
        if value is not None:
            logger.debug("Cache hit", key=key)
            return value

        # Compute value
        logger.debug("Cache miss", key=key)
        if callable(factory):
            value = await factory() if hasattr(factory, "__await__") else factory()
        else:
            value = factory

        # Store in cache
        await self.set(key, value, ttl)
        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        client = await get_redis_client()
        if not client:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                await client.delete(*keys)

            return len(keys)
        except Exception as e:
            logger.warning("Cache invalidate pattern error", pattern=pattern, error=str(e))
            return 0


# Cache key builders
def stock_price_key(ticker: str, date: str) -> str:
    """Build cache key for stock price."""
    return f"price:{ticker}:{date}"


def stock_analysis_key(ticker: str) -> str:
    """Build cache key for stock analysis."""
    return f"analysis:{ticker}"


def market_sentiment_key(date: str) -> str:
    """Build cache key for market sentiment."""
    return f"sentiment:{date}"


def fund_holdings_key(fund_id: int, date: str) -> str:
    """Build cache key for fund holdings."""
    return f"holdings:{fund_id}:{date}"


def news_key(source: str, query: str) -> str:
    """Build cache key for news."""
    return f"news:{source}:{query}"


# Global cache instance
cache = CacheService()


# Job progress functions for WebSocket updates
async def set_job_progress(
    job_id: str,
    status: str,
    progress: int,
    current_step: str,
    result: dict | None = None,
) -> bool:
    """Set job progress in Redis for WebSocket polling."""
    client = await get_redis_client()
    if not client:
        return False

    try:
        data = {
            "status": status,
            "progress": progress,
            "current_step": current_step,
        }
        if result is not None:
            data["result"] = result

        # Store with 1 hour TTL
        await client.setex(f"job_progress:{job_id}", 3600, json.dumps(data))
        return True
    except Exception as e:
        logger.warning("Failed to set job progress", job_id=job_id, error=str(e))
        return False


async def get_job_progress(job_id: str) -> dict | None:
    """Get job progress from Redis."""
    client = await get_redis_client()
    if not client:
        return None

    try:
        data = await client.get(f"job_progress:{job_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning("Failed to get job progress", job_id=job_id, error=str(e))

    return None

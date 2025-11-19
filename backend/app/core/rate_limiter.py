"""Rate limiting utilities."""

import asyncio
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable

import structlog

from backend.app.core.exceptions import RateLimitException

logger = structlog.get_logger(__name__)


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(
        self,
        rate: float,  # tokens per second
        capacity: int,  # maximum tokens
        name: str = "default",
    ) -> None:
        self.rate = rate
        self.capacity = capacity
        self.name = name
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_for_token(self, tokens: int = 1, timeout: float = 30.0) -> None:
        """Wait for tokens to become available."""
        start = time.time()
        while not await self.acquire(tokens):
            if time.time() - start > timeout:
                raise RateLimitException(
                    message=f"Rate limit timeout for {self.name}",
                    retry_after=int(timeout),
                )
            await asyncio.sleep(0.1)


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for user requests."""

    def __init__(self, window_size: int, max_requests: int) -> None:
        self.window_size = window_size  # seconds
        self.max_requests = max_requests
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_size

            # Remove old requests
            self.requests[key] = [
                ts for ts in self.requests[key] if ts > window_start
            ]

            if len(self.requests[key]) >= self.max_requests:
                return False

            self.requests[key].append(now)
            return True

    async def get_remaining(self, key: str) -> int:
        """Get remaining requests for the given key."""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_size
            current_requests = [
                ts for ts in self.requests[key] if ts > window_start
            ]
            return max(0, self.max_requests - len(current_requests))

    async def get_reset_time(self, key: str) -> int:
        """Get seconds until rate limit resets for the given key."""
        async with self._lock:
            if not self.requests[key]:
                return 0
            oldest = min(self.requests[key])
            reset_at = oldest + self.window_size
            return max(0, int(reset_at - time.time()))


# Global rate limiters for different APIs
rate_limiters: dict[str, TokenBucketRateLimiter] = {}


def get_rate_limiter(name: str, rate: float, capacity: int) -> TokenBucketRateLimiter:
    """Get or create a rate limiter by name."""
    if name not in rate_limiters:
        rate_limiters[name] = TokenBucketRateLimiter(rate, capacity, name)
    return rate_limiters[name]


def rate_limited(
    limiter_name: str,
    rate: float,
    capacity: int,
) -> Callable:
    """Decorator to apply rate limiting to async functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = get_rate_limiter(limiter_name, rate, capacity)
            await limiter.wait_for_token()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Pre-configured rate limiters
def get_alpha_vantage_limiter() -> TokenBucketRateLimiter:
    """Get rate limiter for Alpha Vantage API (30 req/min)."""
    return get_rate_limiter("alpha_vantage", rate=0.5, capacity=30)


def get_sec_edgar_limiter() -> TokenBucketRateLimiter:
    """Get rate limiter for SEC EDGAR API (10 req/sec)."""
    return get_rate_limiter("sec_edgar", rate=10, capacity=10)


def get_yahoo_limiter() -> TokenBucketRateLimiter:
    """Get rate limiter for Yahoo Finance (2000 req/hour)."""
    return get_rate_limiter("yahoo", rate=0.55, capacity=100)

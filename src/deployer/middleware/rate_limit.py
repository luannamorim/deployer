from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from deployer.middleware import BYPASS_PATHS

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from deployer.config import Settings

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """Return True if the request is within the rate limit, False if exceeded.

    Uses a Redis sorted set sliding window: entries are keyed by timestamp and
    purged once they fall outside the window.
    """
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    results: list[int] = await pipe.execute()
    count: int = results[1]
    return count < limit


def create_rate_limit_dispatch(
    settings: Settings,
    get_redis: Callable[[], Redis],
) -> Callable[[Request, RequestResponseEndpoint], Awaitable[Response]]:
    """Return a rate-limit dispatch function closed over settings and a Redis getter."""

    async def rate_limit_dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in BYPASS_PATHS:
            return await call_next(request)

        if settings.require_auth:
            identifier = request.headers.get("X-API-Key", "anonymous")
        else:
            identifier = request.client.host if request.client else "unknown"

        key = f"rate_limit:{identifier}"
        allowed = await check_rate_limit(
            get_redis(), key, settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
        if not allowed:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
        return await call_next(request)

    return rate_limit_dispatch

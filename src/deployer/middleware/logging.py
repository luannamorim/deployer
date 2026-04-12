from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

from deployer.observability.logger import get_logger

logger = get_logger("deployer.access")

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


async def logging_dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Log every request with method, path, status code, latency, and masked API key.

    The request_id is automatically included via structlog contextvars — it is bound
    by request_id_dispatch which runs inside this middleware.
    """
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    api_key_raw = request.headers.get("X-API-Key", "")
    api_key_masked = f"***{api_key_raw[-4:]}" if len(api_key_raw) >= 4 else "none"

    logger.info(
        "request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
        api_key=api_key_masked,
    )
    return response

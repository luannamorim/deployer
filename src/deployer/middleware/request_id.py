from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Request-ID"

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


async def request_id_dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Inject a request ID into the context and propagate it on the response."""
    request_id = request.headers.get(HEADER_NAME) or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers[HEADER_NAME] = request_id
    return response

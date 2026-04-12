from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from deployer.middleware import BYPASS_PATHS

if TYPE_CHECKING:
    from deployer.config import Settings

HEADER_NAME = "X-API-Key"

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


def create_auth_dispatch(
    settings: Settings,
) -> Callable[[Request, RequestResponseEndpoint], Awaitable[Response]]:
    """Return an auth dispatch function closed over the given settings."""

    async def auth_dispatch(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in BYPASS_PATHS or not settings.require_auth:
            return await call_next(request)

        api_key = request.headers.get(HEADER_NAME)
        if not api_key:
            return JSONResponse({"detail": "Missing X-API-Key header"}, status_code=401)

        if api_key not in settings.api_keys:
            return JSONResponse({"detail": "Invalid API key"}, status_code=403)

        return await call_next(request)

    return auth_dispatch

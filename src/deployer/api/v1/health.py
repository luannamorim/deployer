"""GET /health and /health/ready — deep and readiness probes."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from deployer.api.v1.schemas import HealthCheck, HealthResponse
from deployer.dependencies import get_redis, get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from deployer.config import Settings
    from deployer.llm.providers.base import LLMProvider

router = APIRouter(tags=["health"])

SettingsDep = Annotated["Settings", Depends(get_settings)]
RedisDep = Annotated["Redis", Depends(get_redis)]


async def _redis_ok(redis: Redis) -> bool:
    try:
        return bool(await redis.ping())
    except Exception:
        return False


async def _provider_ok(provider: LLMProvider | None) -> bool:
    if provider is None:
        return False
    try:
        return await provider.check_health()
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health(
    request: Request,
    cfg: SettingsDep,
    redis: RedisDep,
) -> HealthResponse:
    provider: LLMProvider | None = getattr(request.app.state, "provider", None)
    start_time: float = getattr(request.app.state, "start_time", time.time())

    redis_status = "connected" if await _redis_ok(redis) else "disconnected"
    provider_status = "reachable" if await _provider_ok(provider) else "unreachable"
    uptime = int(time.time() - start_time)

    overall = (
        "healthy" if redis_status == "connected" and provider_status == "reachable" else "degraded"
    )

    return HealthResponse(
        status=overall,
        checks=HealthCheck(
            redis=redis_status,
            llm_provider=provider_status,
            uptime_seconds=uptime,
        ),
        version=cfg.app_version,
    )


@router.get("/health/ready")
async def health_ready(request: Request, redis: RedisDep) -> JSONResponse:
    """Kubernetes-style readiness probe — 200 if ready, 503 if not."""
    provider = getattr(request.app.state, "provider", None)
    if await _redis_ok(redis) and provider is not None:
        return JSONResponse({"status": "ready"}, status_code=200)
    return JSONResponse({"status": "not_ready"}, status_code=503)

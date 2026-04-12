from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from redis.asyncio import Redis

from deployer.config import Settings, settings
from deployer.middleware.auth import create_auth_dispatch
from deployer.middleware.logging import logging_dispatch
from deployer.middleware.rate_limit import create_rate_limit_dispatch
from deployer.middleware.request_id import request_id_dispatch
from deployer.observability.logger import configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg: Settings = app.state.settings
    configure_logging(cfg.log_level)
    redis_client: Redis = Redis.from_url(cfg.redis_url, decode_responses=True)
    app.state.redis = redis_client
    logger.info(
        "application starting",
        app_name=cfg.app_name,
        version=cfg.app_version,
        environment=cfg.environment,
    )
    yield
    await redis_client.aclose()
    logger.info("application shutting down")


def create_app(settings_override: Settings | None = None) -> FastAPI:
    cfg = settings_override or settings
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        lifespan=lifespan,
    )
    app.state.settings = cfg

    def get_redis() -> Redis:
        redis: Redis = app.state.redis
        return redis

    # Middleware registered innermost-first; Starlette makes last-registered the outermost.
    # Execution order on inbound: logging → auth → rate_limit → request_id → route handler
    app.middleware("http")(request_id_dispatch)
    app.middleware("http")(create_rate_limit_dispatch(cfg, get_redis))
    app.middleware("http")(create_auth_dispatch(cfg))
    app.middleware("http")(logging_dispatch)
    return app


app = create_app()

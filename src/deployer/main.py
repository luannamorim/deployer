from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from redis.asyncio import Redis

from deployer.api.router import api_router
from deployer.config import Settings, settings
from deployer.llm.providers.anthropic import AnthropicProvider
from deployer.llm.providers.openai import OpenAIProvider
from deployer.middleware.auth import create_auth_dispatch
from deployer.middleware.logging import logging_dispatch
from deployer.middleware.rate_limit import create_rate_limit_dispatch
from deployer.middleware.request_id import request_id_dispatch
from deployer.observability.logger import configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from deployer.llm.providers.base import LLMProvider

logger = get_logger(__name__)


def build_provider(cfg: Settings) -> LLMProvider:
    """Instantiate the configured LLM provider."""
    if cfg.llm_provider == "anthropic":
        return AnthropicProvider(api_key=cfg.anthropic_api_key, timeout=cfg.request_timeout)
    return OpenAIProvider(api_key=cfg.openai_api_key, timeout=cfg.request_timeout)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg: Settings = app.state.settings
    configure_logging(cfg.log_level)
    if not getattr(app.state, "redis", None):
        redis_client: Redis = Redis.from_url(cfg.redis_url, decode_responses=True)
        app.state.redis = redis_client
    else:
        redis_client = app.state.redis
    if not getattr(app.state, "provider", None):
        app.state.provider = build_provider(cfg)
    app.state.start_time = time.time()
    logger.info(
        "application starting",
        app_name=cfg.app_name,
        version=cfg.app_version,
        environment=cfg.environment,
    )
    yield
    await redis_client.aclose()
    provider: LLMProvider | None = getattr(app.state, "provider", None)
    if provider is not None:
        await provider.close()
    logger.info("application shutting down")


def create_app(
    settings_override: Settings | None = None,
    provider_override: LLMProvider | None = None,
) -> FastAPI:
    cfg = settings_override or settings
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        lifespan=lifespan,
    )
    app.state.settings = cfg
    if provider_override is not None:
        app.state.provider = provider_override

    def get_redis() -> Redis:
        redis: Redis = app.state.redis
        return redis

    # Middleware registered innermost-first; Starlette makes last-registered the outermost.
    # Execution order on inbound: logging → auth → rate_limit → request_id → route handler
    app.middleware("http")(request_id_dispatch)
    app.middleware("http")(create_rate_limit_dispatch(cfg, get_redis))
    app.middleware("http")(create_auth_dispatch(cfg))
    app.middleware("http")(logging_dispatch)

    app.include_router(api_router)
    return app


app = create_app()

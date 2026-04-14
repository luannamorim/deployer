"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from deployer.config import Settings
    from deployer.llm.providers.base import LLMProvider


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def get_provider(request: Request) -> LLMProvider:
    provider: LLMProvider | None = getattr(request.app.state, "provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="LLM provider is not configured")
    return provider

from __future__ import annotations

from typing import TYPE_CHECKING

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from deployer.config import Settings
from deployer.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from redis.asyncio import Redis


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing: auth enabled, 5 req/min limit, known API keys."""
    return Settings(
        api_keys=["test-key-1234", "other-key-5678"],
        require_auth=True,
        rate_limit_requests=5,
        rate_limit_window_seconds=60,
        redis_url="redis://localhost:6379/0",
        log_level="WARNING",
    )


@pytest.fixture
async def fake_redis() -> AsyncGenerator[Redis, None]:
    """Async in-memory fakeredis client for unit tests."""
    server = fakeredis.FakeServer()
    client: Redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def app_client(
    test_settings: Settings, fake_redis: Redis
) -> AsyncGenerator[AsyncClient, None]:
    """Full FastAPI app AsyncClient with fakeredis injected for integration tests."""
    app = create_app(settings_override=test_settings)
    app.state.redis = fake_redis

    @app.get("/test")
    async def test_route() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

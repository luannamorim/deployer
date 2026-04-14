from __future__ import annotations

from typing import TYPE_CHECKING

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from deployer.config import Settings
from deployer.llm.providers.base import (
    CompletionRequest,
    LLMProvider,
    LLMResponse,
    StreamChunk,
)
from deployer.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from redis.asyncio import Redis


class MockLLMProvider(LLMProvider):
    """In-memory LLM provider for tests. Returns canned responses."""

    def __init__(
        self,
        reply: str = "Hello from mock!",
        chunks: list[str] | None = None,
        prompt_tokens: int = 10,
        completion_tokens: int = 5,
        healthy: bool = True,
    ) -> None:
        self.reply = reply
        self.chunks = chunks or ["Hello ", "from ", "mock!"]
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.healthy = healthy
        self.calls: list[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(
            id="mock_id_123",
            model=request.model,
            content=self.reply,
            finish_reason="stop",
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.calls.append(request)
        for piece in self.chunks:
            yield StreamChunk(content=piece)
        yield StreamChunk(
            finish_reason="stop",
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )

    async def check_health(self) -> bool:
        return self.healthy

    async def close(self) -> None:
        return None


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
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
async def app_client(
    test_settings: Settings, fake_redis: Redis, mock_provider: MockLLMProvider
) -> AsyncGenerator[AsyncClient, None]:
    """Full FastAPI app AsyncClient with fakeredis and mock provider injected."""
    app = create_app(settings_override=test_settings, provider_override=mock_provider)
    app.state.redis = fake_redis

    @app.get("/test")
    async def test_route() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

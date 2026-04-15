"""Unit tests for the LLM response cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deployer.llm.cache import CACHE_PREFIX, ResponseCache, make_cache_key
from deployer.llm.providers.base import CompletionRequest, LLMResponse, Message

if TYPE_CHECKING:
    from redis.asyncio import Redis


def _request(**overrides: object) -> CompletionRequest:
    defaults: dict[str, object] = {
        "model": "gpt-4o-mini",
        "messages": [Message(role="user", content="Hello")],
        "temperature": 0.7,
    }
    defaults.update(overrides)
    return CompletionRequest(**defaults)  # type: ignore[arg-type]


def _response() -> LLMResponse:
    return LLMResponse(
        id="resp_1",
        model="gpt-4o-mini",
        content="Hi there",
        finish_reason="stop",
        prompt_tokens=3,
        completion_tokens=2,
    )


class TestMakeCacheKey:
    def test_key_is_deterministic(self) -> None:
        assert make_cache_key(_request()) == make_cache_key(_request())

    def test_key_has_prefix(self) -> None:
        assert make_cache_key(_request()).startswith(CACHE_PREFIX)

    def test_different_models_yield_different_keys(self) -> None:
        assert make_cache_key(_request(model="a")) != make_cache_key(_request(model="b"))

    def test_different_temperature_yields_different_keys(self) -> None:
        a = make_cache_key(_request(temperature=0.1))
        b = make_cache_key(_request(temperature=0.2))
        assert a != b

    def test_different_messages_yield_different_keys(self) -> None:
        a = make_cache_key(_request(messages=[Message(role="user", content="one")]))
        b = make_cache_key(_request(messages=[Message(role="user", content="two")]))
        assert a != b


@pytest.mark.asyncio
class TestResponseCache:
    async def test_miss_returns_none(self, fake_redis: Redis) -> None:
        cache = ResponseCache(fake_redis, ttl_seconds=60)
        assert await cache.get(_request()) is None

    async def test_set_then_get_roundtrips(self, fake_redis: Redis) -> None:
        cache = ResponseCache(fake_redis, ttl_seconds=60)
        request = _request()
        response = _response()
        await cache.set(request, response)
        got = await cache.get(request)
        assert got == response

    async def test_different_requests_isolated(self, fake_redis: Redis) -> None:
        cache = ResponseCache(fake_redis, ttl_seconds=60)
        await cache.set(_request(model="a"), _response())
        assert await cache.get(_request(model="b")) is None

    async def test_ttl_applied(self, fake_redis: Redis) -> None:
        cache = ResponseCache(fake_redis, ttl_seconds=42)
        request = _request()
        await cache.set(request, _response())
        ttl = await fake_redis.ttl(make_cache_key(request))
        assert 0 < ttl <= 42

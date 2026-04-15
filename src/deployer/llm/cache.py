"""Response cache for LLM completions, backed by Redis.

Cache key is a SHA-256 hash of (model, messages, temperature) so identical
requests return cached responses and never hit the provider.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from deployer.llm.providers.base import LLMResponse

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from deployer.llm.providers.base import CompletionRequest

CACHE_PREFIX = "llm_cache:"


def make_cache_key(request: CompletionRequest) -> str:
    """Return a deterministic SHA-256 cache key for the request."""
    payload = {
        "model": request.model,
        "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        "prompt": request.prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{CACHE_PREFIX}{digest}"


class ResponseCache:
    """Redis-backed cache for LLM responses."""

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, request: CompletionRequest) -> LLMResponse | None:
        raw = await self._redis.get(make_cache_key(request))
        if raw is None:
            return None
        data = json.loads(raw)
        return LLMResponse(**data)

    async def set(self, request: CompletionRequest, response: LLMResponse) -> None:
        key = make_cache_key(request)
        value = json.dumps(asdict(response))
        await self._redis.set(key, value, ex=self._ttl)

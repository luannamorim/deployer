"""Response cache for LLM completions, backed by Redis.

Cache key is a SHA-256 hash of (model, messages, temperature) so identical
requests return cached responses and never hit the provider.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from deployer.llm.providers.base import LLMResponse

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from deployer.llm.providers.base import CompletionRequest

CACHE_PREFIX = "llm_cache:"

_log = logging.getLogger(__name__)


def make_cache_key(request: CompletionRequest) -> str:
    """Return a deterministic SHA-256 cache key for the request."""
    payload = {
        "model": request.model,
        "messages": [asdict(m) for m in request.messages],
        "prompt": request.prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"{CACHE_PREFIX}{digest}"


class ResponseCache:
    """Redis-backed cache for LLM responses."""

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, request: CompletionRequest) -> LLMResponse | None:
        try:
            raw = await self._redis.get(make_cache_key(request))
        except Exception:
            _log.warning("cache get failed", exc_info=True)
            return None
        if raw is None:
            return None
        return LLMResponse(**json.loads(raw))

    async def set(self, request: CompletionRequest, response: LLMResponse) -> None:
        try:
            value = json.dumps(asdict(response))
            await self._redis.set(make_cache_key(request), value, ex=self._ttl)
        except Exception:
            _log.warning("cache set failed", exc_info=True)

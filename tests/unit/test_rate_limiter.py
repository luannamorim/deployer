"""Unit tests for the sliding window rate limiter using fakeredis."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from deployer.middleware.rate_limit import check_rate_limit

if TYPE_CHECKING:
    from redis.asyncio import Redis


class TestCheckRateLimit:
    async def test_allows_requests_under_limit(self, fake_redis: Redis) -> None:
        for _ in range(4):
            result = await check_rate_limit(
                fake_redis, "rate_limit:user1", limit=5, window_seconds=60
            )
            assert result is True

    async def test_allows_exactly_at_limit(self, fake_redis: Redis) -> None:
        # 5 requests should all be allowed (count goes 0→1→2→3→4, each < 5)
        for _ in range(5):
            result = await check_rate_limit(
                fake_redis, "rate_limit:user2", limit=5, window_seconds=60
            )
            assert result is True

    async def test_blocks_when_limit_exceeded(self, fake_redis: Redis) -> None:
        for _ in range(5):
            await check_rate_limit(fake_redis, "rate_limit:user3", limit=5, window_seconds=60)
        result = await check_rate_limit(fake_redis, "rate_limit:user3", limit=5, window_seconds=60)
        assert result is False

    async def test_different_keys_are_independent(self, fake_redis: Redis) -> None:
        for _ in range(5):
            await check_rate_limit(fake_redis, "rate_limit:user_a", limit=5, window_seconds=60)
        # user_b should be unaffected by user_a's limit
        result = await check_rate_limit(fake_redis, "rate_limit:user_b", limit=5, window_seconds=60)
        assert result is True

    async def test_expired_entries_do_not_count(self, fake_redis: Redis) -> None:
        """Entries older than the window should be pruned and not count against the limit."""
        old_time = time.time() - 120  # 2 minutes ago, outside the 60s window
        for i in range(10):
            await fake_redis.zadd("rate_limit:user5", {f"old_{i}": old_time + i * 0.001})
        # All old entries should be removed; new request should be allowed
        result = await check_rate_limit(fake_redis, "rate_limit:user5", limit=5, window_seconds=60)
        assert result is True

    async def test_returns_false_with_zero_limit(self, fake_redis: Redis) -> None:
        result = await check_rate_limit(fake_redis, "rate_limit:zero", limit=0, window_seconds=60)
        assert result is False

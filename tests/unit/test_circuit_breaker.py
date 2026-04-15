"""Unit tests for the circuit breaker."""

from __future__ import annotations

import asyncio

import pytest

from deployer.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
)

pytestmark = pytest.mark.asyncio


class _Boom(Exception):
    pass


async def _ok() -> str:
    return "ok"


async def _fail() -> None:
    raise _Boom


class TestCircuitBreaker:
    async def test_starts_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=1)
        assert cb.state is CircuitState.CLOSED

    async def test_successful_call_passes_result(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=1)
        assert await cb.call(_ok) == "ok"
        assert cb.state is CircuitState.CLOSED

    async def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=1)
        for _ in range(3):
            with pytest.raises(_Boom):
                await cb.call(_fail)
        assert cb.state is CircuitState.OPEN

    async def test_rejects_while_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=10)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(_ok)

    async def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=1)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        await cb.call(_ok)
        # Two more failures should not trip because counter reset
        with pytest.raises(_Boom):
            await cb.call(_fail)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        assert cb.state is CircuitState.CLOSED

    async def test_allows_probe_after_recovery(self) -> None:
        # After recovery elapses, the next call is allowed through (not rejected
        # with CircuitBreakerOpen) — the transition to HALF_OPEN happens inside call().
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.02)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        assert cb.state is CircuitState.OPEN
        await asyncio.sleep(0.05)
        # Would raise CircuitBreakerOpen if still open; raises _Boom instead = probe allowed
        with pytest.raises(_Boom):
            await cb.call(_fail)

    async def test_successful_probe_closes_breaker(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.02)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        await asyncio.sleep(0.05)
        assert await cb.call(_ok) == "ok"
        assert cb.state is CircuitState.CLOSED

    async def test_failed_probe_reopens_breaker(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=0.02)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        await asyncio.sleep(0.05)
        with pytest.raises(_Boom):
            await cb.call(_fail)
        assert cb.state is CircuitState.OPEN

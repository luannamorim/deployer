"""Circuit breaker to short-circuit calls to a failing LLM provider.

States:
- CLOSED: calls pass through. Failures increment a counter; once >= threshold,
  the breaker opens.
- OPEN: calls fail fast with CircuitBreakerOpen until recovery_seconds elapses,
  then transitions to HALF_OPEN.
- HALF_OPEN: a single probe call is allowed. Success resets to CLOSED;
  failure re-opens the breaker.
"""

from __future__ import annotations

import enum
import time
from typing import TYPE_CHECKING, ParamSpec, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

P = ParamSpec("P")
T = TypeVar("T")


class CircuitBreakerOpen(Exception):
    """Raised when a call is rejected because the breaker is open."""


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Tracks failures and trips when a threshold is exceeded."""

    def __init__(self, failure_threshold: int, recovery_seconds: float) -> None:
        self._threshold = failure_threshold
        self._recovery = recovery_seconds
        self._failures = 0
        self._opened_at: float | None = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[P, Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> T:
        """Invoke ``func`` guarded by the breaker."""
        if self._state is CircuitState.OPEN:
            if self._opened_at is not None and time.monotonic() - self._opened_at >= self._recovery:
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpen("circuit breaker is open")
        try:
            result = await func(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failures += 1
        if self._state is CircuitState.HALF_OPEN or self._failures >= self._threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

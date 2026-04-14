"""Abstract base class for LLM provider implementations."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class Message:
    """A single chat message."""

    role: str
    content: str


@dataclass
class LLMResponse:
    """Unified response from any LLM provider (non-streaming)."""

    id: str
    model: str
    content: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class StreamChunk:
    """A single chunk from a streaming LLM response."""

    content: str = ""
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass
class CompletionRequest:
    """Parameters for a completion request to an LLM provider."""

    model: str
    messages: list[Message] = field(default_factory=list)
    prompt: str = ""
    temperature: float = 1.0
    max_tokens: int | None = None
    stream: bool = False


class LLMProvider(abc.ABC):
    """Abstract interface for LLM providers.

    All providers implement ``complete`` for non-streaming and
    ``stream`` for streaming token-by-token delivery.
    """

    @abc.abstractmethod
    async def complete(self, request: CompletionRequest) -> LLMResponse:
        """Send a completion request and return the full response."""

    @abc.abstractmethod
    def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Send a completion request and yield streaming chunks."""

    @abc.abstractmethod
    async def check_health(self) -> bool:
        """Return True if the provider is reachable and healthy."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release any resources held by the provider (HTTP clients, etc.)."""

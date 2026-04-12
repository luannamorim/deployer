"""Anthropic provider implementation using direct httpx calls."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

import httpx

from deployer.llm.providers.base import LLMProvider, LLMResponse, StreamChunk

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from deployer.llm.providers.base import CompletionRequest


_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic API."""

    def __init__(self, api_key: str, timeout: int = 60) -> None:
        self._client = httpx.AsyncClient(
            headers={
                "x-api-key": api_key,
                "anthropic-version": _API_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        """Convert a CompletionRequest to Anthropic API payload."""
        messages: list[dict[str, str]] = []
        system: str = ""

        for msg in request.messages:
            if msg.role == "system":
                system = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        if request.prompt and not messages:
            messages = [{"role": "user", "content": request.prompt}]

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1024,
        }
        if system:
            payload["system"] = system
        return payload

    async def complete(self, request: CompletionRequest) -> LLMResponse:
        payload = self._build_payload(request)
        response = await self._client.post(_MESSAGES_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["content"][0]["text"] if data.get("content") else ""
        usage = data.get("usage", {})
        return LLMResponse(
            id=data.get("id", uuid.uuid4().hex),
            model=data.get("model", request.model),
            content=content,
            finish_reason=data.get("stop_reason", "end_turn"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request)
        payload["stream"] = True
        prompt_tokens = 0
        completion_tokens = 0

        async with self._client.stream("POST", _MESSAGES_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: ") :]
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type", "")

                if event_type == "message_start":
                    usage = data.get("message", {}).get("usage", {})
                    prompt_tokens = usage.get("input_tokens", 0)

                elif event_type == "content_block_delta":
                    delta = data.get("delta", {})
                    yield StreamChunk(content=delta.get("text", ""))

                elif event_type == "message_delta":
                    usage = data.get("usage", {})
                    completion_tokens = usage.get("output_tokens", 0)
                    finish_reason = data.get("delta", {}).get("stop_reason", "end_turn")
                    yield StreamChunk(
                        finish_reason=finish_reason,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )

    async def check_health(self) -> bool:
        try:
            # Minimal valid request to verify API connectivity
            payload = {
                "model": "claude-haiku-4-5-20251001",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }
            response = await self._client.post(_MESSAGES_URL, json=payload, timeout=5)
            return response.status_code in {200, 400, 401, 403}
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()

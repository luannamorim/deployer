"""OpenAI provider implementation using direct httpx calls."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

import httpx

from deployer.llm.providers.base import LLMProvider, LLMResponse, StreamChunk

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from deployer.llm.providers.base import CompletionRequest


_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self, api_key: str, timeout: int = 60) -> None:
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        if request.prompt and not messages:
            messages = [{"role": "user", "content": request.prompt}]
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": request.stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    async def complete(self, request: CompletionRequest) -> LLMResponse:
        payload = self._build_payload(request)
        payload["stream"] = False
        response = await self._client.post(_CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            id=data.get("id", uuid.uuid4().hex),
            model=data.get("model", request.model),
            content=choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        async with self._client.stream("POST", _CHAT_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: ") :]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choice = data["choices"][0] if data.get("choices") else {}
                delta = choice.get("delta", {})
                usage = data.get("usage") or {}
                yield StreamChunk(
                    content=delta.get("content") or "",
                    finish_reason=choice.get("finish_reason"),
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                )

    async def check_health(self) -> bool:
        try:
            response = await self._client.get(
                "https://api.openai.com/v1/models",
                timeout=5,
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()

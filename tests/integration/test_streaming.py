"""Integration tests for SSE streaming — /v1/chat/completions and /v1/completions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _parse_sse(raw: str) -> list[dict[str, object]]:
    """Parse raw SSE text into a list of data payloads (skips [DONE])."""
    events = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            if payload == "[DONE]":
                continue
            events.append(json.loads(payload))
    return events


class TestChatCompletionsStreaming:
    async def test_streaming_returns_200(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_all_chunks_start_with_data_prefix(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        for line in response.text.splitlines():
            if line:
                assert line.startswith("data: "), f"Unexpected line: {line!r}"

    async def test_stream_ends_with_done(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        data_lines = [line for line in response.text.splitlines() if line.startswith("data: ")]
        assert data_lines[-1] == "data: [DONE]"

    async def test_content_chunks_contain_delta(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        events = _parse_sse(response.text)
        content_events = [e for e in events if e["choices"][0]["delta"].get("content")]  # type: ignore[index]
        assert len(content_events) > 0
        combined = "".join(
            e["choices"][0]["delta"]["content"]  # type: ignore[index]
            for e in content_events
        )
        assert combined == "Hello from mock!"

    async def test_final_chunk_contains_usage(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        events = _parse_sse(response.text)
        # Final event before [DONE] has finish_reason and usage
        final = events[-1]
        assert final["choices"][0]["finish_reason"] == "stop"  # type: ignore[index]
        usage = final["usage"]  # type: ignore[index]
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["total_tokens"] == 15
        assert "estimated_cost_usd" in usage

    async def test_all_data_lines_are_valid_json(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        for line in response.text.splitlines():
            if line.startswith("data: ") and line != "data: [DONE]":
                json.loads(line[len("data: ") :])  # must not raise

    async def test_streaming_missing_auth_returns_401(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        assert response.status_code == 401


class TestCompletionsStreaming:
    async def test_streaming_returns_200(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "prompt": "Hello", "stream": True},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_content_chunks_use_text_field(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "prompt": "Hello", "stream": True},
        )
        events = _parse_sse(response.text)
        content_events = [e for e in events if e["choices"][0].get("text")]  # type: ignore[index]
        assert len(content_events) > 0
        combined = "".join(e["choices"][0]["text"] for e in content_events)  # type: ignore[index]
        assert combined == "Hello from mock!"

    async def test_stream_ends_with_done(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "prompt": "Hello", "stream": True},
        )
        data_lines = [line for line in response.text.splitlines() if line.startswith("data: ")]
        assert data_lines[-1] == "data: [DONE]"

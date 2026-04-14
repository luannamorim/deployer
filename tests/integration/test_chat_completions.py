"""Integration tests for POST /v1/chat/completions (non-streaming, mock provider)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from tests.conftest import MockLLMProvider

pytestmark = pytest.mark.asyncio


class TestChatCompletionsNonStreaming:
    async def test_returns_200_with_valid_response(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["model"] == "gpt-4o-mini"
        assert len(body["choices"]) == 1
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"] == "Hello from mock!"
        assert body["choices"][0]["finish_reason"] == "stop"

    async def test_usage_fields_populated(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 200
        usage = response.json()["usage"]
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["total_tokens"] == 15
        assert "estimated_cost_usd" in usage
        assert usage["estimated_cost_usd"] >= 0.0

    async def test_provider_received_correct_request(
        self, app_client: AsyncClient, mock_provider: MockLLMProvider
    ) -> None:
        await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Test message"}],
            },
        )
        assert len(mock_provider.calls) == 1
        req = mock_provider.calls[0]
        assert req.model == "gpt-4o-mini"
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"
        assert req.messages[0].content == "Test message"

    async def test_multi_turn_messages_forwarded(
        self, app_client: AsyncClient, mock_provider: MockLLMProvider
    ) -> None:
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "messages": messages},
        )
        assert response.status_code == 200
        req = mock_provider.calls[0]
        assert len(req.messages) == 3
        assert req.messages[2].content == "How are you?"

    async def test_missing_api_key_returns_401(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 401

    async def test_invalid_api_key_returns_403(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "bad-key"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 403

    async def test_empty_messages_returns_422(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "messages": []},
        )
        assert response.status_code == 422

    async def test_missing_model_returns_422(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 422

    async def test_response_id_present(self, app_client: AsyncClient) -> None:
        response = await app_client.post(
            "/v1/chat/completions",
            headers={"X-API-Key": "test-key-1234"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 200
        assert response.json()["id"] == "mock_id_123"

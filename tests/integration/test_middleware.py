"""Integration tests for auth, rate limiting, and request ID middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestAuthMiddleware:
    async def test_missing_api_key_returns_401(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/test")
        assert response.status_code == 401
        assert "Missing" in response.json()["detail"]

    async def test_invalid_api_key_returns_403(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/test", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403
        assert "Invalid" in response.json()["detail"]

    async def test_valid_api_key_returns_200(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/test", headers={"X-API-Key": "test-key-1234"})
        assert response.status_code == 200

    async def test_health_path_bypasses_auth(self, app_client: AsyncClient) -> None:
        # /health has no route registered, so 404 — but it must NOT be 401/403
        response = await app_client.get("/health")
        assert response.status_code not in {401, 403}

    async def test_metrics_path_bypasses_auth(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/metrics")
        assert response.status_code not in {401, 403}


class TestRateLimitMiddleware:
    async def test_allows_requests_under_limit(self, app_client: AsyncClient) -> None:
        headers = {"X-API-Key": "test-key-1234"}
        for _ in range(5):
            response = await app_client.get("/test", headers=headers)
            assert response.status_code == 200

    async def test_returns_429_when_limit_exceeded(self, app_client: AsyncClient) -> None:
        headers = {"X-API-Key": "test-key-1234"}
        for _ in range(5):
            await app_client.get("/test", headers=headers)
        response = await app_client.get("/test", headers=headers)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "Rate limit" in response.json()["detail"]

    async def test_different_keys_have_separate_limits(self, app_client: AsyncClient) -> None:
        for _ in range(5):
            await app_client.get("/test", headers={"X-API-Key": "test-key-1234"})
        # A different valid key should still have its full quota
        response = await app_client.get("/test", headers={"X-API-Key": "other-key-5678"})
        assert response.status_code == 200


class TestRequestIdMiddleware:
    async def test_generates_request_id_header(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/test", headers={"X-API-Key": "test-key-1234"})
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    async def test_propagates_provided_request_id(self, app_client: AsyncClient) -> None:
        response = await app_client.get(
            "/test",
            headers={"X-API-Key": "test-key-1234", "X-Request-ID": "my-custom-id"},
        )
        assert response.headers["x-request-id"] == "my-custom-id"

    async def test_unique_ids_generated_per_request(self, app_client: AsyncClient) -> None:
        headers = {"X-API-Key": "test-key-1234"}
        r1 = await app_client.get("/test", headers=headers)
        r2 = await app_client.get("/test", headers=headers)
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

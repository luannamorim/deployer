"""Integration tests for GET /health and GET /health/ready endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    async def test_returns_200_when_healthy(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/health")
        assert response.status_code == 200

    async def test_status_is_healthy_with_redis_and_provider(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert body["status"] == "healthy"

    async def test_checks_redis_connected(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert body["checks"]["redis"] == "connected"

    async def test_checks_provider_reachable(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert body["checks"]["llm_provider"] == "reachable"

    async def test_uptime_seconds_present(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert "uptime_seconds" in body["checks"]
        assert body["checks"]["uptime_seconds"] >= 0

    async def test_version_field_present(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert "version" in body
        assert isinstance(body["version"], str)

    async def test_degraded_when_provider_unhealthy(
        self,
        test_settings: object,
        fake_redis: object,
    ) -> None:
        from httpx import ASGITransport, AsyncClient

        from deployer.main import create_app
        from tests.conftest import MockLLMProvider

        unhealthy_provider = MockLLMProvider(healthy=False)
        app = create_app(
            settings_override=test_settings,  # type: ignore[arg-type]
            provider_override=unhealthy_provider,
        )
        app.state.redis = fake_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            body = (await client.get("/health")).json()

        assert body["status"] == "degraded"
        assert body["checks"]["llm_provider"] == "unreachable"

    async def test_health_bypasses_auth(self, app_client: AsyncClient) -> None:
        """Health endpoint must be reachable without an API key."""
        response = await app_client.get("/health")
        assert response.status_code == 200

    async def test_response_structure(self, app_client: AsyncClient) -> None:
        body = (await app_client.get("/health")).json()
        assert set(body.keys()) >= {"status", "checks", "version"}
        assert set(body["checks"].keys()) >= {"redis", "llm_provider", "uptime_seconds"}


class TestHealthReadyEndpoint:
    async def test_returns_200_when_ready(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    async def test_returns_503_without_provider(
        self,
        test_settings: object,
        fake_redis: object,
    ) -> None:
        from httpx import ASGITransport, AsyncClient

        from deployer.main import create_app

        # No provider injected — app.state.provider will be None
        app = create_app(settings_override=test_settings)  # type: ignore[arg-type]
        app.state.redis = fake_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"

    async def test_ready_bypasses_auth(self, app_client: AsyncClient) -> None:
        """Readiness probe must be reachable without API key (used by Kubernetes)."""
        response = await app_client.get("/health/ready")
        assert response.status_code == 200

"""Integration tests for GET /metrics — Prometheus scrape endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestMetricsEndpoint:
    async def test_returns_200(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/metrics", headers={"X-API-Key": "test-key-1234"})
        assert response.status_code == 200

    async def test_content_type_is_prometheus(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/metrics", headers={"X-API-Key": "test-key-1234"})
        assert "text/plain" in response.headers["content-type"]

    async def test_body_contains_prometheus_exposition(self, app_client: AsyncClient) -> None:
        response = await app_client.get("/metrics", headers={"X-API-Key": "test-key-1234"})
        # Standard Prometheus exposition format starts with HELP/TYPE lines
        assert b"# HELP" in response.content
        assert b"# TYPE" in response.content

    async def test_bypasses_auth(self, app_client: AsyncClient) -> None:
        """Metrics endpoint is in BYPASS_PATHS — no API key required."""
        response = await app_client.get("/metrics")
        assert response.status_code == 200

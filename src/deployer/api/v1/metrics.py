"""GET /metrics — Prometheus exposition format scrape endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.concurrency import run_in_threadpool

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics() -> Response:
    content = await run_in_threadpool(generate_latest)
    return Response(content=content, media_type=CONTENT_TYPE_LATEST)

"""Aggregate router for all v1 API routes."""

from __future__ import annotations

from fastapi import APIRouter

from deployer.api.v1 import chat, completions, health, metrics

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(completions.router)
api_router.include_router(health.router)
api_router.include_router(metrics.router)

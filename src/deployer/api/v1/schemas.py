"""Pydantic request/response models for the v1 API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = 1.0
    max_tokens: int | None = None
    stream: bool = False


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    temperature: float = 1.0
    max_tokens: int | None = None
    stream: bool = False


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: list[ChatChoice]
    usage: Usage


class CompletionChoice(BaseModel):
    index: int
    text: str
    finish_reason: str


class CompletionResponse(BaseModel):
    id: str
    model: str
    choices: list[CompletionChoice]
    usage: Usage


class HealthCheck(BaseModel):
    redis: str
    llm_provider: str
    uptime_seconds: int


class HealthResponse(BaseModel):
    status: str
    checks: HealthCheck
    version: str

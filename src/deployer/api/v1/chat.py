"""POST /v1/chat/completions — OpenAI-compatible chat completion endpoint."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from deployer.api.v1.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Usage,
)
from deployer.dependencies import get_provider
from deployer.llm.cost_calculator import calculate_cost
from deployer.llm.providers.base import CompletionRequest as ProviderRequest
from deployer.llm.providers.base import LLMProvider
from deployer.llm.providers.base import Message as ProviderMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

router = APIRouter(prefix="/v1", tags=["chat"])

ProviderDep = Annotated[LLMProvider, Depends(get_provider)]


def _to_provider_request(payload: ChatCompletionRequest, stream: bool) -> ProviderRequest:
    return ProviderRequest(
        model=payload.model,
        messages=[ProviderMessage(role=m.role, content=m.content) for m in payload.messages],
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        stream=stream,
    )


async def _stream_chat(payload: ChatCompletionRequest, provider: LLMProvider) -> AsyncIterator[str]:
    """Generate OpenAI-compatible SSE events from a provider stream."""
    provider_request = _to_provider_request(payload, stream=True)
    prompt_tokens = 0
    completion_tokens = 0

    async for chunk in provider.stream(provider_request):
        if chunk.prompt_tokens is not None:
            prompt_tokens = chunk.prompt_tokens
        if chunk.completion_tokens is not None:
            completion_tokens = chunk.completion_tokens

        if chunk.content:
            data = {"choices": [{"delta": {"content": chunk.content}, "index": 0}]}
            yield f"data: {json.dumps(data)}\n\n"

        if chunk.finish_reason:
            cost = calculate_cost(payload.model, prompt_tokens, completion_tokens)
            final = {
                "choices": [{"delta": {}, "finish_reason": chunk.finish_reason, "index": 0}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "estimated_cost_usd": cost.total_cost_usd,
                },
            }
            yield f"data: {json.dumps(final)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    payload: ChatCompletionRequest,
    provider: ProviderDep,
) -> ChatCompletionResponse | StreamingResponse:
    if payload.stream:
        return StreamingResponse(
            _stream_chat(payload, provider),
            media_type="text/event-stream",
        )

    provider_request = _to_provider_request(payload, stream=False)
    result = await provider.complete(provider_request)

    cost = calculate_cost(result.model, result.prompt_tokens, result.completion_tokens)

    return ChatCompletionResponse(
        id=result.id,
        model=result.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=result.content),
                finish_reason=result.finish_reason,
            )
        ],
        usage=Usage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.prompt_tokens + result.completion_tokens,
            estimated_cost_usd=cost.total_cost_usd,
        ),
    )

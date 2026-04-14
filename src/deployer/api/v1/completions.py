"""POST /v1/completions — simple prompt-in, text-out endpoint."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from deployer.api.v1.schemas import (
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    Usage,
)
from deployer.dependencies import get_provider
from deployer.llm.cost_calculator import calculate_cost
from deployer.llm.providers.base import CompletionRequest as ProviderRequest
from deployer.llm.providers.base import LLMProvider
from deployer.llm.providers.base import Message as ProviderMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

router = APIRouter(prefix="/v1", tags=["completions"])

ProviderDep = Annotated[LLMProvider, Depends(get_provider)]


def _to_provider_request(payload: CompletionRequest, stream: bool) -> ProviderRequest:
    return ProviderRequest(
        model=payload.model,
        messages=[ProviderMessage(role="user", content=payload.prompt)],
        prompt=payload.prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        stream=stream,
    )


async def _stream_completion(
    payload: CompletionRequest, provider: LLMProvider
) -> AsyncIterator[str]:
    provider_request = _to_provider_request(payload, stream=True)
    prompt_tokens = 0
    completion_tokens = 0

    async for chunk in provider.stream(provider_request):
        if chunk.prompt_tokens:
            prompt_tokens = chunk.prompt_tokens
        if chunk.completion_tokens:
            completion_tokens = chunk.completion_tokens

        if chunk.content:
            data = {"choices": [{"text": chunk.content, "index": 0}]}
            yield f"data: {json.dumps(data)}\n\n"

        if chunk.finish_reason:
            cost = calculate_cost(payload.model, prompt_tokens, completion_tokens)
            final = {
                "choices": [{"text": "", "finish_reason": chunk.finish_reason, "index": 0}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "estimated_cost_usd": cost.total_cost_usd,
                },
            }
            yield f"data: {json.dumps(final)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/completions", response_model=CompletionResponse)
async def completions(
    payload: CompletionRequest,
    provider: ProviderDep,
) -> CompletionResponse | StreamingResponse:
    if payload.stream:
        return StreamingResponse(
            _stream_completion(payload, provider),
            media_type="text/event-stream",
        )

    provider_request = _to_provider_request(payload, stream=False)
    result = await provider.complete(provider_request)

    cost = calculate_cost(result.model, result.prompt_tokens, result.completion_tokens)

    return CompletionResponse(
        id=result.id,
        model=result.model,
        choices=[
            CompletionChoice(
                index=0,
                text=result.content,
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

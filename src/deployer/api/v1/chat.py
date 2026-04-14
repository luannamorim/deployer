"""POST /v1/chat/completions — OpenAI-compatible chat completion endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

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

router = APIRouter(prefix="/v1", tags=["chat"])

ProviderDep = Annotated[LLMProvider, Depends(get_provider)]


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    payload: ChatCompletionRequest,
    provider: ProviderDep,
) -> ChatCompletionResponse:
    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Streaming is not implemented yet",
        )

    provider_request = ProviderRequest(
        model=payload.model,
        messages=[ProviderMessage(role=m.role, content=m.content) for m in payload.messages],
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        stream=False,
    )
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

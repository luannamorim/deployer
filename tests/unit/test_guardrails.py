"""Unit tests for the guardrails pipeline."""

from __future__ import annotations

import pytest

from deployer.llm.guardrails import Guardrails, GuardrailViolation
from deployer.llm.providers.base import CompletionRequest, LLMResponse, Message

pytestmark = pytest.mark.asyncio


def _request(content: str = "Hello") -> CompletionRequest:
    return CompletionRequest(
        model="gpt-4o-mini",
        messages=[Message(role="user", content=content)],
    )


def _response(content: str = "Hi") -> LLMResponse:
    return LLMResponse(
        id="r",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        prompt_tokens=1,
        completion_tokens=1,
    )


class TestGuardrails:
    async def test_empty_pipeline_is_identity(self) -> None:
        g = Guardrails()
        req = _request()
        assert await g.apply_pre(req) is req
        resp = _response()
        assert await g.apply_post(resp) is resp

    async def test_pre_hook_can_mutate_request(self) -> None:
        async def redact(req: CompletionRequest) -> CompletionRequest:
            req.messages[0].content = "[redacted]"
            return req

        g = Guardrails(pre_hooks=[redact])
        result = await g.apply_pre(_request("secret"))
        assert result.messages[0].content == "[redacted]"

    async def test_post_hook_can_mutate_response(self) -> None:
        async def upper(resp: LLMResponse) -> LLMResponse:
            resp.content = resp.content.upper()
            return resp

        g = Guardrails(post_hooks=[upper])
        result = await g.apply_post(_response("hi"))
        assert result.content == "HI"

    async def test_hooks_run_in_order(self) -> None:
        order: list[str] = []

        async def first(req: CompletionRequest) -> CompletionRequest:
            order.append("first")
            return req

        async def second(req: CompletionRequest) -> CompletionRequest:
            order.append("second")
            return req

        g = Guardrails(pre_hooks=[first, second])
        await g.apply_pre(_request())
        assert order == ["first", "second"]

    async def test_register_pre_appends_hook(self) -> None:
        tag: list[str] = []

        async def hook(req: CompletionRequest) -> CompletionRequest:
            tag.append("ran")
            return req

        g = Guardrails()
        g.register_pre(hook)
        await g.apply_pre(_request())
        assert tag == ["ran"]

    async def test_register_post_appends_hook(self) -> None:
        tag: list[str] = []

        async def hook(resp: LLMResponse) -> LLMResponse:
            tag.append("ran")
            return resp

        g = Guardrails()
        g.register_post(hook)
        await g.apply_post(_response())
        assert tag == ["ran"]

    async def test_hook_can_raise_violation(self) -> None:
        async def reject(req: CompletionRequest) -> CompletionRequest:
            raise GuardrailViolation("nope")

        g = Guardrails(pre_hooks=[reject])
        with pytest.raises(GuardrailViolation):
            await g.apply_pre(_request())
